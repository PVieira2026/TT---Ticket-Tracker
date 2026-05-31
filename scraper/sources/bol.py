"""BOL — Playwright T2 + T3 cart navigation."""
import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category

log=logging.getLogger(__name__)
PLATFORM="BOL"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9","Accept-Encoding":"identity"}
SEARCH_URLS=[
    "https://www.bol.pt/Comprar/Bilhetes/index?categoria=Concertos",
    "https://www.bol.pt/Comprar/Bilhetes/index?categoria=Festivais",
    "https://www.bol.pt/Comprar/Bilhetes/index",
]


def _links(session,today,horizon):
    links,seen=[],set()
    re_l=re.compile(r'href="(/Comprar/Bilhetes/[^"?#]+)"',re.I)
    for url in SEARCH_URLS:
        try:
            r=session.get(url,timeout=20)
            for m in re_l.finditer(r.text):
                path=m.group(1)
                if "index" in path.lower(): continue
                full="https://www.bol.pt"+path
                if full not in seen: seen.add(full); links.append(full)
        except: pass
        time.sleep(0.5)
    return list(links)[:30]


def scrape() -> List[Dict]:
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS)
    results=[]
    for url in _links(s,today,horizon):
        slug=url.rstrip("/").split("/")[-1]
        try:
            time.sleep(0.7)
            r=s.get(url,timeout=20); html=r.text
            if len(html)<500: continue
            h1=re.search(r"<h1[^>]*>([^<]+)</h1>",html,re.I)
            og=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
            name=re.sub(r"<[^>]+>","",(h1.group(1) if h1 else (og.group(1) if og else slug))).replace("&amp;","&").strip()
            if not name or len(name)<2: continue
            tm=re.search(r'<time[^>]+datetime="([^"]+)"',html,re.I)
            ed=parse_date(tm.group(1)) if tm else None
            if not ed:
                m2=re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})",html,re.I)
                if m2: ed=parse_date(m2.group(0))
            if ed:
                try:
                    d=date.fromisoformat(ed)
                    if not(today<=d<=horizon): continue
                except: continue

            # T1
            text=strip_html(html); rows=extract_prices(text); src="static" if rows else ""

            # T2
            if not rows:
                try:
                    from scraper.playwright_engine import render_and_extract
                    pw=render_and_extract(url)
                    if pw: rows=pw; src="playwright"
                except Exception as e: log.warning(f"T2 BOL: {e}")

            # T3: cart navigation (BOL has a ticket selection modal)
            if not rows:
                try:
                    from scraper.playwright_engine import cart_navigate
                    ct=cart_navigate(url)
                    if ct: rows=ct; src="cart"
                except Exception as e: log.warning(f"T3 BOL: {e}")

            prices=[r["price"] for r in rows]
            img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            results.append({
                "id":f"bol-{slug}","name":name,"date":ed or "",
                "platform":PLATFORM,"category":detect_category(name,url),
                "price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "",
                "url":url,"image_url":img.group(1) if img else "",
                "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
                "updated_at":datetime.utcnow().isoformat(),
                "scraper_status":"ok" if prices else "ok_no_prices","price_source":src,
            })
        except Exception as e: log.warning(f"BOL event: {e}")
    return results
