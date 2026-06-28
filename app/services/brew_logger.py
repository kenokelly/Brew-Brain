import logging
import datetime

# We re-use github_integration but maybe we need a specialized function for simple file push
# The existing one expects a recipe dict and builds XML.
# Let's add a generic file pusher to `github_integration.py` or just use the logic here?
# Better to extend `github_integration` to be clean.
# I'll import `Github` here directly for now to avoid refactoring the other file too much 
# unless I decide to refactor it (which I should for quality).

from github import Github
from core.config import get_config

logger = logging.getLogger(__name__)

def generate_log_content(recipe_name, batch_data, water_profile, sourcing_data):
    """
    Generates a Markdown Brew Day Log.
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    md = f"# Brew Log: {recipe_name}\n"
    md += f"**Date:** {date_str}\n\n"
    
    md += "## Target Stats (G40)\n"
    md += f"- **Target OG:** {batch_data.get('og', 'TBD')}\n"
    md += f"- **Target FG:** {batch_data.get('fg', 'TBD')}\n"
    md += f"- **Batch Volume:** {batch_data.get('volume', 'Unknown')} L\n"
    md += f"- **Boil Time:** {batch_data.get('time', 60)} min\n\n"
    
    md += "## Water Profile (RO Targets)\n"
    if water_profile:
        md += f"**Style:** {water_profile.get('name', 'Custom')}\n"
        md += "| Ca | Mg | Na | Cl | SO4 | HCO3 |\n"
        md += "|---|---|---|---|---|---|\n"
        md += f"| {water_profile.get('calcium')} | {water_profile.get('magnesium')} | {water_profile.get('sodium')} | "
        md += f"{water_profile.get('chloride')} | {water_profile.get('sulfate')} | {water_profile.get('bicarbonate')} |\n\n"
        md += "> **Note:** Adjust RO water with approx Xg Gypsum / Yg CaCl based on Bru'n Water.\n\n"
    
    md += "## Sourcing / Cost\n"
    if sourcing_data:
         md += f"**Est. Cost:** £{sourcing_data.get('total_est_cost')}\n"
         md += "| Item | Need | Buy | Est Price |\n"
         md += "|---|---|---|---|\n"
         for item in sourcing_data.get('items', []):
             md += f"| {item['name']} | {item['need']} | {item['buy']} | £{item['est_cost']} |\n"
    md += "\n"
    
    md += "## Process Log\n"
    md += "### Mash\n"
    md += "- [ ] **Strike Water Added**: ____ L @ ____ °C\n"
    md += "- [ ] **Mash In**: Time ____ (Temp: ____ °C)\n"
    md += "- [ ] **Mash Out**: Time ____ (Pre-Boil Gravity: ____ )\n"
    
    md += "\n### Boil\n"
    md += "- [ ] **Boil Start**: Time ____\n"
    md += "- [ ] **Hop Additions**:\n"
    md += "  - [ ] 60 min: ____\n"
    md += "  - [ ] Whirlpool (75C): ____\n"
    
    md += "\n### Fermentation (Tilt / Unitank)\n"
    md += "- [ ] **Pitch Temp**: ____ °C\n"
    md += "- [ ] **Yeast Pitched**: ____\n"
    md += "- [ ] **Tilt Name/Color**: ____\n"
    md += "- [ ] **SmartRef Starting Gravity**: ____\n"

    return md

def save_log(recipe_name, content):
    token = get_config("github_token")
    repo_name = get_config("github_repo")
    
    if not token or not repo_name:
        return {"error": "GitHub Not Configured"}

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_name = recipe_name.replace(" ", "_")
        path = f"logs/{date_str}_{safe_name}.md"
        
        repo.create_file(path, f"Add Brew Log for {recipe_name}", content)
        return {"status": "success", "message": f"Log created at {path}"}
    except Exception as e:
        return {"error": str(e)}


def generate_brewday_log(session_data: dict) -> str:
    """
    Generate a comprehensive Markdown brew day log from session data and save it
    to disk.

    The log includes:
    - Recipe summary (name, targets)
    - Phase-by-phase timeline with timestamps
    - All gravity readings and corrections
    - All events from the session
    - AI evaluation (if available)

    Args:
        session_data: Full session dict from BrewSessionManager.end_session(),
                      optionally enriched with an 'evaluation' key from the AI.

    Returns:
        Absolute path to the saved log file.
    """
    from core.config import DATA_DIR

    batch_name = session_data.get("batch_name", "Unknown")
    recipe = session_data.get("recipe", {})
    readings = session_data.get("gravity_readings", [])
    corrections = session_data.get("corrections_applied", [])
    events = session_data.get("events", [])
    timers = session_data.get("timers", [])
    started_at = session_data.get("started_at", "N/A")
    ended_at = session_data.get("ended_at", "N/A")
    evaluation = session_data.get("evaluation", None)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    md = f"# Brew Day Log: {batch_name}\n\n"
    md += f"**Date:** {date_str}\n\n"

    # --- Recipe Summary ---
    md += "## Recipe Summary\n\n"
    md += f"- **Name:** {recipe.get('name', batch_name)}\n"
    md += f"- **Style:** {recipe.get('style', 'N/A')}\n"
    md += f"- **Target OG:** {recipe.get('og', 'N/A')}\n"
    md += f"- **Target FG:** {recipe.get('fg', 'N/A')}\n"
    md += f"- **Batch Volume:** {recipe.get('volume', 'N/A')} L\n"
    md += f"- **Boil Time:** {recipe.get('boil_time', 'N/A')} min\n\n"

    # --- Session Timeline ---
    md += "## Session Timeline\n\n"
    md += f"- **Started:** {started_at}\n"
    md += f"- **Ended:** {ended_at}\n\n"

    # Phase transitions from events
    phase_events = [e for e in events if e.get("event_type") == "phase_advanced"]
    if phase_events:
        md += "### Phase Transitions\n\n"
        md += "| Time | From | To |\n"
        md += "|------|------|----|\n"
        for pe in phase_events:
            ts = pe.get("timestamp", "N/A")
            data = pe.get("data", {})
            md += f"| {ts} | {data.get('from', '?')} | {data.get('to', '?')} |\n"
        md += "\n"

    # --- Gravity Readings ---
    if readings:
        md += "## Gravity Readings\n\n"
        md += "| Time | Stage | SG | Volume (L) |\n"
        md += "|------|-------|----|------------|\n"
        for r in readings:
            md += (
                f"| {r.get('timestamp', 'N/A')} "
                f"| {r.get('stage', 'N/A')} "
                f"| {r.get('sg', 'N/A')} "
                f"| {r.get('volume_l', 'N/A')} |\n"
            )
        md += "\n"

    # --- Corrections ---
    if corrections:
        md += "## Corrections Applied\n\n"
        for i, c in enumerate(corrections, 1):
            md += f"### Correction {i} ({c.get('stage', 'N/A')})\n\n"
            md += f"- **Measured SG:** {c.get('measured_sg', 'N/A')}\n"
            md += f"- **Target SG:** {c.get('target_sg', 'N/A')}\n"
            if "dme_addition_g" in c:
                md += f"- **DME Addition:** {c['dme_addition_g']}g\n"
            if "dilution_water_l" in c:
                md += f"- **Dilution Water:** {c['dilution_water_l']}L\n"
            if "boil_extension_min" in c:
                md += f"- **Boil Extension:** {c['boil_extension_min']} min\n"
            md += "\n"

    # --- Timers ---
    if timers:
        md += "## Timers\n\n"
        md += "| Name | Duration (min) | Type | Started |\n"
        md += "|------|----------------|------|---------|\n"
        for t in timers:
            md += (
                f"| {t.get('name', 'N/A')} "
                f"| {t.get('duration_min', 'N/A')} "
                f"| {t.get('addition_type', 'N/A')} "
                f"| {t.get('started_at', 'N/A')} |\n"
            )
        md += "\n"

    # --- All Events ---
    if events:
        md += "## Event Log\n\n"
        md += "| Time | Event | Details |\n"
        md += "|------|-------|---------|\n"
        for e in events:
            ts = e.get("timestamp", "N/A")
            etype = e.get("event_type", "N/A")
            detail = str(e.get("data", ""))
            # Truncate long details for the table
            if len(detail) > 80:
                detail = detail[:77] + "..."
            md += f"| {ts} | {etype} | {detail} |\n"
        md += "\n"

    # --- AI Evaluation ---
    if evaluation:
        md += "## AI Brew Day Evaluation\n\n"
        if isinstance(evaluation, dict):
            md += evaluation.get("evaluation", str(evaluation)) + "\n\n"
        else:
            md += str(evaluation) + "\n\n"

    # --- Save to disk ---
    import os

    log_dir = os.path.join(DATA_DIR, "logs", "brew_days")
    os.makedirs(log_dir, exist_ok=True)

    safe_name = batch_name.replace(" ", "_").replace("/", "_")
    filename = f"{date_str}_{safe_name}.md"
    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    logger.info(f"Brew day log saved: {filepath}")
    return filepath
