"""
=================================================================
Link2Reel (مرصاد) - Product Reader Engine
Scrapes product data from e-commerce URLs (Amazon, Noon, Shopify)
Ownership: Smart Analyst | MIA8444
=================================================================
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import json
from typing import Optional, Dict, List

# Try to import Playwright (primary scraping engine)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Headers to avoid bot detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Connection': 'keep-alive',
}

# Rotating User-Agents for retry
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def detect_platform(url: str) -> str:
    """Detect which e-commerce platform the URL belongs to."""
    domain = urlparse(url).netloc.lower()
    if 'amazon' in domain:
        return 'amazon'
    elif 'noon' in domain:
        return 'noon'
    elif 'shopify' in domain or 'myshopify' in domain:
        return 'shopify'
    elif 'aliexpress' in domain:
        return 'aliexpress'
    else:
        return 'generic'


def _scrape_with_playwright(url: str, platform: str) -> Optional[Dict]:
    """
    Scrape using a headless browser (Playwright).
    Renders JS and bypasses anti-bot detection. Works on ALL sites.
    Returns None if Playwright unavailable or fails (so caller falls back to requests).
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None

    try:
        with sync_playwright() as pw:
            # Stealth mode: new headless + realistic args to avoid detection
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768},
                locale='en-US',
            )
            # Hide the webdriver flag so Amazon doesn't spot automation
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until='domcontentloaded')

            # Wait for the page to render product content (best-effort)
            try:
                page.wait_for_selector('#productTitle, h1, [data-testid="product-title"]', timeout=10000)
            except Exception:
                pass  # proceed even if the specific selector isn't found

            # Give JS a moment to populate dynamic content
            page.wait_for_timeout(1500)

            html = page.content()
            context.close()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Use the same platform-specific extractors, then metadata fallback
        if platform == 'amazon':
            result = _scrape_amazon(soup, url)
        elif platform == 'noon':
            result = _scrape_noon(soup, url)
        elif platform == 'shopify':
            result = _scrape_shopify(soup, url)
        else:
            result = _scrape_generic(soup, url)

        # If specific selectors missed the title, try JSON-LD / Open Graph
        if not result.get('title'):
            meta = _scrape_with_metadata(soup, url, platform=platform)
            if meta.get('title'):
                result['title'] = meta['title']
                if not result.get('price'): result['price'] = meta.get('price')
                if not result.get('description'): result['description'] = meta.get('description')
                if not result.get('images'): result['images'] = meta.get('images', [])
                if not result.get('rating'): result['rating'] = meta.get('rating')

        return result
    except Exception as e:
        print(f'Playwright scrape failed: {e}')
        return None


def scrape_product(url: str) -> Dict:
    """
    Main scraping function.
    Returns dict with: title, price, currency, description, features, images, rating, reviews
    """
    platform = detect_platform(url)

    # Primary: Playwright headless browser (renders JS, bypasses anti-bot, works on all sites)
    if PLAYWRIGHT_AVAILABLE:
        result = _scrape_with_playwright(url, platform)
        if result and result.get('title'):
            return result

    # Fallback: requests-based scraper (session + primed cookies for Amazon bot-detection)
    session = requests.Session()
    session.headers.update(HEADERS)
    is_amazon_eg = 'amazon.eg' in url
    if platform == 'amazon':
        try:
            home = 'https://www.amazon.eg/' if is_amazon_eg else 'https://www.amazon.com/'
            session.get(home, headers={**HEADERS, 'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8'}, timeout=20)
        except Exception:
            pass
    for attempt in range(3):
        try:
            headers = HEADERS.copy()
            headers['Accept-Language'] = 'en-US,en;q=0.9,ar;q=0.8'
            headers['Referer'] = 'https://www.amazon.eg/' if is_amazon_eg else 'https://www.google.com/'
            if attempt > 0:
                headers['User-Agent'] = USER_AGENTS[attempt % len(USER_AGENTS)]
                import time
                time.sleep(2)  # Wait between retries

            response = session.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for CAPTCHA/bot detection (specific indicators only)
            page_text = soup.get_text().lower()
            is_captcha = (
                'robot check' in page_text or
                'type the characters' in page_text or
                ('captcha' in page_text and len(page_text) < 5000)
            )
            if is_captcha and attempt < 2:
                continue  # Retry with different UA
            
            if platform == 'amazon':
                return _scrape_amazon(soup, url)
            elif platform == 'noon':
                return _scrape_noon(soup, url)
            elif platform == 'shopify':
                return _scrape_shopify(soup, url)
            else:
                return _scrape_generic(soup, url)
                
        except requests.exceptions.RequestException as e:
            if attempt < 2:
                continue
            return {
                'error': f'Failed to fetch URL after 3 attempts: {str(e)}',
                'title': None,
                'price': None,
                'images': [],
                'description': None,
                'features': [],
                'rating': None,
                'reviews': [],
                'platform': platform,
                'url': url
            }


def _scrape_amazon(soup: BeautifulSoup, url: str) -> Dict:
    """Scrape Amazon product page."""
    # Title
    title = _safe_text(soup.find('span', {'id': 'productTitle'}))
    
    # Price - try multiple selectors (Amazon varies by region/version)
    price = _safe_text(soup.find('span', {'class': 'a-price-whole'}))
    if not price:
        price = _safe_text(soup.find('span', {'class': 'a-offscreen'}))
    if not price:
        price = _safe_text(soup.find('span', {'id': 'priceblock_ourprice'}))
    if not price:
        price = _safe_text(soup.find('span', {'id': 'priceblock_dealprice'}))
    if not price:
        el = soup.find('span', {'class': 'a-price'})
        if el:
            price = el.get_text(strip=True).replace('\n', ' ')
    if not price:
        el = soup.find('div', {'data-a-color': 'price'})
        if el:
            price = el.get_text(strip=True)
    if not price:
        el = soup.find('span', {'id': 'corePrice_feature_div'})
        if el:
            price = el.get_text(strip=True)
    
    # Description
    description = _safe_text(soup.find('div', {'id': 'productDescription'}))
    if not description:
        bullets = soup.find_all('span', {'class': 'a-list-item'})
        description = ' '.join([b.get_text(strip=True) for b in bullets[:5] if b.get_text(strip=True)])
    
    # Features (bullet points)
    features = []
    feature_div = soup.find('div', {'id': 'feature-bullets'})
    if feature_div:
        for li in feature_div.find_all('li'):
            txt = _safe_text(li.find('span', {'class': 'a-list-item'}))
            if txt and len(txt) > 10:
                features.append(txt)
    
    # Images
    images = _extract_images(soup, ['landingImage', 'imgTagWrapperId', 'altImgImages'])
    
    # Rating
    rating = _safe_text(soup.find('span', {'class': 'a-icon-alt'}))
    rating = _parse_rating(rating)
    
    # Reviews
    reviews = _extract_reviews(soup, platform='amazon')
    
    # Fallback to JSON-LD + Open Graph if specific selectors failed
    if not title:
        meta = _scrape_with_metadata(soup, url, platform='amazon')
        if meta.get('title'):
            title = meta['title']
            if not price: price = meta['price']
            if not description: description = meta['description']
            if not images: images = meta['images']
            if not rating: rating = meta['rating']
    
    return {
        'title': title,
        'price': price,
        'currency': 'USD' if 'amazon.com' in url else 'EGP',
        'description': description,
        'features': features,
        'images': images,
        'rating': rating,
        'reviews': reviews,
        'platform': 'amazon',
        'url': url
    }


def _scrape_noon(soup: BeautifulSoup, url: str) -> Dict:
    """Scrape Noon product page."""
    title = _safe_text(soup.find('h1', {'class': 'product-name'}))
    if not title:
        title = soup.title.get_text(strip=True) if soup.title else None
    
    price = _safe_text(soup.find('span', {'class': 'value'}))
    if not price:
        price_el = soup.find('div', {'class': 'price'})
        price = price_el.get_text(strip=True) if price_el else None
    
    description = _safe_text(soup.find('div', {'class': 'product-description'}))
    features = []
    for li in soup.find_all('li', {'class': 'product-attribute'}):
        txt = li.get_text(strip=True)
        if txt:
            features.append(txt)
    
    images = _extract_images(soup, [])
    
    rating = _safe_text(soup.find('span', {'class': 'star-rating'}))
    rating = _parse_rating(rating)
    
    reviews = _extract_reviews(soup, platform='noon')
    
    return {
        'title': title,
        'price': price,
        'currency': 'EGP' if 'noon.com' in url or 'noon' in url else 'AED',
        'description': description,
        'features': features,
        'images': images,
        'rating': rating,
        'reviews': reviews,
        'platform': 'noon',
        'url': url
    }


def _scrape_shopify(soup: BeautifulSoup, url: str) -> Dict:
    """Scrape Shopify store product page."""
    title = soup.title.get_text(strip=True) if soup.title else None
    
    # Shopify usually has product JSON
    price = _safe_text(soup.find('span', {'class': 'price'}))
    if not price:
        price_el = soup.find('div', {'class': 'product-price'})
        price = price_el.get_text(strip=True) if price_el else None
    
    description = _safe_text(soup.find('div', {'class': 'product-description'}))
    if not description:
        description = _safe_text(soup.find('meta', {'name': 'description'}), attr='content')
    
    features = []
    images = _extract_images(soup, [])
    
    rating = _safe_text(soup.find('span', {'class': 'rating'}))
    rating = _parse_rating(rating)
    
    return {
        'title': title,
        'price': price,
        'currency': 'USD',
        'description': description,
        'features': features,
        'images': images,
        'rating': rating,
        'reviews': [],
        'platform': 'shopify',
        'url': url
    }


def _scrape_generic(soup: BeautifulSoup, url: str) -> Dict:
    """Generic scraper fallback for unknown platforms."""
    title = soup.title.get_text(strip=True) if soup.title else None
    
    # Try Open Graph meta tags
    og_title = _safe_text(soup.find('meta', {'property': 'og:title'}), attr='content')
    og_desc = _safe_text(soup.find('meta', {'property': 'og:description'}), attr='content')
    og_image = _safe_text(soup.find('meta', {'property': 'og:image'}), attr='content')
    
    if og_title:
        title = og_title
    description = og_desc or _safe_text(soup.find('meta', {'name': 'description'}), attr='content')
    
    images = []
    if og_image:
        images.append(og_image)
    images.extend(_extract_images(soup, []))
    
    return {
        'title': title,
        'price': None,
        'currency': None,
        'description': description,
        'features': [],
        'images': images[:5],
        'rating': None,
        'reviews': [],
        'platform': 'generic',
        'url': url
    }


# ===== Helper Functions =====

def _scrape_with_metadata(soup: BeautifulSoup, url: str, platform: str = 'generic') -> Dict:
    """Fallback scraper using JSON-LD structured data + Open Graph meta tags."""
    result = {'title': None, 'price': None, 'description': None, 'images': [], 'rating': None}

    # 1) Try JSON-LD structured data (most reliable for Amazon/Shopify)
    for script in soup.find_all('script', {'type': 'application/ld+json'}):
        try:
            raw = script.string or script.get_text()
            if not raw:
                continue
            data = json.loads(raw)
            # JSON-LD can be a single object or a list
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Follow @graph if present
                if '@graph' in item and isinstance(item['@graph'], list):
                    for g in item['@graph']:
                        if isinstance(g, dict) and g.get('@type') in ('Product', 'IndividualProduct'):
                            item = g
                            break
                if item.get('@type') in ('Product', 'IndividualProduct'):
                    if not result['title']:
                        result['title'] = item.get('name')
                    offers = item.get('offers')
                    if offers and not result['price']:
                        if isinstance(offers, list):
                            offers = offers[0] if offers else None
                        if isinstance(offers, dict):
                            result['price'] = str(offers.get('price', '')) or None
                    if not result['description']:
                        result['description'] = item.get('description')
                    if not result['rating']:
                        agg = item.get('aggregateRating')
                        if isinstance(agg, dict):
                            result['rating'] = agg.get('ratingValue')
                    img = item.get('image')
                    if img and not result['images']:
                        if isinstance(img, list):
                            result['images'] = [i for i in img if isinstance(i, str) and i.startswith('http')]
                        elif isinstance(img, str) and img.startswith('http'):
                            result['images'] = [img]
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    # 2) Fallback to Open Graph meta tags
    if not result['title']:
        result['title'] = _safe_text(soup.find('meta', {'property': 'og:title'}), attr='content')
    if not result['description']:
        result['description'] = _safe_text(soup.find('meta', {'property': 'og:description'}), attr='content')
        if not result['description']:
            result['description'] = _safe_text(soup.find('meta', {'name': 'description'}), attr='content')
    if not result['images']:
        og_image = _safe_text(soup.find('meta', {'property': 'og:image'}), attr='content')
        if og_image:
            result['images'] = [og_image]

    return result


def _safe_text(element, attr=None) -> Optional[str]:
    """Safely extract text from a BeautifulSoup element."""
    if element is None:
        return None
    if attr:
        val = element.get(attr)
        return val.strip() if val else None
    return element.get_text(strip=True) or None


def _extract_images(soup: BeautifulSoup, ids: List[str]) -> List[str]:
    """Extract product images from page."""
    images = []
    # Try by ID
    for img_id in ids:
        el = soup.find('img', {'id': img_id})
        if el:
            src = el.get('data-old-hires') or el.get('src')
            if src and src.startswith('http'):
                images.append(src)
    
    # Try by class
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-old-hires')
        if src and src.startswith('http') and ('product' in src.lower() or 'image' in src.lower()):
            if src not in images:
                images.append(src)
    
    return images[:8]  # Max 8 images


def _parse_rating(rating_str: Optional[str]) -> Optional[float]:
    """Parse rating string to float."""
    if not rating_str:
        return None
    match = re.search(r'(\d+\.?\d*)', rating_str)
    return float(match.group(1)) if match else None


def _extract_reviews(soup: BeautifulSoup, platform: str) -> List[Dict]:
    """Extract user reviews."""
    reviews = []
    if platform == 'amazon':
        review_divs = soup.find_all('div', {'data-hook': 'review'})
        for div in review_divs[:5]:
            title = _safe_text(div.find('a', {'data-hook': 'review-title'}))
            body = _safe_text(div.find('span', {'data-hook': 'review-body'}))
            rating = _safe_text(div.find('i', {'data-hook': 'review-star-rating'}))
            if body:
                reviews.append({
                    'title': title,
                    'body': body[:200],
                    'rating': _parse_rating(rating)
                })
    return reviews


# ===== Test =====
if __name__ == '__main__':
    test_url = input('Enter product URL: ').strip()
    if test_url:
        print(f'\n🔍 Scraping: {test_url}')
        data = scrape_product(test_url)
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
