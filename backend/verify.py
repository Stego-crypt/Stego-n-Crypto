import argparse
import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

# Import our new Core Logic
from verifier_core import analyze_file

console = Console()

def verify_media_cli(file_path):
    # 1. UI Header
    console.print(Panel.fit(
        f"[bold cyan]VERIFICATION TOOL[/bold cyan]\n"
        f"[yellow]Scanning:[/yellow] {os.path.basename(file_path)}", 
        border_style="blue"
    ))

    # 2. Call the Core Logic
    data = analyze_file(file_path)

    # 3. Handle Errors immediately
    if data["status"] == "error":
        console.print(Panel(
            f"[bold red]{data['message']}[/bold red]",
            title="Verification Failed",
            border_style="red"
        ))
        return

    # 4. Determine UI Colors based on Status
    status_color = "red"
    status_title = "UNKNOWN"
    
    if data["status"] == "verified":
        status_color = "green"
        status_title = "VERIFIED AUTHENTIC"
    elif data["status"] == "tampered":
        status_color = "yellow"
        status_title = "TAMPERED CONTENT"
    elif data["status"] == "fake":
        status_color = "red"
        status_title = "FAKE SIGNATURE"

    # 5. Build the Report Table
    table = Table(title=f"Verification Report: {status_title}", style=status_color)
    table.add_column("Check", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", justify="left")

    # Row 1: Signature
    sig_bool = data["checks"]["signature"]
    sig_status = "[bold green]PASSED[/bold green]" if sig_bool else "[bold red]FAILED[/bold red]"
    table.add_row("Digital Signature", sig_status, "Cryptographically valid from Authority")

    # Row 2: Integrity
    int_bool = data["checks"]["integrity"]
    int_status = "[bold green]PASSED[/bold green]" if int_bool else "[bold red]FAILED[/bold red]"
    table.add_row("Content Integrity", int_status, data["details"])

    # 6. Metadata Panel
    meta = data["metadata"]
    meta_text = Text()
    meta_text.append(f"Authority:   {meta['authority']}\n", style="bold white")
    meta_text.append(f"Timestamp:   {meta['timestamp']}\n", style="dim white")
    meta_text.append(f"Message:     {meta['message']}", style="bold yellow")

    console.print(Panel(meta_text, title="Embedded Metadata", border_style="white"))
    console.print(table)
    
    # 7. Final Warning
    if data["status"] == "fake":
        console.print("[bold red]WARNING: The signature is invalid. Do not trust this file.[/bold red]")
    elif data["status"] == "tampered":
        console.print("[bold yellow]WARNING: The signature is real, but the content has been altered.[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to verify")
    args = parser.parse_args()
    
    if os.path.exists(args.file):
        verify_media_cli(args.file)
    else:
        console.print(f"[bold red]Error:[/bold red] File {args.file} not found.")