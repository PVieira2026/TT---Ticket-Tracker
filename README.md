# TT Tracker — Concertos & Festivais

Webapp Streamlit + scraper automatico. Stack 100% gratuita.

## Setup (15 min)

1. Fork este repo no GitHub
2. Cria Google Sheet com headers: id, name, date, platform, category, price_min, price_max, url, image_url, tickets_json, tickets_detail, updated_at, scraper_status
3. Partilha como publica (Anyone with link can view)
4. Google Cloud: Service Account + Sheets API + Drive API + partilha Sheet com SA email (Editor)
5. GitHub Secrets: GOOGLE_SERVICE_ACCOUNT_JSON, SPREADSHEET_ID
6. Streamlit Cloud: liga ao repo + secrets SPREADSHEET_ID, SHEET_GID=0
7. Testa: Actions > TT Tracker Scraper > Run workflow
