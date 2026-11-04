"""Keg label: batch name, recipe details and the colour of the beer."""

import re
from typing import Any, Dict, List, Optional

# Brewfather names a new batch "Batch" (or "Batch 44") unless you rename it
GENERIC_BATCH_NAME = re.compile(r"^\s*batch\s*#?\s*\d*\s*$", re.I)
# Recipe names often end in the batch size ("PGBM Hazy Pale 23L")
SIZE_SUFFIX = re.compile(r"\s+\d+(?:[.,]\d+)?\s*(?:l|litres?|liters?|gal)\s*$", re.I)

# Approximate beer colour for SRM 1-40 (standard SRM reference colours)
SRM_HEX = ["#FFE699", "#FFD878", "#FFCA5A", "#FFBF42", "#FBB123", "#F8A600", "#F39C00", "#EA8F00",
           "#E58500", "#DE7C00", "#D77200", "#CF6900", "#CB6200", "#C35900", "#BB5100", "#B54C00",
           "#B04500", "#A63E00", "#A13700", "#9B3200", "#952D00", "#8E2900", "#882300", "#821E00",
           "#7B1A00", "#771900", "#701400", "#6A0E00", "#660D00", "#5E0B00", "#5A0A02", "#600903",
           "#520907", "#4C0505", "#470606", "#440607", "#3F0708", "#3B0607", "#3A070B", "#36080A"]


def display_name(batch_name: Optional[str], recipe_name: Optional[str]) -> str:
    """The name to show: the batch name, or the recipe name if the batch was never renamed."""
    name = (batch_name or "").strip()
    if (not name or GENERIC_BATCH_NAME.match(name)) and recipe_name:
        name = SIZE_SUFFIX.sub("", recipe_name.strip())
    return name or "New Batch"


def srm_hex(srm: Optional[float]) -> str:
    if srm is None:
        return SRM_HEX[4]
    i = min(max(int(round(float(srm))), 1), len(SRM_HEX)) - 1
    return SRM_HEX[i]


def label_info_from_batch(batch: Dict[str, Any]) -> Dict[str, Any]:
    """Pull what the label shows out of a Brewfather batch (with its recipe)."""
    rec = batch.get("recipe") or {}

    def names(items: List[dict], skip_use: tuple = ()) -> List[str]:
        out: List[str] = []
        for item in items or []:
            n = re.sub(r"\s*\((?:[A-Z]{2}|domestic)\)\s*$", "", (item.get("name") or "").strip())
            if n and n not in out and item.get("use") not in skip_use:
                out.append(n)
        return out

    hops = names(rec.get("hops"))
    dry = names([h for h in rec.get("hops") or [] if h.get("use") == "Dry Hop"])
    return {
        "recipe_name": rec.get("name"),
        "batch_no": batch.get("batchNo"),
        "brewer": batch.get("brewer"),
        "abv": batch.get("measuredAbv") or rec.get("abv"),
        "ibu": rec.get("ibu"),
        "srm": rec.get("color"),
        "hops": hops,
        "dry_hops": dry,
        "malts": names(rec.get("fermentables")),
        "carbonation": batch.get("carbonation") or rec.get("carbonation"),
    }
