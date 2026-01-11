import re
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

import unittest

class TestPriceExtraction(unittest.TestCase):
    def test_basic_pounds(self):
        self.assertEqual(extract_price("£10.50"), 10.50)
        self.assertEqual(extract_price("Price: £15.00"), 15.00)
    
    def test_no_symbol(self):
        self.assertEqual(extract_price("12.99"), 12.99)
        self.assertEqual(extract_price("13.5"), 13.5)
        
    def test_dirty_text(self):
        self.assertEqual(extract_price("Starts from £9.99"), 9.99)
        self.assertIsNone(extract_price("Call for price"))

if __name__ == '__main__':
    unittest.main()
