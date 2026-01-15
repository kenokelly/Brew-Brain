#!/usr/bin/env python3
"""
End-to-End (E2E) Integration Test for Brew Brain
Tests the full workflow: Scout → Scale → Source → Log

Run with: python test_e2e_workflow.py
"""

import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("E2E_Test")

def test_e2e_workflow():
    """
    Tests the complete Scout-to-Log workflow.
    Returns: dict with test results
    """
    results = {
        "scout": {"status": "pending"},
        "scale": {"status": "pending"},
        "source": {"status": "pending"},
        "log": {"status": "pending"}
    }
    
    try:
        # ============================
        # STEP 1: SCOUT - Search for a recipe
        # ============================
        logger.info("📡 Step 1: Scout - Searching for recipe...")
        
        from app.services.scout import scout_recipe
        
        scout_result = scout_recipe("hazy ipa", limit=1)
        
        if scout_result and not scout_result.get("error"):
            results["scout"]["status"] = "pass"
            results["scout"]["recipe_count"] = len(scout_result.get("recipes", []))
            recipe = scout_result.get("recipes", [{}])[0] if scout_result.get("recipes") else None
            results["scout"]["sample_recipe"] = recipe.get("name") if recipe else None
            logger.info(f"   ✅ Found {results['scout']['recipe_count']} recipes")
        else:
            results["scout"]["status"] = "fail"
            results["scout"]["error"] = scout_result.get("error", "No recipes found")
            logger.error(f"   ❌ Scout failed: {results['scout']['error']}")
            
    except Exception as e:
        results["scout"]["status"] = "error"
        results["scout"]["error"] = str(e)
        logger.error(f"   ❌ Scout exception: {e}")

    try:
        # ============================
        # STEP 2: SCALE - Fit recipe to G40
        # ============================
        logger.info("⚖️  Step 2: Scale - Fitting to G40 constraints...")
        
        from app.services.calculator import scale_recipe_to_equipment
        
        # Mock recipe for scaling test
        test_recipe = {
            "name": "E2E Test IPA",
            "batch_size": 20,
            "fermentables": [
                {"name": "Pale Malt", "amount": 5.0},
                {"name": "Munich", "amount": 0.5}
            ],
            "hops": [
                {"name": "Citra", "amount": 50},
                {"name": "Mosaic", "amount": 50}
            ],
            "yeasts": [
                {"name": "Safale US-05", "amount": 1}
            ]
        }
        
        scale_result = scale_recipe_to_equipment(test_recipe, max_grain_kg=9.0)
        
        if scale_result and not scale_result.get("error"):
            results["scale"]["status"] = "pass"
            results["scale"]["scaled_batch_size"] = scale_result.get("scaled_batch_size")
            results["scale"]["grain_kg"] = scale_result.get("total_grain_kg")
            logger.info(f"   ✅ Scaled to {scale_result.get('scaled_batch_size')}L, {scale_result.get('total_grain_kg')}kg grain")
        else:
            results["scale"]["status"] = "fail"
            results["scale"]["error"] = scale_result.get("error", "Scaling failed")
            logger.error(f"   ❌ Scale failed: {results['scale']['error']}")
            
    except Exception as e:
        results["scale"]["status"] = "error"
        results["scale"]["error"] = str(e)
        logger.error(f"   ❌ Scale exception: {e}")

    try:
        # ============================
        # STEP 3: SOURCE - Get prices
        # ============================
        logger.info("🛒 Step 3: Source - Comparing prices...")
        
        from app.services.sourcing import compare_recipe_prices
        from app.core.config import get_config
        
        # Check if SerpApi key is configured
        api_key = get_config("serp_api_key")
        
        if not api_key:
            results["source"]["status"] = "skip"
            results["source"]["reason"] = "No SerpApi key configured"
            logger.warning("   ⚠️  Skipped: No SerpApi key")
        else:
            source_result = compare_recipe_prices(test_recipe)
            
            if source_result and not source_result.get("error"):
                results["source"]["status"] = "pass"
                results["source"]["items_priced"] = len(source_result.get("results", []))
                results["source"]["best_total"] = source_result.get("best_total")
                logger.info(f"   ✅ Priced {results['source']['items_priced']} items")
            else:
                results["source"]["status"] = "fail"
                results["source"]["error"] = source_result.get("error", "Sourcing failed")
                logger.error(f"   ❌ Source failed: {results['source']['error']}")
                
    except Exception as e:
        results["source"]["status"] = "error"
        results["source"]["error"] = str(e)
        logger.error(f"   ❌ Source exception: {e}")

    try:
        # ============================
        # STEP 4: LOG - Generate brew log
        # ============================
        logger.info("📝 Step 4: Log - Generating brew log...")
        
        from app.services.brew_logger import generate_brew_log
        
        # Test log generation (dry run - don't actually push to GitHub)
        log_content = generate_brew_log(
            recipe_name="E2E Test IPA",
            og=1.065,
            fg=1.012,
            abv=7.0,
            notes="E2E Integration Test - DO NOT COMMIT",
            dry_run=True
        )
        
        if log_content and not log_content.get("error"):
            results["log"]["status"] = "pass"
            results["log"]["markdown_length"] = len(log_content.get("markdown", ""))
            logger.info(f"   ✅ Generated {results['log']['markdown_length']} char log")
        else:
            results["log"]["status"] = "fail"
            results["log"]["error"] = log_content.get("error", "Log generation failed")
            logger.error(f"   ❌ Log failed: {results['log']['error']}")
            
    except Exception as e:
        results["log"]["status"] = "error"
        results["log"]["error"] = str(e)
        logger.error(f"   ❌ Log exception: {e}")

    # ============================
    # SUMMARY
    # ============================
    passed = sum(1 for r in results.values() if r["status"] == "pass")
    skipped = sum(1 for r in results.values() if r["status"] == "skip")
    failed = sum(1 for r in results.values() if r["status"] in ["fail", "error"])
    
    logger.info("=" * 50)
    logger.info(f"🏁 E2E Test Complete: {passed}/4 passed, {skipped} skipped, {failed} failed")
    logger.info("=" * 50)
    
    results["summary"] = {
        "passed": passed,
        "skipped": skipped,
        "failed": failed,
        "overall": "PASS" if failed == 0 else "FAIL"
    }
    
    return results


if __name__ == "__main__":
    # Add app to path
    sys.path.insert(0, '.')
    sys.path.insert(0, './app')
    
    results = test_e2e_workflow()
    
    print("\n" + "=" * 50)
    print("FULL RESULTS:")
    print(json.dumps(results, indent=2, default=str))
    
    # Exit with code based on result
    sys.exit(0 if results["summary"]["overall"] == "PASS" else 1)
