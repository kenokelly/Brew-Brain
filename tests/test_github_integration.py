import sys
import os
from unittest.mock import MagicMock

sys.modules['github'] = MagicMock()
sys.modules['influxdb_client'] = MagicMock()
sys.modules['influxdb_client.client'] = MagicMock()
sys.modules['influxdb_client.client.write_api'] = MagicMock()

import pytest
from services.github_integration import generate_fallback_beerxml

def test_generate_fallback_beerxml():
    recipe_data = {
        'name': 'Test Beer <Special>',
        'og': 1.050,
        'ibu': 30,
        'abv': 5.0,
        'source_url': 'http://example.com/recipe.xml'
    }

    xml_str = generate_fallback_beerxml(recipe_data)

    # Check that special characters are escaped properly
    assert "Test Beer &lt;Special&gt;" in xml_str
    assert "<NAME>Test Beer &lt;Special&gt;</NAME>" in xml_str

    # Check that standard fields are present
    assert "<OG>1.05</OG>" in xml_str
    assert "<IBU>30</IBU>" in xml_str
    assert "<EST_ABV>5.0</EST_ABV>" in xml_str
    assert "<SOURCE>http://example.com/recipe.xml</SOURCE>" in xml_str

    # Check that root structure is valid
    assert "<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>" in xml_str
    assert "<RECIPES>" in xml_str
    assert "<RECIPE>" in xml_str

def test_generate_fallback_beerxml_special_characters():
    recipe_data = {
        'name': 'Märzen Kölsch',
        'og': 1.050,
        'ibu': 30,
        'abv': 5.0,
        'source_url': 'http://example.com/recipe.xml'
    }

    xml_str = generate_fallback_beerxml(recipe_data)

    assert "Märzen Kölsch" in xml_str

def test_generate_fallback_beerxml_missing_fields():
    recipe_data = {
        'name': 'Simple Ale'
    }

    xml_str = generate_fallback_beerxml(recipe_data)

    assert "<NAME>Simple Ale</NAME>" in xml_str
    assert "<OG>None</OG>" in xml_str
    assert "<IBU>None</IBU>" in xml_str
    assert "<EST_ABV>None</EST_ABV>" in xml_str
    assert "<SOURCE>None</SOURCE>" in xml_str
    assert "<NOTES>Imported via Brew-Brain from None</NOTES>" in xml_str
