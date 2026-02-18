import os
import mimetypes
import hashlib
import imagehash
import re
from modules import crypto

try:
    from modules import stega_image
    from modules import stega_pdf
    from modules import stega_text
except ImportError:
    pass

HAMMING_THRESHOLD = 10 

def calculate_text_hash_without_sig(file_path):
    try:
        # 1. Open in strictly BINARY mode ("rb"). No encoding parameter allowed!
        with open(file_path, "rb") as f:
            content = f.read()
            
        # 2. Use a regex byte-string (b"...") to find the header.
        # \r?\n perfectly handles both Windows (\r\n) and Linux (\n) line endings.
        header_pattern = b"\r?\n\r?\n-----BEGIN OFFICIAL SIGNATURE-----\r?\n"
        
        # 3. Split the raw binary content
        split_content = re.split(header_pattern, content)
        
        # 4. Take the exact bytes before the signature block
        original_content = split_content[0]
        
        # --- NEWLINE AGNOSTIC HASHING ---
        # 1. Raw Hash (Exactly as received over the network)
        hash_raw = hashlib.sha256(original_content).hexdigest()
        
        # 2. Linux Hash (Force all formatting to \n)
        content_linux = original_content.replace(b"\r\n", b"\n")
        hash_linux = hashlib.sha256(content_linux).hexdigest()
        
        # 3. Windows Hash (Force all formatting to \r\n)
        content_windows = content_linux.replace(b"\n", b"\r\n")
        hash_windows = hashlib.sha256(content_windows).hexdigest()
        
        # Return a LIST of all possible valid hashes
        return [hash_raw, hash_linux, hash_windows]
        
    except Exception as e:
        print(f"Hash calculation error: {e}")
        return []

def analyze_file(file_path):
    """
    Core logic: Scans file -> Returns Dictionary with results.
    Used by both CLI (verify.py) and Web Server.
    """
    result = {
        "status": "error",           
        "message": "Unknown Error",
        "metadata": {
            "authority": "Unknown",
            "timestamp": "Unknown",
            "message": "None"
        },
        "checks": {
            "signature": False,
            "integrity": False
        },
        "details": ""
    }

    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type and file_path.lower().endswith('.txt'):
        mime_type = 'text/plain'

    extracted_string = None
    is_image = mime_type and mime_type.startswith('image')
    is_pdf = mime_type == 'application/pdf'
    is_text = mime_type == 'text/plain'

    
    if is_image: extracted_string = stega_image.extract(file_path)
    elif is_pdf: extracted_string = stega_pdf.extract(file_path)
    elif is_text: extracted_string = stega_text.extract(file_path)

    if not extracted_string:
        result["message"] = "No Signature Found"
        return result

  
    try:
        if "||SIG||" in extracted_string:
            raw_data, signature = extracted_string.split("||SIG||")
        else:
            # Smart Regex Fallback
            split_match = re.search(r"\|\|.{3}\|\|", extracted_string)
            if split_match:
                separator = split_match.group(0)
                raw_data, signature = extracted_string.split(separator)
            else:
                raise ValueError("Separator lost")

        original_hash_str, timestamp, auth_name, message = raw_data.split("|")
        
        
        result["metadata"] = {
            "authority": auth_name,
            "timestamp": timestamp,
            "message": message
        }

    except ValueError:
        result["message"] = "Malformed Payload"
        return result

 
    try:
        public_key = crypto.load_public_key(auth_name)
        if crypto.verify_signature(public_key, raw_data, signature):
            result["checks"]["signature"] = True
        else:
            result["message"] = "Invalid Cryptographic Signature"
            result["status"] = "fake"
            return result
    except FileNotFoundError:
        result["message"] = f"Unknown Authority: {auth_name}"
        return result
    except Exception as e:
        result["message"] = f"Crypto Error: {str(e)}"
        return result

    
    integrity_passed = False
    details_msg = ""

    if is_image:
        current_hash_str = crypto.generate_file_hash(file_path, is_image=True)
        try:
            h_orig = imagehash.hex_to_hash(original_hash_str)
            h_curr = imagehash.hex_to_hash(current_hash_str)
            distance = h_orig - h_curr
            if distance <= HAMMING_THRESHOLD:
                integrity_passed = True
                details_msg = f"Hamming Distance: {distance} (Pass)"
            else:
                details_msg = f"Hamming Distance: {distance} (Fail)"
        except:
            details_msg = "Hash Error"

    elif is_text:
        # Now returns a list of 3 possible hashes
        valid_hashes = calculate_text_hash_without_sig(file_path)
        
        # Check if the original signature matches ANY of our formatting hashes
        if original_hash_str in valid_hashes:
            integrity_passed = True
            details_msg = "Exact Match"
        else:
            details_msg = "Content Modified"
            
    else: 
        current_hash_str = crypto.generate_file_hash(file_path)
        if current_hash_str == original_hash_str:
            integrity_passed = True
            details_msg = "Content Stream Match"
        else:
            details_msg = "Content Tampered"

    result["checks"]["integrity"] = integrity_passed
    result["details"] = details_msg

    
    if result["checks"]["signature"] and result["checks"]["integrity"]:
        result["status"] = "verified"
        result["message"] = "File is Authentic"
    elif result["checks"]["signature"]:
        result["status"] = "tampered"
        result["message"] = "Signature valid, but content changed."
    else:
        result["status"] = "fake"
    
    return result