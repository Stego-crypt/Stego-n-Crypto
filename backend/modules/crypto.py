import os
import hashlib
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import imagehash
from PIL import Image
from pypdf import PdfReader 

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

# --- HASHING (UPDATED FOR DEEP LOGICAL INTEGRITY) ---

def generate_file_hash(file_path, is_image=False):
    """
    Generates a hash for the file content.
    - Images: Uses Perceptual Hash (pHash).
    - PDFs: Uses Deep Logical Hash (Pages + Annots + Meta - Sig).
    - Other: Uses SHA-256 of raw bytes.
    """
    # 1. Image Logic (Perceptual)
    if is_image:
        try:
            img = Image.open(file_path)
            return str(imagehash.phash(img)) 
        except Exception as e:
            raise ValueError(f"Failed to generate pHash: {e}")

    # 2. PDF Logic (Deep Logical Integrity)
    elif file_path.lower().endswith('.pdf'):
        try:
            return _hash_pdf_logic(file_path)
        except Exception as e:
            # Fallback to standard hashing if PDF is encrypted or malformed
            print(f"Warning: PDF Logic Hash failed ({e}), falling back to raw.")
            return _hash_raw_file(file_path)

    # 3. Standard File Logic (Text, etc.)
    else:
        return _hash_raw_file(file_path)

def _hash_pdf_logic(file_path):
    """
    Hashes the logical content of a PDF to detect tampering (deletions, annotations, reordering),
    while explicitly ignoring the '/OfficialSignature' metadata field.
    """
    sha256 = hashlib.sha256()
    reader = PdfReader(file_path)
    
    # 1. Hash Metadata (Author, Title, etc.)
    # We MUST sort keys to ensure consistency.
    if reader.metadata:
        sorted_keys = sorted(reader.metadata.keys())
        for key in sorted_keys:
            # CRITICAL: Ignore our signature field, but hash everything else
            # This solves the "Observer Effect" where signing the file changes the hash.
            if key == "/OfficialSignature":
                continue
            
            value = reader.metadata[key]
            # Update hash with Key + Value
            sha256.update(str(key).encode('utf-8', errors='ignore'))
            sha256.update(str(value).encode('utf-8', errors='ignore'))

    # 2. Hash Page Count (Detects Deletion/Insertion)
    # Adding the count ensures that removing a blank page changes the hash.
    page_count = len(reader.pages)
    sha256.update(f"COUNT:{page_count}".encode('utf-8'))

    # 3. Hash Page Content & Annotations
    for i, page in enumerate(reader.pages):
        # A. Hash Page Index (Detects Reordering)
        sha256.update(f"PAGE:{i}".encode('utf-8'))
        
        # B. Hash Content Stream (Text/Images)
        content_obj = page.get_contents()
        if content_obj:
            if isinstance(content_obj, list):
                for obj in content_obj:
                    sha256.update(obj.get_data())
            else:
                sha256.update(content_obj.get_data())
        
        # C. Hash Annotations (Highlights, Comments, Signatures)
        # This catches "Overlays" that don't change the main content stream.
        if "/Annots" in page:
            annots = page["/Annots"]
            if annots:
                try:
                    for annot in annots:
                        # Hash the annotation object representation
                        annot_obj = annot.get_object()
                        sha256.update(str(annot_obj).encode('utf-8', errors='ignore'))
                except Exception:
                    pass # Skip if complex annotation fails

    return sha256.hexdigest()

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