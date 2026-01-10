import logging
import json
from app.qat.dataset import generate_golden_dataset
from app.services import learning, sourcing, calculator

logger = logging.getLogger(__name__)

class QATRunner:
    def __init__(self):
        self.data = generate_golden_dataset()
        self.report = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        
    def log_result(self, name, success, message=""):
        self.report["tests"].append({
            "name": name,
            "status": "PASS" if success else "FAIL",
            "message": message
        })
        if success: self.report["passed"] += 1
        else: self.report["failed"] += 1

    def run_suite(self):
        """Runs the full QA Suite."""
        
        # Override Services Data Sources (In Memory Mock)
        # We perform 'dependency injection' by temporarily swapping the data provider methods
        # or just passing data where functions allow.
        # Since our services read from files, we might need to mock get_history.
        # For simplicity in this script, we will Monkey Patch the `get_history` and `get_inventory`
        
        original_get_history = learning.get_history
        original_get_inv = sourcing.get_inventory
        
        learning.get_history = lambda: self.data['history']
        sourcing.get_inventory = lambda: self.data['inventory']
        
        try:
            # TEST 1: ML Regression Training
            model = learning.train_efficiency_model()
            # With our data, m should be negative (efficiency drops as grain rises)
            # m ~ -1.5
            if -2.0 < model['m'] < -1.0:
                self.log_result("ML Regression Trend", True, f"Slope {round(model['m'], 2)} is valid (Negative correlation).")
            else:
                self.log_result("ML Regression Trend", False, f"Slope {model['m']} is out of expected range (-1.5).")
                
            # TEST 2: Hardware Guardrails
            # 20kg grain, 20L volume -> Should fail G40 max grain
            hw_check = calculator.validate_equipment(20, 20)
            if not hw_check['valid'] and "Max Grain" in str(hw_check['warnings']):
                 self.log_result("Hardware Guardrails", True, "Correctly rejected 20kg grain bill.")
            else:
                 self.log_result("Hardware Guardrails", False, "Failed to reject dangerous grain bill.")
                 
            # TEST 3: Smart Restock
            suggestions = sourcing.get_restock_suggestions()
            # Should find Citra (50g) and Maris Otter (500g)
            found_citra = any(i['name'] == 'Citra' for i in suggestions)
            found_mo = any(i['name'] == 'Maris Otter' for i in suggestions)
            
            if found_citra and found_mo:
                self.log_result("Auto-Restock Logic", True, "Correctly identified low Citra and Maris Otter.")
            else:
                self.log_result("Auto-Restock Logic", False, f"Missed items. Found: {[i['name'] for i in suggestions]}")
                
            # TEST 4: Recipe Audit
            # Check 'Broken IPA' (OG 1.030) vs History (IPA Avg ~1.060-ish)
            audit = learning.audit_recipe(self.data['bad_recipe'])
            # Should look for tips regarding OG
            has_warning = any("Gravity Deviation" in t for t in audit['tips'])
            if has_warning:
                self.log_result("AI Recipe Audit", True, "Correctly flagged Low OG for IPA.")
            else:
                self.log_result("AI Recipe Audit", False, "Failed to flag deviations.")
                
        except Exception as e:
            self.log_result("CRITICAL SUITE ERROR", False, str(e))
        finally:
            # Restore Originals
            learning.get_history = original_get_history
            sourcing.get_inventory = original_get_inv
            
        # TELEGRAM INTEGRATION
        if self.report['failed'] > 0:
            try:
                from app.services.notifications import send_telegram_message
                msg = f"🚨 *SYSTEM FAILURE DETECTED* (QAT)\n\n"
                msg += f"Failed Tests: {self.report['failed']}\n"
                for t in self.report['tests']:
                    if t['status'] == 'FAIL':
                        msg += f"❌ {t['name']}: {t['message']}\n"
                send_telegram_message(msg)
            except: pass
            
        return self.report
