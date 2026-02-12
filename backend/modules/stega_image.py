import numpy as np
import pywt
from PIL import Image
from rich.console import Console

console = Console()


DELIMITER = "#####"  

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
    
        full_payload = payload_string + DELIMITER
        bits = text_to_bits(full_payload)
        data_len = len(bits)
        

        original_img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = original_img.split()
        
        
        cb_array = np.array(cb, dtype=float)

  
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs

   
        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        total_slots = len(LH_flat) + len(HL_flat)
        if data_len > total_slots:
            console.print(f"[bold red]Error:[/bold red] Image too small! Need {data_len} bits, have {total_slots}.")
            return False

        
        bit_idx = 0
        
    
        for i in range(len(LH_flat)):
            if bit_idx < data_len:
                val = int(LH_flat[i])
                # Clear the LSB and set it to our bit
                val = (val & ~1) | int(bits[bit_idx])
                LH_flat[i] = float(val)
                bit_idx += 1
        
       
        for i in range(len(HL_flat)):
            if bit_idx < data_len:
                val = int(HL_flat[i])
                val = (val & ~1) | int(bits[bit_idx])
                HL_flat[i] = float(val)
                bit_idx += 1

    
        LH = LH_flat.reshape(LH.shape)
        HL = HL_flat.reshape(HL.shape)
        
        new_coeffs = (LL, (LH, HL, HH))
        new_cb_array = pywt.idwt2(new_coeffs, 'haar')
        

        new_cb_array = np.clip(new_cb_array, 0, 255)
        new_cb = Image.fromarray(np.uint8(new_cb_array), mode='L')

   
        final_image = Image.merge('YCbCr', (y, new_cb, cr)).convert('RGB')
        final_image.save(output_path, "PNG")
        
        return True

    except Exception as e:
        console.print(f"[bold red]DWT Embedding Failed:[/bold red] {e}")
        return False

def extract(image_path):

    try:
       
        img = Image.open(image_path).convert('YCbCr')
        y, cb, cr = img.split()
        cb_array = np.array(cb, dtype=float)

       
        coeffs = pywt.dwt2(cb_array, 'haar')
        LL, (LH, HL, HH) = coeffs


        LH_flat = LH.flatten()
        HL_flat = HL.flatten()
        
        bits = []
        
        
        for val in LH_flat:
            bits.append(str(int(val) & 1))
            
      
        for val in HL_flat:
            bits.append(str(int(val) & 1))


        binary_string = "".join(bits)
        chars = []
        
        for i in range(0, len(binary_string), 8):
            byte = binary_string[i:i+8]
            if len(byte) < 8: break
            
            char = chr(int(byte, 2))
            chars.append(char)
            
          
            if len(chars) >= len(DELIMITER):
             
                tail = "".join(chars[-len(DELIMITER):])
                if tail == DELIMITER:
                   
                    return "".join(chars[:-len(DELIMITER)])

        
        return None 

    except Exception as e:
        console.print(f"[bold red]DWT Extraction Failed:[/bold red] {e}")
        return None