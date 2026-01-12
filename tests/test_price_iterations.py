#!/usr/bin/env python3
"""
Iteration Test: Price Comparison Function (v4 - Fixed detection)
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules["serpapi"] = MagicMock()

from app.services.sourcing import get_page_content, parse_product_page

# CORRECTED Product URLs
TEST_CASES = [
    {"name": "Citra Hops TMM", "url": "https://www.themaltmiller.co.uk/product/citra/", "vendor": "The Malt Miller"},
    {"name": "Cascade Hops TMM", "url": "https://www.themaltmiller.co.uk/product/cascade/", "vendor": "The Malt Miller"},
    {"name": "Simcoe Hops TMM", "url": "https://www.themaltmiller.co.uk/product/simcoe/", "vendor": "The Malt Miller"},
]

def run_iteration(test_case, iteration):
    results = {"name": test_case["name"], "iteration": iteration, "vendor": test_case["vendor"]}
    
    print(f"\n{'='*60}")
    print(f"ITERATION {iteration}: {test_case['name']}")
    print(f"URL: {test_case['url']}")
    print(f"{'='*60}")
    
    html = get_page_content(test_case["url"])
    
    if html:
        print(f"✅ HTML fetched: {len(html)} chars")
        
        # Parse the page
        data = parse_product_page(html, test_case["vendor"])
        print(f"Parsed: {data}")
        
        results["price"] = data.get("price") if data else None
        results["weight"] = data.get("weight") if data else None
        results["status"] = "OK" if data and data.get("price") else "NO_PRICE"
    else:
        print("❌ Failed to fetch HTML")
        results["status"] = "FETCH_FAILED"
        results["price"] = None
        results["weight"] = None
    
    return results

def main():
    print("🧪 PRICE EXTRACTION ITERATION TEST v4 (TMM Only)")
    print("=" * 60)
    
    all_results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        result = run_iteration(test_case, i)
        all_results.append(result)
    
    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"{'#':<3} {'Item':<25} {'Price':<12} {'Weight':<10} {'Status'}")
    print("-" * 80)
    
    for r in all_results:
        price = r.get("price", "N/A") or "N/A"
        weight = r.get("weight", "N/A") or "N/A"
        if isinstance(price, float): price = f"£{price:.2f}"
        status_icon = "✅" if r.get("status") == "OK" else "❌"
        print(f"{r['iteration']:<3} {r['name']:<25} {str(price):<12} {str(weight):<10} {status_icon} {r.get('status')}")
    
    ok_count = sum(1 for r in all_results if r.get("status") == "OK")
    print(f"\n{ok_count}/{len(all_results)} successful extractions")

if __name__ == "__main__":
    main()
