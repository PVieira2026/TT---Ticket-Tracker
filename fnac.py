"""Entry point — GitHub Actions calls this."""
import os, sys, logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    log.info(f"TT Tracker starting — {datetime.utcnow().isoformat()}")

    from scraper.pipeline import run_all
    from utils.sheets     import upsert_events
    from utils.dedup      import SheetState

    sid = os.environ.get("SPREADSHEET_ID","")

    # ── Load existing sheet state BEFORE scraping
    # This lets scrapers skip T2/T3 for events that already have prices
    if sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        log.info("Loading existing sheet state (skip logic)...")
        sheet_state = SheetState.from_sheet(sid)
    else:
        sheet_state = SheetState.empty()

    # ── Run all scrapers with skip awareness
    events = run_all(sheet_state=sheet_state)
    log.info(f"Total events to upsert: {len(events)}")

    # ── Write to sheet
    if sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        n = upsert_events(events, sid, os.environ.get("SHEET_NAME","Eventos"))
        log.info(f"Sheet: {n} rows written.")
    else:
        log.warning("[DRY RUN] No credentials.")
        for ev in events[:5]:
            src = ev.get("price_source","?")
            log.info(f"  {ev['name']} | {ev['date']} | "
                     f"{ev.get('price_min','-')}€-{ev.get('price_max','-')}€ [{src}]")
    log.info("Done.")


if __name__ == "__main__":
    main()
