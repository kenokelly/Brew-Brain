#!/usr/bin/env python3
import os
import time
import sys
import subprocess
import urllib.request

PING_TARGET = "8.8.8.8"
CHECK_INTERVAL = 300 
MAX_RETRIES = 5

def log(msg): 
    # Log to stdout for systemd capture
    print(f"[{time.ctime()}] WATCHDOG: {msg}")
    sys.stdout.flush()

def check_internet():
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "2", PING_TARGET])
        return True
    except:
        return False

def check_brew_brain():
    try:
        code = urllib.request.urlopen("http://localhost:5000/api/status", timeout=5).getcode()
        return code == 200
    except:
        return False

def restart_wifi():
    log("Restarting WiFi via nmcli...")
    try:
        os.system("/usr/bin/nmcli radio wifi off")
        time.sleep(5)
        os.system("/usr/bin/nmcli radio wifi on")
        time.sleep(10)
    except Exception as e:
        log(f"WiFi Restart Error: {e}")

def restart_docker():
    log("Restarting Container...")
    os.system("/usr/bin/sudo /usr/bin/docker restart brew-brain")

def main():
    fail_count = 0
    log("Watchdog active (Pi 5)")
    while True:
        if not check_internet():
            fail_count += 1
            log(f"Network Down {fail_count}/{MAX_RETRIES}")
            if fail_count == 3: restart_wifi()
            if fail_count >= MAX_RETRIES: 
                log("Rebooting due to network failure...")
                os.system("/usr/bin/sudo /sbin/reboot")
        else:
            fail_count = 0
            if not check_brew_brain(): 
                log("API check failed. Restarting Docker.")
                restart_docker()
            else:
                # Optional: Log heartbeat every hour (12 * 300s)
                pass 
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    time.sleep(60)
    main()