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
        wp=sum(1 for e in events if e.get("price_min")); sk=sum(1 for e in events if e.get("price_source")=="skipped")
        log.info(f"[{label}] {time.time()-start:.0f}s - {len(events)} events, {wp} with prices, {sk} skipped")
        return events
    except Exception as e: log.error(f"[{label}] FAILED: {e}"); return []
def run_all(sheet_state=None):
    from scraper.sources.ein import scrape as s_ein
    from scraper.sources.fnac import scrape as s_fnac
    from scraper.sources.ticketline import scrape as s_tl
    from scraper.sources.bol import scrape as s_bol
    from utils.dedup import dedup_events
    all_events=_run("EIN",s_ein,sheet_state); results={}; threads=[]
    for lbl,fn in [("FNAC",s_fnac),("Ticketline",s_tl),("BOL",s_bol)]:
        def worker(l=lbl,f=fn): results[l]=_run(l,f,sheet_state)
        t=threading.Thread(target=worker,daemon=True); t.start(); threads.append(t)
    for t in threads: t.join(timeout=1200)
    for lbl in ["FNAC","Ticketline","BOL"]: all_events.extend(results.get(lbl,[]))
    all_events=dedup_events(all_events)
    today=date.today(); horizon=today+timedelta(days=180)
    all_events=[ev for ev in all_events if not ev.get("date") or today.isoformat()<=ev["date"]<=horizon.isoformat()]
    all_events.sort(key=lambda e: e.get("date") or "9999")
    log.info(f"Pipeline done: {len(all_events)} events, {sum(1 for e in all_events if e.get('price_min'))} with prices")
    return all_events
