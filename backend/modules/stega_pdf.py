import os
from pypdf import PdfReader, PdfWriter
from rich.console import Console

console = Console()


METADATA_KEY = "/OfficialSignature"

def embed(source_path, payload_string, output_path):

    try:
        console.print(f"   [PDF] Reading: {os.path.basename(source_path)}")
        
        reader = PdfReader(source_path)
        writer = PdfWriter()

       
        for page in reader.pages:
            writer.add_page(page)

       
        current_metadata = reader.metadata
        metadata_dict = {}

        if current_metadata:
            
            for key, value in current_metadata.items():
                metadata_dict[key] = value

      
        metadata_dict[METADATA_KEY] = payload_string

        
        writer.add_metadata(metadata_dict)

        with open(output_path, "wb") as f:
            writer.write(f)
            
        return True

    except Exception as e:
        console.print(f"[bold red]PDF Embedding Failed:[/bold red] {e}")
        return False

def extract(source_path):

    try:
        reader = PdfReader(source_path)
        metadata = reader.metadata
        
        
        if metadata and METADATA_KEY in metadata:
            
            return metadata[METADATA_KEY]
        else:
            return None

    except Exception as e:
        console.print(f"[bold red]PDF Extraction Failed:[/bold red] {e}")
        return None