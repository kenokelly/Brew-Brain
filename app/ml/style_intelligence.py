import numpy as np
import sqlite3
import os
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

DB_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "external_recipes.db")

class StyleIntelligence:
    """Handles style embeddings and finding similar brewing styles."""
    
    def __init__(self):
        self.styles = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self.embeddings = None
        self._load_styles()

    def _load_styles(self):
        """Load unique styles from the external database and build embeddings."""
        if not os.path.exists(DB_PATH):
            logger.warning("External recipes database not found, skipping style intelligence setup.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT style FROM recipes WHERE style IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()

            self.styles = [row[0] for row in rows if row[0]]
            if self.styles:
                self.embeddings = self.vectorizer.fit_transform(self.styles)
                logger.info(f"Loaded {len(self.styles)} unique styles for embedding.")
        except Exception as e:
            logger.error(f"Failed to load styles for intelligence: {e}")

    def find_similar_styles(self, target_style: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Find the most similar styles to the target style name."""
        if not self.styles or self.embeddings is None:
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

        # Simple weighted average (weighted by sample size)
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
