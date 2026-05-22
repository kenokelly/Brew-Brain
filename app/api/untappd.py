import logging
import requests
from bs4 import BeautifulSoup
from typing import Tuple
from flask import Blueprint, request, Response
from core.auth import require_api_token
from api.routes import api_response, handle_error

logger = logging.getLogger(__name__)

untappd_bp = Blueprint('untappd', __name__)

@untappd_bp.route('/fetch', methods=['POST'])
@require_api_token
def fetch_untappd() -> Tuple[Response, int]:
    """Scrapes Untappd public beer page for metadata."""
    try:
        data = request.json or {}
        url = data.get('url')
        if not url or 'untappd.com/b/' not in url:
            return api_response(status="error", error="A valid Untappd beer URL is required.", code=400)
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Title is usually "Name - Brewery - Untappd"
        og_title = soup.find('meta', property='og:title')
        title = og_title['content'] if og_title else ''
        
        name = "Unknown"
        if title:
            parts = title.split(" - ")
            name = parts[0] if parts else title
            
        abv_elem = soup.select_one('.abv')
        abv = 0.0
        if abv_elem:
            abv_text = abv_elem.text.strip().replace('% ABV', '').strip()
            try:
                abv = float(abv_text)
            except ValueError:
                pass
                
        ibu_elem = soup.select_one('.ibu')
        ibu = 0.0
        if ibu_elem:
            ibu_text = ibu_elem.text.strip().replace(' IBU', '').strip()
            if ibu_text and ibu_text.lower() != 'n/a' and ibu_text.lower() != 'no':
                try:
                    ibu = float(ibu_text)
                except ValueError:
                    pass
                    
        style_elem = soup.select_one('.style')
        style = style_elem.text.strip() if style_elem else "Unknown Style"
        
        result = {
            "name": name,
            "abv": abv,
            "ibu": ibu,
            "style": style
        }
        
        return api_response(status="success", data=result)
        
    except requests.RequestException as e:
        logger.error(f"Untappd fetch failed: {e}")
        return api_response(status="error", error="Failed to fetch Untappd URL. It may be private or invalid.", code=400)
    except Exception as e:
        return handle_error(e, "Untappd Fetch Error")
