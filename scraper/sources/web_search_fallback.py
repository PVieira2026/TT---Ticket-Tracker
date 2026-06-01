import re, os, time, logging
import requests
from typing import List, Dict
from scraper.parser import extract_prices, build_tickets_detail, build_tickets_json

log=logging.getLogger(__name__)
SERPER_KEY=os.environ.get("SERPER_API_KEY","")
# Backup: add SERPER_API_KEY_2 for when primary is exhausted
SERPER_KEY_2=os.environ.get("SERPER_API_KEY_2","")


def _active_serper_key():
    """Return first available Serper key."""
    if SERPER_KEY: return SERPER_KEY
    if SERPER_KEY_2: return SERPER_KEY_2
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
        resp=requests.get("https://api.duckduckgo.com/",
            params={"q":query,"format":"json","no_html":1,"skip_disambig":1},timeout=12)
        data=resp.json(); results=[]
        if data.get("AbstractText"):
            results.append({"title":data.get("Heading",""),"snippet":data["AbstractText"],"link":data.get("AbstractURL","")})
        for t in data.get("RelatedTopics",[])[:6]:
            if isinstance(t,dict) and t.get("Text"):
                results.append({"title":"","snippet":t["Text"],"link":t.get("FirstURL","")})
        return results
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
