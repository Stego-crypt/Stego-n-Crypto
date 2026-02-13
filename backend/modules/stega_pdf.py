import os
import io
from pypdf import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib.units import inch
from rich.console import Console

console = Console()

METADATA_KEY = "/OfficialSignature"

def create_watermark_layer(text):
  
    packet = io.BytesIO()
    
    c = canvas.Canvas(packet, pagesize=(8.5*inch, 11*inch))
    
  
    base_x = 7.2 * inch
    base_y = 0.8 * inch
    
    
    watermark_color = Color(0.4, 0.45, 0.50, alpha=0.25)
    
    c.setStrokeColor(watermark_color)
    c.setFillColor(watermark_color)
    c.setLineWidth(1.5)

    
    s = 0.8 
    
    p = c.beginPath()

    p.moveTo(base_x, base_y + (20*s))
   
    p.curveTo(base_x + (10*s), base_y + (25*s), base_x + (20*s), base_y + (25*s), base_x + (30*s), base_y + (20*s))
    
    p.lineTo(base_x + (30*s), base_y - (10*s))
    
    p.curveTo(base_x + (30*s), base_y - (30*s), base_x + (15*s), base_y - (40*s), base_x + (15*s), base_y - (40*s))
   
    p.curveTo(base_x + (15*s), base_y - (40*s), base_x, base_y - (30*s), base_x, base_y - (10*s))
    p.close()
    c.drawPath(p, fill=0, stroke=1) 

 
    c.setLineWidth(2)
    path_check = c.beginPath()
    path_check.moveTo(base_x + (8*s), base_y - (5*s))
    path_check.lineTo(base_x + (15*s), base_y - (12*s))
    path_check.lineTo(base_x + (25*s), base_y + (5*s))
    c.drawPath(path_check, fill=0, stroke=1)

    
    text_x = base_x - (10 * s) 
    text_y_top = base_y + (5 * s)
    text_y_bot = base_y - (10 * s)

    c.setFillColor(watermark_color)
    

    c.setFont("Helvetica-Bold", 7)
    c.drawRightString(text_x, text_y_top, "DIGITALLY SECURED DOCUMENT")
    
   
    c.setFont("Helvetica", 6)
    
    max_len = 30
    display_text = (text[:max_len] + '...') if len(text) > max_len else text
    c.drawRightString(text_x, text_y_bot, f"Authority: {display_text}")

    c.save()
    packet.seek(0)
    return PdfReader(packet)

def stamp_pdf(input_path, output_path, authority_name):
  
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        watermark_pdf = create_watermark_layer(authority_name)
        watermark_page = watermark_pdf.pages[0]

        for page in reader.pages:
            
            page.merge_page(watermark_page)
            writer.add_page(page)

   
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        with open(output_path, "wb") as f:
            writer.write(f)
            
        console.print(f"   [PDF] Visual Stamp applied: {authority_name}")
        return True

    except Exception as e:
        console.print(f"[bold red]PDF Stamping Failed:[/bold red] {e}")
        
        import traceback
        traceback.print_exc()
        return False

def embed(source_path, payload_string, output_path):
    
    try:
        console.print(f"   [PDF] Embedding Metadata: {os.path.basename(source_path)}")
        
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