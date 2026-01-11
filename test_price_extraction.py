
import re

# Copy of the function from app/services/sourcing.py
def extract_price(text):
    if not text: return None
    # Clean text
    text = text.replace(',', '') # Handle 1,000.00
    
    # 1. Look for £ followed by digits
    match = re.search(r'£\s?(\d+(?:\.\d{2})?)', text)
    if match:
            return float(match.group(1))
            
    # 2. Look for "GBP" or pure numbers if context suggests (simplified)
    # Often rich snippets just have the number "13.95"
    try:
        # If text is just a number (common in rich snippet 'price' field)
        return float(text)
    except:
        pass
        
    return None

test_cases = [
    ("£13.95", 13.95),
    ("£ 13.95", 13.95),
    ("13.95", 13.95),
    ("Price: £13.95", 13.95),
    ("Price: 13.95", None), # Current logic might fail this if it expects just number or £
    ("13.95 GBP", None),    # Should fail currently
    ("£1,200.00", 1200.0),
    ("From £10.00", 10.0),
    ("£10", 10.0)
]

print("Running Price Extraction Tests...")
for input_str, expected in test_cases:
    result = extract_price(input_str)
    status = "✅" if result == expected else f"❌ (Expected {expected}, got {result})"
    print(f"Input: '{input_str}' -> {status}")
