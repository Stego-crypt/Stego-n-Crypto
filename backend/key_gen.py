import argparse
import os
import sys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_authority_keys(authority_name):
    
    safe_name = "".join([c if c.isalnum() else "_" for c in authority_name])
    
    
    keys_dir = "keys"
    if not os.path.exists(keys_dir):
        os.makedirs(keys_dir)
        print(f"Created directory: {keys_dir}/")

    # Define file paths
    priv_path = os.path.join(keys_dir, f"{safe_name}_private.pem")
    pub_path = os.path.join(keys_dir, f"{safe_name}_public.pem")

    if os.path.exists(priv_path):
        print(f"ABORTING: Identity for '{authority_name}' already exists at {priv_path}")
        print("   (Delete the files manually if you really want to regenerate them.)")
        return

    print(f"Generating 2048-bit RSA keys for: '{authority_name}'...")

    # 4. Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 5. Save Private Key
    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 6. Save Public Key
    with open(pub_path, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print(f"SUCCESS: New Authority Created!")
    print(f"Name: {authority_name}")
    print(f"Private Key: {priv_path} (KEEP SECRET)")
    print(f"Public Key:  {pub_path} (DISTRIBUTE)")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate keys for a new Issuing Authority")
    parser.add_argument("name", type=str, help="Name of the authority (e.g. 'Government of India')")
    
    args = parser.parse_args()
    
    # Run the generator
    generate_authority_keys(args.name)