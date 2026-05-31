"""
Cascade pipeline:
1. Run all scrapers in parallel (one thread each).
2. Deduplicate by name similarity.
3. For events with no prices, attempt cross-platform enrichment.
"""
import logging, time, concurrent.futures
from typing import List, Dict
from datetime import date, timedelta

log = logging.getLogger(__name__)


def _run_scraper(label, fn):
    try:
        log.info(f"Starting {label}...")
        events = fn()
        log.info(f"{label}: {len(events)} events ({sum(1 for e in events if e.get('price_min'))} with prices)")
        return events
    except Exception as e:
        log.error(f"{label} failed: {e}")
        return []


def run_all() -> List[Dict]:
    from scraper.sources.ein        import scrape as s_ein
    from scraper.sources.fnac       import scrape as s_fnac
    from scraper.sources.ticketline import scrape as s_tl
    from scraper.sources.bol        import scrape as s_bol

    scrapers = [("EIN", s_ein), ("FNAC", s_fnac), ("Ticketline", s_tl), ("BOL", s_bol)]

    all_events = []
    # Run scrapers sequentially to avoid Playwright concurrency issues
    for label, fn in scrapers:
        events = _run_scraper(label, fn)
        all_events.extend(events)

    # Deduplicate by ID
    seen, unique = set(), []
    for ev in all_events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            unique.append(ev)

    # Filter to future events within 6 months
    today   = date.today()
    horizon = today + timedelta(days=180)
    unique  = [
        ev for ev in unique
        if not ev.get("date") or (
            today.isoformat() <= ev["date"] <= horizon.isoformat()
        )
    ]

    unique.sort(key=lambda e: e.get("date") or "9999")
    log.info(f"Pipeline complete: {len(unique)} unique events, "
             f"{sum(1 for e in unique if e.get('price_min'))} with prices")
    return unique
