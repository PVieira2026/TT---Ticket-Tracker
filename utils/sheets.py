"""Google Sheets — batch upsert to avoid rate limiting."""
import json, os, time
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
    """
    Batch upsert — reads all rows once, builds full updated matrix,
    writes everything in ONE API call. Avoids 429 rate-limit errors.
    """
    gc = _client()
    ws = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    # ── Read current state (1 read call)
    existing = ws.get_all_values()  # list of lists including header row

    if not existing or existing[0] != COLUMNS:
        # Sheet is empty or headers missing — write headers first
        ws.clear()
        ws.append_row(COLUMNS)
        existing = [COLUMNS]

    # Build id → row-index map (row 0 = headers, data starts at row 1)
    id_col  = COLUMNS.index("id")
    id_map  = {row[id_col]: i for i, row in enumerate(existing) if i > 0}

    # Build the full updated matrix starting from existing data
    matrix = [list(r) + [""] * max(0, len(COLUMNS) - len(r)) for r in existing]

    new_rows = []
    for ev in events:
        row = [str(ev.get(c, "") or "") for c in COLUMNS]
        if ev["id"] in id_map:
            matrix[id_map[ev["id"]]] = row   # update in-place
        else:
            new_rows.append(row)              # queue for append

    # ── Write updated existing rows in one batch
    if len(matrix) > 1:
        # Retry logic for any remaining rate-limit hits
        for attempt in range(3):
            try:
                ws.update("A1", matrix)
                break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(30)
                else:
                    raise

    # ── Append new rows in chunks of 20 (safe batch size)
    CHUNK = 20
    for i in range(0, len(new_rows), CHUNK):
        chunk = new_rows[i:i + CHUNK]
        for attempt in range(3):
            try:
                ws.append_rows(chunk, value_input_option="USER_ENTERED")
                break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) and attempt < 2:
                    time.sleep(30)
                else:
                    raise
        if i + CHUNK < len(new_rows):
            time.sleep(2)  # small pause between chunks

    return len(events)
