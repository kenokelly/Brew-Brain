"""
Tests for Phase 4 — External Learning

Covers:
- scraper.py: deduplication, BeerXML parsing with ingredient extraction, recipe_count
- peer_comparison.py: percentile ranking, z-score, compare() output
- style_intelligence.py: ingredient-aware similarity
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

# Point the DB to a temp file for test isolation
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["BREW_BRAIN_DATA"] = os.path.dirname(_test_db.name)

# Patch DB_PATH before importing modules under test
import app.ml.scraper as scraper
import app.ml.peer_comparison as peer_mod

scraper.DB_PATH = _test_db.name
peer_mod.DB_PATH = _test_db.name

BEERXML_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<RECIPES>
  <RECIPE>
    <NAME>Test West Coast IPA</NAME>
    <STYLE><NAME>American IPA</NAME></STYLE>
    <YEASTS><YEAST><NAME>US-05</NAME></YEAST></YEASTS>
    <FERMENTABLES>
      <FERMENTABLE><NAME>Pale Malt</NAME></FERMENTABLE>
      <FERMENTABLE><NAME>Crystal 40L</NAME></FERMENTABLE>
    </FERMENTABLES>
    <HOPS>
      <HOP><NAME>Centennial</NAME></HOP>
      <HOP><NAME>Cascade</NAME></HOP>
    </HOPS>
    <EST_OG>1.065</EST_OG>
    <EST_FG>1.012</EST_FG>
    <EST_ABV>7.0</EST_ABV>
    <IBU>65</IBU>
  </RECIPE>
  <RECIPE>
    <NAME>Oatmeal Stout</NAME>
    <STYLE><NAME>Oatmeal Stout</NAME></STYLE>
    <YEASTS><YEAST><NAME>WLP004</NAME></YEAST></YEASTS>
    <FERMENTABLES>
      <FERMENTABLE><NAME>Pale Malt</NAME></FERMENTABLE>
      <FERMENTABLE><NAME>Roasted Barley</NAME></FERMENTABLE>
      <FERMENTABLE><NAME>Flaked Oats</NAME></FERMENTABLE>
    </FERMENTABLES>
    <HOPS>
      <HOP><NAME>East Kent Goldings</NAME></HOP>
    </HOPS>
    <EST_OG>1.052</EST_OG>
    <EST_FG>1.014</EST_FG>
    <EST_ABV>5.0</EST_ABV>
    <IBU>30</IBU>
  </RECIPE>
</RECIPES>
"""


class TestScraperDeduplication(unittest.TestCase):

    def setUp(self):
        scraper.init_db()

    def tearDown(self):
        conn = sqlite3.connect(_test_db.name)
        conn.execute("DELETE FROM recipes")
        conn.commit()
        conn.close()

    def test_batch_save_dedup(self):
        """Inserting the same recipe twice should only count once."""
        recipe = {
            "name": "Dupe Test", "style": "IPA", "og": 1.060,
            "fg": 1.010, "abv": 6.5, "ibu": 50, "yeast": "US-05",
            "source_url": "test"
        }
        first_count = scraper.batch_save_recipes([recipe])
        second_count = scraper.batch_save_recipes([recipe])
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)

        stats = scraper.recipe_count()
        self.assertEqual(stats["total"], 1)

    def test_save_recipe_dedup(self):
        """Single-insert dedup via save_recipe."""
        recipe = {
            "name": "Single Test", "style": "Stout", "og": 1.050,
            "fg": 1.012, "abv": 5.0, "ibu": 35, "yeast": "WLP004",
            "source_url": "test"
        }
        self.assertTrue(scraper.save_recipe(recipe))
        self.assertFalse(scraper.save_recipe(recipe))

    def test_recipe_count(self):
        """recipe_count returns correct totals and style breakdown."""
        recipes = [
            {"name": "A", "style": "IPA", "og": 1.065, "fg": 1.012, "abv": 7.0, "ibu": 65, "yeast": "US-05", "source_url": "test"},
            {"name": "B", "style": "IPA", "og": 1.070, "fg": 1.010, "abv": 7.8, "ibu": 85, "yeast": "WLP001", "source_url": "test"},
            {"name": "C", "style": "Stout", "og": 1.042, "fg": 1.010, "abv": 4.2, "ibu": 35, "yeast": "WLP004", "source_url": "test"},
        ]
        scraper.batch_save_recipes(recipes)
        stats = scraper.recipe_count()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["styles"]["IPA"], 2)
        self.assertEqual(stats["styles"]["Stout"], 1)


class TestBeerXMLParsing(unittest.TestCase):

    def test_parse_extracts_ingredients(self):
        """parse_beerxml should extract grain_bill and hop_bill."""
        recipes = scraper.parse_beerxml(BEERXML_SAMPLE)
        self.assertEqual(len(recipes), 2)

        ipa = recipes[0]
        self.assertEqual(ipa["name"], "Test West Coast IPA")
        self.assertEqual(ipa["style"], "American IPA")
        self.assertEqual(ipa["yeast"], "US-05")
        self.assertEqual(ipa["og"], 1.065)
        self.assertEqual(ipa["fg"], 1.012)
        self.assertIn("Pale Malt", ipa["grain_bill"])
        self.assertIn("Crystal 40L", ipa["grain_bill"])
        self.assertIn("Centennial", ipa["hop_bill"])
        self.assertIn("Cascade", ipa["hop_bill"])

        stout = recipes[1]
        self.assertEqual(stout["style"], "Oatmeal Stout")
        self.assertIn("Roasted Barley", stout["grain_bill"])
        self.assertIn("Flaked Oats", stout["grain_bill"])

    def test_parse_invalid_xml(self):
        """Malformed XML should return empty list, not crash."""
        result = scraper.parse_beerxml("<not valid xml")
        self.assertEqual(result, [])


class TestPeerComparison(unittest.TestCase):

    def setUp(self):
        scraper.init_db()
        # Seed population for "American IPA"
        population = [
            {"name": f"IPA #{i}", "style": "American IPA", "og": 1.060 + i * 0.005,
             "fg": 1.010 + i * 0.001, "abv": 6.5 + i * 0.3, "ibu": 55 + i * 5,
             "yeast": "US-05", "source_url": "test"}
            for i in range(10)
        ]
        scraper.batch_save_recipes(population)

    def tearDown(self):
        conn = sqlite3.connect(_test_db.name)
        conn.execute("DELETE FROM recipes")
        conn.commit()
        conn.close()

    def test_compare_returns_percentiles(self):
        """compare() should return percentile rankings for each metric."""
        pc = peer_mod.PeerComparison()
        result = pc.compare(
            {"og": 1.065, "fg": 1.012, "abv": 7.0, "ibu": 65},
            "American IPA"
        )
        self.assertEqual(result["style"], "American IPA")
        self.assertGreater(result["sample_size"], 0)
        self.assertIn("comparisons", result)
        self.assertIn("og", result["comparisons"])
        self.assertIn("percentile", result["comparisons"]["og"])
        self.assertIsNotNone(result["comparisons"]["og"]["percentile"])

    def test_compare_attenuation(self):
        """compare() should compute attenuation percentile when OG+FG given."""
        pc = peer_mod.PeerComparison()
        result = pc.compare(
            {"og": 1.070, "fg": 1.012},
            "American IPA"
        )
        self.assertIn("attenuation", result.get("comparisons", {}))

    def test_compare_insufficient_data(self):
        """compare() should return an error message for unknown styles."""
        pc = peer_mod.PeerComparison()
        result = pc.compare(
            {"og": 1.050, "fg": 1.010},
            "Nonexistent Experimental Style"
        )
        self.assertIn("error", result)

    def test_percentile_rank(self):
        """Verify percentile calculation against a known distribution."""
        pc = peer_mod.PeerComparison()
        pop = [1.0, 2.0, 3.0, 4.0, 5.0]
        # 3.0 → 3/5 = 60th percentile
        self.assertAlmostEqual(pc._percentile_rank(3.0, pop), 60.0)
        # 1.0 → 1/5 = 20th percentile
        self.assertAlmostEqual(pc._percentile_rank(1.0, pop), 20.0)

    def test_z_score(self):
        """Verify z-score calculation."""
        pc = peer_mod.PeerComparison()
        pop = [10.0, 10.0, 10.0, 10.0]
        self.assertEqual(pc._z_score(10.0, pop), 0.0)


class TestDeduplicate(unittest.TestCase):

    def setUp(self):
        scraper.init_db()

    def tearDown(self):
        conn = sqlite3.connect(_test_db.name)
        conn.execute("DELETE FROM recipes")
        conn.commit()
        conn.close()

    def test_deduplicate_backfill(self):
        """deduplicate() should handle rows with NULL source_hash."""
        # Manually insert rows without source_hash to simulate pre-migration data
        conn = sqlite3.connect(_test_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recipes (name, style, og, fg, source_url, source_hash)
            VALUES ('Old Recipe', 'IPA', 1.060, 1.010, 'test', NULL)
        """)
        cursor.execute("""
            INSERT INTO recipes (name, style, og, fg, source_url, source_hash)
            VALUES ('Old Recipe', 'IPA', 1.060, 1.010, 'test', NULL)
        """)
        conn.commit()
        conn.close()

        removed = scraper.deduplicate()
        self.assertEqual(removed, 1)

        stats = scraper.recipe_count()
        self.assertEqual(stats["total"], 1)


if __name__ == "__main__":
    unittest.main()
