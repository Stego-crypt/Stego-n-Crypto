import argparse
import os
import sys
import mimetypes
from datetime import datetime
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

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

def process_signing(file_path, authority_name, message):
  
    console.print(Panel.fit(
        f"[bold cyan]MEDIA SIGNER v1.0[/bold cyan]\n"
        f"[yellow]Authority:[/yellow] {authority_name}\n"
        f"[yellow]Target:[/yellow]    {os.path.basename(file_path)}",
        title="[bold red]CONFIDENTIAL[/bold red]",
        border_style="blue"
    ))

    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        if file_path.lower().endswith('.txt'): mime_type = 'text/plain'
        else:
            console.print("[bold red]Error:[/bold red] Could not detect file type.")
            return

    console.print(f"[italic]Detected MIME Type:[/italic] [bold]{mime_type}[/bold]")

   
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = os.path.basename(file_path)
    base_name, ext = os.path.splitext(file_name)
    
    if mime_type.startswith('image'):
        output_filename = f"signed_{base_name}.png" 
    else:
        output_filename = f"signed_{file_name}"
        
    final_output_path = os.path.join(output_dir, output_filename)

    
    
    file_to_hash = file_path 
    temp_stamped_path = None

    if mime_type == 'application/pdf':
        if stega_pdf:
            console.print("[cyan]Applying Visual Watermark...[/cyan]")
            temp_stamped_path = os.path.join(output_dir, f"temp_{file_name}")
            
          
            success = stega_pdf.stamp_pdf(file_path, temp_stamped_path, authority_name)
            if success:
                
                file_to_hash = temp_stamped_path
            else:
                return 
        else:
             console.print("[bold red]Error:[/bold red] PDF module missing, cannot apply watermark.")

    payload_data = ""
    signature = ""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        
        task1 = progress.add_task("[cyan]Loading Authority Keys...", total=None)
        try:
            private_key = crypto.load_private_key(authority_name)
            time.sleep(0.5) 
            progress.update(task1, completed=100)
        except Exception as e:
            console.print(f"[bold red]Key Error:[/bold red] {e}")
            return

        task2 = progress.add_task("[cyan]Calculating Hash & Generating Signature...", total=None)
        
        is_image = mime_type.startswith('image')
        
        
        file_hash = crypto.generate_file_hash(file_to_hash, is_image=is_image)
        
        timestamp = datetime.now().isoformat()
        payload_data = f"{file_hash}|{timestamp}|{authority_name}|{message}"
        
        signature = crypto.sign_payload(private_key, payload_data)
        time.sleep(0.5) 
        progress.update(task2, completed=100)

    console.print(Panel(
        f"[green]Payload:[/green] {payload_data}\n"
        f"[green]Signature:[/green] {signature[:50]}...[dim](truncated)[/dim]",
        title="Generated Cryptographic Proof",
        border_style="green"
    ))

    
    final_stega_payload = f"{payload_data}||SIG||{signature}"

    if is_image:
        if stega_image:
            console.print("[bold yellow]Routing to Image Steganography Module (DWT)...[/bold yellow]")
            stega_image.embed(file_path, final_stega_payload, final_output_path)
            console.print(f"[bold green]SUCCESS![/bold green] Signed Image saved to: [underline]{final_output_path}[/underline]")
        else:
            console.print("[bold red]Error:[/bold red] 'stega_image.py' module is missing!")

    elif mime_type == 'application/pdf':
        if stega_pdf:
            console.print("[bold yellow]Routing to PDF Steganography Module (Metadata)...[/bold yellow]")
            
            stega_pdf.embed(temp_stamped_path, final_stega_payload, final_output_path)
            
            
            if os.path.exists(temp_stamped_path):
                os.remove(temp_stamped_path)
                
            console.print(f"[bold green]SUCCESS![/bold green] Signed PDF saved to: [underline]{final_output_path}[/underline]")
        else:
            console.print("[bold red]Error:[/bold red] 'stega_pdf.py' module is missing!")

    elif mime_type == 'text/plain':
        if stega_text:
            console.print("[bold yellow]Routing to Text Steganography Module (Append)...[/bold yellow]")
            stega_text.embed(file_path, final_stega_payload, final_output_path)
            console.print(f"[bold green]SUCCESS![/bold green] Signed Text saved to: [underline]{final_output_path}[/underline]")
        else:
             console.print("[bold red]Error:[/bold red] 'stega_text.py' module is missing!")

    else:
        console.print(f"[bold red]Error:[/bold red] No embedding strategy for {mime_type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sign media with Authority private key")
    parser.add_argument("file", help="Path to the file to sign")
    parser.add_argument("--auth", help="Name of the Issuing Authority", required=True)
    parser.add_argument("--msg", help="The official message/truth to embed", default="OFFICIAL RELEASE")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        console.print(f"[bold red]Error:[/bold red] File {args.file} not found.")
        sys.exit(1)
        
    process_signing(args.file, args.auth, args.msg)