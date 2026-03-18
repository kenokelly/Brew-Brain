import os
import sqlite3
import logging
import requests
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "external_recipes.db")

# --- Curated public BeerXML sources ---
# Each entry: (url, description)
SEED_SOURCES: List[Tuple[str, str]] = [
    (
        "https://raw.githubusercontent.com/BeerXML/BeerXML-Standard/master/samples/recipes.xml",
        "BeerXML standard sample recipes"
    ),
    (
        "https://raw.githubusercontent.com/homebrew-formula/beer-recipes/main/recipes.xml",
        "Homebrew community recipe archive"
    ),
]


def _compute_hash(recipe: Dict[str, Any]) -> str:
    """Compute a deterministic hash for deduplication."""
    key = f"{recipe.get('name', '')}|{recipe.get('style', '')}|{recipe.get('og', '')}|{recipe.get('fg', '')}|{recipe.get('source_url', '')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def init_db():
    """Initialize the external recipes database with latest schema."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
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
        grain_bill TEXT,
        hop_bill TEXT,
        description TEXT,
        source_url TEXT,
        source_hash TEXT UNIQUE,
        last_updated DATETIME
    )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_style ON recipes(style)')

    # --- Schema migration: add columns if missing on older DBs ---
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(recipes)").fetchall()}
    for col, col_type in [("grain_bill", "TEXT"), ("hop_bill", "TEXT"),
                          ("description", "TEXT"), ("source_hash", "TEXT")]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE recipes ADD COLUMN {col} {col_type}")
            logger.info(f"Migrated: added column '{col}' to recipes table")

    # Create indexes on source_hash AFTER migration ensures column exists
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_hash ON recipes(source_hash)')
    try:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_source_hash_unique ON recipes(source_hash)')
    except sqlite3.OperationalError:
        pass  # Index already exists or hash column has dupes pre-migration

    conn.commit()
    conn.close()
    logger.info(f"Initialized external recipes database at {DB_PATH}")


def recipe_count() -> Dict[str, Any]:
    """Return total recipe count and per-style breakdown."""
    if not os.path.exists(DB_PATH):
        return {"total": 0, "styles": {}}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    rows = cursor.execute(
        "SELECT style, COUNT(*) FROM recipes GROUP BY style ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()

    return {
        "total": total,
        "styles": {row[0]: row[1] for row in rows if row[0]},
    }


def deduplicate() -> int:
    """
    Backfill source_hash for rows that lack one, then remove duplicates.
    Returns the number of duplicate rows removed.
    """
    if not os.path.exists(DB_PATH):
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Backfill hashes on rows that have none
    rows = cursor.execute(
        "SELECT id, name, style, og, fg, source_url FROM recipes WHERE source_hash IS NULL"
    ).fetchall()

    removed = 0
    for row in rows:
        rid, name, style, og, fg, source_url = row
        key = f"{name or ''}|{style or ''}|{og or ''}|{fg or ''}|{source_url or ''}"
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        try:
            cursor.execute("UPDATE recipes SET source_hash = ? WHERE id = ?", (h, rid))
        except sqlite3.IntegrityError:
            # Duplicate — another row already has this hash
            cursor.execute("DELETE FROM recipes WHERE id = ?", (rid,))
            removed += 1

    conn.commit()
    conn.close()
    logger.info(f"Deduplication complete: {removed} duplicates removed, {len(rows)} rows checked")
    return removed


def save_recipe(recipe: Dict[str, Any]) -> bool:
    """
    Save a normalized recipe to the database.
    Returns True if inserted, False if duplicate.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    h = _compute_hash(recipe)

    try:
        cursor.execute('''
        INSERT INTO recipes (name, style, og, fg, abv, ibu, yeast, grain_bill, hop_bill,
                             description, source_url, source_hash, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recipe.get('name'),
            recipe.get('style'),
            recipe.get('og'),
            recipe.get('fg'),
            recipe.get('abv'),
            recipe.get('ibu'),
            recipe.get('yeast'),
            recipe.get('grain_bill'),
            recipe.get('hop_bill'),
            recipe.get('description'),
            recipe.get('source_url'),
            h,
            datetime.now().isoformat()
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Duplicate hash — skip
        return False
    finally:
        conn.close()


def batch_save_recipes(recipes: List[Dict[str, Any]]) -> int:
    """
    Save multiple recipes in a single transaction, skipping duplicates.
    Returns the number of new recipes inserted.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0

    for r in recipes:
        h = _compute_hash(r)
        try:
            cursor.execute('''
            INSERT INTO recipes (name, style, og, fg, abv, ibu, yeast, grain_bill, hop_bill,
                                 description, source_url, source_hash, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r.get('name'),
                r.get('style'),
                r.get('og'),
                r.get('fg'),
                r.get('abv'),
                r.get('ibu'),
                r.get('yeast'),
                r.get('grain_bill'),
                r.get('hop_bill'),
                r.get('description'),
                r.get('source_url'),
                h,
                datetime.now().isoformat()
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            continue  # Duplicate — skip

    conn.commit()
    conn.close()
    logger.info(f"Batch save: {inserted}/{len(recipes)} new recipes inserted")
    return inserted


def parse_beerxml(xml_content: str) -> List[Dict[str, Any]]:
    """Parse a BeerXML string and extract core recipe metrics + ingredient bills."""
    recipes = []
    try:
        root = ET.fromstring(xml_content)

        recipe_nodes = root.findall('.//RECIPE')
        if not recipe_nodes and root.tag.upper() == 'RECIPE':
            recipe_nodes = [root]

        for node in recipe_nodes:
            def get_text(parent, tag_name, default=None):
                for child in parent:
                    if child.tag.upper() == tag_name.upper():
                        return child.text
                return default

            name = get_text(node, 'NAME', 'Unknown')

            # Style
            style_name = "Unknown"
            style_node = None
            for child in node:
                if child.tag.upper() == 'STYLE':
                    style_node = child
                    break
            if style_node is not None:
                style_name = get_text(style_node, 'NAME', style_name)

            # Primary Yeast
            yeast_name = "Unknown"
            yeasts_node = None
            for child in node:
                if child.tag.upper() == 'YEASTS':
                    yeasts_node = child
                    break
            if yeasts_node is not None:
                yeast_node = None
                for child in yeasts_node:
                    if child.tag.upper() == 'YEAST':
                        yeast_node = child
                        break
                if yeast_node is not None:
                    yeast_name = get_text(yeast_node, 'NAME', yeast_name)

            # --- Extract grain bill ---
            grain_names = []
            fermentables_node = None
            for child in node:
                if child.tag.upper() == 'FERMENTABLES':
                    fermentables_node = child
                    break
            if fermentables_node is not None:
                for ferm in fermentables_node:
                    if ferm.tag.upper() == 'FERMENTABLE':
                        gname = get_text(ferm, 'NAME')
                        if gname:
                            grain_names.append(gname.strip())

            # --- Extract hop bill ---
            hop_names = []
            hops_node = None
            for child in node:
                if child.tag.upper() == 'HOPS':
                    hops_node = child
                    break
            if hops_node is not None:
                for hop in hops_node:
                    if hop.tag.upper() == 'HOP':
                        hname = get_text(hop, 'NAME')
                        if hname:
                            hop_names.append(hname.strip())

            # Quantitative metrics
            try:
                og = float(get_text(node, 'EST_OG') or get_text(node, 'OG') or 1.000)
                fg = float(get_text(node, 'EST_FG') or get_text(node, 'FG') or 1.000)
                abv = float(get_text(node, 'EST_ABV') or get_text(node, 'ABV') or 0.0)
                ibu = float(get_text(node, 'IBU') or get_text(node, 'EST_IBU') or 0.0)
            except ValueError:
                continue  # Skip if unparseable numbers

            recipe = {
                "name": name,
                "style": style_name,
                "og": round(og, 3),
                "fg": round(fg, 3),
                "abv": round(abv, 1),
                "ibu": round(ibu, 1),
                "yeast": yeast_name,
                "grain_bill": ", ".join(grain_names) if grain_names else None,
                "hop_bill": ", ".join(hop_names) if hop_names else None,
                "source_url": "api_ingest"
            }
            recipes.append(recipe)

    except ET.ParseError as e:
        logger.error(f"Failed to parse BeerXML: {e}")

    return recipes


def scrape_open_brewing_data(url: str = None) -> int:
    """
    Downloads and parses a BeerXML from a URL and saves it.
    Returns the number of NEW recipes saved (deduped).
    """
    if not url:
        return 0

    try:
        logger.info(f"Downloading external recipe batch from {url}...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        recipes = parse_beerxml(resp.text)
        if recipes:
            for r in recipes:
                r["source_url"] = url
            inserted = batch_save_recipes(recipes)
            logger.info(f"Ingested {inserted} new recipes ({len(recipes)} parsed) from {url}")
            return inserted

    except requests.Timeout:
        logger.error(f"Timeout fetching {url}")
    except requests.RequestException as e:
        logger.error(f"URL fetch failed for {url}: {e}")
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")

    return 0


def ingest_all_sources() -> Dict[str, Any]:
    """
    Iterate all SEED_SOURCES and ingest recipes.
    Returns summary of ingestion results.
    """
    init_db()
    results = []
    total_inserted = 0

    for url, description in SEED_SOURCES:
        try:
            count = scrape_open_brewing_data(url)
            total_inserted += count
            results.append({"url": url, "description": description, "inserted": count, "status": "ok"})
        except Exception as e:
            logger.error(f"Failed to ingest {url}: {e}")
            results.append({"url": url, "description": description, "inserted": 0, "status": f"error: {e}"})

    stats = recipe_count()
    logger.info(f"Ingestion complete: {total_inserted} new recipes. DB total: {stats['total']}")

    return {
        "total_inserted": total_inserted,
        "sources_processed": len(results),
        "source_results": results,
        "db_total": stats["total"],
    }


def get_style_averages(style_name: str) -> Dict[str, Any]:
    """Get average metrics for a given style from the external database."""
    if not os.path.exists(DB_PATH):
        return {}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

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
        {"name": "Classic IPA", "style": "American IPA", "og": 1.065, "fg": 1.012, "abv": 7.0, "ibu": 65, "yeast": "US-05", "grain_bill": "Pale Malt, Crystal 40L", "hop_bill": "Centennial, Cascade, Simcoe", "source_url": "manual"},
        {"name": "West Coast Legend", "style": "American IPA", "og": 1.070, "fg": 1.010, "abv": 7.8, "ibu": 85, "yeast": "WLP001", "grain_bill": "Pale Malt, Munich, Crystal 60L", "hop_bill": "Simcoe, Citra, Amarillo", "source_url": "manual"},
        {"name": "Hazy Days", "style": "New England IPA", "og": 1.062, "fg": 1.015, "abv": 6.2, "ibu": 35, "yeast": "London Fog", "grain_bill": "Pale Malt, Wheat Malt, Flaked Oats", "hop_bill": "Citra, Galaxy, Mosaic", "source_url": "manual"},
        {"name": "Dry Stout", "style": "Irish Stout", "og": 1.042, "fg": 1.010, "abv": 4.2, "ibu": 35, "yeast": "WLP004", "grain_bill": "Pale Malt, Roasted Barley, Flaked Barley", "hop_bill": "East Kent Goldings, Fuggles", "source_url": "manual"},
        {"name": "Imperial Stout", "style": "Imperial Stout", "og": 1.100, "fg": 1.025, "abv": 10.5, "ibu": 75, "yeast": "US-05", "grain_bill": "Pale Malt, Chocolate Malt, Roasted Barley, Crystal 120L", "hop_bill": "Magnum, Willamette", "source_url": "manual"},
        {"name": "German Pils", "style": "German Pils", "og": 1.048, "fg": 1.008, "abv": 5.0, "ibu": 35, "yeast": "WLP830", "grain_bill": "Pilsner Malt", "hop_bill": "Hallertau, Saaz", "source_url": "manual"},
        {"name": "Summer Saison", "style": "Saison", "og": 1.055, "fg": 1.004, "abv": 6.7, "ibu": 30, "yeast": "Belle Saison", "grain_bill": "Pilsner Malt, Wheat Malt, Vienna Malt", "hop_bill": "Styrian Goldings, Saaz", "source_url": "manual"}
    ]
    inserted = batch_save_recipes(mock_recipes)
    print(f"Inserted: {inserted}")
    print(f"Stats: {recipe_count()}")
    print(f"IPA averages: {get_style_averages('IPA')}")
    print(f"Stout averages: {get_style_averages('Stout')}")
