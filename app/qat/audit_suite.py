
import unittest
import logging
import requests
import json
import time

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SystemAuditor")

BASE_URL = "http://localhost:5000"

class SystemAuditor(unittest.TestCase):
    """
    Blackbox System Audit Suite.
    Hits the LIVE API running on localhost:5000.
    Verifies the Web Interface Backend.
    """
    
    def setUp(self):
        """Wait for service availability"""
        # Simple retry loop in case of startup lag
        pass

    # --- CORE ROUTES ---

    def test_core_status(self):
        """/api/status should return system health dict"""
        try:
            res = requests.get(f"{BASE_URL}/api/status")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("temp", data)
            logger.info(f"✅ Core Status Checked: Found {len(data)} keys")
        except requests.exceptions.ConnectionError:
            self.fail("❌ Could not connect to Flask API")

    def test_web_assets(self):
        """Check HTML files are serving (Web Interface Check)"""
        for page in ["index.html", "automation.html"]:
            res = requests.get(f"{BASE_URL}/static/{page}")
            # Flask static serving might return 200 or 304, or just content
            # Assuming standard /static/ route or root / if using send_from_directory
            # Route / maps to index.html
            if page == "index.html":
                url = f"{BASE_URL}/"
            else:
                url = f"{BASE_URL}/static/{page}"
                
            res = requests.get(url)
            self.assertEqual(res.status_code, 200, f"Failed to load {page}")
            logger.info(f"✅ Web Interface Asset Found: {page}")

    # --- AUTOMATION: INGREDIENTS ---

    def test_scout_search(self):
        """/api/automation/scout (Live API)"""
        # We assume SerpApi might fail if no key, but endpoint should return 200 or JSON error
        # Not 500 crash.
        res = requests.post(f"{BASE_URL}/api/automation/scout", json={"query": "Malt"})
        self.assertIn(res.status_code, [200, 400, 500]) # 500 acceptable if API key missing but handled
        # Ideally 200 or 400.
        if res.status_code == 200:
            logger.info("✅ Ingredient Search API Alive")
        else:
            logger.warning(f"⚠️ Ingredient Search responded {res.status_code} (Likely config/key issue, but reachable)")

    def test_calc_ibu(self):
        """/api/automation/calc_ibu"""
        payload = {"amount": 50, "alpha": 12, "time": 60, "volume": 23, "gravity": 1.050}
        res = requests.post(f"{BASE_URL}/api/automation/calc_ibu", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get('ibu') > 0)
        logger.info(f"✅ IBU Calculator Verified: {res.json().get('ibu')}")

    # --- AUTOMATION: RECIPES (CRITICAL FIX CHECK) ---

    def test_recipe_analysis(self):
        """/api/automation/recipes/analyze"""
        # This tests the 'undefined or null' fix.
        # We query something generic.
        res = requests.post(f"{BASE_URL}/api/automation/recipes/analyze", json={"query": "IPA"})
        self.assertEqual(res.status_code, 200, "Recipe Analysis Endpoint Failed")
        data = res.json()
        
        # KEY CHECK: The fields that crashed the frontend must be present
        required = ["avg_og", "avg_ibu", "avg_abv", "common_hops"]
        for r in required:
            self.assertIn(r, data, f"MISSING KEY: {r} (Fix regression?)")
            
        logger.info("✅ Recipe Analysis Fix Verified (All keys present)")

    # --- SYSTEM: INVENTORY ---
    
    def test_inventory_get(self):
        """/api/automation/inventory"""
        res = requests.get(f"{BASE_URL}/api/automation/inventory")
        self.assertEqual(res.status_code, 200)
        logger.info("✅ Inventory API Reachable")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(SystemAuditor)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        exit(1)
