"""
Cascade pipeline — parallel scrapers + smart tier selection.
T3 (cart navigation) capped at MAX_CART_EVENTS globally.
"""
import logging, time, threading
from typing import List, Dict
from datetime import date, timedelta

log             = logging.getLogger(__name__)
MAX_CART_EVENTS = 10   # max events that go to T3 cart per run
T3_LOCK         = threading.Lock()
t3_count        = 0    # shared counter across threads


def _run_scraper(label: str, fn) -> List[Dict]:
    start = time.time()
    try:
        log.info(f"[{label}] Starting...")
        events = fn()
        elapsed = time.time() - start
        with_prices = sum(1 for e in events if e.get("price_min"))
        log.info(f"[{label}] Done in {elapsed:.0f}s — {len(events)} events, {with_prices} with prices")
        return events
    except Exception as e:
        log.error(f"[{label}] FAILED: {e}")
        return []


def run_all() -> List[Dict]:
    global t3_count
    t3_count = 0  # reset for this run

    from scraper.sources.ein        import scrape as s_ein
    from scraper.sources.fnac       import scrape as s_fnac
    from scraper.sources.ticketline import scrape as s_tl
    from scraper.sources.bol        import scrape as s_bol

    # EIN is fast, run first synchronously
    all_events = _run_scraper("EIN", s_ein)

    # FNAC + Ticketline + BOL run in parallel threads
    results  = {}
    threads  = []
    scrapers = [("FNAC", s_fnac), ("Ticketline", s_tl), ("BOL", s_bol)]

    def worker(label, fn):
        results[label] = _run_scraper(label, fn)

    for label, fn in scrapers:
        t = threading.Thread(target=worker, args=(label, fn), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=1200)  # 20 min max per thread

    for label, _ in scrapers:
        all_events.extend(results.get(label, []))

    # Deduplicate by ID
    seen, unique = set(), []
    for ev in all_events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            unique.append(ev)

    # Filter to future events within 6 months
    today   = date.today()
    horizon = today + timedelta(days=180)
    unique  = [ev for ev in unique if not ev.get("date")
               or today.isoformat() <= ev["date"] <= horizon.isoformat()]
    unique.sort(key=lambda e: e.get("date") or "9999")

    with_prices = sum(1 for e in unique if e.get("price_min"))
    log.info(f"Pipeline complete: {len(unique)} events, {with_prices} with prices")
    return unique
