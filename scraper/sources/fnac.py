import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category, FNAC_BOILERPLATE
log=logging.getLogger(__name__); PLATFORM="FNAC Bilheteira"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9","Accept-Encoding":"identity","Cookie":"CookieConsent=1; fnac_cookie_consent=accepted","Referer":"https://bilheteira.fnac.pt/"}
INVALID_NAME={"utiliza\u00e7\u00e3o de cookies","cookie","privacidade","consentimento","rgpd"}
def _name(html):
    m=re.search(r"<title>([\s\S]*?)</title>",html,re.I)
    if m:
        n=re.sub(r"\s+"," ",m.group(1)).strip(); n=re.sub(r"(?i)^Bilheteira FNAC\s*[-\u2013|]\s*","",n).strip()
        if n and len(n)>3 and not any(t in n.lower() for t in INVALID_NAME): return n
    m=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
    if m:
        n=re.sub(r"(?i)^Bilheteira FNAC\s*[-\u2013|]\s*","",m.group(1)).strip()
        if n and len(n)>3 and not any(t in n.lower() for t in INVALID_NAME): return n
    return ""
def _links(session,today,horizon):
    links,seen=[],set(); re_l=re.compile(r'href="(/Evento-(\d+)/[^"?#]+)"',re.I)
    for url in [f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}&category=Espetaculos",f"https://bilheteira.fnac.pt/Pesquisa/page/2?datefrom={today}&dateto={horizon}&category=Espetaculos",f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}","https://bilheteira.fnac.pt/"]:
        try:
            r=session.get(url,timeout=20)
            for m in re_l.finditer(r.text):
                path,eid=m.group(1),m.group(2)
                if "Pack-Fnac" in path: continue
                if eid not in seen: seen.add(eid); links.append({"url":"https://bilheteira.fnac.pt"+path,"id":eid})
        except: pass
        time.sleep(0.3)
    return links
def scrape(sheet_state=None):
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS); results=[]
    for item in _links(s,today,horizon)[:40]:
        try:
            time.sleep(0.5); r=s.get(item["url"],timeout=20); html=r.text
            if len(html)<3000: continue
            name=_name(html)
            if not name or len(name)<3: continue
            html_ns=re.sub(r'<script[\s\S]*?</script>','',html,flags=re.I)
            tm=re.search(r'<time[^>]+datetime="([^"]+)"',html_ns,re.I); ed=parse_date(tm.group(1)) if tm else None
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
            img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            if sheet_state and not sheet_state.needs_scraping(name):
                results.append({"id":f"fnac-{item['id']}","name":name,"date":ed or "","platform":PLATFORM,"category":detect_category(name,item["url"]),"price_min":"","price_max":"","url":item["url"],"image_url":img.group(1) if img else "","tickets_json":"","tickets_detail":"","updated_at":datetime.utcnow().isoformat(),"scraper_status":"ok_no_prices","price_source":"skipped"}); continue
            text=strip_html(html)
            rows=[r for r in extract_prices(text,True) if r["price"] not in FNAC_BOILERPLATE]
            prices=[r["price"] for r in rows]
            if prices: log.info(f"  [FNAC] {len(rows)} prices: {name}")
            else: log.info(f"  [FNAC] No prices in text: {name}")
            results.append({"id":f"fnac-{item['id']}","name":name,"date":ed or "","platform":PLATFORM,"category":detect_category(name,item["url"]),"price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "","url":item["url"],"image_url":img.group(1) if img else "","tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),"updated_at":datetime.utcnow().isoformat(),"scraper_status":"ok" if prices else "ok_no_prices","price_source":"static" if prices else ""})
        except Exception as e: log.warning(f"FNAC: {e}")
    return results
