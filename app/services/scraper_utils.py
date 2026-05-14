import logging
import requests
import re
import json
import threading
import time as std_time
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Thread-safe rate limiting and circuit breaking
_req_lock = threading.Lock()
_last_request_time = {}
_MIN_REQUEST_INTERVAL = 2.0

_circuit_breaker = {}
_MAX_FAILURES = 3
_BACKOFF_TIME = 300.0  # 5 minutes


def extract_price(text):
    if not text: return None
    # Clean text
    text = text.replace(',', '') # Handle 1,000.00
    
    # 1. Look for £ followed by digits (e.g. £13.95)
    match = re.search(r'[£$€]\s?(\d+(?:\.\d{2})?)', text)
    if match: return float(match.group(1))

    # 2. Look for digits followed by GBP (e.g. 7.50 GBP)
    match = re.search(r'(\d+(?:\.\d{2})?)\s?GBP', text, re.IGNORECASE)
    if match: return float(match.group(1))

    # 3. Look for "Price/Cost:" followed by digits (e.g. Price: 10.00)
    match = re.search(r'(?:Price|Cost):\s?£?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if match: return float(match.group(1))
            
    # 4. Fallback: Pure number if context suggests (simplified)
    try:
        return float(text)
    except Exception as e:
        pass
        
    return None

def get_page_content(url, retries=2):
    """
    Fetches page HTML using requests + retries with exponential backoff.
    Includes thread-safe rate limiting and a circuit breaker.
    """
    from urllib.parse import urlparse
    
    # SSRF PROTECTION: Strict Domain Allowlist
    ALLOWED_DOMAINS = {
        "themaltmiller.co.uk", "www.themaltmiller.co.uk",
        "geterbrewed.com", "www.geterbrewed.com"
    }
    domain = urlparse(url).netloc
    if domain not in ALLOWED_DOMAINS:
        logger.error(f"SSRF BLOCK: Attempted to scrape unauthorized domain: {domain} -> {url}")
        return None
        
    # Check Circuit Breaker
    with _req_lock:
        cb = _circuit_breaker.get(domain, {"failures": 0, "backoff_until": 0})
        now = std_time.time()
        if cb["failures"] >= _MAX_FAILURES:
            if now < cb["backoff_until"]:
                remaining = int(cb["backoff_until"] - now)
                logger.warning(f"Circuit Breaker active for {domain} ({remaining}s remaining). Skipping request.")
                return None
            else:
                logger.info(f"Circuit Breaker cooling period over for {domain}. Retrying...")
                cb["failures"] = 0
                _circuit_breaker[domain] = cb
    
    # Thread-safe Rate limiting
    wait_time = 0
    with _req_lock:
        now = std_time.time()
        if domain in _last_request_time:
            elapsed = now - _last_request_time[domain]
            if elapsed < _MIN_REQUEST_INTERVAL:
                wait_time = _MIN_REQUEST_INTERVAL - elapsed
                _last_request_time[domain] = now + wait_time
            else:
                _last_request_time[domain] = now
        else:
            _last_request_time[domain] = now

    if wait_time > 0:
        logger.debug(f"Rate limiting: thread waiting {wait_time:.1f}s for {domain}")
        std_time.sleep(wait_time)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            r.raise_for_status()
            
            # Reset failure count on success
            with _req_lock:
                if domain in _circuit_breaker:
                    _circuit_breaker[domain]["failures"] = 0
            
            return r.text
        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            
            # Record failure for Circuit Breaker
            with _req_lock:
                cb = _circuit_breaker.get(domain, {"failures": 0, "backoff_until": 0})
                cb["failures"] += 1
                if cb["failures"] >= _MAX_FAILURES:
                    cb["backoff_until"] = std_time.time() + _BACKOFF_TIME
                    logger.error(f"CIRCUIT BREAKER TRIGGERED for {domain} due to: {e}")
                _circuit_breaker[domain] = cb

            # Rate limited or Forbidden
            if status_code in (429, 403):
                wait_time = 30 * (attempt + 1) # More aggressive backoff for 429/403
                logger.warning(f"Rate limited (HTTP {status_code}) on {domain}, waiting {wait_time}s")
                if attempt < retries:
                    std_time.sleep(wait_time)
                    continue
                return None
            
            if attempt < retries:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"Retry {attempt + 1}/{retries} for {url} after {wait_time}s: {e}")
                std_time.sleep(wait_time)
            else:
                logger.warning(f"Failed to fetch {url} after {retries + 1} attempts: {e}")
                return None
    return None

def extract_weight_in_grams(text):
    if not text: return None
    text = text.lower()
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?kg\b', text)
    if match: return float(match.group(1)) * 1000
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?g\b', text)
    if match: return float(match.group(1))
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?lbs?\b', text)
    if match: return float(match.group(1)) * 453.59
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?oz\b', text)
    if match: return float(match.group(1)) * 28.35
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?ml\b', text)
    if match: return float(match.group(1))
    match = re.search(r'\b(\d+(?:\.\d+)?)\s?l\b', text)
    if match: return float(match.group(1)) * 1000
    return None

def extract_json_ld_products(html):
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    for script in soup.find_all('script', type='application/ld+json'):
        if not script.string: continue
        # Bolt Optimization: Fast substring check before expensive JSON parsing
        if '"Product"' not in script.string: continue
        try:
            data = json.loads(script.string)
            items = data.get('@graph', data) if isinstance(data, dict) else data
            if isinstance(items, dict): items = [items]
            for item in items:
                if item.get('@type') == 'Product':
                    products.append(item)
        except json.JSONDecodeError:
            continue
    return products

def parse_product_page(html, source):
    """
    Extracts price and weight/pack-size from HTML.
    Calculates cost per gram if possible.
    """
    if not html: return None
    data = {"price": None, "weight": None, "weight_g": None, "title": None}
    
    # 1. Try JSON-LD
    products = extract_json_ld_products(html)
    if products:
        p = products[0]
        offers = p.get('offers', {})
        if isinstance(offers, dict): offers = [offers]
        for offer in offers:
            if offer.get('@type') == 'Offer' and offer.get('price'):
                try:
                    data['price'] = float(offer['price'])
                    break
                except ValueError:
                    pass
        data['title'] = p.get('name')
        if data['title']:
            data['weight_g'] = extract_weight_in_grams(data['title'])

    if data['price']:
        return data
        
    soup = BeautifulSoup(html, 'html.parser')
    try:
        if "malt miller" in str(source).lower() or soup.select('.tmm-logo'):
            price_tag = soup.select_one('.price .amount')
            if price_tag: data['price'] = extract_price(price_tag.get_text())
            
            title = soup.select_one('h1.product_title') or soup.find('h1')
            title_text = title.get_text() if title else ""
            weight_match = re.search(r'(\d+)\s?(g|kg|ml|l)', title_text, re.IGNORECASE)
            if weight_match: data['weight'] = f"{weight_match.group(1)}{weight_match.group(2)}"
                
        elif "get er brewed" in str(source).lower() or "geterbrewed" in str(source).lower():
             price_tag = soup.select_one('[itemprop="price"]') or soup.select_one('.product-price')
             if price_tag:
                 p_text = price_tag.get("content") or price_tag.get_text()
                 data['price'] = extract_price(p_text)
                 
             title = soup.select_one('h1')
             title_text = title.get_text() if title else ""
             weight_match = re.search(r'(\d+)\s?(g|kg|ml|l)', title_text, re.IGNORECASE)
             if weight_match: data['weight'] = f"{weight_match.group(1)}{weight_match.group(2)}"
        else:
             price_meta = soup.select_one('meta[property="product:price:amount"]') or soup.select_one('meta[property="og:price:amount"]')
             if price_meta: data['price'] = float(price_meta['content'])
        
        if data.get('weight'):
            data['weight_g'] = extract_weight_in_grams(data['weight'])
                 
    except Exception as e:
        logger.error(f"Page Parsing Error: {e}")
        
    return data
