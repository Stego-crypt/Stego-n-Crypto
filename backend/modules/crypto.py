import os
import hashlib
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import imagehash
from PIL import Image


def _get_key_path(authority_name, key_type):

    safe_name = "".join([c if c.isalnum() else "_" for c in authority_name])
    return os.path.join("keys", f"{safe_name}_{key_type}.pem")

def load_private_key(authority_name):
 
    key_path = _get_key_path(authority_name, "private")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"Private key not found at {key_path}. "
            f"Please run 'python key_gen.py \"{authority_name}\"' first."
        )

    with open(key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
    return private_key

def load_public_key(authority_name):
  
    key_path = _get_key_path(authority_name, "public")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Public key not found at {key_path}.")

    with open(key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
    return public_key


def generate_file_hash(file_path, is_image=False):
 
    if is_image:
        try:
            img = Image.open(file_path)
            return str(imagehash.phash(img)) 
        except Exception as e:
            raise ValueError(f"Failed to generate pHash: {e}")
    else:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            raise ValueError(f"Failed to generate SHA-256: {e}")


def sign_payload(private_key, payload_string):
   
    payload_bytes = payload_string.encode('utf-8')

    signature = private_key.sign(
        payload_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return base64.b64encode(signature).decode('utf-8')

def verify_signature(public_key, payload_string, signature_base64):
    
    try:
        signature_bytes = base64.b64decode(signature_base64)
        payload_bytes = payload_string.encode('utf-8')

        public_key.verify(
            signature_bytes,
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True 
        
    except (InvalidSignature, ValueError, TypeError):
        return False 