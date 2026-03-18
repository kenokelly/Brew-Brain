import requests

API_URL = "http://localhost:5000"

def test_health():
    print(f"Testing {API_URL}/api/health (Should be 200/unauthenticated)")
    try:
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()[:200] if r.status_code == 200 else r.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_auth_rejection():
    print(f"\nTesting {API_URL}/api/sync_brewfather without token (Should be 401)")
    try:
        r = requests.post(f"{API_URL}/api/sync_brewfather", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json() if r.status_code == 401 else r.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_ssrf():
    print(f"\nTesting SSRF vulnerability on {API_URL}/api/sourcing/compare-by-tag/<tag>")
    # We will pass a URL disguised as a tag. Since we protected `compare_recipe_prices` to use `alerts.py`, 
    # it won't even hit `get_page_content` directly with the tag. But let's verify it doesn't crash.
    test_tag = "http://169.254.169.254" 
    try:
        r = requests.get(f"{API_URL}/api/sourcing/compare-by-tag/{requests.utils.quote(test_tag)}", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_health()
    test_auth_rejection()
    test_ssrf()
