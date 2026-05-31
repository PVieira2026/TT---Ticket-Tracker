"""Blueticket — direct scrape with T2 Playwright."""
import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category

log=logging.getLogger(__name__)
PLATFORM="Blueticket"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9","Accept-Encoding":"identity"}


def _search_links(session,today,horizon):
    links,seen=[],set()
    re_l=re.compile(r'href="((?:https?://(?:www\.)?blueticket\.pt)?/evento/(\d+)/[^"?#]*)"',re.I)
    search="https://www.blueticket.pt/pesquisa?texto=&tipo=&distrito=&data_inicio=&data_fim="
    try:
        r=session.get(search,timeout=20)
        for m in re_l.finditer(r.text):
            href,eid=m.group(1),m.group(2)
            full=href if href.startswith("http") else "https://www.blueticket.pt"+href
            if eid not in seen: seen.add(eid); links.append({"url":full,"id":eid})
    except: pass
    return links[:25]


def scrape() -> List[Dict]:
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS)
    results=[]
    for item in _search_links(s,today,horizon):
        try:
            time.sleep(0.8)
            rows=[]; src=""
            # T2: Playwright (BT is JS-heavy)
            try:
                from scraper.playwright_engine import render_and_extract
                pw=render_and_extract(item["url"])
                if pw: rows=pw; src="playwright"
            except Exception as e: log.warning(f"T2 BT: {e}")
            # T3 if T2 failed
            if not rows:
                try:
                    from scraper.playwright_engine import cart_navigate
                    ct=cart_navigate(item["url"])
                    if ct: rows=ct; src="cart"
                except Exception as e: log.warning(f"T3 BT: {e}")

            prices=[r["price"] for r in rows]
            # Get name/date from static HTML at least
            try:
                r2=s.get(item["url"],timeout=20); html=r2.text
                h1=re.search(r"<h1[^>]*>([^<]+)</h1>",html,re.I)
                og=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
                name=re.sub(r"<[^>]+>","",(h1.group(1) if h1 else (og.group(1) if og else f"BT-{item['id']}"))).replace("&amp;","&").strip()
                tm=re.search(r'<time[^>]+datetime="([^"]+)"',html,re.I)
                ed=parse_date(tm.group(1)) if tm else None
                img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            except:
                name=f"BT-{item['id']}"; ed=None; img=None
            if not name or len(name)<2: continue
            results.append({
                "id":f"bt-{item['id']}","name":name,"date":ed or "",
                "platform":PLATFORM,"category":detect_category(name,item["url"]),
                "price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "",
                "url":item["url"],"image_url":img.group(1) if img else "",
                "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
                "updated_at":datetime.utcnow().isoformat(),
                "scraper_status":"ok" if prices else "ok_no_prices","price_source":src,
            })
        except Exception as e: log.warning(f"BT event: {e}")
    return results
