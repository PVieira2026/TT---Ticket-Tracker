import re, time, logging, os
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category

log=logging.getLogger(__name__); PLATFORM="BOL"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9","Accept-Encoding":"identity"}
SERPER_KEY=os.environ.get("SERPER_API_KEY","")

def _find_bol_urls(year):
    if not SERPER_KEY: return []
    urls=set()
    try:
        for q in [f"site:bol.pt/Comprar/Bilhetes concertos {year}",f"site:bol.pt/Comprar/Bilhetes festivais {year}"]:
            resp=requests.post("https://google.serper.dev/search",
                headers={"X-API-KEY":SERPER_KEY,"Content-Type":"application/json"},
                json={"q":q,"gl":"pt","num":10},timeout=12)
            if resp.status_code==200:
                for r in resp.json().get("organic",[]):
                    lnk=r.get("link","")
                    if "bol.pt/Comprar/Bilhetes" in lnk and "Lista" not in lnk: urls.add(lnk)
            time.sleep(0.5)
    except Exception as e: log.warning(f"BOL Serper: {e}")
    log.info(f"[BOL] {len(urls)} URLs"); return list(urls)[:25]

def scrape(sheet_state=None):
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS)
    results=[]
    for url in _find_bol_urls(str(today.year)):
        try:
            time.sleep(0.7); r=s.get(url,timeout=20); html=r.text
            if len(html)<500 or "404" in r.url: continue
            h1=re.search(r"<h1[^>]*>([^<]+)</h1>",html,re.I); og=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
            name=re.sub(r"<[^>]+>","",(h1.group(1) if h1 else (og.group(1) if og else url.split("/")[-1]))).replace("&amp;","&").strip()
            if not name or len(name)<2: continue
            tm=re.search(r'<time[^>]+datetime="([^"]+)"',html,re.I); ed=parse_date(tm.group(1)) if tm else None
            if not ed:
                m2=re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})",html,re.I)
                if m2: ed=parse_date(m2.group(0))
            if ed:
                try:
                    d=date.fromisoformat(ed)
                    if not(today<=d<=horizon): continue
                except: continue
            if sheet_state and not sheet_state.needs_scraping(name): continue
            text=strip_html(html); rows=extract_prices(text); src="static" if rows else ""
            if not rows:
                try:
                    from scraper.playwright_engine import render_one
                    rows=render_one(url); src="playwright" if rows else ""
                except: pass
            img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            prices=[r["price"] for r in rows]
            slug=re.sub(r"[^a-z0-9]+","-",url.lower().split("bol.pt/")[-1])[:40]
            results.append({"id":f"bol-{slug}","name":name,"date":ed or "","platform":PLATFORM,
                "category":detect_category(name,url),"price_min":str(min(prices)) if prices else "",
                "price_max":str(max(prices)) if prices else "","url":url,"image_url":img.group(1) if img else "",
                "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
                "updated_at":datetime.utcnow().isoformat(),"scraper_status":"ok" if prices else "ok_no_prices","price_source":src})
        except Exception as e: log.warning(f"BOL: {e}")
    return results
