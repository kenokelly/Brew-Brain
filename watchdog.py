import os
import time
import subprocess
import urllib.request

PING_TARGET = "8.8.8.8"
CHECK_INTERVAL = 300 
MAX_RETRIES = 5

def log(msg): print(f"[{time.ctime()}] WATCHDOG: {msg}")

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
        os.system("nmcli radio wifi off")
        time.sleep(5)
        os.system("nmcli radio wifi on")
        time.sleep(10)
    except Exception as e:
        log(f"Error: {e}")

def restart_docker():
    log("Restarting Container...")
    os.system("docker restart brew-brain")

def main():
    fail_count = 0
    log("Watchdog active (Pi 5)")
    while True:
        if not check_internet():
            fail_count += 1
            log(f"Network Down {fail_count}/{MAX_RETRIES}")
            if fail_count == 3: restart_wifi()
            if fail_count >= MAX_RETRIES: os.system("sudo reboot")
        else:
            fail_count = 0
            if not check_brew_brain(): restart_docker()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    time.sleep(60)
    main()