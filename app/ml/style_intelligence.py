import numpy as np
import sqlite3
import os
import logging
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "external_recipes.db")
EMBEDDINGS_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "models", "style_embeddings.joblib")


class StyleIntelligence:
    """
    Handles style embeddings and finding similar brewing styles.

    Builds TF-IDF vectors from per-style ingredient lists (grains + hops + yeast)
    so that similarity reflects actual recipe composition, not just style name text.
    Falls back to style-name similarity if ingredient data is sparse.
    """

    def __init__(self):
        self.styles: List[str] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.embeddings = None
        self._load_styles()

    def _load_styles(self):
        """Load styles from the external DB and build ingredient-based embeddings."""
        if not os.path.exists(DB_PATH):
            logger.warning("External recipes database not found, skipping style intelligence setup.")
            return

        # Try cached embeddings first
        if self._load_cached():
            return

        self._build_embeddings()

    def _load_cached(self) -> bool:
        """Attempt to load a previously saved vectorizer + embeddings from disk."""
        if not os.path.exists(EMBEDDINGS_PATH):
            return False

        try:
            cached = joblib.load(EMBEDDINGS_PATH)
            self.styles = cached["styles"]
            self.vectorizer = cached["vectorizer"]
            self.embeddings = cached["embeddings"]
            logger.info(f"Loaded cached style embeddings ({len(self.styles)} styles)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load cached embeddings, rebuilding: {e}")
            return False

    def _build_embeddings(self):
        """Build TF-IDF embeddings from per-style ingredient corpus."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Aggregate ingredient tokens per style
            cursor.execute("""
                SELECT style,
                       GROUP_CONCAT(COALESCE(grain_bill, ''), ' ') AS grains,
                       GROUP_CONCAT(COALESCE(hop_bill, ''), ' ')   AS hops,
                       GROUP_CONCAT(COALESCE(yeast, ''), ' ')      AS yeasts
                FROM recipes
                WHERE style IS NOT NULL
                GROUP BY style
            """)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                logger.warning("No recipe styles found in DB for embedding.")
                return

            self.styles = []
            documents = []

            for style, grains, hops, yeasts in rows:
                if not style:
                    continue
                self.styles.append(style)
                # Concatenate all ingredient tokens for this style into one document
                # Include the style name itself for baseline similarity
                doc = f"{style} {grains or ''} {hops or ''} {yeasts or ''}"
                documents.append(doc.strip())

            if not documents:
                return

            # Build TF-IDF with bigrams to capture e.g. "Pale Malt", "Cascade hop"
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=500,  # Keep memory bounded on Pi
                stop_words=None,  # Ingredient names are meaningful
            )
            self.embeddings = self.vectorizer.fit_transform(documents)

            logger.info(f"Built style embeddings from ingredients: {len(self.styles)} styles, "
                        f"{self.embeddings.shape[1]} features")

            # Persist to disk
            self._save_cached()

        except Exception as e:
            logger.error(f"Failed to build style embeddings: {e}")

    def _save_cached(self):
        """Persist vectorizer + embeddings to disk."""
        try:
            os.makedirs(os.path.dirname(EMBEDDINGS_PATH), exist_ok=True)
            joblib.dump({
                "styles": self.styles,
                "vectorizer": self.vectorizer,
                "embeddings": self.embeddings,
            }, EMBEDDINGS_PATH)
            logger.info(f"Saved style embeddings to {EMBEDDINGS_PATH}")
        except Exception as e:
            logger.error(f"Failed to save style embeddings: {e}")

    def rebuild(self):
        """Force rebuild of embeddings (e.g. after new data ingestion)."""
        self._build_embeddings()

    def find_similar_styles(self, target_style: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Find the most similar styles to the target style name."""
        if not self.styles or self.embeddings is None or self.vectorizer is None:
            return []

        try:
            target_vec = self.vectorizer.transform([target_style])
            similarities = cosine_similarity(target_vec, self.embeddings).flatten()
            indices = similarities.argsort()[-top_n:][::-1]

            return [(self.styles[i], float(similarities[i])) for i in indices if similarities[i] > 0.1]
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def get_style_neighborhood_metrics(self, style_name: str) -> Dict[str, Any]:
        """
        Get metrics for a style and its close neighbors.
        Useful when data for a specific style is sparse.
        """
        similar = self.find_similar_styles(style_name)
        logger.info(f"Style intelligence: found similar styles for '{style_name}': {similar}")
        if not similar:
            return {}

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Aggregate data from style and its top 2 neighbors
        relevant_styles = [s[0] for s in similar[:2]]
        logger.info(f"Style intelligence: querying data for {relevant_styles}")

        results = []
        for s in relevant_styles:
            cursor.execute('''
            SELECT AVG(og), AVG(fg), AVG(abv), AVG(ibu), COUNT(*) 
            FROM recipes 
            WHERE style = ?
            ''', (s,))
            row = cursor.fetchone()
            logger.info(f"Style intelligence: result for {s}: {row}")
            if row and row[4] > 0:
                results.append(row)

        conn.close()

        if not results:
            return {}

        # Weighted average by sample size
        total_samples = sum(r[4] for r in results)
        avg_og = sum(r[0] * r[4] for r in results) / total_samples
        avg_fg = sum(r[1] * r[4] for r in results) / total_samples
        avg_abv = sum(r[2] * r[4] for r in results) / total_samples
        avg_ibu = sum(r[3] * r[4] for r in results) / total_samples

        return {
            "primary_style": style_name,
            "included_styles": relevant_styles,
            "avg_og": round(avg_og, 3),
            "avg_fg": round(avg_fg, 3),
            "avg_abv": round(avg_abv, 1),
            "avg_ibu": round(avg_ibu, 1),
            "total_samples": total_samples
        }

    def get_style_profile(self, style_name: str) -> Dict[str, Any]:
        """
        Return the ingredient fingerprint for a style: top grains, top hops,
        typical OG/FG/IBU ranges, and sample count.
        """
        if not os.path.exists(DB_PATH):
            return {}

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT grain_bill, hop_bill, yeast, og, fg, ibu, abv
            FROM recipes
            WHERE style LIKE ?
              AND (grain_bill IS NOT NULL OR hop_bill IS NOT NULL)
        """, (f"%{style_name}%",))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {}

        # Tally ingredient frequency
        grain_counts: Dict[str, int] = {}
        hop_counts: Dict[str, int] = {}
        yeast_counts: Dict[str, int] = {}
        og_vals, fg_vals, ibu_vals, abv_vals = [], [], [], []

        for grain_bill, hop_bill, yeast, og, fg, ibu, abv in rows:
            if grain_bill:
                for g in grain_bill.split(","):
                    g = g.strip()
                    if g:
                        grain_counts[g] = grain_counts.get(g, 0) + 1
            if hop_bill:
                for h in hop_bill.split(","):
                    h = h.strip()
                    if h:
                        hop_counts[h] = hop_counts.get(h, 0) + 1
            if yeast:
                yeast_counts[yeast] = yeast_counts.get(yeast, 0) + 1
            if og:
                og_vals.append(og)
            if fg:
                fg_vals.append(fg)
            if ibu:
                ibu_vals.append(ibu)
            if abv:
                abv_vals.append(abv)

        top_grains = sorted(grain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_hops = sorted(hop_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_yeasts = sorted(yeast_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "style": style_name,
            "sample_count": len(rows),
            "top_grains": [{"name": name, "count": count} for name, count in top_grains],
            "top_hops": [{"name": name, "count": count} for name, count in top_hops],
            "top_yeasts": [{"name": name, "count": count} for name, count in top_yeasts],
            "og_range": {"min": round(min(og_vals), 3), "max": round(max(og_vals), 3), "avg": round(np.mean(og_vals), 3)} if og_vals else None,
            "fg_range": {"min": round(min(fg_vals), 3), "max": round(max(fg_vals), 3), "avg": round(np.mean(fg_vals), 3)} if fg_vals else None,
            "ibu_range": {"min": round(min(ibu_vals), 1), "max": round(max(ibu_vals), 1), "avg": round(np.mean(ibu_vals), 1)} if ibu_vals else None,
            "abv_range": {"min": round(min(abv_vals), 1), "max": round(max(abv_vals), 1), "avg": round(np.mean(abv_vals), 1)} if abv_vals else None,
        }

    def get_recommendations(self, style_name: str) -> List[str]:
        """Generate fermentation recommendations based on style benchmarks."""
        metrics = self.get_style_neighborhood_metrics(style_name)
        if not metrics:
            return ["No style-specific recommendations available."]

        recs = []
        avg_fg = metrics.get('avg_fg', 1.012)
        recs.append(f"Style peers typically reach a Final Gravity of {avg_fg:.3f}.")

        if "IPA" in style_name.upper():
            recs.append("Consider dry hopping once gravity reaches 1.020 for optimal aroma.")
        elif "STOUT" in style_name.upper() or "PORTER" in style_name.upper():
            recs.append("Ensure mash temp was high enough to leave residual body.")

        recs.append("Maintain stable fermentation temperature for the first 72 hours.")
        return recs


# Global instance
style_intel = StyleIntelligence()

if __name__ == "__main__":
    logger.info("Starting Style Intelligence verification...")
    # Test Similarity
    test_style = "American IPA"
    logger.info(f"Finding similar styles for '{test_style}'...")
    similar = style_intel.find_similar_styles(test_style)
    print(f"Styles similar to '{test_style}': {similar}")

    # Test Neighborhood Metrics
    logger.info(f"Getting neighborhood metrics for '{test_style}'...")
    metrics = style_intel.get_style_neighborhood_metrics(test_style)
    print(f"Neighborhood metrics for '{test_style}': {metrics}")

    # Test Style Profile
    logger.info(f"Getting style profile for '{test_style}'...")
    profile = style_intel.get_style_profile(test_style)
    print(f"Style profile for '{test_style}': {profile}")

    # Test Recommendations
    logger.info(f"Getting recommendations for '{test_style}'...")
    recs = style_intel.get_recommendations(test_style)
    print(f"Recommendations for '{test_style}': {recs}")

    # Test Fuzzy Match
    test_style_2 = "Double IPA"
    logger.info(f"Getting neighborhood metrics for '{test_style_2}' (Fuzzy Match)...")
    metrics_2 = style_intel.get_style_neighborhood_metrics(test_style_2)
    print(f"Neighborhood metrics for '{test_style_2}' (Fuzzy Match): {metrics_2}")
    logger.info("Verification complete.")
