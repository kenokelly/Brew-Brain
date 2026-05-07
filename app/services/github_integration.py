import logging
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
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
            recipes_elem = ET.Element("RECIPES")
            recipe_elem = ET.SubElement(recipes_elem, "RECIPE")

            def add_child(parent, tag, text):
                child = ET.SubElement(parent, tag)
                child.text = str(text) if text is not None else ""

            add_child(recipe_elem, "NAME", recipe_data.get("name"))
            add_child(recipe_elem, "OG", recipe_data.get("og"))
            add_child(recipe_elem, "IBU", recipe_data.get("ibu"))
            add_child(recipe_elem, "EST_ABV", recipe_data.get("abv"))
            add_child(recipe_elem, "SOURCE", recipe_data.get("source_url"))
            add_child(recipe_elem, "NOTES", f"Imported via Brew-Brain from {recipe_data.get('source_url')}")

            # Pretty print XML using minidom
            raw_xml = ET.tostring(recipes_elem)
            parsed_xml = minidom.parseString(raw_xml)
            content = parsed_xml.toprettyxml(indent="  ", encoding="ISO-8859-1").decode("ISO-8859-1")

        file_path = f"recipes/{name}.xml"
        
        # IDEMPOTENCY CHECK
        try:
            contents = repo.get_contents(file_path)
            # Update existing
            repo.update_file(contents.path, f"Update recipe {name}", content, contents.sha)
            return {"status": "success", "message": f"Updated {file_path} in {repo_name}"}
        except Exception:
            # Create new
            repo.create_file(file_path, f"Add recipe {name}", content)
            return {"status": "success", "message": f"Created {file_path} in {repo_name}"}

    except Exception as e:
        logger.error(f"GitHub Push Error: {e}")
        return {"error": str(e)}
