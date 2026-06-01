import json, os, time, logging
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
log=logging.getLogger(__name__)
SCOPES=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.readonly"]
COLUMNS=["id","name","date","platform","category","price_min","price_max","url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]

# Fields that a user might edit manually — scraper will NOT overwrite these if the row is 'manual' or 'locked'
_HUMAN_FIELDS = {"name","date","platform","category","price_min","price_max","url","image_url","tickets_json","tickets_detail"}
# Statuses that mean "do not overwrite at all"
_PROTECTED_STATUSES = {"manual","locked","manual-locked"}

def _client():
    info=json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]); creds=Credentials.from_service_account_info(info,scopes=SCOPES); return gspread.authorize(creds)

def read_sheet(spreadsheet_id,sheet_name="Eventos"):
    import pandas as pd
    try:
        gc=_client(); ws=gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df=pd.DataFrame(ws.get_all_records()).fillna("")
        for col in COLUMNS:
            if col not in df.columns: df[col]=""
        return df
    except Exception as e: log.warning(f"read_sheet: {e}"); import pandas as pd; return pd.DataFrame(columns=COLUMNS)

def upsert_events(events,spreadsheet_id,sheet_name="Eventos"):
    gc=_client(); ws=gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
    existing=ws.get_all_values()
    if not existing or existing[0]!=COLUMNS:
        ws.clear(); ws.append_row(COLUMNS); existing=[COLUMNS]
    id_col=COLUMNS.index("id")
    status_col=COLUMNS.index("scraper_status")
    id_map={row[id_col]:i for i,row in enumerate(existing) if i>0}
    matrix=[list(r)+[""]*(max(0,len(COLUMNS)-len(r))) for r in existing]
    new_rows=[]
    for ev in events:
        ev_id=ev["id"]
        # Build the new row from scraper data
        new_row=[str(ev.get(c,"") or "") for c in COLUMNS]
        if ev_id in id_map:
            existing_row=matrix[id_map[ev_id]]
            existing_status=existing_row[status_col].strip().lower() if len(existing_row)>status_col else ""
            # PROTECTED: never overwrite rows marked manual/locked
            if existing_status in _PROTECTED_STATUSES:
                log.info(f"Skipping protected row: {ev_id} (status={existing_status})")
                continue
            # SKIPPED pricing: keep existing prices if scraper couldn't get them
            if ev.get("price_source")=="skipped":
                if existing_row[COLUMNS.index("price_min")]:
                    # Keep all existing data, only update updated_at
                    continue
            # MERGE: for normal scraper updates, preserve any manually-set fields
            # A field is considered manually-set if it differs from what the scraper found
            # AND the existing status suggests a human touched it (starts with 'manual')
            merged_row=new_row[:]
            if existing_status.startswith("manual"):
                for fi,col in enumerate(COLUMNS):
                    if col in _HUMAN_FIELDS:
                        old_val=existing_row[fi] if fi<len(existing_row) else ""
                        if old_val and old_val!=new_row[fi]:
                            merged_row[fi]=old_val  # keep human edit
            matrix[id_map[ev_id]]=merged_row
        else:
            new_rows.append(new_row)
    for attempt in range(3):
        try:
            if len(matrix)>1: ws.update("A1",matrix); break
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt<2: time.sleep(30)
            else: raise
    CHUNK=20
    for i in range(0,len(new_rows),CHUNK):
        for attempt in range(3):
            try: ws.append_rows(new_rows[i:i+CHUNK],value_input_option="USER_ENTERED"); break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) and attempt<2: time.sleep(30)
                else: raise
        if i+CHUNK<len(new_rows): time.sleep(2)
    log.info(f"Upserted {len(events)} events ({len(new_rows)} new)."); return len(events)
