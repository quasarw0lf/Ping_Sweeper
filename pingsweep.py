import ipaddress
import subprocess
import platform
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
import pandas as pd

console = Console()

def display_banner():
    """Display the geeky banner for Ping Sweeper."""
    banner_text = """
    ██████╗ ██╗███╗   ██╗ ██████╗     ███████╗██╗    ██╗███████╗███████╗██████╗ ███████╗██████╗ 
    ██╔══██╗██║████╗  ██║██╔════╝     ██╔════╝██║    ██║██╔════╝██╔════╝██╔══██╗██╔════╝██╔══██╗
    ██████╔╝██║██╔██╗ ██║██║  ███╗    ███████╗██║ █╗ ██║█████╗  █████╗  ██████╔╝█████╗  ██████╔╝
    ██╔═══╝ ██║██║╚██╗██║██║   ██║    ╚════██║██║███╗██║██╔══╝  ██╔══╝  ██╔═══╝ ██╔══╝  ██╔══██╗
    ██║     ██║██║ ╚████║╚██████╔╝    ███████║╚███╔███╔╝███████╗███████╗██║     ███████╗██║  ██║
    ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝     ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝
    """
    
    credit_text = "Made with ❤️  by Quasar CyberTech Research Team"
    
    panel = Panel(
        Text(banner_text, style="bold green") + "\n" + 
        Text(credit_text, style="bold magenta", justify="center"),
        padding=(1, 2)
    )
    console.print(panel)
    console.print()

def ping_ip(ip):
    """Ping a single IP and return (IP, is_reachable)."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', '-W', '1', str(ip)]
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(ip), result.returncode == 0
    except Exception:
        return str(ip), False

def determine_subnet(entry):
    """Convert input to subnet. Default to /24 if only IP provided."""
    try:
        if '/' in entry:
            return ipaddress.ip_network(entry.strip(), strict=False)
        else:
            ip = ipaddress.ip_address(entry.strip())
            return ipaddress.ip_network(f"{ip}/24", strict=False)
    except ValueError as e:
        console.print(f"[red]Invalid IP or CIDR: {entry} - {e}[/red]")
        return None

def scan_network(network, max_threads=100):
    """Ping all IPs in the subnet."""
    hosts = list(network.hosts())
    results = []

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for ip, status in tqdm(executor.map(ping_ip, hosts), total=len(hosts), desc=f"Scanning {network}", leave=False):
            results.append((str(ip), "Reachable" if status else "Unreachable"))

    return results

def read_input_file(filepath):
    """Read non-empty lines from input file."""
    try:
        with open(filepath, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        console.print(f"[red]Input file '{filepath}' not found.[/red]")
        sys.exit(1)

def style_and_save_excel(all_results, all_reachable, all_unreachable, output_excel):
    """Write all sheets to Excel with styling using xlsxwriter."""
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',  # Blue
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({
            'border': 1
        })

        # Write each network sheet
        for sheet_name, df in all_results.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            worksheet = writer.sheets[sheet_name[:31]]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(0, len(df.columns)-1, 20, cell_format)

        # Write All_Reachable
        df_r = pd.DataFrame(all_reachable, columns=["Reachable IPs"])
        df_r.to_excel(writer, sheet_name="All_Reachable", index=False)
        ws_r = writer.sheets["All_Reachable"]
        ws_r.write(0, 0, "Reachable IPs", header_format)
        ws_r.set_column(0, 0, 25, cell_format)

        # Write All_Unreachable
        df_u = pd.DataFrame(all_unreachable, columns=["Unreachable IPs"])
        df_u.to_excel(writer, sheet_name="All_Unreachable", index=False)
        ws_u = writer.sheets["All_Unreachable"]
        ws_u.write(0, 0, "Unreachable IPs", header_format)
        ws_u.set_column(0, 0, 25, cell_format)

    console.print(f"\n[green]Scan complete! Results saved to:[/green] [bold]{output_excel}[/bold]")

def interactive_mode():
    """Interactive mode for user-friendly operation."""
    console.print("[bold yellow]🔍 Interactive Ping Sweeper Mode[/bold yellow]")
    console.print("Enter IP addresses or CIDR ranges to scan (one per line)")
    console.print("Examples: 192.168.1.1, 10.0.0.0/24, 172.16.5.0/26")
    console.print("Type 'done' when finished, 'quit' to exit\n")
    
    entries = []
    while True:
        try:
            entry = Prompt.ask("[cyan]Enter IP/CIDR").strip()
            if entry.lower() == 'quit':
                console.print("[yellow]Exiting...[/yellow]")
                sys.exit(0)
            elif entry.lower() == 'done':
                break
            elif entry:
                # Validate entry
                network = determine_subnet(entry)
                if network:
                    entries.append(entry)
                    console.print(f"[green]✓ Added: {network}[/green]")
                else:
                    console.print("[red]Invalid entry, please try again[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            sys.exit(0)
    
    if not entries:
        console.print("[red]No valid entries provided. Exiting.[/red]")
        sys.exit(1)
    
    # Get threading preference
    max_threads = Prompt.ask(
        "[cyan]Max threads for scanning",
        default="100",
        show_default=True
    )
    try:
        max_threads = int(max_threads)
    except ValueError:
        max_threads = 100
        console.print("[yellow]Invalid thread count, using default: 100[/yellow]")
    
    # Get output file preference
    output_excel = Prompt.ask(
        "[cyan]Output Excel filename",
        default="ping_scan_results.xlsx",
        show_default=True
    )
    
    return entries, output_excel, max_threads

def main(input_file=None, output_excel="ping_scan_results.xlsx", max_threads=100, interactive=False):
    display_banner()
    
    if interactive:
        entries, output_excel, max_threads = interactive_mode()
    elif input_file:
        entries = read_input_file(input_file)
    else:
        input_file = input("Enter path to input file (e.g., ip_list.txt): ").strip()
        entries = read_input_file(input_file)
    
    all_results = {}
    all_reachable = []
    all_unreachable = []
    
    start_time = time.time()
    
    for entry in entries:
        network = determine_subnet(entry)
        if not network:
            continue

        console.print(f"[cyan]Scanning: {network} ({len(list(network.hosts()))} hosts)[/cyan]")
        results = scan_network(network, max_threads)

        df = pd.DataFrame(results, columns=["IP Address", "Status"])
        sheet_name = str(network).replace("/", "_")[:31]
        all_results[sheet_name] = df

        reachable_count = sum(1 for ip, status in results if status == "Reachable")
        console.print(f"[green]✓ Found {reachable_count} reachable hosts in {network}[/green]")

        all_reachable.extend([ip for ip, status in results if status == "Reachable"])
        all_unreachable.extend([ip for ip, status in results if status == "Unreachable"])

    total_time = time.time() - start_time
    console.print(f"\n[bold]📊 Scan Summary:[/bold]")
    console.print(f"[green]Total Reachable: {len(all_reachable)}[/green]")
    console.print(f"[red]Total Unreachable: {len(all_unreachable)}[/red]")
    console.print(f"[blue]Total Time: {total_time:.2f} seconds[/blue]")
    
    style_and_save_excel(all_results, all_reachable, all_unreachable, output_excel)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ping Sweeper - Network Host Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ping_sweeper.py -f ip_list.txt
  python ping_sweeper.py -i
  python ping_sweeper.py -f networks.txt -o results.xlsx -t 200
        """
    )
    
    parser.add_argument('-f', '--file', help='Input file containing IP addresses/CIDR ranges')
    parser.add_argument('-o', '--output', default='ping_scan_results.xlsx', 
                       help='Output Excel file (default: ping_scan_results.xlsx)')
    parser.add_argument('-t', '--threads', type=int, default=100, 
                       help='Maximum number of threads (default: 100)')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='Run in interactive mode')
    
    args = parser.parse_args()
    
    if args.interactive:
        main(interactive=True)
    elif args.file:
        main(args.file, args.output, args.threads)
    else:
        main()