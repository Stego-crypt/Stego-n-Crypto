import numpy as np
import pywt
from PIL import Image
from rich.console import Console

console = Console()

# --- CONFIGURATION ---
DELIMITER = "#####" 
# Q-Factor: The "Step Size". 
# Higher = More Robust (survives IDWT), but slightly more visual noise.
# 5.0 is the "Sweet Spot" for Haar wavelets.
Q = 5.0 

def text_to_bits(text):
    return ''.join(format(ord(char), '08b') for char in text)

def bits_to_text(bits):
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        chars.append(chr(int(byte, 2)))
    return ''.join(chars)

def embed(image_path, payload_string, output_path):
    try:
        # 1. Prepare Payload
        full_payload = payload_string + DELIMITER
        bits = text_to_bits(full_payload)
        data_len = len(bits)
        
        # 2. Load Image & Process
        # We use YCbCr and embed in the BLUE channel (Cb) for invisibility
        original_img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = original_img.split()
        
        # Convert to arrays (float for DWT)
        cb_array = np.array(cb, dtype=float)

        # 3. Apply DWT
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        # 4. Embed using Quantization (QIM)
        # We target the vertical (LH) and horizontal (HL) bands
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        if data_len > (len(LH_flat) + len(HL_flat)):
            console.print(f"[bold red]❌ Error:[/bold red] Image too small for this payload!")
            return False

        bit_idx = 0
        
        # Helper to embed a bit into a coefficient
        def embed_in_coeff(val, bit):
            bit = int(bit)
            # Quantize the value to the nearest step
            v_quantized = round(val / Q)
            
            # Check parity (Even or Odd?)
            if v_quantized % 2 != bit:
                # If wrong parity, shift to the nearest neighbor with correct parity
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
        
        # Embed in HL (if still needed)
        for i in range(len(HL_flat)):
            if bit_idx < data_len:
                HL_flat[i] = embed_in_coeff(HL_flat[i], bits[bit_idx])
                bit_idx += 1

        # 5. Reconstruct (IDWT)
        LH = LH_flat.reshape(LH.shape)
        HL = HL_flat.reshape(HL.shape)
        
        new_coeffs = (LL, (LH, HL, HH))
        new_cb_array = pywt.idwt2(new_coeffs, 'haar')
        
        # 6. Save
        new_cb_array = np.clip(new_cb_array, 0, 255)
        new_cb = Image.fromarray(np.uint8(new_cb_array), mode='L')
        
        final_image = Image.merge('YCbCr', (y, new_cb, cr)).convert('RGB')
        final_image.save(output_path, "PNG")
        
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

        # 2. Extract Bits using Quantization
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        bits = []
        
        # Helper to extract bit
        def get_bit(val):
            return str(int(round(val / Q) % 2))

        # Read LH
        for val in LH_flat:
            bits.append(get_bit(val))
            
        # Read HL
        for val in HL_flat:
            bits.append(get_bit(val))

        # 3. Reconstruct & Find Delimiter
        binary_string = "".join(bits)
        chars = []
        
        for i in range(0, len(binary_string), 8):
            byte = binary_string[i:i+8]
            if len(byte) < 8: break
            
            # Safe conversion (ignore weird noise chars)
            try:
                char = chr(int(byte, 2))
                chars.append(char)
            except:
                continue
            
            # Check for delimiter (look back 5 chars)
            if len(chars) >= len(DELIMITER):
                tail = "".join(chars[-len(DELIMITER):])
                if tail == DELIMITER:
                    return "".join(chars[:-len(DELIMITER)])

        return None 

    except Exception as e:
        console.print(f"[bold red]❌ DWT Extraction Failed:[/bold red] {e}")
        return None