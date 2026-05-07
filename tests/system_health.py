import requests
import json
import sys
import time

API_URL = "http://localhost:5000"
PROXY_URL = "http://localhost:3001"
TOKEN = "secure_default_token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def check_step(name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{status}] {name}: {details}")
    return success

def run_audit():
    print(f"🚀 Starting System Health Audit at {time.ctime()}")
    print("-" * 50)
    
    overall_success = True

    # 1. API Basic Connectivity (Direct)
    try:
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        is_healthy = r.status_code == 200 and r.json().get("status") == "healthy"
        if not check_step("API Direct (5000)", is_healthy, f"Status: {r.status_code}"):
            overall_success = False
    except Exception as e:
        check_step("API Direct (5000)", False, str(e))
        overall_success = False

    # 2. Frontend Proxy Integrity (Port 3001)
    try:
        # This checks if Nginx is correctly forwarding /api requests to the backend
        r = requests.get(f"{PROXY_URL}/api/health", timeout=5)
        is_proxied = r.status_code == 200 and r.json().get("status") == "healthy"
        if not check_step("Frontend Proxy (3001)", is_proxied, f"Status: {r.status_code}"):
            overall_success = False
    except Exception as e:
        check_step("Frontend Proxy (3001)", False, str(e))
        overall_success = False

    # 3. InfluxDB Round-Trip (via Status API)
    try:
        r = requests.get(f"{API_URL}/api/status", timeout=5)
        data = r.json()
        has_data = data.get("sg") is not None or data.get("pi_temp") is not None
        if not check_step("InfluxDB Connectivity", has_data, f"Temp: {data.get('pi_temp')}°C"):
            overall_success = False
    except Exception as e:
        check_step("InfluxDB Connectivity", False, str(e))
        overall_success = False

    # 4. Redis/Celery Task Flow
    try:
        r = requests.post(f"{API_URL}/api/ml/train", headers=HEADERS, timeout=5)
        task_queued = r.status_code == 200 and "task_id" in r.json().get("data", {})
        if not check_step("Async Task Queue (Redis)", task_queued, f"TaskID: {r.json().get('data', {}).get('task_id')}"):
            overall_success = False
    except Exception as e:
        check_step("Async Task Queue (Redis)", False, str(e))
        overall_success = False

    # 5. Node-RED (TILTpi) Heartbeat
    try:
        r = requests.get("http://localhost:1880", timeout=3)
        if not check_step("Node-RED Driver Pulse", r.status_code == 200, "Port 1880 reachable"):
            overall_success = False
    except Exception as e:
        check_step("Node-RED Driver Pulse", False, "Port 1880 unreachable (Driver Down)")
        overall_success = False

    print("-" * 50)
    if overall_success:
        print("✨ SYSTEM STABLE: All Gates Passed.")
        sys.exit(0)
    else:
        print("⚠️  SYSTEM DEGRADED: Audit Failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
