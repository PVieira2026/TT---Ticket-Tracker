import os, sys
from datetime import datetime
from scraper.ein        import scrape as s_ein
from scraper.fnac       import scrape as s_fnac
from scraper.ticketline import scrape as s_tl
from utils.sheets       import upsert_events


def main():
    print(f"[{datetime.utcnow().isoformat()}] TT Tracker starting...")
    all_ev, errs = [], []
    for lbl, fn in [("EIN", s_ein), ("FNAC", s_fnac), ("Ticketline", s_tl)]:
        try:
            ev = fn()
            print(f"  {lbl}: {len(ev)} events")
            all_ev.extend(ev)
        except Exception as e:
            print(f"  {lbl} error: {e}", file=sys.stderr)
            errs.append(lbl)

    s, uniq = set(), []
    for ev in all_ev:
        if ev["id"] not in s:
            s.add(ev["id"])
            uniq.append(ev)
    uniq.sort(key=lambda e: e.get("date") or "9999")

    sid = os.environ.get("SPREADSHEET_ID", "")
    if sid and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        n = upsert_events(uniq, sid, os.environ.get("SHEET_NAME", "Eventos"))
        print(f"  Sheet: {n} rows written.")
    else:
        print("  [DRY RUN] — set SPREADSHEET_ID + GOOGLE_SERVICE_ACCOUNT_JSON")

    if errs:
        print(f"  Errors: {', '.join(errs)}", file=sys.stderr)
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
