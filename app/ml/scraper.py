import os
import sqlite3
import logging
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "external_recipes.db")

def init_db():
    """Initialize the external recipes database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        style TEXT,
        og REAL,
        fg REAL,
        abv REAL,
        ibu REAL,
        yeast TEXT,
        source_url TEXT,
        last_updated DATETIME
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_style ON recipes(style)')
    conn.commit()
    conn.close()
    logger.info(f"Initialized external recipes database at {DB_PATH}")

def save_recipe(recipe: Dict[str, Any]):
    """Save a normalized recipe to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO recipes (name, style, og, fg, abv, ibu, yeast, source_url, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        recipe.get('name'),
        recipe.get('style'),
        recipe.get('og'),
        recipe.get('fg'),
        recipe.get('abv'),
        recipe.get('ibu'),
        recipe.get('yeast'),
        recipe.get('source_url'),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()

def batch_save_recipes(recipes: List[Dict[str, Any]]):
    """Save multiple recipes in a single transaction."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.executemany('''
    INSERT INTO recipes (name, style, og, fg, abv, ibu, yeast, source_url, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (
            r.get('name'),
            r.get('style'),
            r.get('og'),
            r.get('fg'),
            r.get('abv'),
            r.get('ibu'),
            r.get('yeast'),
            r.get('source_url'),
            datetime.now().isoformat()
        ) for r in recipes
    ])
    
    conn.commit()
    conn.close()
    logger.info(f"Saved {len(recipes)} recipes to database")

def scrape_open_brewing_data():
    """
    Example scraper for the Open Brewing dataset (or similar).
    For now, this is a placeholder mimicking the retrieval of a JSON dataset.
    """
    # Placeholder URL - in a real scenario, this would be a GitHub Raw URL or API
    DATASET_URL = "https://raw.githubusercontent.com/openbrewing/beerjson/master/examples/pale_ale.json"
    
    try:
        # This is a conceptual implementation. We will use local BeerXML or mock data
        # to demonstrate the pipeline since we don't want to rely on external uptime for this demo.
        logger.info("Starting recipe scraping from external sources...")
        
        # Real-world datasets often come in BeerJSON or BeerXML
        # We will implement a robust parser for these formats.
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")

def get_style_averages(style_name: str) -> Dict[str, Any]:
    """Get average metrics for a given style from the external database."""
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Simple fuzzy match for style
    cursor.execute('''
    SELECT AVG(og), AVG(fg), AVG(abv), AVG(ibu), COUNT(*) 
    FROM recipes 
    WHERE style LIKE ?
    ''', (f'%{style_name}%',))
    
    row = cursor.fetchone()
    conn.close()
    
    if row and row[4] > 0:
        return {
            "avg_og": round(row[0], 3),
            "avg_fg": round(row[1], 3),
            "avg_abv": round(row[2], 1),
            "avg_ibu": round(row[3], 1),
            "sample_size": row[4]
        }
    return {}

if __name__ == "__main__":
    init_db()
    # For testing: add a set of mock recipes
    mock_recipes = [
        {"name": "Classic IPA", "style": "American IPA", "og": 1.065, "fg": 1.012, "abv": 7.0, "ibu": 65, "yeast": "US-05", "source_url": "manual"},
        {"name": "West Coast Legend", "style": "American IPA", "og": 1.070, "fg": 1.010, "abv": 7.8, "ibu": 85, "yeast": "WLP001", "source_url": "manual"},
        {"name": "Hazy Days", "style": "New England IPA", "og": 1.062, "fg": 1.015, "abv": 6.2, "ibu": 35, "yeast": "London Fog", "source_url": "manual"},
        {"name": "Dry Stout", "style": "Irish Stout", "og": 1.042, "fg": 1.010, "abv": 4.2, "ibu": 35, "yeast": "WLP004", "source_url": "manual"},
        {"name": "Imperial Stout", "style": "Imperial Stout", "og": 1.100, "fg": 1.025, "abv": 10.5, "ibu": 75, "yeast": "US-05", "source_url": "manual"},
        {"name": "German Pils", "style": "German Pils", "og": 1.048, "fg": 1.008, "abv": 5.0, "ibu": 35, "yeast": "WLP830", "source_url": "manual"},
        {"name": "Summer Saison", "style": "Saison", "og": 1.055, "fg": 1.004, "abv": 6.7, "ibu": 30, "yeast": "Belle Saison", "source_url": "manual"}
    ]
    batch_save_recipes(mock_recipes)
    print(get_style_averages("IPA"))
    print(get_style_averages("Stout"))
