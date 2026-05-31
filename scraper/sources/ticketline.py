import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category
log=logging.getLogger(__name__); PLATFORM="Ticketline"
HDRS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9","Accept-Encoding":"identity"}
def _links(session,today,horizon):
    links,seen=[],set()
    re_l=re.compile(r'href="((?:https?://(?:www\.)?ticketline\.(?:pt|sapo\.pt))?/evento/([^"?#]+))"',re.I)
    for cat in ["104","121",""]:
        try:
            r=session.get(f"https://www.ticketline.pt/pesquisa?query=&district=&venue=&category={cat}&from={today}&to={horizon}",timeout=20)
            for m in re_l.finditer(r.text):
                href,slug=m.group(1),m.group(2)
                if "http%3A" in href or "pesquisa" in href: continue
                full=(href if href.startswith("http") else "https://www.ticketline.pt"+href).replace("ticketline.sapo.pt","www.ticketline.pt")
                eid_m=re.search(r"(\d+)$",slug); eid=eid_m.group(1) if eid_m else slug
                if eid not in seen: seen.add(eid); links.append({"url":full,"slug":slug})
        except: pass
        time.sleep(0.4)
    return links
def _session_url(html):
    sessions=re.findall(r'href="(/evento/[^"]+/sessao/[^"]+)"',html)
    return "https://www.ticketline.pt"+sessions[0] if sessions else None
def scrape(sheet_state=None):
    today,horizon=date.today(),date.today()+timedelta(days=180)
    s=requests.Session(); s.headers.update(HDRS); raw=[]
    for item in _links(s,today,horizon)[:35]:
        try:
            time.sleep(0.6); r=s.get(item["url"],timeout=20); html=r.text
            if len(html)<500: continue
            h1=re.search(r"<h1[^>]*>([^<]+)</h1>",html,re.I); og=re.search(r'property="og:title"[^>]*content="([^"]+)"',html,re.I)
            name=re.sub(r"<[^>]+>","",(h1.group(1) if h1 else (og.group(1) if og else item["slug"]))).replace("&amp;","&").strip()
            if not name or len(name)<2: continue
            tm=re.search(r'<time[^>]+datetime="([^"]+)"',html,re.I); ed=parse_date(tm.group(1)) if tm else None
            if not ed:
                for pat in [r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa]+)(?:\s+de)?\s+(202[5-9])",r"(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[^\d]*(202[5-9])"]:
                    m2=re.search(pat,html,re.I)
                    if m2: ed=parse_date(m2.group(0)); break
            if ed:
                try:
                    d=date.fromisoformat(ed)
                    if not(today<=d<=horizon): continue
                except: continue
            if sheet_state and not sheet_state.needs_scraping(name):
                img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
                raw.append({"id":f"ticketline-{item['slug']}","name":name,"date":ed or "","platform":PLATFORM,"category":detect_category(name,item["url"]),"url":item["url"],"session_url":item["url"],"image_url":img.group(1) if img else "","rows":[],"src":"skipped"}); continue
            text=strip_html(html); rows=extract_prices(text); src="static" if rows else ""
            surl=_session_url(html) or item["url"]
            img=re.search(r'property="og:image"[^>]*content="([^"]+)"',html,re.I)
            raw.append({"id":f"ticketline-{item['slug']}","name":name,"date":ed or "","platform":PLATFORM,"category":detect_category(name,item["url"]),"url":item["url"],"session_url":surl,"image_url":img.group(1) if img else "","rows":rows,"src":src})
        except Exception as e: log.warning(f"TL: {e}")
    need_pw=[ev for ev in raw if not ev["rows"] and ev["src"]!="skipped"]
    if need_pw:
        log.info(f"[TL] T2 session pages: {len(need_pw)}")
        try:
            from scraper.playwright_engine import batch_render
            surls=[ev["session_url"] for ev in need_pw]; pw=batch_render(surls)
            for ev,su in zip(need_pw,surls):
                if pw.get(su): ev["rows"]=pw[su]; ev["src"]="playwright"
        except Exception as e: log.warning(f"TL T2: {e}")
    need_cart=[ev for ev in raw if not ev["rows"] and ev["src"]!="skipped"][:8]
    if need_cart:
        try:
            from scraper.playwright_engine import batch_cart
            curls=[ev["session_url"] for ev in need_cart]; ct=batch_cart(curls)
            for ev,cu in zip(need_cart,curls):
                if ct.get(cu): ev["rows"]=ct[cu]; ev["src"]="cart"
        except Exception as e: log.warning(f"TL T3: {e}")
    results=[]
    for ev in raw:
        rows=ev["rows"]; prices=[r["price"] for r in rows]
        results.append({"id":ev["id"],"name":ev["name"],"date":ev["date"],"platform":PLATFORM,"category":ev["category"],"price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "","url":ev["url"],"image_url":ev["image_url"],"tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),"updated_at":datetime.utcnow().isoformat(),"scraper_status":"ok" if prices else "ok_no_prices","price_source":ev["src"]})
    return results
