import numpy as np
import pywt
from PIL import Image
from rich.console import Console
from reedsolo import RSCodec, ReedSolomonError
import struct

console = Console()

# --- CONFIGURATION ---
# 1. ECC Strength: 
# 50 parity bytes allows us to correct up to 25 byte errors per block.
ECC_BYTES = 50 

# 2. Robustness (Q-Factor):
# Q=40.0 is aggressive enough to survive WhatsApp compression
# while RS takes care of the bit-flips.
Q = 40.0 

# Initialize Codec
rsc = RSCodec(ECC_BYTES)

def text_to_bits(text):
    return ''.join(format(ord(char), '08b') for char in text)

def int_to_bin_32(number):
    """Pack an integer into a 32-bit binary string (Fixed Header)."""
    return format(number, '032b')

def bin_to_int_32(binary_str):
    """Unpack a 32-bit binary string back to an integer."""
    return int(binary_str, 2)

def bits_to_bytes(bits):
    """Convert binary string to bytearray."""
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break # Ignore trailing fragments
        byte_array.append(int(byte, 2))
    return bytes(byte_array)

def bytes_to_bits(data_bytes):
    """Convert bytes to binary string."""
    return ''.join(format(byte, '08b') for byte in data_bytes)

def embed(image_path, payload_string, output_path):
    try:
        # 1. PREPARE PAYLOAD (Reed-Solomon Encode)
        payload_bytes = payload_string.encode('utf-8')
        encoded_payload = rsc.encode(payload_bytes)
        
        # 2. CREATE PACKET: [LENGTH_HEADER (4 bytes)] + [ENCODED_PAYLOAD]
        total_len = len(encoded_payload)
        header_bits = int_to_bin_32(total_len)
        payload_bits = bytes_to_bits(encoded_payload)
        
        full_bits = header_bits + payload_bits
        data_len = len(full_bits)

        # 3. LOAD IMAGE & FIX DIMENSIONS
        original_img = Image.open(image_path)
        
        # --- FIX: FORCE EVEN DIMENSIONS ---
        # DWT fails if dimensions are odd numbers. We resize to the nearest even number.
        width, height = original_img.size
        if width % 2 != 0 or height % 2 != 0:
            new_width = width - (width % 2)
            new_height = height - (height % 2)
            original_img = original_img.resize((new_width, new_height), Image.LANCZOS)
            # console.print(f"   [Auto-Fix] Resized image to {new_width}x{new_height} (Even dimensions required)")
        # ----------------------------------

        original_img = original_img.convert('YCbCr')
        y, cb, cr = original_img.split()
        cb_array = np.array(cb, dtype=float)

        # 4. DWT TRANSFORM
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs
        
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        if data_len > (len(LH_flat) + len(HL_flat)):
            console.print(f"[bold red]❌ Error:[/bold red] Image too small. Need {data_len} bits.")
            return False

        # 5. EMBEDDING (QIM)
        bit_idx = 0
        
        def embed_coeff(val, bit):
            bit = int(bit)
            v_quantized = round(val / Q)
            if v_quantized % 2 != bit:
                if v_quantized < val / Q: v_quantized += 1
                else: v_quantized -= 1
            return v_quantized * Q

        # Embed in LH
        for i in range(len(LH_flat)):
            if bit_idx < data_len:
                LH_flat[i] = embed_coeff(LH_flat[i], full_bits[bit_idx])
                bit_idx += 1
        
        # Embed in HL
        for i in range(len(HL_flat)):
            if bit_idx < data_len:
                HL_flat[i] = embed_coeff(HL_flat[i], full_bits[bit_idx])
                bit_idx += 1

        # 6. RECONSTRUCT & SAVE
        LH = LH_flat.reshape(LH.shape)
        HL = HL_flat.reshape(HL.shape)
        new_coeffs = (LL, (LH, HL, HH))
        
        # IDWT Reconstruct
        new_cb_array = pywt.idwt2(new_coeffs, 'haar')
        
        # --- FIX: CROP RECONSTRUCTION ---
        # IDWT might output a slightly larger array (e.g. 502px) than the original (500px)
        # We crop it to match the exact shape of the original Cb channel.
        if new_cb_array.shape != cb_array.shape:
             new_cb_array = new_cb_array[:cb_array.shape[0], :cb_array.shape[1]]
        # --------------------------------
        
        new_cb_array = np.clip(new_cb_array, 0, 255)
        new_cb = Image.fromarray(np.uint8(new_cb_array), mode='L')
        final_image = Image.merge('YCbCr', (y, new_cb, cr)).convert('RGB')
        
        final_image.save(output_path, "PNG")
        console.print(f"   [DWT] Embedded {len(payload_bytes)} bytes + {ECC_BYTES} ECC parity.")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ Embed Failed:[/bold red] {e}")
        return False

def extract(image_path):
    try:
        # 1. LOAD & DWT
        img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = img.split()
        cb_array = np.array(cb, dtype=float)
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        LH_flat = LH.flatten()
        HL_flat = HL.flatten()

        # 2. EXTRACT BITSTREAM
        bits = []
        
        def get_bit(val):
            return str(int(round(val / Q) % 2))

        # We need to read enough bits to at least get the Header (32 bits)
        # We read a large buffer first, then parse.
        BUFFER_SIZE = 15000 
        
        for val in LH_flat: 
            if len(bits) < BUFFER_SIZE: bits.append(get_bit(val))
        for val in HL_flat: 
            if len(bits) < BUFFER_SIZE: bits.append(get_bit(val))

        full_bit_stream = "".join(bits)

        # 3. PARSE HEADER (First 32 bits)
        header_bits = full_bit_stream[:32]
        payload_length_bytes = bin_to_int_32(header_bits)
        
        # Sanity Check: If length is 0 or astronomically huge, extraction failed (noise)
        if payload_length_bytes == 0 or payload_length_bytes > 5000:
            return None
        
        payload_length_bits = payload_length_bytes * 8
        
        # 4. EXTRACT BODY
        # We slice exactly the number of bits the header told us exists.
        start = 32
        end = 32 + payload_length_bits
        
        if end > len(full_bit_stream):
            return None
            
        payload_bits = full_bit_stream[start:end]
        raw_bytes = bits_to_bytes(payload_bits)

        # 5. REED-SOLOMON DECODE
        try:
            # This is the magic step. 
            decoded_msg, decoded_msgecc, errata_pos = rsc.decode(raw_bytes)
            
            # If successful, we return the clean string
            clean_text = decoded_msg.decode('utf-8')
            
            if len(errata_pos) > 0:
                console.print(f"   [RS] Fixed {len(errata_pos)} byte errors.", style="bold green")
            
            return clean_text

        except ReedSolomonError:
            return None
        except Exception:
            return None

    except Exception as e:
        console.print(f"[bold red]❌ Extract Failed:[/bold red] {e}")
        return None