"""
Pipeline — parallel scrapers + skip logic + cross-platform dedup.
"""
import os, logging, time, threading
from typing import List, Dict
from datetime import date, timedelta

log = logging.getLogger(__name__)


def _run_scraper(label: str, fn, sheet_state=None) -> List[Dict]:
    start = time.time()
    try:
        log.info(f"[{label}] Starting...")
        # Pass sheet_state to scrapers that support it
        try:
            events = fn(sheet_state=sheet_state)
        except TypeError:
            events = fn()
        elapsed = time.time() - start
        wp = sum(1 for e in events if e.get("price_min"))
        sk = sum(1 for e in events if e.get("price_source") == "skipped")
        log.info(f"[{label}] {elapsed:.0f}s — {len(events)} events, "
                 f"{wp} with prices, {sk} skipped (already had prices)")
        return events
    except Exception as e:
        log.error(f"[{label}] FAILED: {e}")
        return []


def run_all(sheet_state=None) -> List[Dict]:
    from scraper.sources.ein        import scrape as s_ein
    from scraper.sources.fnac       import scrape as s_fnac
    from scraper.sources.ticketline import scrape as s_tl
    from scraper.sources.bol        import scrape as s_bol
    from utils.dedup                import dedup_events

    # EIN: fast, run synchronously first
    all_events = _run_scraper("EIN", s_ein, sheet_state)

    # FNAC + TL + BOL: parallel threads
    results, threads = {}, []
    for label, fn in [("FNAC", s_fnac), ("Ticketline", s_tl), ("BOL", s_bol)]:
        def worker(lbl=label, f=fn):
            results[lbl] = _run_scraper(lbl, f, sheet_state)
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=1200)

    for label in ["FNAC","Ticketline","BOL"]:
        all_events.extend(results.get(label, []))

    # Cross-platform deduplication
    all_events = dedup_events(all_events)

    # Filter future events only
    today   = date.today()
    horizon = today + timedelta(days=180)
    all_events = [
        ev for ev in all_events
        if not ev.get("date")
        or today.isoformat() <= ev["date"] <= horizon.isoformat()
    ]
    all_events.sort(key=lambda e: e.get("date") or "9999")

    wp = sum(1 for e in all_events if e.get("price_min"))
    log.info(f"Pipeline done: {len(all_events)} unique events, {wp} with prices")
    return all_events
