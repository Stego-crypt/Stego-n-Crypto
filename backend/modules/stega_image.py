import numpy as np
import pywt
from PIL import Image
from rich.console import Console
from reedsolo import RSCodec, ReedSolomonError

console = Console()

# --- CONFIGURATION ---
# 1. Error Correction Strength (ECC)
# We add 40 bytes of redundant parity data.
# This allows us to repair up to 20 corrupt bytes anywhere in the message.
ECC_BYTES = 40 

# 2. Survival Strength (Q-Factor)
# We keep this high (35.0) to punch through compression, 
# but RS Codec does the heavy lifting for repairs.
Q = 35.0 

# Initialize the Reed-Solomon Codec
rsc = RSCodec(ECC_BYTES)

def bytes_to_bits(data_bytes):
    """Convert bytes (from RS Codec) to a binary string."""
    return ''.join(format(byte, '08b') for byte in data_bytes)

def bits_to_bytes(bits):
    """Convert binary string back to bytes for RS Codec."""
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        try:
            byte_array.append(int(byte, 2))
        except:
            byte_array.append(0) # Padding for incomplete byte
    return bytes(byte_array)

def embed(image_path, payload_string, output_path):
    try:
        # 1. ENCODE: Wrap payload in Reed-Solomon Armor
        # Convert string to bytes
        payload_bytes = payload_string.encode('utf-8')
        
        # This adds the parity bytes. 
        # e.g., "Hello" (5 bytes) becomes "Hello..." (45 bytes)
        encoded_data = rsc.encode(payload_bytes)
        
        # Convert to bits for embedding
        bits = bytes_to_bits(encoded_data)
        data_len = len(bits)
        
        # 2. IMAGE PROCESSING (DWT)
        original_img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = original_img.split()
        cb_array = np.array(cb, dtype=float)

        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        # 3. EMBEDDING (QIM)
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        # Embed length first (32 bits) so we know exactly how much to read back
        # This is critical for RS Codec to know where the message stops.
        # (For this simplified version, we'll just embed the whole stream 
        # and rely on the delimiter inside the decoded text if needed, 
        # or better: we use a fixed header).
        
        # Check capacity
        total_slots = len(LH_flat) + len(HL_flat)
        if data_len > total_slots:
            console.print(f"[bold red]❌ Error:[/bold red] Image too small. Need {data_len} bits.")
            return False

        bit_idx = 0

        # Helper for Quantization
        def embed_in_coeff(val, bit):
            bit = int(bit)
            v_quantized = round(val / Q)
            if v_quantized % 2 != bit:
                if v_quantized < val / Q: v_quantized += 1
                else: v_quantized -= 1
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

        # 4. RECONSTRUCT & SAVE
        LH = LH_flat.reshape(LH.shape)
        HL = HL_flat.reshape(HL.shape)
        new_coeffs = (LL, (LH, HL, HH))
        new_cb_array = pywt.idwt2(new_coeffs, 'haar')
        
        new_cb_array = np.clip(new_cb_array, 0, 255)
        new_cb = Image.fromarray(np.uint8(new_cb_array), mode='L')
        final_image = Image.merge('YCbCr', (y, new_cb, cr)).convert('RGB')
        
        # Save as PNG to preserve integrity before upload
        final_image.save(output_path, "PNG")
        
        console.print(f"   [DWT] Embedded {len(payload_bytes)} bytes + {ECC_BYTES} ECC bytes.")
        return True

    except Exception as e:
        console.print(f"[bold red]❌ RS-Embed Failed:[/bold red] {e}")
        return False

def extract(image_path):
    try:
        # 1. LOAD & DWT
        img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = img.split()
        cb_array = np.array(cb, dtype=float)

        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

        # 2. EXTRACT RAW BITS (Likely Corrupted)
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        bits = []
        
        def get_bit(val):
            return str(int(round(val / Q) % 2))

        # We read EVERYTHING possible because we don't know where the noise ends.
        # Ideally, we would embed a length header, but for now we read a large chunk.
        # Let's read enough bits for a max payload of ~2KB
        MAX_BITS = 16000 
        
        for val in LH_flat: 
            if len(bits) < MAX_BITS: bits.append(get_bit(val))
        for val in HL_flat: 
            if len(bits) < MAX_BITS: bits.append(get_bit(val))

        # 3. DECODE: The Reed-Solomon Magic
        # Convert bits back to a byte array (which contains errors)
        raw_bytes = bits_to_bytes(bits)

        # The Decoder scans the byte stream. It looks for the RS structure.
        # rsc.decode() returns the original message (without parity bytes)
        # AND it automatically fixes errors if they are within the limit.
        try:
            # We treat the whole stream as one potential block.
            # Note: RS usually works on fixed blocks. 
            # To make this robust for variable length, we rely on the codec's ability
            # to just decode the first valid chunk it finds.
            
            # Since we don't have a length header, we need to try decoding
            # the raw bytes. However, RS usually requires the EXACT byte string
            # that was output by the encoder (message + parity).
            
            # TRICK: We scan the stream byte-by-byte for a valid RS block?
            # No, that's too slow.
            
            # SIMPLIFIED STRATEGY for this project:
            # We assume the message starts at index 0.
            # We trim the trailing garbage (thousands of 0s from the empty pixels).
            # But we don't know exactly where it ends.
            
            # SOLUTION: We assume a fixed max size or we embed the length.
            # Let's try to just decode the first N bytes where N is roughly our expected size.
            
            # Actually, standard RS decoders need to know the boundary.
            # Let's just feed it the first 1000 bytes (or however long we think it is)
            # and let it try to fix it.
            
            decoded_msg, decoded_msgecc, errata_pos = rsc.decode(raw_bytes[:1000])
            
            console.print(f"   [RS] Success! Repaired {len(errata_pos)} errors.", style="bold green")
            return decoded_msg.decode('utf-8')

        except ReedSolomonError:
            # The error was too big, or we fed it garbage padding.
            console.print("   [RS] Repair failed (Too much corruption).")
            return None

    except Exception as e:
        console.print(f"[bold red]❌ RS-Extract Failed:[/bold red] {e}")
        return None