import argparse
import os
import sys
import mimetypes
import hashlib
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import imagehash 

from modules import crypto

try:
    from modules import stega_image
except ImportError:
    stega_image = None

try:
    from modules import stega_pdf
except ImportError:
    stega_pdf = None

try:
    from modules import stega_text
except ImportError:
    stega_text = None

console = Console()

# --- CONFIGURATION ---
HAMMING_THRESHOLD = 10 

def calculate_text_hash_without_sig(file_path):
    """
    Reads a text file, strips the signature block, and hashes the original content.
    """
    HEADER = "\n\n-----BEGIN OFFICIAL SIGNATURE-----\n"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Strip the signature to get original content
        if HEADER in content:
            original_content = content.split(HEADER)[0]
        else:
            original_content = content

        # Calculate SHA-256 of the original content
        sha256 = hashlib.sha256()
        sha256.update(original_content.encode('utf-8'))
        return sha256.hexdigest()
    except Exception as e:
        return None

def verify_media(file_path):
    # 1. UI Header
    console.print(Panel.fit(
        f"[bold cyan]VERIFICATION TOOL[/bold cyan]\n"
        f"[yellow]Scanning:[/yellow] {os.path.basename(file_path)}", 
        border_style="blue"
    ))

    # 2. Detect Type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type and file_path.lower().endswith('.txt'):
        mime_type = 'text/plain'

    extracted_string = None
    is_image = mime_type and mime_type.startswith('image')
    is_text = mime_type == 'text/plain'

    # 3. Extract Payload
    if is_image:
        if stega_image: extracted_string = stega_image.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] Image module missing.")
    elif mime_type == 'application/pdf':
        if stega_pdf: extracted_string = stega_pdf.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] PDF module missing.")
    elif is_text:
        if stega_text: extracted_string = stega_text.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] Text module missing.")
    
    if not extracted_string:
        console.print(Panel(
            "[bold red]NO SIGNATURE FOUND[/bold red]\n\n"
            "This file does not contain a valid hidden payload.", 
            title="Verification Failed", 
            border_style="red"
        ))
        return

    # 4. Parse the Payload (ROBUST VERSION)
    try:
        console.print(Panel(f"{extracted_string}", title="[DEBUG] Raw Extracted Data", border_style="magenta"))
        
        if "||SIG||" in extracted_string:
            raw_data, signature = extracted_string.split("||SIG||")
        else:
            import re
            split_match = re.search(r"\|\|.{3}\|\|", extracted_string)
            if split_match:
                separator = split_match.group(0)
                raw_data, signature = extracted_string.split(separator)
            else:
                raise ValueError("Separator lost")

        original_hash_str, timestamp, auth_name, message = raw_data.split("|")
    except ValueError:
        console.print("[bold red]❌ MALFORMED PAYLOAD[/bold red] - Could not parse structure.")
        return

    # 5. Verify Cryptographic Signature
    try:
        public_key = crypto.load_public_key(auth_name)
        is_valid_sig = crypto.verify_signature(public_key, raw_data, signature)
    except FileNotFoundError:
        console.print(f"[bold red]UNKNOWN AUTHORITY[/bold red]\nWe do not have the Public Key for '{auth_name}'")
        return
    except Exception as e:
        console.print(f"[bold red]CRYPTO ERROR:[/bold red] {e}")
        return

    # 6. Verify Integrity
    integrity_passed = False
    details_msg = ""

    if is_image:
        # Image: Use Hamming Distance (pHash)
        current_hash_str = crypto.generate_file_hash(file_path, is_image=True)
        try:
            h_orig = imagehash.hex_to_hash(original_hash_str)
            h_curr = imagehash.hex_to_hash(current_hash_str)
            distance = h_orig - h_curr
            
            if distance <= HAMMING_THRESHOLD:
                integrity_passed = True
                details_msg = f"Hamming Distance: {distance} (Threshold: {HAMMING_THRESHOLD})"
            else:
                integrity_passed = False
                details_msg = f"Hamming Distance: {distance} (TOO HIGH!)"
        except Exception as e:
            integrity_passed = False
            details_msg = f"Hash Calculation Error: {e}"

    elif is_text:
        # Text: Strip signature before hashing
        current_hash_str = calculate_text_hash_without_sig(file_path)
        if current_hash_str == original_hash_str:
            integrity_passed = True
            details_msg = "Exact Match (Signature Stripped)"
        else:
            integrity_passed = False
            details_msg = "Content Mismatch (Modified)"
            
    else:
        # PDF / Other: Uses Semantic Hash from crypto.py
        current_hash_str = crypto.generate_file_hash(file_path)
        if current_hash_str == original_hash_str:
            integrity_passed = True
            details_msg = "Content Stream Match"
        else:
            integrity_passed = False
            details_msg = "SHA-256 Mismatch (Content Altered)"

    # 7. Final Report
    if is_valid_sig and integrity_passed:
        status_color = "green"
        status_title = "VERIFIED AUTHENTIC"
    elif is_valid_sig and not integrity_passed:
        status_color = "yellow" 
        status_title = "TAMPERED CONTENT"
    else:
        status_color = "red"
        status_title = "FAKE SIGNATURE"
    
    table = Table(title=f"Verification Report: {status_title}", style=status_color)
    table.add_column("Check", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", justify="left")

    sig_status = "[bold green]PASSED[/bold green]" if is_valid_sig else "[bold red]FAILED[/bold red]"
    table.add_row("Digital Signature", sig_status, "Cryptographically valid from Authority")

    int_status = "[bold green]PASSED[/bold green]" if integrity_passed else "[bold red]FAILED[/bold red]"
    table.add_row("Content Integrity", int_status, details_msg)

    meta_text = Text()
    meta_text.append(f"Authority:   {auth_name}\n", style="bold white")
    meta_text.append(f"Timestamp:   {timestamp}\n", style="dim white")
    meta_text.append(f"Message:     {message}", style="bold yellow")

    console.print(Panel(meta_text, title="Embedded Metadata", border_style="white"))
    console.print(table)
    
    if not is_valid_sig:
        console.print("[bold red]WARNING: The signature is invalid. Do not trust this file.[/bold red]")
    elif not integrity_passed:
        console.print("[bold yellow]WARNING: The signature is real, but the content has been altered.[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to verify")
    args = parser.parse_args()
    
    if os.path.exists(args.file):
        verify_media(args.file)
    else:
        console.print(f"[bold red]Error:[/bold red] File {args.file} not found.")