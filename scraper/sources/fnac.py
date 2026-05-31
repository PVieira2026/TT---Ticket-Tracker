"""FNAC — T1 static → T2 batch Playwright → T3 batch cart."""
import re, time, logging
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category, FNAC_BOILERPLATE

log      = logging.getLogger(__name__)
PLATFORM = "FNAC Bilheteira"
HDRS     = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":"text/html,*/*;q=0.8","Accept-Language":"pt-PT,pt;q=0.9",
    "Accept-Encoding":"identity","Cookie":"CookieConsent=1; fnac_cookie_consent=accepted",
    "Referer":"https://bilheteira.fnac.pt/",
}


def _links(session, today, horizon):
    links, seen = [], set()
    re_l = re.compile(r'href="(/Evento-(\d+)/[^"?#]+)"', re.I)
    for url in [
        f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}&category=Espetaculos",
        f"https://bilheteira.fnac.pt/Pesquisa/page/2?datefrom={today}&dateto={horizon}&category=Espetaculos",
        f"https://bilheteira.fnac.pt/Pesquisa/page/1?datefrom={today}&dateto={horizon}",
        "https://bilheteira.fnac.pt/",
    ]:
        try:
            r = session.get(url, timeout=20)
            for m in re_l.finditer(r.text):
                path, eid = m.group(1), m.group(2)
                if "Pack-Fnac" in path: continue
                if eid not in seen:
                    seen.add(eid)
                    links.append({"url": "https://bilheteira.fnac.pt"+path, "id": eid})
        except Exception: pass
        time.sleep(0.3)
    return links


def scrape() -> List[Dict]:
    today, horizon = date.today(), date.today()+timedelta(days=180)
    s = requests.Session(); s.headers.update(HDRS)

    # ── Collect metadata for all events (static, fast)
    raw_events = []
    for item in _links(s, today, horizon)[:40]:
        try:
            time.sleep(0.5)
            r = s.get(item["url"], timeout=20); html = r.text
            if len(html) < 3000: continue
            h1 = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.I)
            og = re.search(r'property="og:title"[^>]*content="([^"]+)"', html, re.I)
            name = re.sub(r"<[^>]+>","", (h1.group(1) if h1 else (og.group(1) if og else ""))).replace("&amp;","&").strip()
            if not name or len(name)<3: continue
            tm = re.search(r'<time[^>]+datetime="([^"]+)"', html, re.I)
            ed = parse_date(tm.group(1)) if tm else None
            if not ed:
                m2 = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})", html, re.I)
                if m2: ed = parse_date(m2.group(0))
            if not ed:
                m2 = re.search(r"(\d{2})/(\d{2})/(\d{4})", html)
                if m2: ed = f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
            if ed:
                try:
                    d = date.fromisoformat(ed)
                    if not(today<=d<=horizon): continue
                except Exception: continue
            # T1: static
            text  = strip_html(html)
            rows  = [r for r in extract_prices(text, True) if r["price"] not in FNAC_BOILERPLATE]
            img   = re.search(r'property="og:image"[^>]*content="([^"]+)"', html, re.I)
            raw_events.append({
                "id":f"fnac-{item['id']}","name":name,"date":ed or "","url":item["url"],
                "image_url":img.group(1) if img else "","rows":rows,"src":"static" if rows else "",
                "category":detect_category(name,item["url"]),
            })
        except Exception as e: log.warning(f"FNAC static: {e}")

    # ── T2 batch: Playwright for events still missing prices (ONE browser)
    no_prices = [ev for ev in raw_events if not ev["rows"]]
    if no_prices:
        log.info(f"[FNAC] T2 batch: {len(no_prices)} events need Playwright")
        try:
            from scraper.playwright_engine import batch_render
            pw_results = batch_render([ev["url"] for ev in no_prices], filter_boilerplate=True)
            for ev in no_prices:
                rows = [r for r in pw_results.get(ev["url"],[]) if r["price"] not in FNAC_BOILERPLATE]
                if rows: ev["rows"] = rows; ev["src"] = "playwright"
        except Exception as e: log.warning(f"FNAC T2 batch: {e}")

    # ── T3 batch: cart navigation for events still missing (capped)
    still_missing = [ev for ev in raw_events if not ev["rows"]][:8]  # cap at 8
    if still_missing:
        log.info(f"[FNAC] T3 cart: {len(still_missing)} events")
        try:
            from scraper.playwright_engine import batch_cart
            cart_results = batch_cart([ev["url"] for ev in still_missing])
            for ev in still_missing:
                rows = [r for r in cart_results.get(ev["url"],[]) if r["price"] not in FNAC_BOILERPLATE]
                if rows: ev["rows"] = rows; ev["src"] = "cart"
        except Exception as e: log.warning(f"FNAC T3 batch: {e}")

    # ── Build final results
    results = []
    for ev in raw_events:
        rows   = ev["rows"]
        prices = [r["price"] for r in rows]
        results.append({
            "id":ev["id"],"name":ev["name"],"date":ev["date"],
            "platform":PLATFORM,"category":ev["category"],
            "price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "",
            "url":ev["url"],"image_url":ev["image_url"],
            "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
            "updated_at":datetime.utcnow().isoformat(),
            "scraper_status":"ok" if prices else "ok_no_prices","price_source":ev["src"],
        })
    return results
