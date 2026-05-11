import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies before import
sys.modules["influxdb_client"] = MagicMock()
sys.modules["influxdb_client.client"] = MagicMock()
sys.modules["influxdb_client.client.write_api"] = MagicMock()
sys.modules["serpapi"] = MagicMock()

from app.services.sourcing import extract_price, parse_product_page

class TestSourcing(unittest.TestCase):
    def test_extract_price(self):
        cases = [
            ("£13.95", 13.95),
            ("Price: £10.00", 10.00),
            ("12.50 GBP", 12.50),
            ("Cost: 5.99", 5.99),
            ("Just a number 7.50", None), 
            ("7.50", 7.50),
            ("1,000.00", 1000.0),
            (None, None),
            ("No price here", None)
        ]
        
        for text, expected in cases:
            with self.subTest(text=text):
                result = extract_price(text)
                self.assertEqual(result, expected)

    def test_parse_tmm(self):
        html = """
        <html>
            <h1 class="product_title entry-title">Citra Whole Hops 100g</h1>
            <p class="price"><span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">£</span>7.50</bdi></span></p>
        </html>
        """
        result = parse_product_page(html, "The Malt Miller")
        self.assertEqual(result['price'], 7.50)
        self.assertEqual(result['weight'], "100g")

    def test_parse_geb(self):
        html = """
        <html>
            <h1>Citra Hops 100g</h1>
            <span itemprop="price" content="6.50">£6.50</span>
        </html>
        """
        result = parse_product_page(html, "Get Er Brewed")
        self.assertEqual(result['price'], 6.50)
        self.assertEqual(result['weight'], "100g")

    def test_parse_fallback(self):
        html = """
        <html>
            <meta property="product:price:amount" content="12.99" />
        </html>
        """
        result = parse_product_page(html, "Other")
        self.assertEqual(result['price'], 12.99)

if __name__ == "__main__":
    unittest.main()
