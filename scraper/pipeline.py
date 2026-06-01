import logging, time, threading
from typing import List, Dict
from datetime import date, timedelta

log=logging.getLogger(__name__)

def _run(label,fn,sheet_state=None):
    start=time.time()
    try:
        log.info(f"[{label}] Starting...")
        try: events=fn(sheet_state=sheet_state)
        except TypeError: events=fn()
        wp=sum(1 for e in events if e.get("price_min"))
        sk=sum(1 for e in events if e.get("price_source")=="skipped")
        log.info(f"[{label}] {time.time()-start:.0f}s - {len(events)} events, {wp} prices, {sk} skipped")
        return events
    except Exception as e: log.error(f"[{label}] FAILED: {e}"); return []

def _fill_images(events):
    from scraper.sources.web_search_fallback import search_image
    GENERIC=["EverythingIsNew.png","fundo","bilheteira.fnac.pt/Content","blueticket.pt/imageserver"]
    need=[ev for ev in events if not ev.get("image_url") or any(g in ev.get("image_url","") for g in GENERIC)]
    if not need: log.info("[Images] All OK"); return events
    log.info(f"[Images] Fetching {len(need)} missing images")
    for ev in need:
        try:
            time.sleep(0.5)
            url=search_image(ev["name"],ev.get("date",""))
            if url: ev["image_url"]=url; log.info(f"  [Img] {ev['name'][:40]}")
        except Exception as e: log.warning(f"  [Img] {ev['name']}: {e}")
    return events

def _web_search(events):
    from scraper.sources.web_search_fallback import search_prices
    from scraper.parser import build_tickets_detail, build_tickets_json
    from datetime import datetime
    no_prices=[ev for ev in events if not ev.get("price_min") and ev.get("scraper_status")!="skipped" and ev.get("price_source") not in ("web_search",)]
    if not no_prices: log.info("[T4] No events need web search"); return events
    log.info(f"[T4] Web search for {len(no_prices)} events")
    succ=0
    for ev in no_prices:
        try:
            time.sleep(1.2)
            rows,src=search_prices(ev["name"],ev.get("date",""))
            if rows:
                prices=[r["price"] for r in rows]
                ev["price_min"]=str(min(prices)); ev["price_max"]=str(max(prices))
                ev["tickets_json"]=build_tickets_json(rows); ev["tickets_detail"]=build_tickets_detail(rows)
                ev["scraper_status"]="ok"; ev["price_source"]="web_search"
                ev["updated_at"]=datetime.utcnow().isoformat()
                log.info(f"  [T4] {ev['name']}: {min(prices)}-{max(prices)}€ [{src}]"); succ+=1
        except Exception as e: log.warning(f"  [T4] {ev['name']}: {e}")
    log.info(f"[T4] {succ}/{len(no_prices)} found"); return events

def run_all(sheet_state=None):
    from scraper.sources.ein        import scrape as s_ein
    from scraper.sources.fnac       import scrape as s_fnac
    from scraper.sources.ticketline import scrape as s_tl
    from scraper.sources.bol        import scrape as s_bol
    from utils.dedup                import dedup_events
    all_events=_run("EIN",s_ein,sheet_state)
    results={}; threads=[]
    for lbl,fn in [("FNAC",s_fnac),("Ticketline",s_tl),("BOL",s_bol)]:
        def worker(l=lbl,f=fn): results[l]=_run(l,f,sheet_state)
        t=threading.Thread(target=worker,daemon=True); t.start(); threads.append(t)
    for t in threads: t.join(timeout=1200)
    for lbl in ["FNAC","Ticketline","BOL"]: all_events.extend(results.get(lbl,[]))
    all_events=dedup_events(all_events)
    today=date.today(); horizon=today+timedelta(days=180)
    all_events=[ev for ev in all_events if not ev.get("date") or today.isoformat()<=ev["date"]<=horizon.isoformat()]
    all_events.sort(key=lambda e: e.get("date") or "9999")
    all_events=_web_search(all_events)
    all_events=_fill_images(all_events)
    wp=sum(1 for e in all_events if e.get("price_min"))
    ws=sum(1 for e in all_events if e.get("price_source")=="web_search")
    log.info(f"Pipeline: {len(all_events)} events, {wp} prices ({ws} web search)")
    return all_events
