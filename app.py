"""TT Tracker v3 — Merged & Upgraded."""
import os, json, re
from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TT Tracker — Concertos & Festivais",
    page_icon="🎪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');"
    "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;800;900&display=swap');"
    ":root{"
    "  --bg:#07040F;"
    "  --card:#110D1E;"
    "  --card2:#16112A;"
    "  --border:#2A1F45;"
    "  --accent:#FF5C35;"
    "  --accent2:#FF9A3C;"
    "  --purple:#8B5CF6;"
    "  --green:#00D68F;"
    "  --blue:#3B82F6;"
    "  --text:#F0EBF8;"
    "  --muted:#7C6FA0;"
    "  --tag-bg:#0E0A1C;"
    "  --past-border:#352B4A;"
    "  --danger:#EF4444;"
    "}"
    "html,body,[class*='css']{font-family:'Inter',sans-serif;background:var(--bg)!important;color:var(--text);}"
    "#MainMenu,footer,header{visibility:hidden;}"
    ".block-container{padding-top:0!important;max-width:1440px;}"

    "/* ── Hero ── */"
    ".tt-hero{"
    "  position:relative;overflow:hidden;"
    "  background:linear-gradient(135deg,#1A0533 0%,#2D0B5A 30%,#4A1070 55%,#2D0B5A 80%,#1A0533 100%);"
    "  border-radius:20px;margin-bottom:16px;padding:0;"
    "  border:1px solid rgba(139,92,246,.3);"
    "  box-shadow:0 20px 60px rgba(139,92,246,.2),0 0 0 1px rgba(255,92,53,.15);"
    "}"
    ".tt-hero-glow{"
    "  position:absolute;top:-40%;left:-10%;width:50%;height:200%;"
    "  background:radial-gradient(ellipse,rgba(255,92,53,.18) 0%,transparent 65%);"
    "  pointer-events:none;"
    "}"
    ".tt-hero-glow2{"
    "  position:absolute;top:-20%;right:-5%;width:40%;height:180%;"
    "  background:radial-gradient(ellipse,rgba(139,92,246,.2) 0%,transparent 65%);"
    "  pointer-events:none;"
    "}"
    ".tt-hero-inner{"
    "  position:relative;z-index:1;padding:36px 40px;"
    "  display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:12px;"
    "}"
    ".tt-logo-mark{"
    "  width:56px;height:56px;border-radius:14px;flex-shrink:0;"
    "  background:linear-gradient(135deg,#FF5C35,#FF9A3C);"
    "  display:flex;align-items:center;justify-content:center;"
    "  font-size:1.7rem;box-shadow:0 8px 24px rgba(255,92,53,.4);"
    "  margin:0;"
    "}"
    ".tt-title-block{min-width:0;}"
    ".tt-title{"
    "  font-family:'Outfit',sans-serif;font-weight:900;"
    "  font-size:2.6rem;line-height:1.1;"
    "  background:linear-gradient(90deg,#FF9A3C 0%,#FF5C35 40%,#C084FC 80%,#818CF8 100%);"
    "  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
    "  margin:0 0 5px;letter-spacing:-1px;"
    "}"
    ".tt-sub{font-size:.87rem;color:rgba(240,235,248,.55);font-weight:400;margin:0;letter-spacing:.3px;}"
    ".tt-tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:6px;}"
    ".tt-tag{"
    "  font-size:.68rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;"
    "  padding:3px 10px;border-radius:20px;border:1px solid;"
    "}"
    ".tt-tag-hot{background:rgba(255,92,53,.15);color:#FF7A5C;border-color:rgba(255,92,53,.35);}"
    ".tt-tag-live{background:rgba(0,214,143,.12);color:#00D68F;border-color:rgba(0,214,143,.3);"
    "  animation:pulse-dot 2s infinite;}"
    ".tt-tag-pt{background:rgba(139,92,246,.15);color:#A78BFA;border-color:rgba(139,92,246,.35);}"
    "@keyframes pulse-dot{0%,100%{box-shadow:0 0 0 0 rgba(0,214,143,.3);}50%{box-shadow:0 0 0 6px rgba(0,214,143,0);}}"

    "/* ── Action buttons ── */"
    ".action-bar{display:flex;gap:10px;align-items:center;margin-bottom:18px;}"
    "button[data-testid='baseButton-primary']{"
    "  background:linear-gradient(135deg,#FF5C35,#FF9A3C)!important;"
    "  border:none!important;border-radius:10px!important;"
    "  color:#fff!important;font-weight:700!important;"
    "  box-shadow:0 4px 15px rgba(255,92,53,.35)!important;"
    "  transition:all .2s!important;"
    "}"
    "button[data-testid='baseButton-primary']:hover{"
    "  transform:translateY(-2px)!important;"
    "  box-shadow:0 8px 25px rgba(255,92,53,.5)!important;"
    "}"
    "button[data-testid='baseButton-secondary']{"
    "  background:rgba(139,92,246,.1)!important;"
    "  border:1px solid rgba(139,92,246,.35)!important;border-radius:10px!important;"
    "  color:var(--text)!important;font-weight:600!important;"
    "  transition:all .2s!important;"
    "}"
    "button[data-testid='baseButton-secondary']:hover{"
    "  background:rgba(139,92,246,.25)!important;"
    "  border-color:rgba(139,92,246,.6)!important;"
    "  transform:translateY(-1px)!important;"
    "}"

    "/* ── Inputs ── */"
    ".stTextInput input{background:var(--card)!important;border:1px solid var(--border)!important;"
    "  border-radius:10px!important;color:var(--text)!important;padding:10px 16px!important;}"
    ".stTextInput input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(255,92,53,.15)!important;}"
    ".stSelectbox>div>div{background:var(--card)!important;border:1px solid var(--border)!important;"
    "  border-radius:10px!important;color:var(--text)!important;}"
    ".stTextArea textarea{background:var(--card)!important;border:1px solid var(--border)!important;"
    "  border-radius:10px!important;color:var(--text)!important;}"

    "/* ── Tabs ── */"
    ".stTabs [data-baseweb='tab-list']{gap:4px;background:transparent;border-bottom:1px solid var(--border)!important;}"
    ".stTabs [data-baseweb='tab']{background:transparent;border:none;border-radius:8px 8px 0 0;"
    "  color:var(--muted);font-weight:600;padding:10px 20px;font-size:.88rem;transition:color .15s;}"
    ".stTabs [data-baseweb='tab']:hover{color:var(--text)!important;}"
    ".stTabs [aria-selected='true']{background:var(--card)!important;color:#fff!important;"
    "  border-top:2px solid var(--accent)!important;}"
    ".stTabs [data-baseweb='tab-panel']{padding-top:18px;background:transparent;}"

    "/* ── Stat pills ── */"
    ".sp{"
    "  background:var(--card);border:1px solid var(--border);border-radius:12px;"
    "  padding:14px 16px;text-align:center;"
    "  transition:border-color .2s,box-shadow .2s,transform .15s;"
    "  cursor:pointer;text-decoration:none!important;display:block;"
    "}"
    ".sp:hover{"
    "  border-color:rgba(255,92,53,.5);transform:translateY(-2px);"
    "  box-shadow:0 6px 24px rgba(255,92,53,.14);"
    "}"
    ".sp.sp-active{border-color:rgba(255,92,53,.7)!important;box-shadow:0 4px 20px rgba(255,92,53,.2)!important;}"
    ".sp .n{font-family:'Outfit',sans-serif;font-size:1.7rem;font-weight:800;color:var(--accent);line-height:1;}"
    ".sp .l{font-size:.68rem;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:1px;}"

    "/* ── Event cards ── */"
    ".ev-concerto{--c-accent:#1E6FFF;--c-accent-rgb:30,111,255;}"
    ".ev-festival{--c-accent:#FF6B2B;--c-accent-rgb:255,107,43;}"
    ".ev-evento{--c-accent:#8B5CF6;--c-accent-rgb:139,92,246;}"
    ".ev-card{"
    "  background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;"
    "  transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;"
    "  display:flex;flex-direction:column;height:100%;position:relative;"
    "}"
    ".ev-card:hover{"
    "  transform:translateY(-4px);border-color:var(--c-accent)!important;"
    "  box-shadow:0 12px 40px rgba(var(--c-accent-rgb),.25),0 2px 8px rgba(0,0,0,.4);"
    "}"
    ".ev-img-wrap{position:relative;overflow:hidden;flex-shrink:0;}"
    ".ev-img{width:100%;height:200px;object-fit:cover;display:block;transition:filter .3s,opacity .3s;}"
    ".ev-noimg{"
    "  width:100%;height:200px;display:flex;align-items:center;justify-content:center;"
    "  font-size:3.5rem;"
    "  background:linear-gradient(135deg,#1A0D35 0%,#2D1060 50%,#1A0D35 100%);"
    "}"
    ".ev-img-link{display:block;}"
    ".ev-img-link:hover .ev-img,.ev-img-link:hover .ev-noimg{opacity:.85;}"

    "/* ── Past event styles ── */"
    ".past-card{border-color:var(--past-border)!important;}"
    ".past-card:hover{transform:none!important;border-color:var(--past-border)!important;"
    "  box-shadow:none!important;}"
    ".past-card .ev-img{filter:grayscale(55%) brightness(0.6);}"
    ".past-stamp{"
    "  position:absolute;top:26px;left:-36px;"
    "  width:180px;text-align:center;"
    "  transform:rotate(-35deg);"
    "  background:rgba(185,15,15,.93);"
    "  color:#fff;"
    "  font-family:'Outfit',sans-serif;"
    "  font-weight:900;font-size:.7rem;"
    "  letter-spacing:2.5px;"
    "  padding:7px 0;"
    "  text-transform:uppercase;"
    "  z-index:5;"
    "  box-shadow:0 3px 16px rgba(0,0,0,.6);"
    "  border-top:1px solid rgba(255,120,120,.25);"
    "  border-bottom:1px solid rgba(255,120,120,.25);"
    "  white-space:nowrap;"
    "}"

    "/* ── Card inner ── */"
    ".ev-ribbon{color:#fff;font-size:.68rem;font-weight:700;letter-spacing:.8px;padding:5px 12px;text-transform:uppercase;}"
    ".r-concerto{background:#1E6FFF;}"
    ".r-festival{background:#FF6B2B;}"
    ".r-evento{background:#8B5CF6;}"
    ".hot-badge{background:rgba(255,154,60,.2);color:#FF9A3C;font-size:.62rem;font-weight:700;"
    "  padding:2px 8px;border-radius:20px;margin-left:6px;letter-spacing:.5px;"
    "  border:1px solid rgba(255,154,60,.4);}"
    ".manual-badge{background:rgba(0,214,143,.1);color:#00D68F;font-size:.6rem;font-weight:700;"
    "  padding:1px 7px;border-radius:10px;margin-left:5px;border:1px solid rgba(0,214,143,.3);}"
    ".ev-body{padding:16px;flex:1;display:flex;flex-direction:column;}"
    ".ev-name{font-size:1.05rem;font-weight:700;color:#fff;margin:0 0 5px;line-height:1.3;}"
    ".ev-title-link{color:#fff!important;text-decoration:none!important;display:block;margin-bottom:5px;}"
    ".ev-title-link:hover{color:var(--accent)!important;}"
    ".ev-date-row{"
    "  font-size:.82rem;font-weight:600;color:var(--accent2);"
    "  margin-bottom:6px;display:flex;align-items:center;gap:5px;"
    "}"
    ".ev-date-row.past-date{color:var(--muted);font-weight:500;}"
    ".ev-meta{display:flex;gap:8px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin-bottom:12px;}"
    ".ev-meta .soon{color:#00D68F;font-weight:600;}"
    ".ev-meta .past-txt{color:#5A4D6E;}"

    "/* ── Prices ── */"
    ".ev-prices{background:var(--tag-bg);border:1px solid rgba(42,31,69,.8);"
    "  border-radius:10px;padding:10px 12px;margin-bottom:12px;flex:1;}"
    ".ev-prices-hdr{font-size:.67rem;font-weight:700;letter-spacing:1px;color:var(--accent);"
    "  text-transform:uppercase;margin-bottom:8px;}"
    ".pr-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;"
    "  border-bottom:1px solid rgba(42,31,69,.8);font-size:.82rem;}"
    ".pr-row:last-child{border-bottom:none;}"
    ".pr-sec{color:var(--text);font-weight:500;}"
    ".pr-val{color:var(--green);font-weight:700;font-size:.9rem;white-space:nowrap;}"
    ".pr-sold{color:#EF4444;font-size:.72rem;font-weight:600;margin-left:4px;}"
    ".pr-note{color:var(--muted);font-size:.72rem;font-style:italic;margin-left:4px;}"
    ".no-price{color:var(--muted);font-size:.82rem;font-style:italic;padding:4px 0;}"
    ".ver-mais-btn{background:none;border:none;color:var(--muted);font-size:.72rem;"
    "  padding:5px 0 0;cursor:pointer;text-align:left;width:100%;transition:color .15s;}"
    ".ver-mais-btn:hover{color:var(--accent);}"

    "/* ── Card footer ── */"
    ".ev-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:8px;}"
    ".src-link{color:var(--muted);font-size:.72rem;text-decoration:none!important;transition:color .15s;}"
    ".src-link:hover{color:var(--accent)!important;}"

    "/* ── Add form section ── */"
    ".add-section{"
    "  background:linear-gradient(135deg,#130826 0%,#1E0D40 100%);"
    "  border:1px solid rgba(139,92,246,.35);"
    "  border-radius:16px;padding:28px 32px;margin-bottom:24px;"
    "  box-shadow:0 8px 32px rgba(139,92,246,.12);"
    "}"
    ".add-section-title{"
    "  font-family:'Outfit',sans-serif;font-weight:800;font-size:1.4rem;"
    "  background:linear-gradient(90deg,#C084FC,#818CF8);"
    "  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
    "  margin:0 0 4px;"
    "}"
    ".add-section-sub{color:var(--muted);font-size:.85rem;margin:0 0 22px;}"
    ".add-divider{border:none;border-top:1px solid rgba(139,92,246,.2);margin:20px 0;}"
    ".add-field-label{font-size:.82rem;font-weight:600;color:var(--muted);"
    "  text-transform:uppercase;letter-spacing:.8px;margin:16px 0 6px;}"

    "/* ── Misc ── */"
    ".no-res{text-align:center;padding:60px 20px;color:var(--muted);}"
    ".ts{font-size:.72rem;color:var(--muted);text-align:right;margin-top:4px;margin-bottom:14px;}"
    ".stButton>button{transition:all .2s!important;}"

    "/* ── JS-style delete button ── */"
    "<script>"
    "(function applyDelStyle(){"
    "  document.querySelectorAll('button').forEach(function(b){"
    "    if(b.innerText&&b.innerText.includes('Remover do Sheet')){"
    "      b.style.cssText+='background:rgba(239,68,68,.12)!important;border-color:rgba(239,68,68,.35)!important;color:#F87171!important;';"
    "    }"
    "  });"
    "  setTimeout(applyDelStyle,800);"
    "})()"
    "</script>"
    "</style>"
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
COLS = ["id","name","date","platform","category","price_min","price_max",
        "url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]
HIGH_REL = [
    "coldplay","radiohead","ed sheeran","billie eilish","taylor swift","the weeknd",
    "beyonce","rihanna","adele","harry styles","depeche mode","the national","arcade fire",
    "arctic monkeys","metallica","iron maiden","foo fighters","red hot chili peppers",
    "guns n roses","blur","oasis","placebo","laura pausini","anitta","anastacia",
    "brandi carlile","dua lipa","imagine dragons","maroon 5","lana del rey","the cure",
    "massive attack","nos alive","super bock","mares vivas","neopop","paredes de coura",
    "primavera sound","rock in rio","evillive","meo mares","sudowoodo"
]

def relevance(name, url=""):
    t = (name + " " + url).lower()
    if any(k in t for k in HIGH_REL): return 3
    if any(k in t for k in ["festival","altice","coliseu","pavilh","campo pequeno","arena"]): return 2
    return 1

def _s(k, d=""):
    try: return os.environ.get(k) or st.secrets.get(k, d)
    except: return d

SPREADSHEET_ID = _s("SPREADSHEET_ID")
GID = _s("SHEET_GID", "0")
SA_JSON = _s("GOOGLE_SERVICE_ACCOUNT_JSON")

# ── Data layer ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=15, show_spinner=False)
def load_data():
    """Load events — gspread (service account) or CSV fallback with real-time cache-bust."""
    if not SPREADSHEET_ID or SPREADSHEET_ID == "id-da-sheet":
        return pd.DataFrame()
    if SA_JSON and len(SA_JSON) > 50:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
                      "https://www.googleapis.com/auth/drive.readonly"]
            creds = Credentials.from_service_account_info(json.loads(SA_JSON), scopes=SCOPES)
            gc = gspread.authorize(creds)
            ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Eventos")
            df = pd.DataFrame(ws.get_all_records()).fillna("")
            df["_row_idx"] = range(len(df))
            for c in COLS:
                if c not in df.columns: df[c] = ""
            df["_date_start"], df["_date_end"] = zip(*df["date"].apply(_split_date_range))
            df["_dt"] = pd.to_datetime(df["_date_start"], errors="coerce")
            df["_rel"] = df.apply(lambda r: relevance(r["name"], r.get("url", "")), axis=1)
            df = _dedup_display(df)
            return df.sort_values(["_dt","_row_idx"], na_position="last").reset_index(drop=True)
        except Exception as e:
            st.toast(f"gspread: {e}", icon="⚠️")
    # Fallback: public CSV with cache-buster
    try:
        import time as _ct
        ts_buster = int(_ct.time())
        url = (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
               f"/gviz/tq?tqx=out:csv&gid={GID}&t={ts_buster}")
        df = pd.read_csv(url, dtype=str).fillna("")
        if "name" in df.columns:
            df = df[df["name"].str.strip() != ""]
        df["_row_idx"] = range(len(df))
        for c in COLS:
            if c not in df.columns: df[c] = ""
        df["_date_start"], df["_date_end"] = zip(*df["date"].apply(_split_date_range))
        df["_dt"] = pd.to_datetime(df["_date_start"], errors="coerce")
        df["_rel"] = df.apply(lambda r: relevance(r["name"], r.get("url", "")), axis=1)
        df = _dedup_display(df)
        return df.sort_values(["_dt","_row_idx"], na_position="last").reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def _split_date_range(d_str):
    """Split 'YYYY-MM-DD' or 'YYYY-MM-DD/YYYY-MM-DD' into (start, end)."""
    s = str(d_str).strip()
    if "/" in s:
        parts = s.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    return s, ""

def get_data(force=False):
    if force:
        load_data.clear()
    return load_data()

def _dedup_display(df):
    """Deduplicate by normalised name. Manual/locked rows always win."""
    import re as _r
    if df.empty: return df
    def norm(n): return ' '.join(sorted(_r.sub(r'[^a-z0-9\s]', ' ', n.lower()).split()))
    df['_norm'] = df['name'].apply(norm)
    _MANUAL_STATUSES = {'manual', 'locked', 'manual-locked'}
    df['_is_manual'] = (df.get('scraper_status', pd.Series([''] * len(df)))
                        .str.strip().str.lower().isin(_MANUAL_STATUSES).astype(int))
    df['_score'] = (
        df['_is_manual'] * 1000
        + (df['price_min'].str.len() > 0).astype(int) * 10
        + df['tickets_detail'].str.len().fillna(0).clip(0, 100)
    )
    df = df.sort_values('_score', ascending=False).drop_duplicates(subset=['_norm'], keep='first')
    return df.drop(columns=['_norm','_score','_is_manual'], errors='ignore')

# ── Web search helpers ────────────────────────────────────────────────────────

def _search_event_web(query):
    import requests as _req
    sk = ''
    try: sk = os.environ.get('SERPER_API_KEY') or st.secrets.get('SERPER_API_KEY', '')
    except: sk = os.environ.get('SERPER_API_KEY', '')
    snippets = []
    if sk:
        try:
            resp = _req.post('https://google.serper.dev/search',
                headers={'X-API-KEY': sk, 'Content-Type': 'application/json'},
                json={'q': query + ' bilhetes preco portugal', 'gl': 'pt', 'hl': 'pt', 'num': 6},
                timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('answerBox'):
                    ab = data['answerBox']
                    snippets.append({'title': 'answer',
                                     'snippet': ab.get('snippet', ab.get('answer', '')),
                                     'link': ab.get('link', '')})
                for r2 in data.get('organic', []):
                    snippets.append({'title': r2.get('title',''),
                                     'snippet': r2.get('snippet',''),
                                     'link': r2.get('link','')})
        except: pass
    if not snippets:
        try:
            resp = _req.get('https://api.duckduckgo.com/',
                params={'q': query + ' bilhetes', 'format': 'json', 'no_html': 1}, timeout=10)
            data = resp.json()
            if data.get('AbstractText'):
                snippets.append({'title': data.get('Heading',''),
                                 'snippet': data['AbstractText'],
                                 'link': data.get('AbstractURL','')})
        except: pass
    return snippets

def _parse_snippets(snippets):
    combined = ' | '.join(s.get('snippet','') for s in snippets)
    MONTHS = {
        'jan':1,'fev':2,'mar':3,'abr':4,'mai':5,'jun':6,'jul':7,'ago':8,
        'set':9,'out':10,'nov':11,'dez':12,'janeiro':1,'fevereiro':2,'marco':3,
        'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,
        'outubro':10,'novembro':11,'dezembro':12
    }
    date_found = ''
    for s in snippets:
        txt = s.get('snippet','')
        m = re.search(r'(\d{1,2})\s+(?:de\s+)?([a-záéíóúç]+)(?:\s+de)?\s+(202[5-9])', txt, re.I)
        if m:
            mon = MONTHS.get(m.group(2).lower()) or MONTHS.get(m.group(2)[:3].lower())
            if mon:
                date_found = f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
                break
        m2 = re.search(r'(\d{2})/(\d{2})/(202[5-9])', txt)
        if m2:
            date_found = f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
            break
    price_lines = [l.strip() for l in re.split(r'[\n;|]', combined)
                   if '€' in l and 8 <= len(l.strip()) <= 150]
    url = ''
    for s in snippets:
        lnk = s.get('link','')
        if any(p in lnk for p in ['blueticket','ticketline','bilheteira.fnac','bol.pt','livenation','everythingisnew']):
            url = lnk; break
    if not url and snippets: url = snippets[0].get('link','')
    return {'date': date_found, 'price_lines': price_lines, 'url': url}

# ── Sheet operations ──────────────────────────────────────────────────────────

def _delete_row_from_sheet(ev_id, ev_name):
    """Remove event row from Google Sheets by ID or name."""
    if not SA_JSON or len(SA_JSON) < 50:
        st.error("GOOGLE_SERVICE_ACCOUNT_JSON não configurado.")
        return False
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(json.loads(SA_JSON), scopes=SCOPES)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Eventos")
        existing = ws.get_all_records()
        row_num = None
        for i, r in enumerate(existing):
            if str(r.get('id','')) == str(ev_id) or str(r.get('name','')) == str(ev_name):
                row_num = i + 2  # +1 header, +1 0-indexed
                break
        if row_num:
            ws.delete_rows(row_num)
            st.cache_data.clear()
            return True
        st.error(f"Evento «{ev_name}» não encontrado no Sheet.")
        return False
    except Exception as e:
        st.error(f"Erro ao remover: {e}")
        return False

# ── Display helpers ───────────────────────────────────────────────────────────

def pp(v):
    try: return float(str(v).replace(",",".").strip())
    except: return 0.0

def is_past_event(d_str):
    """True if event start date is before today."""
    try:
        return datetime.fromisoformat(str(d_str).strip()).date() < date.today()
    except: return False

def fd(d_str):
    """Format a single date nicely with emoji suffix."""
    try:
        dt = datetime.fromisoformat(str(d_str).strip())
        mn = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        days = (dt.date() - date.today()).days
        if days < 0: return f"{dt.day} {mn[dt.month-1]} {dt.year}"
        suf = " 🔥" if days <= 7 else " 📅" if days <= 30 else ""
        return f"{dt.day} {mn[dt.month-1]} {dt.year}{suf}"
    except: return str(d_str) or "TBD"

def fd_range(d_start, d_end):
    """Format a date range for multi-day events/festivals."""
    try:
        mn = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        s = datetime.fromisoformat(str(d_start).strip())
        e = datetime.fromisoformat(str(d_end).strip())
        if s.year == e.year and s.month == e.month:
            return f"{s.day}–{e.day} {mn[s.month-1]} {s.year}"
        elif s.year == e.year:
            return f"{s.day} {mn[s.month-1]} – {e.day} {mn[e.month-1]} {s.year}"
        else:
            return f"{s.day} {mn[s.month-1]} {s.year} – {e.day} {mn[e.month-1]} {e.year}"
    except: return fd(d_start)

def days_until(d_str):
    try: return (datetime.fromisoformat(str(d_str).strip()).date() - date.today()).days
    except: return 999

def rcls(cat):
    c = (cat or "").lower()
    if "festival" in c: return "r-festival"
    if "concerto" in c: return "r-concerto"
    return "r-evento"

def plat_s(p):
    p = (p or "").lower()
    if "fnac" in p: return "FNAC"
    if "ticketline" in p: return "Ticketline"
    if "everything" in p: return "EIN"
    if "bol" in p: return "BOL"
    if "blueticket" in p: return "Blueticket"
    return p.split()[0].title() if p.strip() else ""

def price_rows(tj, td):
    rows = []
    # Priority 1 — tickets_detail (manual / formatted text)
    if td:
        for line in td.splitlines():
            line = line.strip()
            if not line: continue
            if ":" in line:
                pts = line.split(":", 1)
                sec = pts[0].strip(); rest = pts[1].strip()
                m = re.search(r"(\d+(?:[,.]?\d+)?)\s*€", rest)
                if m and sec:
                    rows.append({"sector": sec,
                                 "price": float(m.group(1).replace(",",".")),
                                 "note": "",
                                 "sold_out": "esgotado" in rest.lower()})
                    continue
            m = re.search(r"^(.+?)\s+(\d+(?:[,.]?\d+)?)\s*€\s*$", line)
            if m:
                sec = m.group(1).strip()
                price = float(m.group(2).replace(",","."))
                if sec and price > 0:
                    rows.append({"sector": sec, "price": price, "note": "",
                                 "sold_out": "esgotado" in line.lower()})
        if rows: return rows
    # Priority 2 — tickets_json (scraper output)
    if tj:
        try:
            for cat in json.loads(tj).get("categories",[]):
                for row in cat.get("rows",[]):
                    sec = row.get("sector","Geral") or "Geral"
                    note = row.get("note","") or ""
                    sold = row.get("sold_out", False)
                    for p in row.get("prices",[{"price": row.get("price",0)}]):
                        pv = p.get("price", row.get("price",0))
                        pn = note or p.get("note","") or ""
                        if pn in ("Preco","Preço",""): pn = ""
                        if pv and float(pv) > 0:
                            rows.append({"sector": sec, "price": float(pv), "note": pn,
                                         "sold_out": bool(sold or p.get("sold_out",False))})
            if rows: return rows
        except: pass
    return []

# ── Card rendering ────────────────────────────────────────────────────────────

def render_card(row, card_idx=0):
    name    = str(row.get("name","") or "")
    d_start = str(row.get("_date_start", row.get("date","")) or "").strip()
    d_end   = str(row.get("_date_end","") or "").strip()
    plat    = str(row.get("platform","") or "")
    cat     = str(row.get("category","Evento") or "Evento")
    url     = str(row.get("url","") or "")
    img     = str(row.get("image_url","") or "")
    tj      = str(row.get("tickets_json","") or "")
    td      = str(row.get("tickets_detail","") or "")
    rel     = int(row.get("_rel",1))
    ev_id   = str(row.get("id","") or "")
    status  = str(row.get("scraper_status","") or "").strip().lower()
    _MANUAL = {"manual","locked","manual-locked"}
    is_manual = status in _MANUAL or status.startswith("manual")

    # Category CSS class color mapping
    cat_lower = cat.lower()
    if "festival" in cat_lower:
        card_cat_cls = " ev-festival"
    elif "concerto" in cat_lower:
        card_cat_cls = " ev-concerto"
    else:
        card_cat_cls = " ev-evento"

    # Past event?
    past = is_past_event(d_start) if d_start else False
    past_cls = " past-card" if past else ""

    # Date display
    has_end = bool(d_end and d_end != d_start)
    if d_start:
        date_display = fd_range(d_start, d_end) if has_end else fd(d_start)
    else:
        date_display = "Data TBD"
    date_cls = "past-date" if past else ""

    # Platform / soon meta
    du = days_until(d_start) if d_start else 999
    if past:
        meta_html = f'<span class="past-txt">📍 {plat_s(plat)}</span>'
    else:
        soon_bit = ""
        if 0 <= du <= 7:
            soon_bit = f' · <span class="soon">🔥 em {du}d</span>'
        elif 0 < du <= 30:
            soon_bit = f' · <span class="soon">em {du}d</span>'
        meta_html = f'<span>🎫 {plat_s(plat)}</span>{soon_bit}'

    # Image block with safe onerror fallback image to prevent UIs glitches
    if img:
        img_tag = f'<img class="ev-img" src="{img}" onerror="this.onerror=null;this.src=\'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=400\';">'
    else:
        img_tag = '<div class="ev-noimg">🎵</div>'
    img_block = (f'<a href="{url}" target="_blank" rel="noopener" class="ev-img-link">{img_tag}</a>'
                 if url else img_tag)

    # JÁ REALIZADO stamp
    stamp = '<div class="past-stamp">JÁ REALIZADO</div>' if past else ""

    # Ribbon + badges
    hb = '<span class="hot-badge">🔥 DESTAQUE</span>' if rel == 3 else ""
    mb = '<span class="manual-badge">✏️ manual</span>' if is_manual else ""
    rb = f'<div class="ev-ribbon {rcls(cat)}">{cat}{hb}</div>'

    # Name
    if url:
        name_html = (f'<a href="{url}" target="_blank" rel="noopener" '
                     f'class="ev-title-link ev-name">{name}{mb}</a>')
    else:
        name_html = f'<div class="ev-name">{name}{mb}</div>'

    # Date row
    date_icon = "📅" if not past else "🕐"
    date_row = (f'<div class="ev-date-row {date_cls}">'
                f'<span>{date_icon}</span><span>{date_display}</span></div>')

    # Prices block with working + categorias toggle (fixed single quotes and element selectors)
    prows = price_rows(tj, td)
    if prows:
        import hashlib as _hlib
        _uid = "pr_" + _hlib.md5((name + str(card_idx)).encode()).hexdigest()[:8]
        VISIBLE = 6

        def _pr_line(r):
            nt = f'<span class="pr-note">({r["note"]})</span>' if r["note"] else ""
            sl = '<span class="pr-sold">ESGOTADO</span>' if r["sold_out"] else ""
            pv = r["price"]
            pstr = str(int(pv)) if pv == int(pv) else f"{pv:.1f}"
            return (f'<div class="pr-row">'
                    f'<span class="pr-sec">{r["sector"]}{nt}</span>'
                    f'<span class="pr-val">{pstr}€{sl}</span></div>')

        visible_lines = "".join(_pr_line(r) for r in prows[:VISIBLE])
        extra_lines   = "".join(_pr_line(r) for r in prows[VISIBLE:])
        extra_block   = ""
        ver_mais_btn  = ""
        if len(prows) > VISIBLE:
            extra_block = f'<div id="{_uid}" style="display:none">{extra_lines}</div>'
            n_extra = len(prows) - VISIBLE
            ver_mais_btn = (
                f"<button class='ver-mais-btn' onclick=\"(function(b){{"
                f"var el=document.getElementById('{_uid}');"
                f"if(el.style.display==='none'){{"
                f"el.style.display='block';"
                f"b.textContent='▲ ver menos'}}"
                f"else{{"
                f"el.style.display='none';"
                f"b.textContent='▼ +{n_extra} categorias'}}}}"
                f")(this)\">▼ +{n_extra} categorias</button>"
            )
        pb = (f'<div class="ev-prices">'
              f'<div class="ev-prices-hdr">🎫 Bilhetes</div>'
              f'{visible_lines}{extra_block}{ver_mais_btn}</div>')
    else:
        pb = '<div class="ev-prices"><span class="no-price">Preços em breve</span></div>'

    # Footer link
    lk = f'<a href="{url}" target="_blank" class="src-link">ver fonte ↗</a>' if url else ""
    footer = f'<div class="ev-footer">{lk}</div>'

    # Render card (includes dynamic category class)
    st.markdown(
        f'<div class="ev-card{card_cat_cls}{past_cls}">'
        f'<div class="ev-img-wrap">{img_block}{stamp}</div>'
        f'{rb}'
        f'<div class="ev-body">'
        f'{name_html}'
        f'{date_row}'
        f'<div class="ev-meta">{meta_html}</div>'
        f'{pb}{footer}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Delete button (only for past events with SA_JSON) ────────────────
    if past and ev_id and SA_JSON and len(SA_JSON) > 50:
        confirm_key = f"confirm_del_{ev_id}_{card_idx}"
        del_key     = f"del_{ev_id}_{card_idx}"
        if st.session_state.get(confirm_key):
            co1, co2 = st.columns(2)
            with co1:
                if st.button("✅ Confirmar remoção", key=f"yes_{del_key}",
                             use_container_width=True, type="primary"):
                    if _delete_row_from_sheet(ev_id, name):
                        st.success(f'"{name}" removido do Sheet!')
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            with co2:
                if st.button("❌ Cancelar", key=f"no_{del_key}", use_container_width=True):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
        else:
            if st.button(f"🗑️ Remover do Sheet", key=del_key, use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()


def render_grid(df, base_idx=0):
    if df.empty:
        st.markdown(
            '<div class="no-res">'
            '<div style="font-size:3rem;margin-bottom:12px">🔍</div>'
            '<p>Sem resultados.</p></div>',
            unsafe_allow_html=True
        )
        return
    for i in range(0, len(df), 3):
        cols = st.columns(3, gap="medium")
        for j, col in enumerate(cols):
            if i + j < len(df):
                with col:
                    render_card(df.iloc[i + j], card_idx=base_idx + i + j)
        st.markdown("<br>", unsafe_allow_html=True)

# ── Add event form ────────────────────────────────────────────────────────────

def _render_add_form():
    st.markdown(
        '<div class="add-section">'
        '<div class="add-section-title">✏️ Adicionar Evento</div>'
        '<div class="add-section-sub">'
        'Preenche os campos abaixo e guarda directamente no Sheet. '
        'Usa a pesquisa web (opcional) para pré-preencher dados.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Optional web search (collapsed by default)
    with st.expander("🔍 Pesquisar dados na web (opcional)", expanded=False):
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            q = st.text_input('', '', placeholder='Ex: NOS Alive 2026, Placebo Lisboa, Sol da Caparica...',
                              label_visibility='collapsed', key='mq')
        with sc2:
            go = st.button('🔍 Pesquisar', use_container_width=True, key='ms')
        if go and q.strip():
            with st.spinner('A pesquisar na web...'):
                snips = _search_event_web(q.strip())
                parsed = _parse_snippets(snips)
                parsed['snips'] = snips
            st.session_state['mr'] = parsed
            st.session_state['mn'] = q.strip()
        if 'mr' in st.session_state:
            r0 = st.session_state['mr']
            for s in r0.get('snips',[])[:5]:
                lnk = s.get('link',''); title = s.get('title',''); snippet = s.get('snippet','')
                if not lnk: continue
                icon = '🎫' if any(p in lnk for p in
                    ['blueticket','ticketline','bilheteira.fnac','bol.pt','livenation']) else '🔗'
                st.markdown(
                    f"{icon} **[{title or lnk[:60]}]({lnk})**  \n`{snippet[:140]}`"
                    if snippet else f"{icon} **[{title or lnk}]({lnk})**"
                )
                st.divider()
            if r0.get('price_lines'):
                with st.expander('💰 Preços encontrados (referência)'):
                    for ln in r0['price_lines'][:8]: st.code(ln, language=None)

    # Pre-fill values from web search
    r = st.session_state.get('mr', {})
    _prefill_name = st.session_state.get('mn', '')
    _prefill_url  = r.get('url', '')
    _prefill_date = r.get('date', '')

    # ── Row 1: Name ───────────────────────────────────────────────────────
    st.markdown('<div class="add-field-label">Nome do Evento</div>', unsafe_allow_html=True)
    nm = st.text_input('Nome do evento *', value=_prefill_name,
                       placeholder='Ex: NOS Alive 2026',
                       label_visibility='collapsed', key='mm_n')

    # ── Row 2: Platform + Category ────────────────────────────────────────
    pc1, pc2 = st.columns(2)
    with pc1:
        plat = st.selectbox('Plataforma', ['FNAC Bilheteira','Ticketline','Everything Is New',
                                            'BOL','Blueticket','Outro'], key='mm_p')
    with pc2:
        cat = st.selectbox('Categoria', ['Festival','Concerto','Evento'], key='mm_c')

    # ── Row 3: Dates (own row so calendar doesn't overlap) ────────────────
    st.markdown('<div class="add-field-label">📅 Datas</div>', unsafe_allow_html=True)
    # Give dates plenty of space with a 3-column layout
    dcol1, dcol2, dcol_spacer = st.columns([1.4, 1.4, 2])
    with dcol1:
        _dt_default = None
        try:
            if _prefill_date:
                _dt_default = date.fromisoformat(_prefill_date)
        except: pass
        dt_start = st.date_input(
            'Data de início *',
            value=_dt_default,
            format='DD/MM/YYYY',
            key='mm_d_start'
        )
    with dcol2:
        dt_end = st.date_input(
            'Data de fim (opcional)',
            value=None,
            format='DD/MM/YYYY',
            key='mm_d_end'
        )

    dt_start_str = dt_start.isoformat() if dt_start else ''
    # Build date field value: "start/end" if multi-day, else just start
    if dt_end and dt_start and dt_end > dt_start:
        date_to_save = f"{dt_start_str}/{dt_end.isoformat()}"
    else:
        date_to_save = dt_start_str

    # ── Row 4: URL + Image ────────────────────────────────────────────────
    ui1, ui2 = st.columns(2)
    with ui1:
        ev_url = st.text_input('URL do evento', value=_prefill_url, key='mm_u')
    with ui2:
        ev_img = st.text_input('URL da imagem',
                               value=st.session_state.get('mm_img_v',''),
                               placeholder='https://...', key='mm_img')
    if ev_img:
        try: st.image(ev_img, width=180, caption='Preview')
        except: st.markdown(f'`{ev_img[:80]}`')

    # ── Row 5: Prices ─────────────────────────────────────────────────────
    st.markdown('<div class="add-field-label">💰 Preços</div>', unsafe_allow_html=True)
    pr1, pr2, pr3 = st.columns([1, 1, 2])
    with pr1:
        pmin = st.text_input('Preço mínimo (€)', '', placeholder='25', key='mm_pn')
    with pr2:
        pmax = st.text_input('Preço máximo (€)', '', placeholder='85', key='mm_px')
    with pr3:
        detail = st.text_area('Bilhetes (linha por linha)', '', height=90,
                               placeholder='Bilhete Diário: 25€\nPasse 3 dias: 75€', key='mm_det')

    st.markdown('<hr class="add-divider">', unsafe_allow_html=True)

    # ── Action buttons ────────────────────────────────────────────────────
    ba1, ba2, ba3 = st.columns([3, 1.4, 1.2])
    with ba1:
        if st.button('✅ Guardar no Sheet', use_container_width=True,
                     key='mm_save', type='primary'):
            if not nm.strip():
                st.error('Nome é obrigatório.')
            elif not dt_start_str:
                st.error('Data de início é obrigatória.')
            elif not SPREADSHEET_ID or not SA_JSON or len(SA_JSON) < 50:
                st.error('Configura os Streamlit Secrets (SPREADSHEET_ID + GOOGLE_SERVICE_ACCOUNT_JSON).')
            else:
                try:
                    import gspread
                    from google.oauth2.service_account import Credentials as _Cred
                    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                              'https://www.googleapis.com/auth/drive.readonly']
                    creds = _Cred.from_service_account_info(json.loads(SA_JSON), scopes=SCOPES)
                    gc = gspread.authorize(creds)
                    ws = gc.open_by_key(SPREADSHEET_ID).worksheet('Eventos')
                    slug = re.sub(r'[^a-z0-9]+', '-', nm.lower()).strip('-')
                    ev_id = f'manual-{slug[:30]}'
                    lo = float(pmin.replace(',','.')) if pmin else 0
                    hi = float(pmax.replace(',','.')) if pmax else lo
                    rows_d = []
                    if detail:
                        for ln in detail.splitlines():
                            m3 = re.search(r'([^:]+):\s*(\d+(?:[,.]?\d+)?)\s*€', ln)
                            if m3:
                                rows_d.append({'sector': m3.group(1).strip(),
                                               'price': float(m3.group(2).replace(',','.')),
                                               'note': '', 'sold_out': False})
                    if not rows_d and lo:
                        rows_d = [
                            {'sector':'Preço mínimo','price':lo,'note':'manual','sold_out':False},
                            {'sector':'Preço máximo','price':hi,'note':'manual','sold_out':False}
                        ]
                    prices_d = [r2['price'] for r2 in rows_d]
                    tj_save = (json.dumps({
                        'summary': {'min': min(prices_d), 'max': max(prices_d), 'currency': 'EUR'},
                        'categories': [{'name': 'Bilhetes', 'rows': rows_d}]
                    }, ensure_ascii=False) if prices_d else '')
                    final_img = ev_img or st.session_state.get('mm_img_v','')
                    row_data = [
                        ev_id, nm.strip(), date_to_save, plat, cat,
                        str(min(prices_d)) if prices_d else '',
                        str(max(prices_d)) if prices_d else '',
                        ev_url, final_img, tj_save, detail,
                        datetime.utcnow().isoformat(), 'manual'
                    ]
                    existing = ws.get_all_records()
                    id_map = {r2.get('id'): i + 2 for i, r2 in enumerate(existing)}
                    if ev_id in id_map:
                        ws.update(f'A{id_map[ev_id]}', [row_data])
                        st.success(f'✅ "{nm}" actualizado!')
                    else:
                        ws.append_row(row_data, value_input_option='USER_ENTERED')
                        st.success(f'✅ "{nm}" adicionado!')
                    st.cache_data.clear()
                    get_data(force=True)
                    for k in ['mr','mn','mm_img_v']:
                        if k in st.session_state: del st.session_state[k]
                except Exception as e:
                    st.error(f'Erro ao guardar: {e}')
    with ba2:
        if st.button('🔄 Limpar formulário', use_container_width=True, key='mm_clear'):
            for k in ['mr','mn','mm_img_v']:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    with ba3:
        if st.button('✖ Fechar', use_container_width=True, key='mm_close'):
            st.session_state['show_add'] = False
            st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Session state init
    if 'show_add' not in st.session_state:
        st.session_state['show_add'] = False

    # Load data
    with st.spinner("A carregar eventos..."):
        df_all = get_data()

    tot_all = len(df_all)

    import datetime as _dtnow
    _fetch_t = _dtnow.datetime.now().strftime("%H:%M")
    last_scrape = ""
    if not df_all.empty:
        _last = df_all["updated_at"].replace("","NaT")
        _last = _last[_last != "NaT"]
        if not _last.empty:
            try: last_scrape = pd.to_datetime(_last.iloc[0]).strftime("%d/%m %H:%M")
            except: pass

    # ── HERO ──────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="tt-hero">'
        '<div class="tt-hero-glow"></div>'
        '<div class="tt-hero-glow2"></div>'
        '<div class="tt-hero-inner">'
        '<div class="tt-logo-mark">🎪</div>'
        '<div class="tt-title-block">'
        '<div class="tt-title">Ticket Tracker</div>'
        '<div class="tt-sub">Concertos &amp; Festivais em Portugal — preços actualizados em tempo real</div>'
        '<div class="tt-tags">'
        '<span class="tt-tag tt-tag-pt">'
        '<img src="https://flagcdn.com/w80/pt.png" '
        'style="height:12px;border-radius:2px;vertical-align:middle;margin-top:-2px;margin-right:4px">'
        'Portugal</span>'
        '<span class="tt-tag tt-tag-hot">🔥 Verão 2026</span>'
        f'<span class="tt-tag tt-tag-live">● {tot_all} eventos</span>'
        '</div>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── PRIMARY ACTION BUTTONS (Centered) ─────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, _ab1, _ab2, _ = st.columns([2.2, 2.5, 2.5, 2.2])
    with _ab1:
        add_lbl = "✖ Fechar Formulário" if st.session_state['show_add'] else "➕ Adicionar Evento"
        if st.button(add_lbl, key="hero_add", type="primary", use_container_width=True):
            st.session_state['show_add'] = not st.session_state['show_add']
            st.rerun()
    with _ab2:
        if st.button("🔄 Forçar Actualização", key="hero_refresh", use_container_width=True):
            get_data(force=True)
            st.toast("✅ Dados actualizados!", icon="🔄")
            st.rerun()

    # ── ADD FORM SECTION ──────────────────────────────────────────────────
    if st.session_state['show_add']:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_add_form()
        st.markdown(
            '<hr style="border:none;border-top:2px solid rgba(139,92,246,.18);margin:4px 0 26px">',
            unsafe_allow_html=True
        )

    # ── EVENTS SECTION ────────────────────────────────────────────────────
    if df_all.empty:
        st.warning("⚙️ Configura os Streamlit Secrets.")
        st.code('SPREADSHEET_ID = "o-teu-id"\nSHEET_GID = "0"', language="toml")
        st.stop()

    # Timestamp
    ts_info = (f"🔄 Actualizado às {_fetch_t}"
               + (f" · scrape {last_scrape}" if last_scrape else "")
               + f" · {len(df_all)} eventos")
    st.markdown(f'<div class="ts">{ts_info}</div>', unsafe_allow_html=True)

    # Read query params for tab + sort
    _qp_tab  = st.query_params.get("tab",  "todos")
    _qp_sort = st.query_params.get("sort", "data")

    # Apply sort/filter to full dataset
    f = df_all.copy()
    if _qp_sort == "pop":
        # Keep ONLY highlight events (with fire / relevance == 3)
        f = f[f["_rel"] == 3].reset_index(drop=True)
    else:
        f = f.sort_values("_dt", na_position="last").reset_index(drop=True)

    # Static full dataset counts to display on pills
    full_tot = len(df_all)
    full_con = len(df_all[df_all["category"].str.contains("Concerto", case=False, na=False)])
    full_fst = len(df_all[df_all["category"].str.contains("Festival", case=False, na=False)])
    full_oth = full_tot - full_con - full_fst
    full_hot = len(df_all[df_all["_rel"] == 3])

    # ── STAT PILLS ────────────────────────────────────────────────────────
    pill_data = [
        ("Total",         str(full_tot), "todos",     "data"),
        ("Concertos",     str(full_con), "concertos",  "data"),
        ("Festivais",     str(full_fst), "festivais",  "data"),
        ("Outros",        str(full_oth), "outros",     "data"),
        ("Destaque 🔥",   str(full_hot), "todos",      "pop"),
    ]
    p_cols = st.columns(5)
    for i, (label, num, tab_key, sort_key) in enumerate(pill_data):
        is_active = (_qp_tab == tab_key and (_qp_sort == sort_key if sort_key == "pop" else _qp_sort != "pop"))
        active_cls = " sp-active" if is_active else ""
        dest_url = f"?tab={tab_key}" + ("&sort=pop" if sort_key == "pop" else "")
        click_action = f"window.parent.location.search='{dest_url}';"
        p_cols[i].markdown(
            f'<div class="sp{active_cls}" onclick="{click_action}">'
            f'<div class="n">{num}</div>'
            f'<div class="l">{label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SEARCH BAR ────────────────────────────────────────────────────────
    sc1, sc2 = st.columns([6, 1])
    with sc1:
        srch = st.text_input("", "", placeholder="🔍  Pesquisar artista ou festival...",
                             label_visibility="collapsed", key="srch")
    with sc2:
        if st.button("🔄", use_container_width=True, key="srch_refresh",
                     help="Forçar actualização do Sheet"):
            get_data(force=True)
            st.rerun()

    # Apply search to the active dataset
    if srch.strip():
        f = f[f["name"].str.contains(srch.strip(), case=False, na=False)]

    # Dynamic counts for tab headers based on the current filtered dataset f
    tot = len(f)
    con = len(f[f["category"].str.contains("Concerto", case=False, na=False)])
    fst = len(f[f["category"].str.contains("Festival", case=False, na=False)])
    oth = tot - con - fst

    # ── TABS ──────────────────────────────────────────────────────────────
    _tab_map   = {"todos": 0, "concertos": 1, "festivais": 2, "outros": 3}
    _active_tab = _tab_map.get(_qp_tab, 0)

    t1, t2, t3, t4 = st.tabs([
        f"🎵 Todos ({tot})",
        f"  🎤 Concertos ({con})",
        f"  🎪 Festivais ({fst})",
        f"  🎭 Outros ({oth})"
    ])

    # Activate correct tab via robust IIFE interval script
    if _active_tab > 0:
        st.markdown(
            f'<script>'
            f'(function() {{'
            f'  var count = 0;'
            f'  var interval = setInterval(function() {{'
            f'    var tabs = window.parent.document.querySelectorAll("[data-baseweb=\'tab\']");'
            f'    if (tabs && tabs[{_active_tab}]) {{'
            f'      tabs[{_active_tab}].click();'
            f'      clearInterval(interval);'
            f'    }}'
            f'    if (++count > 50) clearInterval(interval);'
            f'  }}, 50);'
            f'}})();'
            f'</script>',
            unsafe_allow_html=True
        )

    with t1: render_grid(f, base_idx=0)
    with t2: render_grid(f[f["category"].str.contains("Concerto", case=False, na=False)], base_idx=1000)
    with t3: render_grid(f[f["category"].str.contains("Festival", case=False, na=False)], base_idx=2000)
    with t4: render_grid(f[~f["category"].str.contains("Concerto|Festival", case=False, na=False)], base_idx=3000)


if __name__ == "__main__":
    main()