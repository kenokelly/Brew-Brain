import logging
import datetime
from services.github_integration import push_recipe_to_repo

# We re-use github_integration but maybe we need a specialized function for simple file push
# The existing one expects a recipe dict and builds XML.
# Let's add a generic file pusher to `github_integration.py` or just use the logic here?
# Better to extend `github_integration` to be clean.
# I'll import `Github` here directly for now to avoid refactoring the other file too much 
# unless I decide to refactor it (which I should for quality).

from github import Github
from app.core.config import get_config

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
