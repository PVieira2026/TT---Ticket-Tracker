"""FNAC Bilheteira — T1: static text → T2: Playwright → T3: cart."""
import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category, FNAC_BOILERPLATE

log=logging.getLogger(__name__)
PLATFORM="FNAC Bilheteira"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9",
      "Accept-Encoding":"identity","Cookie":"CookieConsent=1; fnac_cookie_consent=accepted",
      "Referer":"https://bilheteira.fnac.pt/"}


def _links(session, today, horizon):
    links,seen=[],set()
    re_l=re.compile(r'href="(/Evento-(\d+)/[^"?#]+)"',re.I)
    for url in [
        f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}&category=Espetaculos",
        f"https://bilheteira.fnac.pt/Pesquisa/page/2?datefrom={today}&dateto={horizon}&category=Espetaculos",
        f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}",
        "https://bilheteira.fnac.pt/",
    ]:
        try:
            r=session.get(url,timeout=20)
            for m in re_l.finditer(r.text):
                path,eid=m.group(1),m.group(2)
                if "Pack-Fnac" in path: continue
                if eid not in seen: seen.add(eid); links.append({"url":"https://bilheteira.fnac.pt"+path,"id":eid})
        except: pass
        time.sleep(0.4)
    return links


def scrape() -> List[Dict]:
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS)
    results=[]
    for item in _links(s,today,horizon)[:40]:
        try:
            time.sleep(0.6)
            r=s.get(item["url"],timeout=20); html=r.text
            if len(html)<3000: continue
            h1=re.search(r"<h1[^>]*>([^<]+)</h1>",html,re.I)
            og=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
            name=re.sub(r"<[^>]+>","",(h1.group(1) if h1 else (og.group(1) if og else ""))).replace("&amp;","&").strip()
            if not name or len(name)<3: continue
            tm=re.search(r'<time[^>]+datetime="([^"]+)"',html,re.I)
            ed=parse_date(tm.group(1)) if tm else None
            if not ed:
                m2=re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})",html,re.I)
                if m2: ed=parse_date(m2.group(0))
            if not ed:
                m2=re.search(r"(\d{2})/(\d{2})/(\d{4})",html)
                if m2: ed=f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
            if ed:
                try:
                    d=date.fromisoformat(ed)
                    if not(today<=d<=horizon): continue
                except: continue

            # T1: static text (filter boilerplate)
            text=strip_html(html)
            rows=[r for r in extract_prices(text) if r["price"] not in FNAC_BOILERPLATE]
            src="static" if rows else ""

            # T2: Playwright
            if not rows:
                try:
                    from scraper.playwright_engine import render_and_extract
                    pw=[r for r in render_and_extract(item["url"],True) if r["price"] not in FNAC_BOILERPLATE]
                    if pw: rows=pw; src="playwright"
                except Exception as e: log.warning(f"T2 FNAC: {e}")

            # T3: Cart navigation
            if not rows:
                try:
                    from scraper.playwright_engine import cart_navigate
                    ct=[r for r in cart_navigate(item["url"]) if r["price"] not in FNAC_BOILERPLATE]
                    if ct: rows=ct; src="cart"
                except Exception as e: log.warning(f"T3 FNAC: {e}")

            prices=[r["price"] for r in rows]
            img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            results.append({
                "id":f"fnac-{item['id']}","name":name,"date":ed or "",
                "platform":PLATFORM,"category":detect_category(name,item["url"]),
                "price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "",
                "url":item["url"],"image_url":img.group(1) if img else "",
                "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
                "updated_at":datetime.utcnow().isoformat(),
                "scraper_status":"ok" if prices else "ok_no_prices","price_source":src,
            })
        except Exception as e: log.warning(f"FNAC event: {e}")
    return results
