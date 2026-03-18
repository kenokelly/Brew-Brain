"""
Peer Comparison Module for Brew Brain

Compares a user's recipe or active batch against the external recipe database,
returning percentile rankings for OG, FG, ABV, IBU, and attenuation within the
target style population.

Uses the same z-score approach validated in production by anomaly.py.
"""

import sqlite3
import os
import logging
import numpy as np
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("BREW_BRAIN_DATA", "data"), "external_recipes.db")


class PeerComparison:
    """Compare a user recipe against the external recipe database."""

    @staticmethod
    def _get_style_population(style_name: str) -> List[Dict[str, Any]]:
        """Fetch all recipes matching a style from the external DB."""
        if not os.path.exists(DB_PATH):
            return []

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT og, fg, abv, ibu
            FROM recipes
            WHERE style LIKE ?
              AND og IS NOT NULL
              AND fg IS NOT NULL
        """, (f"%{style_name}%",))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def _percentile_rank(value: float, population: List[float]) -> Optional[float]:
        """
        Calculate the percentile rank of `value` within `population`.
        Returns a value 0–100, or None if population is too small.
        """
        if len(population) < 2:
            return None
        arr = np.array(population, dtype=float)
        rank = float(np.searchsorted(np.sort(arr), value, side="right"))
        return round((rank / len(arr)) * 100, 1)

    @staticmethod
    def _z_score(value: float, population: List[float]) -> Optional[float]:
        """Calculate z-score of `value` within `population`."""
        if len(population) < 2:
            return None
        arr = np.array(population, dtype=float)
        std = float(np.std(arr))
        if std == 0:
            return 0.0
        return round(float((value - np.mean(arr)) / std), 2)

    def compare(self, user_recipe: Dict[str, Any], style: str) -> Dict[str, Any]:
        """
        Compare a user recipe against the external DB population for a style.

        Args:
            user_recipe: Dict with keys like 'og', 'fg', 'abv', 'ibu'.
            style: BJCP or free-form style name to compare against.

        Returns:
            Dict with:
              - style, sample_size
              - per-metric: { value, avg, std, percentile, z_score, verdict }
        """
        population = self._get_style_population(style)

        if len(population) < 2:
            return {
                "style": style,
                "sample_size": len(population),
                "error": "Not enough external recipes for this style to compare against.",
            }

        # Build population arrays per metric
        metrics_config = [
            ("og", "Original Gravity"),
            ("fg", "Final Gravity"),
            ("abv", "ABV %"),
            ("ibu", "IBU"),
        ]

        comparisons: Dict[str, Any] = {}

        for key, label in metrics_config:
            user_val = user_recipe.get(key)
            if user_val is None:
                continue

            user_val = float(user_val)
            pop_vals = [r[key] for r in population if r.get(key) is not None]

            if len(pop_vals) < 2:
                comparisons[key] = {"label": label, "value": user_val, "insufficient_data": True}
                continue

            pop_arr = np.array(pop_vals, dtype=float)
            avg = round(float(np.mean(pop_arr)), 3)
            std = round(float(np.std(pop_arr)), 3)
            pct = self._percentile_rank(user_val, pop_vals)
            z = self._z_score(user_val, pop_vals)

            # Human-readable verdict
            if pct is not None:
                if pct < 10:
                    verdict = "Well below style peers"
                elif pct < 25:
                    verdict = "Below average for style"
                elif pct < 75:
                    verdict = "Typical for style"
                elif pct < 90:
                    verdict = "Above average for style"
                else:
                    verdict = "Well above style peers"
            else:
                verdict = "Insufficient data"

            comparisons[key] = {
                "label": label,
                "value": round(user_val, 3),
                "avg": avg,
                "std": std,
                "percentile": pct,
                "z_score": z,
                "verdict": verdict,
            }

        # Compute attenuation comparison if OG and FG available
        user_og = user_recipe.get("og")
        user_fg = user_recipe.get("fg")
        if user_og and user_fg:
            user_og, user_fg = float(user_og), float(user_fg)
            if user_og > 1.0:
                user_att = round(((user_og - user_fg) / (user_og - 1.0)) * 100, 1)
                pop_att = []
                for r in population:
                    og_v, fg_v = r.get("og"), r.get("fg")
                    if og_v and fg_v and og_v > 1.0:
                        pop_att.append(round(((og_v - fg_v) / (og_v - 1.0)) * 100, 1))

                if len(pop_att) >= 2:
                    pop_arr = np.array(pop_att, dtype=float)
                    comparisons["attenuation"] = {
                        "label": "Apparent Attenuation %",
                        "value": user_att,
                        "avg": round(float(np.mean(pop_arr)), 1),
                        "std": round(float(np.std(pop_arr)), 1),
                        "percentile": self._percentile_rank(user_att, pop_att),
                        "z_score": self._z_score(user_att, pop_att),
                        "verdict": "Typical for style",  # Will be overridden below
                    }
                    pct = comparisons["attenuation"]["percentile"]
                    if pct is not None:
                        if pct < 10:
                            comparisons["attenuation"]["verdict"] = "Well below style peers"
                        elif pct < 25:
                            comparisons["attenuation"]["verdict"] = "Below average for style"
                        elif pct < 75:
                            comparisons["attenuation"]["verdict"] = "Typical for style"
                        elif pct < 90:
                            comparisons["attenuation"]["verdict"] = "Above average for style"
                        else:
                            comparisons["attenuation"]["verdict"] = "Well above style peers"

        return {
            "style": style,
            "sample_size": len(population),
            "comparisons": comparisons,
        }


# Module-level instance for convenience
peer_comparison = PeerComparison()
