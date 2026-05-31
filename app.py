"""TT Tracker — Consulta de preços de bilhetes."""
import os, json, re
from datetime import datetime
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TT Tracker",
    page_icon="\U0001f3DF\uFE0F",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
:root{--navy:#050A18;--card:#0D1526;--border:#1E2D4D;
  --accent:#1E6FFF;--green:#00C48C;--text:#E8EDF5;--muted:#6B7A99;--tag-bg:#131E35;}
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:var(--navy)!important;color:var(--text);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:1.2rem!important;max-width:1400px;}
.tt-hdr{background:linear-gradient(135deg,#0A1628 0%,#0D1E42 50%,#0A1628 100%);
  border:1px solid var(--border);border-radius:16px;padding:24px 36px;margin-bottom:20px;
  display:flex;align-items:center;justify-content:space-between;}
.tt-hdr h1{color:#fff;font-size:1.7rem;font-weight:800;margin:0;letter-spacing:-.5px;}
.tt-hdr p{color:var(--muted);margin:4px 0 0;font-size:.85rem;}
.tt-badge{background:var(--accent);border-radius:20px;padding:5px 14px;color:#fff;font-size:.78rem;font-weight:600;}
.stTextInput input{background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;padding:10px 16px!important;}
.stTextInput input:focus{border-color:var(--accent)!important;}
.stSelectbox>div>div{background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;color:var(--text)!important;}
.sp{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;text-align:center;}
.sp .n{font-size:1.6rem;font-weight:800;color:var(--accent);line-height:1;}
.sp .l{font-size:.7rem;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:1px;}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:transparent;border-bottom:1px solid var(--border)!important;padding-bottom:0;}
.stTabs [data-baseweb="tab"]{background:transparent;border:none;border-radius:8px 8px 0 0;
  color:var(--muted);font-weight:600;padding:8px 18px;font-size:.88rem;}
.stTabs [aria-selected="true"]{background:var(--card)!important;color:#fff!important;
  border-top:2px solid var(--accent)!important;}
.stTabs [data-baseweb="tab-panel"]{padding-top:18px;background:transparent;}
.ev-card{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;
  transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease;
  display:flex;flex-direction:column;height:100%;}
.ev-card:hover{transform:translateY(-3px);border-color:var(--accent);
  box-shadow:0 8px 28px rgba(30,111,255,.18);}
.ev-img{width:100%;height:200px;object-fit:cover;display:block;}
.ev-noimg{width:100%;height:200px;background:linear-gradient(135deg,#0D1E42 0%,#142040 100%);
  display:flex;align-items:center;justify-content:center;font-size:4rem;}
.ev-ribbon{background:var(--accent);color:#fff;font-size:.68rem;font-weight:700;
  letter-spacing:.8px;padding:4px 10px;text-transform:uppercase;}
.ev-ribbon.festival{background:#FF6B2B;}
.ev-ribbon.evento{background:#7C3AED;}
.ev-body{padding:16px;flex:1;display:flex;flex-direction:column;}
.ev-name{font-size:1.05rem;font-weight:700;color:#fff;margin:0 0 8px;line-height:1.3;}
.ev-meta{display:flex;gap:10px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin-bottom:12px;}
.ev-prices{background:var(--tag-bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;margin-bottom:12px;flex:1;}
.ev-prices-hdr{font-size:.68rem;font-weight:700;letter-spacing:1px;color:var(--accent);
  text-transform:uppercase;margin-bottom:8px;}
.pr-row{display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:1px solid rgba(30,45,77,.6);font-size:.83rem;}
.pr-row:last-child{border-bottom:none;}
.pr-sec{color:var(--text);font-weight:500;}
.pr-val{color:var(--green);font-weight:700;font-size:.9rem;white-space:nowrap;}
.pr-sold{color:#EF4444;font-size:.72rem;font-weight:600;margin-left:6px;}
.pr-note{color:var(--muted);font-size:.72rem;font-style:italic;margin-left:4px;}
.no-price{color:var(--muted);font-size:.82rem;font-style:italic;padding:4px 0;}
.ev-footer{display:flex;align-items:center;justify-content:flex-end;}
.src-link{color:var(--muted);font-size:.72rem;text-decoration:none!important;}
.src-link:hover{color:var(--text)!important;}
.no-res{text-align:center;padding:60px 20px;color:var(--muted);}
.ts{font-size:.73rem;color:var(--muted);text-align:right;margin-top:-8px;margin-bottom:14px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

COLS = ["id","name","date","platform","category","price_min","price_max",
        "url","image_url","tickets_json","tickets_detail","updated_at","scraper_status"]

def _s(k, d=""):
    try: return os.environ.get(k) or st.secrets.get(k, d)
    except: return d

SPREADSHEET_ID = _s("SPREADSHEET_ID")
GID            = _s("SHEET_GID", "0")
SA_JSON        = _s("GOOGLE_SERVICE_ACCOUNT_JSON")


@st.cache_data(ttl=600, show_spinner=False)
def load_data():
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
            for c in COLS:
                if c not in df.columns: df[c] = ""
            df["_dt"] = pd.to_datetime(df["date"], errors="coerce")
            return df.sort_values("_dt", na_position="last").reset_index(drop=True)
        except Exception as e:
            st.toast(f"gspread: {e}", icon="\u26a0\ufe0f")
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID}"
        df  = pd.read_csv(url, dtype=str).fillna("")
        for c in COLS:
            if c not in df.columns: df[c] = ""
        df["_dt"] = pd.to_datetime(df["date"], errors="coerce")
        return df.sort_values("_dt", na_position="last").reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()


def pp(v):
    try: return float(str(v).replace(",",".").strip())
    except: return 0.0

def fd(d):
    try:
        dt = datetime.fromisoformat(d)
        mn = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        return f"{dt.day} {mn[dt.month-1]} {dt.year}"
    except: return d or "TBD"

def ribbon_cls(cat):
    c = (cat or "").lower()
    if "festival" in c: return "festival"
    if "concerto" in c: return "concerto"
    return "evento"

def plat_short(p):
    p = p.lower()
    if "fnac" in p: return "FNAC"
    if "ticketline" in p: return "Ticketline"
    if "everything" in p: return "EIN"
    if "blueticket" in p: return "Blueticket"
    if "bol" in p: return "BOL"
    return p.split()[0].title() if p else p


def parse_ticket_rows(tj, td):
    rows = []
    if tj:
        try:
            data = json.loads(tj)
            for cat in data.get("categories", []):
                for row in cat.get("rows", []):
                    sec  = row.get("sector","") or ""
                    note = row.get("note","")   or ""
                    sold = row.get("sold_out", False)
                    ps   = row.get("prices", [{"price": row.get("price", 0)}])
                    for p in ps:
                        pv = p.get("price", row.get("price", 0))
                        pn = note or p.get("note","") or p.get("phase","") or ""
                        if pn in ("Preco","Preço",""): pn = ""
                        if pv and float(pv) > 0:
                            rows.append({
                                "sector":   sec or "Geral",
                                "price":    float(pv),
                                "note":     pn,
                                "sold_out": bool(sold or p.get("sold_out",False))
                            })
            if rows: return rows
        except Exception: pass
    if td:
        for line in td.splitlines():
            line = line.strip().lstrip()
            if not line or line.lower().startswith("bilhete"): continue
            if ":" in line:
                parts = line.split(":", 1)
                sec   = parts[0].strip()
                rest  = parts[1].strip()
                m = re.search(r"(\d+(?:[,.]\d+)?)\s*\u20ac", rest)
                if m:
                    rows.append({
                        "sector":   sec,
                        "price":    float(m.group(1).replace(",",".")),
                        "note":     "",
                        "sold_out": "esgotado" in rest.lower() or "sold" in rest.lower()
                    })
        if rows: return rows
    return []


def render_card(row):
    name = row["name"]
    ds   = fd(row["date"]) if row["date"] else "Data TBD"
    plat = row["platform"]
    cat  = row.get("category","Evento") or "Evento"
    url  = row.get("url","")
    img  = row.get("image_url","")
    tj   = row.get("tickets_json","")
    td   = row.get("tickets_detail","")

    img_html = (f'<img class="ev-img" src="{img}">' if img
                else '<div class="ev-noimg">\U0001f3b5</div>')
    ribbon   = f'<div class="ev-ribbon {ribbon_cls(cat)}">{cat}</div>'
    meta     = (f'<div class="ev-meta"><span>\U0001f4c5 {ds}</span>' +
                f'<span>\U0001f3ab {plat_short(plat)}</span></div>')

    ticket_rows = parse_ticket_rows(tj, td)
    if ticket_rows:
        lines = ""
        for r in ticket_rows[:9]:
            nt = f'<span class="pr-note">({r["note"]})</span>' if r["note"] else ""
            sl = '<span class="pr-sold">ESGOTADO</span>' if r["sold_out"] else ""
            lines += (f'<div class="pr-row">' +
                      f'<span class="pr-sec">{r["sector"]}{nt}</span>' +
                      f'<span class="pr-val">{r["price"]:.0f}\u20ac{sl}</span></div>')
        if len(ticket_rows) > 9:
            extra = len(ticket_rows) - 9
            lines += f'<div style="color:var(--muted);font-size:.72rem;padding:4px 0 0">+{extra} categorias</div>'
        prices_block = f'<div class="ev-prices"><div class="ev-prices-hdr">\U0001f3ab Bilhetes</div>{lines}</div>'
    else:
        prices_block = '<div class="ev-prices"><span class="no-price">Pre\u00e7os em breve</span></div>'

    # Subtle source link (not a buy button — just reference)
    footer_link = f'<a href="{url}" target="_blank" class="src-link">ver fonte \u2197</a>' if url else ""
    footer = f'<div class="ev-footer">{footer_link}</div>'

    card = (f'<div class="ev-card">{img_html}{ribbon}' +
            f'<div class="ev-body"><div class="ev-name">{name}</div>{meta}' +
            f'{prices_block}{footer}</div></div>')
    st.markdown(card, unsafe_allow_html=True)


def render_grid(df):
    if df.empty:
        st.markdown(
            '<div class="no-res"><div style="font-size:3rem;margin-bottom:12px">\U0001f50d</div>' +
            '<p>Nenhum evento encontrado</p></div>',
            unsafe_allow_html=True)
        return
    for i in range(0, len(df), 3):
        cols = st.columns(3, gap="medium")
        for j, col in enumerate(cols):
            if i + j < len(df):
                with col: render_card(df.iloc[i + j])
        st.markdown("<br>", unsafe_allow_html=True)


def main():
    st.markdown(
        '<div class="tt-hdr">' +
        '<div style="display:flex;align-items:center">' +
        '<span style="font-size:1.5rem;margin-right:12px">\U0001f3DF\uFE0F</span>' +
        '<div><h1>TT Tracker</h1>' +
        '<p>Concertos &amp; Festivais em Portugal \u2014 pre\u00e7os em tempo real</p></div></div>' +
        '<span class="tt-badge">\U0001f1f5\U0001f1f9 Portugal</span></div>',
        unsafe_allow_html=True)

    with st.spinner("A carregar eventos..."): df = load_data()

    if df.empty:
        st.warning("\u2699\uFE0F A Google Sheet n\u00e3o est\u00e1 acess\u00edvel.")
        with st.expander("Como resolver"):
            st.markdown("""
**Opn A (simples) \u2014 tornar a Sheet p\u00fablica:**
1. Google Sheet \u2192 Partilhar \u2192 Qualquer pessoa com o link \u2192 Leitor
2. Streamlit Secrets:
```toml
SPREADSHEET_ID = "o-teu-id"
SHEET_GID      = "0"
```

**Op\u00e7\u00e3o B \u2014 Sheet privada (Service Account):**
```toml
SPREADSHEET_ID              = "o-teu-id"
SHEET_GID                   = "0"
GOOGLE_SERVICE_ACCOUNT_JSON = '''{"type":"service_account",...}'''
```
""")
        st.stop()

    last = df["updated_at"].replace("","NaT"); last = last[last!="NaT"]
    if not last.empty:
        try:
            ts = pd.to_datetime(last.iloc[0]).strftime("%d/%m/%Y %H:%M")
            st.markdown(f'<div class="ts">\U0001f550 Actualizado: {ts} UTC \u00b7 {len(df)} eventos</div>',
                        unsafe_allow_html=True)
        except: pass

    c1,c2,c3,c4 = st.columns([3,1.5,1.5,0.8])
    with c1: srch = st.text_input("","",placeholder="\U0001f50d  Pesquisar artista ou festival...",label_visibility="collapsed")
    with c2:
        pls = ["Todas as plataformas"]+sorted(df["platform"].dropna().unique().tolist())
        pf  = st.selectbox("",pls,label_visibility="collapsed")
    with c3:
        pf2 = st.selectbox("",["Qualquer pre\u00e7o","At\u00e9 30\u20ac","At\u00e9 60\u20ac","At\u00e9 100\u20ac","At\u00e9 150\u20ac","Mais de 150\u20ac"],label_visibility="collapsed")
    with c4:
        if st.button("\U0001f504",use_container_width=True,help="Actualizar"): st.cache_data.clear(); st.rerun()

    f = df.copy()
    if srch.strip(): f = f[f["name"].str.contains(srch.strip(),case=False,na=False)]
    if pf != "Todas as plataformas": f = f[f["platform"]==pf]
    if pf2 != "Qualquer pre\u00e7o":
        def ok(r):
            mn2,mx2 = pp(r["price_min"]),pp(r["price_max"])
            if mn2==0 and mx2==0: return True
            p2 = mn2 if mn2>0 else mx2
            if   pf2=="At\u00e9 30\u20ac":      return p2<=30
            elif pf2=="At\u00e9 60\u20ac":      return p2<=60
            elif pf2=="At\u00e9 100\u20ac":     return p2<=100
            elif pf2=="At\u00e9 150\u20ac":     return p2<=150
            elif pf2=="Mais de 150\u20ac": return mx2>150
            return True
        f = f[f.apply(ok,axis=1)]

    tot=len(f); con=len(f[f["category"].str.contains("Concerto",case=False,na=False)])
    fst=len(f[f["category"].str.contains("Festival",case=False,na=False)]); oth=tot-con-fst
    wpr=len(f[f["price_min"].str.len()>0])
    s1,s2,s3,s4,s5=st.columns(5)
    for col2,n,l in[(s1,tot,"Total"),(s2,con,"Concertos"),(s3,fst,"Festivais"),(s4,oth,"Outros"),(s5,wpr,"Com pre\u00e7os")]:
        col2.markdown(f'<div class="sp"><div class="n">{n}</div><div class="l">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    t1,t2,t3,t4=st.tabs([f"\U0001f3b5 Todos ({tot})",f"\U0001f3a4 Concertos ({con})",
                         f"\U0001f3aa Festivais ({fst})",f"\U0001f3ad Outros ({oth})"])
    with t1: render_grid(f)
    with t2: render_grid(f[f["category"].str.contains("Concerto",case=False,na=False)])
    with t3: render_grid(f[f["category"].str.contains("Festival",case=False,na=False)])
    with t4: render_grid(f[~f["category"].str.contains("Concerto|Festival",case=False,na=False)])

if __name__=="__main__": main()
