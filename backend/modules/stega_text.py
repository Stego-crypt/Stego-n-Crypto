import os
from rich.console import Console

console = Console()

HEADER = "\n\n-----BEGIN OFFICIAL SIGNATURE-----\n"
FOOTER = "\n-----END OFFICIAL SIGNATURE-----"

def embed(source_path, payload_string, output_path):
 
    try:
   
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        
        if HEADER in content:
            console.print("[bold yellow]Warning:[/bold yellow] File appears to be already signed. Overwriting signature.")

            content = content.split(HEADER)[0].strip()

   
        signed_content = f"{content}{HEADER}{payload_string}{FOOTER}"

  
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(signed_content)
            
        return True

    except Exception as e:
        console.print(f"[bold red]Text Embedding Failed:[/bold red] {e}")
        return False

def extract(source_path):

    try:
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        if HEADER in content:
            
            parts = content.split(HEADER)
            
           
            raw_block = parts[-1]
            
            if FOOTER in raw_block:
               
                payload = raw_block.split(FOOTER)[0]
                return payload.strip() 
            else:
                console.print("[bold red]Error:[/bold red] Found Signature Header but missing Footer.")
                return None
        else:
            return None

    except Exception as e:
        console.print(f"[bold red]Text Extraction Failed:[/bold red] {e}")
        return None