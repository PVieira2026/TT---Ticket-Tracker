import os, sys, logging
from datetime import datetime
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",datefmt="%H:%M:%S")
log=logging.getLogger(__name__)
def main():
    log.info(f"TT Tracker starting - {datetime.utcnow().isoformat()}")
    from scraper.pipeline import run_all
    from utils.sheets import upsert_events
    from utils.dedup import SheetState
    sid=os.environ.get("SPREADSHEET_ID","")
    sheet_state=SheetState.from_sheet(sid) if (sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")) else SheetState.empty()
    events=run_all(sheet_state=sheet_state); log.info(f"Total: {len(events)}")
    if sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        n=upsert_events(events,sid,os.environ.get("SHEET_NAME","Eventos")); log.info(f"Sheet: {n} rows.")
    else: log.warning("[DRY RUN]")
    log.info("Done.")
if __name__=="__main__": main()
