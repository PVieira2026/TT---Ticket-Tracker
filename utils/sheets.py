import json, os, time, logging
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
log=logging.getLogger(__name__)
SCOPES=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.readonly"]
COLUMNS=["id","name","date","platform","category","price_min","price_max","url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]

# Campos que o scraper NÃO deve sobrescrever se a linha foi editada/criada manualmente
_MANUAL_PROTECTED_FIELDS = {"price_min","price_max","tickets_json","tickets_detail","image_url","date","name","category","url"}

def _client():
    info=json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds=Credentials.from_service_account_info(info,scopes=SCOPES)
    return gspread.authorize(creds)

def read_sheet(spreadsheet_id, sheet_name="Eventos"):
    import pandas as pd
    try:
        gc=_client()
        ws=gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df=pd.DataFrame(ws.get_all_records()).fillna("")
        for col in COLUMNS:
            if col not in df.columns: df[col]=""
        return df
    except Exception as e:
        log.warning(f"read_sheet: {e}")
        import pandas as pd
        return pd.DataFrame(columns=COLUMNS)

def upsert_events(events, spreadsheet_id, sheet_name="Eventos"):
    gc=_client()
    ws=gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
    existing=ws.get_all_values()

    if not existing or existing[0]!=COLUMNS:
        ws.clear()
        ws.append_row(COLUMNS)
        existing=[COLUMNS]

    id_col=COLUMNS.index("id")
    status_col=COLUMNS.index("scraper_status")

    # Build lookup: id -> row_index in matrix
    id_map={row[id_col]: i for i, row in enumerate(existing) if i > 0}
    matrix=[list(r)+[""]*(max(0,len(COLUMNS)-len(r))) for r in existing]
    new_rows=[]

    for ev in events:
        ev_id=ev["id"]
        new_row=[str(ev.get(c,"") or "") for c in COLUMNS]

        if ev_id in id_map:
            existing_row=matrix[id_map[ev_id]]
            existing_status=existing_row[status_col] if len(existing_row)>status_col else ""

            # ── REGRA DE PROTECÇÃO MANUAL ──────────────────────────────────
            # Se a linha existente foi criada/editada manualmente, o scraper
            # NUNCA sobrescreve os campos protegidos — só actualiza updated_at
            if existing_status == "manual":
                log.info(f"[upsert] Skipping manual row: {ev.get('name','')}")
                continue

            # Se o scraper está a saltar (skipped) e já há preço na sheet,
            # não sobrescreve nada
            if ev.get("price_source") == "skipped":
                existing_price=existing_row[COLUMNS.index("price_min")] if len(existing_row)>COLUMNS.index("price_min") else ""
                if existing_price:
                    log.info(f"[upsert] Price exists, skipping scraper row: {ev.get('name','')}")
                    continue

            matrix[id_map[ev_id]]=new_row
        else:
            new_rows.append(new_row)

    # Write back full matrix
    CHUNK=500
    for attempt in range(3):
        try:
            if len(matrix)>1:
                ws.update("A1", matrix)
            break
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt<2: time.sleep(30)
            else: raise

    # Append new rows in chunks
    CHUNK=20
    for i in range(0, len(new_rows), CHUNK):
        for attempt in range(3):
            try:
                ws.append_rows(new_rows[i:i+CHUNK], value_input_option="USER_ENTERED")
                break
            except gspread.exceptions.APIError as e:
                if "429" in str(e) and attempt<2: time.sleep(30)
                else: raise
        if i+CHUNK<len(new_rows): time.sleep(2)

    log.info(f"Upserted {len(events)} events ({len(new_rows)} new, manual rows preserved).")
    return len(events)
