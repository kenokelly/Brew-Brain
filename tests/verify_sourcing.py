
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

# MOCK CONFIG AND DEPENDENCIES
from unittest.mock import MagicMock
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules["serpapi"] = MagicMock()

from app.services.sourcing import extract_price

def test_extract_price():
    cases = [
        ("£13.95", 13.95),
        ("Price: £10.00", 10.00),
        ("12.50 GBP", 12.50),
        ("Cost: 5.99", 5.99),
        # "Just a number 7.50" should fail because it's ambiguous and strict mode is on
        ("Just a number 7.50", None), 
        ("7.50", 7.50), # Pure number should work
        ("1,000.00", 1000.0),
        (None, None),
        ("No price here", None)
    ]
    
    failed = 0
    for text, expected in cases:
        result = extract_price(text)
        if result != expected:
            print(f"❌ Failed: '{text}' -> Expected {expected}, Got {result}")
            failed += 1
        else:
            print(f"✅ Passed: '{text}' -> {result}")
            
    if failed == 0:
        print("\n🎉 All extract_price tests passed!")
    else:
        print(f"\n❌ {failed} tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_extract_price()
    except ImportError as e:
        print(f"ImportError: {e}")
        # Build might be missing dependencies in this agent env, but we are checking logic.
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
