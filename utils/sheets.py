"""Google Sheets — batch upsert (avoids 429 rate limit)."""
import json, os, time, logging
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials

log     = logging.getLogger(__name__)
SCOPES  = ["https://www.googleapis.com/auth/spreadsheets",
           "https://www.googleapis.com/auth/drive.readonly"]
COLUMNS = ["id","name","date","platform","category","price_min","price_max",
           "url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]


def _client():
    info  = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def read_sheet(spreadsheet_id: str, gid: str = "0") -> "pd.DataFrame":
    """Read sheet using service account (works even if sheet is private)."""
    import pandas as pd
    gc = _client()
    ws = gc.open_by_key(spreadsheet_id).worksheet("Eventos")
    data = ws.get_all_records(expected_headers=COLUMNS)
    df = pd.DataFrame(data).fillna("")
    for col in COLUMNS:
        if col not in df.columns: df[col] = ""
    return df


def upsert_events(events: List[Dict], spreadsheet_id: str, sheet_name: str = "Eventos") -> int:
    gc = _client()
    ws = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    existing = ws.get_all_values()
    if not existing or existing[0] != COLUMNS:
        ws.clear(); ws.append_row(COLUMNS); existing = [COLUMNS]

    id_col  = COLUMNS.index("id")
    id_map  = {row[id_col]: i for i,row in enumerate(existing) if i > 0}
    matrix  = [list(r) + [""]*(max(0,len(COLUMNS)-len(r))) for r in existing]

    new_rows = []
    for ev in events:
        row = [str(ev.get(c,"") or "") for c in COLUMNS]
        if ev["id"] in id_map:
            matrix[id_map[ev["id"]]] = row
        else:
            new_rows.append(row)

    for attempt in range(3):
        try:
            if len(matrix)>1: ws.update("A1", matrix); break
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt<2: time.sleep(30)
            else: raise

    CHUNK=20
    for i in range(0,len(new_rows),CHUNK):
        for attempt in range(3):
            try:
                ws.append_rows(new_rows[i:i+CHUNK], value_input_option="USER_ENTERED"); break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) and attempt<2: time.sleep(30)
                else: raise
        if i+CHUNK<len(new_rows): time.sleep(2)

    log.info(f"Written {len(events)} rows to sheet.")
    return len(events)
