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
        
        from app.services.scout import search_recipes
        
        scout_result = search_recipes("hazy ipa")
        
        # search_recipes returns a list directly, or a list with one error dict
        if scout_result and isinstance(scout_result, list) and "error" not in scout_result[0]:
            results["scout"]["status"] = "pass"
            results["scout"]["recipe_count"] = len(scout_result)
            recipe = scout_result[0]
            results["scout"]["sample_recipe"] = recipe.get("title")
            logger.info(f"   ✅ Found {results['scout']['recipe_count']} recipes")
        else:
            results["scout"]["status"] = "fail"
            results["scout"]["error"] = scout_result[0].get("title", "Unknown error") if scout_result else "No results"
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
            "batch_size_l": 20,
            "total_grain_kg": 5.5, # Added required field
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
        
        # Note: function uses 'batch_size_l' not 'batch_size'
        scale_result = scale_recipe_to_equipment(test_recipe)
        
        if scale_result and not scale_result.get("error"):
            results["scale"]["status"] = "pass"
            results["scale"]["scaled_batch_size"] = scale_result.get("batch_size_l")
            results["scale"]["grain_kg"] = scale_result.get("total_grain_kg")
            logger.info(f"   ✅ Scaled to {scale_result.get('batch_size_l')}L, {scale_result.get('total_grain_kg')}kg grain")
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
        
        from app.services.brew_logger import generate_log_content
        
        # Test log generation (dry run - just generate content)
        batch_data = {
            "og": 1.065,
            "fg": 1.012,
            "volume": 20,
            "time": 60
        }
        
        log_content = generate_log_content(
            recipe_name="E2E Test IPA",
            batch_data=batch_data,
            water_profile=None,
            sourcing_data=None
        )
        
        if log_content:
            results["log"]["status"] = "pass"
            results["log"]["markdown_length"] = len(log_content)
            logger.info(f"   ✅ Generated {results['log']['markdown_length']} char log")
        else:
            results["log"]["status"] = "fail"
            results["log"]["error"] = "Log content empty"
            logger.error(f"   ❌ Log failed: Empty content")
            
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
