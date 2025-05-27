import ipaddress
import subprocess
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from rich.console import Console
import pandas as pd

console = Console()

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

def main(input_file, output_excel):
    entries = read_input_file(input_file)
    all_results = {}
    all_reachable = []
    all_unreachable = []

    for entry in entries:
        network = determine_subnet(entry)
        if not network:
            continue

        console.print(f"[cyan]Scanning: {network}[/cyan]")
        results = scan_network(network)

        df = pd.DataFrame(results, columns=["IP Address", "Status"])
        sheet_name = str(network).replace("/", "_")[:31]
        all_results[sheet_name] = df

        all_reachable.extend([ip for ip, status in results if status == "Reachable"])
        all_unreachable.extend([ip for ip, status in results if status == "Unreachable"])

    style_and_save_excel(all_results, all_reachable, all_unreachable, output_excel)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = input("Enter path to input file (e.g., ip_list.txt): ").strip()

    output_excel = "ping_scan_results.xlsx"
    main(input_file, output_excel)