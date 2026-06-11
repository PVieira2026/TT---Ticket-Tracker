import re, os, time, logging
import requests
from typing import List, Dict
from scraper.parser import extract_prices, build_tickets_detail, build_tickets_json

log=logging.getLogger(__name__)
SERPER_KEY=os.environ.get("SERPER_API_KEY","")
# Backup: add SERPER_API_KEY_2 for when primary is exhausted
SERPER_KEY_2=os.environ.get("SERPER_API_KEY_2","")


def _active_serper_key():
    """Return first available Serper key dynamically checking environment."""
    key = os.environ.get("SERPER_API_KEY", "") or SERPER_KEY
    if key: return key
    key2 = os.environ.get("SERPER_API_KEY_2", "") or SERPER_KEY_2
    if key2: return key2
    return ""


def _clean_query(name, year=""):
    q=re.sub(r'[|()\[\]{}]',' ',name); q=re.sub(r'\s+',' ',q).strip()
    # Trim to first 5 words if very long (avoid over-specific queries)
    words=q.split()
    if len(words)>5: q=" ".join(words[:5])
    if year and year not in q: q+=f" {year}"
    return q+" preço bilhetes"


def _filter_price_lines(text):
    """
    Keep ONLY short lines/sentences that contain a euro sign.
    This prevents long narrative sentences from becoming garbage sector names.
    Max line length: 150 chars. Must contain EUR sign.
    """
    result=[]
    for chunk in re.split(r'[\n|;]',text):
        chunk=chunk.strip()
        if '\u20ac' in chunk and 8<=len(chunk)<=150:
            result.append(chunk)
    # Also try splitting on sentence boundaries
    for sent in re.split(r'(?<=[.!?])\s+',text):
        sent=sent.strip()
        if '\u20ac' in sent and 8<=len(sent)<=120 and sent not in result:
            result.append(sent)
    return '\n'.join(result)


def _search_serper(query):
    key=_active_serper_key()
    if not key: return []
    try:
        resp=requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY":key,"Content-Type":"application/json"},
            json={"q":query,"gl":"pt","hl":"pt","num":8},timeout=12)
        if resp.status_code!=200:
            log.warning(f"Serper {resp.status_code}: {resp.text[:100]}")
            return []
        data=resp.json()
        results=[]
        # answerBox: rich snippet from Google (most useful!)
        if data.get("answerBox"):
            ab=data["answerBox"]
            for txt in [ab.get("answer",""),ab.get("snippet",""),ab.get("snippetHighlighted","")]:
                if txt: results.append({"title":"answerBox","snippet":str(txt),"link":ab.get("link","")})
        for r in data.get("organic",[]):
            results.append({"title":r.get("title",""),"snippet":r.get("snippet",""),"link":r.get("link","")})
        return results
    except Exception as e: log.warning(f"Serper: {e}"); return []


def _search_duckduckgo(query):
    try:
        from bs4 import BeautifulSoup
        resp=requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        for a in soup.find_all('a', class_='result__snippet'):
            text = a.text.strip()
            if text:
                results.append({"title": "", "snippet": text, "link": ""})
        return results[:8]
    except Exception as e: log.warning(f"DDG: {e}"); return []


def _search_google_direct(query):
    """Direct Google scraping — last resort, may get blocked."""
    try:
        import urllib.parse
        url=f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=pt&gl=pt&num=8"
        resp=requests.get(url,headers={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language":"pt-PT,pt;q=0.9,en;q=0.8","Accept":"text/html"
        },timeout=12)
        html=resp.text
        results=[]
        # Extract div snippets (Google's result structure)
        for pattern in [r'<div[^>]+data-sncf[^>]*>(.*?)</div>',r'<span[^>]+class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</span>']:
            for s in re.findall(pattern,html,re.S)[:6]:
                text=re.sub(r'<[^>]+>',' ',s).replace("&nbsp;"," ").strip()
                if '\u20ac' in text and len(text)>10:
                    results.append({"title":"","snippet":text,"link":""})
        return results
    except Exception as e: log.warning(f"GoogleDirect: {e}"); return []


def _extract_from_snippets(snippets, event_name):
    """
    Extract structured ticket prices from search result snippets.
    Step 1: filter to price-containing lines only (removes garbage sector names).
    Step 2: run extract_prices on clean text.
    Step 3: fallback to range extraction.
    """
    # Combine and filter
    combined=" | ".join(s["snippet"] for s in snippets if s.get("snippet"))
    filtered=_filter_price_lines(combined)

    if filtered:
        rows=extract_prices(filtered)
        # Remove rows with suspiciously long sector names (>50 chars = probably garbage)
        rows=[r for r in rows if len(r["sector"])<=60]
        if rows:
            log.info(f"[WebSearch] {len(rows)} prices for '{event_name}'")
            return rows, "structured"

    # Fallback: extract a simple range from unfiltered text
    m=re.search(r'(\d+(?:[,.]\d+)?)\s*\u20ac[^€]{0,50}?(\d+(?:[,.]\d+)?)\s*\u20ac',combined)
    if m:
        lo,hi=float(m.group(1).replace(",",".")),float(m.group(2).replace(",","."))
        if 1<=lo<=2000 and lo!=hi and abs(hi-lo)<500:
            rows=[
                {"sector":"Pre\u00e7o m\u00ednimo","price":round(min(lo,hi),2),"note":"web search","sold_out":False},
                {"sector":"Pre\u00e7o m\u00e1ximo","price":round(max(lo,hi),2),"note":"web search","sold_out":False},
            ]
            log.info(f"[WebSearch] Range {lo}-{hi}\u20ac for '{event_name}'")
            return rows, "range"

    return [], ""


def search_prices(event_name, event_date=""):
    """Search for event ticket prices. Returns (rows, source_label)."""
    year=event_date[:4] if event_date else ""
    query=_clean_query(event_name,year)
    log.info(f"[WebSearch] Query: {repr(query)}")

    # Try sources in order: Serper → DuckDuckGo → Google Direct
    snippets=[]
    if _active_serper_key():
        snippets=_search_serper(query)
    if not snippets:
        snippets=_search_duckduckgo(query)
    if not snippets:
        snippets=_search_google_direct(query)

    if not snippets:
        log.info(f"[WebSearch] No results for '{event_name}'")
        return [], ""

    return _extract_from_snippets(snippets, event_name)

def search_image(event_name: str, event_date: str = '') -> str:
    year = event_date[:4] if event_date else ''
    query = re.sub(r'[|()\[\]{}]', ' ', event_name).strip()
    words = query.split()
    if len(words) > 5: query = ' '.join(words[:5])
    if year and year not in query: query += f' {year}'
    key = _active_serper_key()
    if key:
        try:
            resp = requests.post('https://google.serper.dev/images',
                headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
                json={'q': query, 'gl': 'pt', 'num': 5}, timeout=10)
            if resp.status_code == 200:
                for img in resp.json().get('images', []):
                    url = img.get('imageUrl', '')
                    if url and any(e in url.lower() for e in ['.jpg','.jpeg','.png','.webp']):
                        return url
                imgs = resp.json().get('images', [])
                if imgs: return imgs[0].get('imageUrl', '')
        except Exception as e: log.warning(f'[ImageSearch] {e}')
    # Bing Images fallback (excellent for posters and events)
    try:
        import urllib.parse
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query + ' cartaz')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            # Bing stores full image URLs in murl":"..."
            matches = re.findall(r'murl&quot;:&quot;(https?[^&]+?\.(?:jpg|jpeg|png|webp))&quot;', resp.text, re.IGNORECASE)
            if matches:
                # Retorna o primeiro resultado válido
                return matches[0]
            
            # Alternative Bing format
            matches2 = re.findall(r'murl":"(https?[^"]+?\.(?:jpg|jpeg|png|webp))"', resp.text, re.IGNORECASE)
            if matches2:
                return matches2[0]
    except Exception as e: 
        log.warning(f'[ImageSearch/Bing] {e}')
        
    # Wikipedia fallback (absolute last resort)
    try:
        resp = requests.get('https://en.wikipedia.org/w/api.php',
            params={'action':'query','titles':event_name,'prop':'pageimages','format':'json','pithumbsize':600,'piprop':'thumbnail'},
            timeout=8)
        if resp.status_code == 200:
            for pg in resp.json().get('query',{}).get('pages',{}).values():
                url = pg.get('thumbnail',{}).get('source','')
                if url: return url
    except Exception as e: log.warning(f'[ImageSearch/Wiki] {e}')
    
    return ''

def scrape_urls_for_context(snippets: list) -> tuple:
    """Scrapes the actual URLs found in snippets to provide deep context and official images, avoiding 60s Toqan timeouts."""
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
    except ImportError:
        return "", ""
    
    extracted_text = ""
    urls_to_scrape = []
    official_image_url = ""
    
    for s in snippets:
        link = s.get('link', '')
        if any(d in link.lower() for d in ['blueticket', 'fnac', 'ticketline', 'bol.pt', 'everythingisnew', 'festival']):
            if link not in urls_to_scrape:
                urls_to_scrape.append(link)
                
    if not urls_to_scrape:
        urls_to_scrape = [s.get('link') for s in snippets[:2] if s.get('link')]
        
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for url in urls_to_scrape[:2]:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                html_text = resp.text
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Agressively extract official image using Regex (bypasses JS rendering issues)
                if not official_image_url:
                    # 1. Try to find known CDN image patterns in the raw HTML or JSON state
                    cdn_patterns = [
                        r'(https://blueticketcdn\.pt/imagesserver/[^"\'\s>]+?\.(?:jpg|jpeg|png|webp))',
                        r'(https://multimedia\.fnac\.pt/[^"\'\s>]+?\.(?:jpg|jpeg|png|webp))',
                        r'(https://ticketline\.sapo\.pt/fotos/eventos/[^"\'\s>]+?\.(?:jpg|jpeg|png|webp))',
                        r'(https://bol\.pt/Eventos/Cartaz/[^"\'\s>]+?\.(?:jpg|jpeg|png|webp))'
                    ]
                    for pattern in cdn_patterns:
                        matches = re.findall(pattern, html_text, re.IGNORECASE)
                        if matches:
                            official_image_url = matches[0]
                            break
                            
                    # 2. Try og:image with regex if CDN fails
                    if not official_image_url:
                        og_match = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                        if og_match:
                            official_image_url = og_match.group(1)
                            
                    # 3. Try standard soup og:image as last resort
                    if not official_image_url:
                        og_img = soup.find("meta", property="og:image")
                        if og_img and og_img.get("content"):
                            official_image_url = og_img["content"]
                        
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator=' ')
                text = re.sub(r'\s+', ' ', text).strip()
                extracted_text += f"\n--- CONTENT FROM {url} ---\n{text[:5000]}\n"
        except Exception as e:
            log.warning(f"Failed to scrape {url}: {e}")
            
    return extracted_text, official_image_url