import logging
import base64
from github import Github
from core.config import get_config

logger = logging.getLogger(__name__)

def push_recipe_to_repo(recipe_data, token, repo_name):
    """
    Pushes valid recipe data to the user's GitHub repository as an XML file.
    Path: recipes/{recipe_name}.xml
    """
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Construct content
        # We need a valid XML string. If the recipe_data contains raw XML, use it.
        # Otherwise, we construct a basic BeerXML wrapper.
        
        content = ""
        name = recipe_data.get("name", "Unknown_Recipe").replace(" ", "_")
        
        if recipe_data.get("xml_content"):
            content = recipe_data["xml_content"]
        elif recipe_data.get("source_url") and recipe_data.get("source_url").endswith(".xml"):
            # If we only have URL, we might need to fetch it again or assume caller passed content.
            # Ideally caller passes content.
            return {"error": "No XML content provided to save."}
        else:
            # Construct minimal valid XML from dict (fallback)
            # This is a bit hacky but ensures we save *something* useful.
            content = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<RECIPES>
  <RECIPE>
    <NAME>{recipe_data.get('name')}</NAME>
    <OG>{recipe_data.get('og')}</OG>
    <IBU>{recipe_data.get('ibu')}</IBU>
    <EST_ABV>{recipe_data.get('abv')}</EST_ABV>
    <SOURCE>{recipe_data.get('source_url')}</SOURCE>
    <NOTES>Imported via Brew-Brain from {recipe_data.get('source_url')}</NOTES>
  </RECIPE>
</RECIPES>"""

        file_path = f"recipes/{name}.xml"
        
        # IDEMPOTENCY CHECK
        try:
            contents = repo.get_contents(file_path)
            # Update existing
            repo.update_file(contents.path, f"Update recipe {name}", content, contents.sha)
            return {"status": "success", "message": f"Updated {file_path} in {repo_name}"}
        except:
            # Create new
            repo.create_file(file_path, f"Add recipe {name}", content)
            return {"status": "success", "message": f"Created {file_path} in {repo_name}"}

    except Exception as e:
        logger.error(f"GitHub Push Error: {e}")
        return {"error": str(e)}
