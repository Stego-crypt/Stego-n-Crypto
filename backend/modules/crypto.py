import os
import hashlib
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import imagehash
from PIL import Image
from pypdf import PdfReader # Ensure pypdf is installed: pip install pypdf

# --- KEY MANAGEMENT ---

def _get_key_path(authority_name, key_type):
    """Helper to construct sanitized key paths."""
    safe_name = "".join([c if c.isalnum() else "_" for c in authority_name])
    return os.path.join("keys", f"{safe_name}_{key_type}.pem")

def load_private_key(authority_name):
    """Loads the Private Key for signing."""
    key_path = _get_key_path(authority_name, "private")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Private key not found at {key_path}. Run key_gen.py first.")

    with open(key_path, "rb") as key_file:
        return serialization.load_pem_private_key(key_file.read(), password=None)

def load_public_key(authority_name):
    """Loads the Public Key for verification."""
    key_path = _get_key_path(authority_name, "public")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Public key not found at {key_path}.")

    with open(key_path, "rb") as key_file:
        return serialization.load_pem_public_key(key_file.read())

# --- HASHING (UPDATED FOR SEMANTIC INTEGRITY) ---

def generate_file_hash(file_path, is_image=False):
    """
    Generates a hash for the file content.
    - Images: Uses Perceptual Hash (pHash).
    - PDFs: Uses Semantic Content Hash (Page Streams).
    - Other: Uses SHA-256 of raw bytes.
    """
    # 1. Image Logic (Perceptual)
    if is_image:
        try:
            img = Image.open(file_path)
            return str(imagehash.phash(img)) 
        except Exception as e:
            raise ValueError(f"Failed to generate pHash: {e}")

    # 2. PDF Logic (Semantic Content)
    elif file_path.lower().endswith('.pdf'):
        try:
            sha256 = hashlib.sha256()
            reader = PdfReader(file_path)
            
            # We loop through every page and hash its raw content stream.
            # This captures text, images, and layout, but IGNORES metadata.
            for page in reader.pages:
                content_obj = page.get_contents()
                if content_obj:
                    # Content can be a single object or a list of objects
                    if isinstance(content_obj, list):
                        for obj in content_obj:
                            sha256.update(obj.get_data())
                    else:
                        sha256.update(content_obj.get_data())
            
            return sha256.hexdigest()
        except Exception as e:
            # Fallback to standard hashing if PDF is encrypted or malformed
            return _hash_raw_file(file_path)

    # 3. Standard File Logic (Text, etc.)
    else:
        return _hash_raw_file(file_path)

def _hash_raw_file(file_path):
    """Standard SHA-256 file hashing helper."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        raise ValueError(f"Failed to generate SHA-256: {e}")

# --- SIGNING & VERIFICATION ---

def sign_payload(private_key, payload_string):
    """Signs the payload string using the private key."""
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
    """Verifies the signature against the payload."""
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