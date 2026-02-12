import numpy as np
import pywt
from PIL import Image
from rich.console import Console
from collections import Counter

console = Console()

# --- CONFIGURATION ---
DELIMITER = "#####" 

# SURVIVAL CONFIGURATION
# Q=5.0 is invisible but fragile.
# Q=25.0 is visible (grainy) but survives WhatsApp.
Q = 25.0 

# REPETITION FACTOR
# We embed the payload this many times to survive corruption.
REPEATS = 3 

def text_to_bits(text):
    return ''.join(format(ord(char), '08b') for char in text)

def bits_to_text(bits):
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        try:
            chars.append(chr(int(byte, 2)))
        except:
            chars.append('?') # Corrupt char placeholder
    return ''.join(chars)

def embed(image_path, payload_string, output_path):
    try:
        # 1. Prepare Payload with Redundancy
        # Format: PAYLOAD ##### PAYLOAD ##### PAYLOAD #####
        full_payload = (payload_string + DELIMITER) * REPEATS
        bits = text_to_bits(full_payload)
        data_len = len(bits)
        
        # 2. Load Image & Process
        # We stick to YCbCr/Blue Channel.
        original_img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = original_img.split()
        cb_array = np.array(cb, dtype=float)

        # 3. Apply DWT
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        # 4. Embed (targeting LH and HL)
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        total_slots = len(LH_flat) + len(HL_flat)
        if data_len > total_slots:
            console.print(f"[bold red]❌ Error:[/bold red] Image too small for Survival Mode (Need {data_len} bits).")
            return False

        bit_idx = 0
        
        # Helper function for Robust QIM
        def embed_in_coeff(val, bit):
            bit = int(bit)
            # Quantize
            v_quantized = round(val / Q)
            
            # Force Parity
            if v_quantized % 2 != bit:
                if v_quantized < val / Q:
                    v_quantized += 1
                else:
                    v_quantized -= 1
            
            return v_quantized * Q

        # Embed in LH
        for i in range(len(LH_flat)):
            if bit_idx < data_len:
                LH_flat[i] = embed_in_coeff(LH_flat[i], bits[bit_idx])
                bit_idx += 1
        
        # Embed in HL
        for i in range(len(HL_flat)):
            if bit_idx < data_len:
                HL_flat[i] = embed_in_coeff(HL_flat[i], bits[bit_idx])
                bit_idx += 1

        # 5. Reconstruct
        LH = LH_flat.reshape(LH.shape)
        HL = HL_flat.reshape(HL.shape)
        new_coeffs = (LL, (LH, HL, HH))
        new_cb_array = pywt.idwt2(new_coeffs, 'haar')
        
        # 6. Save (Still as PNG to preserve our strength before upload)
        new_cb_array = np.clip(new_cb_array, 0, 255)
        new_cb = Image.fromarray(np.uint8(new_cb_array), mode='L')
        final_image = Image.merge('YCbCr', (y, new_cb, cr)).convert('RGB')
        final_image.save(output_path, "PNG")
        
        console.print(f"   [DWT] Embedded with Q={Q} and {REPEATS}x Redundancy.")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ DWT Embedding Failed:[/bold red] {e}")
        return False

def extract(image_path):
    try:
        # 1. Load & Transform
        img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = img.split()
        cb_array = np.array(cb, dtype=float)

        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        # 2. Extract Bits
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        bits = []
        
        def get_bit(val):
            return str(int(round(val / Q) % 2))

        for val in LH_flat: bits.append(get_bit(val))
        for val in HL_flat: bits.append(get_bit(val))

        # 3. Reconstruct & Voting Logic
        # We extracted a massive string. It contains multiple copies.
        # We need to find ONE valid copy.
        binary_string = "".join(bits)
        chars = []
        
        # Stream decode
        raw_text = ""
        for i in range(0, len(binary_string), 8):
            byte = binary_string[i:i+8]
            if len(byte) < 8: break
            try:
                char = chr(int(byte, 2))
                raw_text += char
            except:
                raw_text += "?"

        # 4. Search for Delimiters
        # The text might look like: "Data#####Data#####Da?a#####"
        parts = raw_text.split(DELIMITER)
        
        # Filter out empty strings and garbage
        valid_candidates = [p for p in parts if len(p) > 10 and "|" in p]
        
        if not valid_candidates:
            return None

        # 5. Majority Vote (Optional) or just take the first valid one
        # For this project, if we find ANY valid-looking payload, we take it.
        # A valid payload must have the pipe structure: "Hash|Time|Auth|Msg"
        for candidate in valid_candidates:
            if candidate.count("|") >= 3: # Crude check for structure
                return candidate

        return None 

    except Exception as e:
        console.print(f"[bold red]❌ DWT Extraction Failed:[/bold red] {e}")
        return None