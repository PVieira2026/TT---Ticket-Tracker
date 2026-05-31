"""Entry point — called by GitHub Actions."""
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

    events = run_all()
    log.info(f"Total events to write: {len(events)}")

    sid = os.environ.get("SPREADSHEET_ID","")
    if sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        n = upsert_events(events, sid, os.environ.get("SHEET_NAME","Eventos"))
        log.info(f"Sheet: {n} rows written.")
    else:
        log.warning("[DRY RUN] — SPREADSHEET_ID or GOOGLE_SERVICE_ACCOUNT_JSON not set")
        for ev in events[:5]:
            log.info(f"  {ev['name']} | {ev['date']} | {ev.get('price_min','')}€-{ev.get('price_max','')}€ [{ev.get('price_source','?')}]")
    log.info("Done.")


if __name__ == "__main__":
    main()
