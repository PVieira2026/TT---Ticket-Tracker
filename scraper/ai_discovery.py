import os
import re
import time
import logging
import json
import requests
from datetime import date, timedelta
from utils.sheets import read_sheet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Fetch environment variables
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SA_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")
N8N_WEBHOOK_TOKEN = os.environ.get("N8N_WEBHOOK_TOKEN", "")

def get_existing_event_names(df):
    if df.empty:
        return set()
    # Return a set of lowercase normalized names of events already in the sheet
    def norm(n):
        return ' '.join(sorted(re.sub(r'[^a-z0-9\s]', ' ', n.lower()).split()))
    return {norm(n) for n in df['name'] if n.strip()}

def fetch_ticketline_candidates(session):
    """Fetch recent event names from Ticketline's index/search page."""
    log.info("Fetching event candidates from Ticketline...")
    today = date.today()
    horizon = today + timedelta(days=180)
    names = []
    seen = set()
    re_l = re.compile(r'href="((?:https?://(?:www\.)?ticketline\.(?:pt|sapo\.pt))?/evento/([^"?#]+))"', re.I)
    
    for cat in ["104", "121", ""]:
        try:
            url = f"https://www.ticketline.pt/pesquisa?query=&district=&venue=&category={cat}&from={today}&to={horizon}"
            r = session.get(url, timeout=20)
            for m in re_l.finditer(r.text):
                slug = m.group(2)
                # Clean name from slug
                name_cand = slug.replace("-", " ").title()
                # Remove ID from end if present
                name_cand = re.sub(r'\s+\d+$', '', name_cand).strip()
                if name_cand.lower() not in seen:
                    seen.add(name_cand.lower())
                    names.append(name_cand)
        except Exception as e:
            log.warning(f"Error fetching Ticketline candidates: {e}")
        time.sleep(0.3)
    return names

def fetch_fnac_candidates(session):
    """Fetch recent event names from FNAC's search pages."""
    log.info("Fetching event candidates from FNAC...")
    today = date.today()
    horizon = today + timedelta(days=180)
    names = []
    seen = set()
    re_l = re.compile(r'href="(/Evento-\d+/([^"?#]+))"', re.I)
    
    for url in [
        f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}&category=Espetaculos",
        f"https://bilheteira.fnac.pt/Pesquisa/page/2?datefrom={today}&dateto={horizon}&category=Espetaculos"
    ]:
        try:
            r = session.get(url, timeout=20)
            for m in re_l.finditer(r.text):
                slug = m.group(2)
                name_cand = slug.replace("-", " ").title()
                if name_cand.lower() not in seen:
                    seen.add(name_cand.lower())
                    names.append(name_cand)
        except Exception as e:
            log.warning(f"Error fetching FNAC candidates: {e}")
        time.sleep(0.3)
    return names

def run_discovery():
    if not SPREADSHEET_ID or not SA_JSON:
        log.error("SPREADSHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON are required in environment!")
        return

    if not N8N_WEBHOOK_URL:
        log.error("N8N_WEBHOOK_URL is required in environment!")
        return

    # 1. Read existing events from Google Sheets
    log.info("Reading current events from Google Sheets...")
    df_existing = read_sheet(SPREADSHEET_ID)
    existing_names = get_existing_event_names(df_existing)
    log.info(f"Loaded {len(existing_names)} unique event names from sheet.")

    # 2. Gather candidates from Ticketing sites indexes
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,*/*;q=0.8"
    })
    
    candidates = []
    candidates.extend(fetch_ticketline_candidates(session))
    candidates.extend(fetch_fnac_candidates(session))
    
    # Remove duplicates from candidates
    unique_candidates = []
    seen_candidates = set()
    for c in candidates:
        if c.lower() not in seen_candidates:
            seen_candidates.add(c.lower())
            unique_candidates.append(c)

    log.info(f"Found {len(unique_candidates)} total candidate events from indexes.")

    # 3. Check which candidates are not in the sheet and run AI on them
    def norm(n):
        return ' '.join(sorted(re.sub(r'[^a-z0-9\s]', ' ', n.lower()).split()))

    new_events_added = 0
    for name in unique_candidates:
        norm_name = norm(name)
        if norm_name in existing_names:
            log.info(f"Skipping already existing event: {name}")
            continue

        log.info(f"🆕 NEW EVENT DETECTED: '{name}'. Calling AI/Toqan Agent for full details...")
        
        try:
            # Fetch search context first to help the AI extract info quickly and reliably
            from scraper.sources.web_search_fallback import (
                _search_serper, _search_duckduckgo, _search_google_direct, 
                _active_serper_key, scrape_urls_for_context, search_image
            )
            
            log.info(f"  Fetching search context for '{name}'...")
            snippets = []
            if _active_serper_key():
                snippets = _search_serper(name)
            if not snippets:
                snippets = _search_duckduckgo(name)
            if not snippets:
                snippets = _search_google_direct(name)
            
            context = ""
            for i, s in enumerate(snippets[:6]):
                context += f"Result {i+1}:\nTitle: {s.get('title', '')}\nLink: {s.get('link', '')}\nSnippet: {s.get('snippet', '')}\n\n"
            
            if snippets:
                try:
                    text_content, _ = scrape_urls_for_context(snippets)
                    context += "\n" + text_content
                except Exception as ex:
                    log.warning(f"  Could not scrape URL details: {ex}")
            
            img_url = ""
            try:
                img_url = search_image(name)
            except Exception:
                pass
                
            payload = {
                'query': name,
                'search_context': context,
                'pre_fetched_image': img_url,
                'spreadsheet_id': SPREADSHEET_ID
            }
            
            # Post to n8n webhook (which runs Toqan and automatically inserts/updates the sheet!)
            headers = {}
            if N8N_WEBHOOK_TOKEN:
                headers["X-N8N-API-KEY"] = N8N_WEBHOOK_TOKEN
            resp = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=120)
            if resp.status_code == 200:
                log.info(f"  Successfully processed and updated Sheet via n8n for event: {name}")
                new_events_added += 1
                existing_names.add(norm_name)
            else:
                log.error(f"  n8n webhook error {resp.status_code}: {resp.text}")
        except Exception as e:
            log.error(f"  Failed to process event '{name}': {e}")
        
        # Sleep slightly between requests to avoid rate limits
        time.sleep(2.0)

    log.info(f"Discovery complete. Added {new_events_added} new events to Google Sheets!")

if __name__ == "__main__":
    run_discovery()
