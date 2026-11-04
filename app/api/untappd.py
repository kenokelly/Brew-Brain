import logging
import re
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
    """Scrapes Untappd public beer page for metadata with slug fallback."""
    try:
        data = request.json or {}
        url = data.get('url', '').strip()
        if not url or 'untappd.com/b/' not in url:
            return api_response(status="error", error="A valid Untappd beer URL is required (e.g. https://untappd.com/b/brewery-beer/12345).", code=400)
            
        # Parse fallback name from URL slug (e.g. untappd.com/b/brewery-beer-name/12345)
        slug_match = re.search(r'untappd\.com/b/([^/]+)', url)
        fallback_name = "Untappd Beer"
        if slug_match:
            slug_parts = slug_match.group(1).replace('-', ' ').title().split(' ')
            # If slug has brewery and beer name, join them nicely
            fallback_name = " ".join(slug_parts)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        name = fallback_name
        abv = 0.0
        ibu = 0.0
        style = "Unknown Style"
        
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Title is usually "Name - Brewery - Untappd"
                og_title = soup.find('meta', property='og:title')
                title = og_title['content'] if og_title and og_title.get('content') else ''
                
                if title:
                    parts = title.split(" - ")
                    name = parts[0] if parts else title
                    
                abv_elem = soup.select_one('.abv')
                if abv_elem:
                    abv_text = abv_elem.text.strip().replace('% ABV', '').strip()
                    try:
                        abv = float(abv_text)
                    except ValueError:
                        pass
                        
                ibu_elem = soup.select_one('.ibu')
                if ibu_elem:
                    ibu_text = ibu_elem.text.strip().replace(' IBU', '').strip()
                    if ibu_text and ibu_text.lower() not in ['n/a', 'no']:
                        try:
                            ibu = float(ibu_text)
                        except ValueError:
                            pass
                            
                style_elem = soup.select_one('.style')
                if style_elem:
                    style = style_elem.text.strip()
        except Exception as fetch_err:
            logger.warning(f"Untappd live scrape warning (using slug fallback): {fetch_err}")

        result = {
            "name": name,
            "abv": abv,
            "ibu": ibu,
            "style": style,
            "url": url
        }
        
        return api_response(status="success", data=result)
        
    except Exception as e:
        return handle_error(e, "Untappd Fetch Error")

