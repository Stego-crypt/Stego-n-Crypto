import argparse
import os
import sys
import mimetypes
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

def verify_media(file_path):
    # 1. UI Header
    console.print(Panel.fit(
        f"[bold cyan]VERIFICATION TOOL[/bold cyan]\n"
        f"[yellow]Scanning:[/yellow] {os.path.basename(file_path)}", 
        border_style="blue"
    ))

    # 2. Detect Type
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # Fallback for text files
    if not mime_type and file_path.lower().endswith('.txt'):
        mime_type = 'text/plain'

    extracted_string = None
    is_image = mime_type and mime_type.startswith('image')

    # 3. Extract Payload
    if is_image:
        if stega_image: extracted_string = stega_image.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] Image module missing.")
    elif mime_type == 'application/pdf':
        if stega_pdf: extracted_string = stega_pdf.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] PDF module missing.")
    elif mime_type == 'text/plain':
        if stega_text: extracted_string = stega_text.extract(file_path)
        else: console.print("[bold red]Error:[/bold red] Text module missing.")
    
    if not extracted_string:
        console.print(Panel(
            "[bold red]NO SIGNATURE FOUND[/bold red]\n\n"
            "This file does not contain a valid hidden payload.\n"
            "It is either unsigned or has been heavily corrupted.", 
            title="Verification Failed", 
            border_style="red"
        ))
        return

    # 4. Parse the Payload (WITH DEBUGGING)
    try:
        # --- NEW DEBUG SECTION ---
        # This allows us to see exactly what characters survived WhatsApp compression
        console.print(Panel(f"{extracted_string}", title="[DEBUG] Raw Extracted Data", border_style="magenta"))
        # -------------------------

        raw_data, signature = extracted_string.split("||SIG||")
        original_hash_str, timestamp, auth_name, message = raw_data.split("|")
    except ValueError:
        console.print("[bold red]❌ MALFORMED PAYLOAD[/bold red] - Could not parse structure.")
        console.print("[yellow]Tip: Check the Magenta DEBUG panel above. Look for damaged separators (e.g. '||S?G||').[/yellow]")
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
    current_hash_str = crypto.generate_file_hash(file_path, is_image=is_image)
    
    integrity_passed = False
    details_msg = ""
    distance = 0

    if is_image:
        try:
            h_original = imagehash.hex_to_hash(original_hash_str)
            h_current = imagehash.hex_to_hash(current_hash_str)
            
            distance = h_original - h_current
            
            if distance <= HAMMING_THRESHOLD:
                integrity_passed = True
                details_msg = f"Hamming Distance: {distance} (Threshold: {HAMMING_THRESHOLD})"
            else:
                integrity_passed = False
                details_msg = f"Hamming Distance: {distance} (TOO HIGH!)"
        except Exception as e:
            integrity_passed = False
            details_msg = f"Hash Calculation Error: {e}"
            
    else:
        if current_hash_str == original_hash_str:
            integrity_passed = True
            details_msg = "Exact SHA-256 Match"
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