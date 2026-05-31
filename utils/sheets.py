import json, os
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials

SCOPES  = ["https://www.googleapis.com/auth/spreadsheets",
           "https://www.googleapis.com/auth/drive.readonly"]
COLUMNS = ["id","name","date","platform","category","price_min","price_max",
           "url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]

def _client():
    info  = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def upsert_events(events: List[Dict], spreadsheet_id: str, sheet_name: str = "Eventos") -> int:
    gc     = _client()
    ws     = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
    data   = ws.get_all_records(expected_headers=COLUMNS)
    id_map = {row["id"]: idx + 2 for idx, row in enumerate(data)}
    written = 0
    for ev in events:
        row = [str(ev.get(c, "") or "") for c in COLUMNS]
        if ev["id"] in id_map:
            ws.update(f"A{id_map[ev['id']]}", [row])
        else:
            ws.append_row(row, value_input_option="USER_ENTERED")
        written += 1
    return written
