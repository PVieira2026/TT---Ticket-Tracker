"""TT Tracker — Streamlit webapp for concert & festival prices."""
import os, json
from datetime import datetime
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TT Tracker",
    page_icon="🎟️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:1.5rem!important;max-width:1400px;}
.tt-hdr{background:linear-gradient(135deg,#7C3AED 0%,#4F46E5 60%,#2563EB 100%);
  border-radius:16px;padding:28px 36px;margin-bottom:24px;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 8px 32px rgba(124,58,237,.35);}
.tt-hdr h1{color:#fff;font-size:1.8rem;font-weight:800;margin:0;}
.tt-hdr p{color:rgba(255,255,255,.75);margin:4px 0 0;font-size:.9rem;}
.tt-badge{background:rgba(255,255,255,.15);border-radius:20px;
  padding:6px 14px;color:#fff;font-size:.8rem;font-weight:600;}
.stTextInput input{background:#1A1A24!important;border:1px solid #2D2D3D!important;
  border-radius:10px!important;color:#F1F1F3!important;padding:10px 16px!important;}
.stTextInput input:focus{border-color:#7C3AED!important;}
.stSelectbox>div>div{background:#1A1A24!important;border:1px solid #2D2D3D!important;
  border-radius:10px!important;color:#F1F1F3!important;}
.sp{background:#1A1A24;border:1px solid #2D2D3D;border-radius:12px;padding:16px 20px;text-align:center;}
.sp .n{font-size:1.8rem;font-weight:800;color:#7C3AED;line-height:1;}
.sp .l{font-size:.75rem;color:#888;margin-top:4px;text-transform:uppercase;letter-spacing:.8px;}
.ec{background:#1A1A24;border:1px solid #2D2D3D;border-radius:16px;overflow:hidden;
  transition:all .2s ease;display:flex;flex-direction:column;margin-bottom:4px;}
.ec:hover{border-color:#7C3AED;box-shadow:0 8px 24px rgba(124,58,237,.2);transform:translateY(-2px);}
.ec-img{width:100%;height:175px;object-fit:cover;}
.ec-noimg{width:100%;height:175px;background:linear-gradient(135deg,#1E1B3A,#2D2D3D);
  display:flex;align-items:center;justify-content:center;font-size:3rem;}
.ec-body{padding:16px;flex:1;display:flex;flex-direction:column;}
.ec-name{font-size:1rem;font-weight:700;color:#F1F1F3;margin:0 0 10px;line-height:1.3;}
.ec-meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}
.tag{font-size:.7rem;font-weight:600;padding:3px 9px;border-radius:20px;}
.t-dt{background:rgba(124,58,237,.15);color:#A78BFA;}
.t-fn{background:rgba(234,179,8,.15);color:#FCD34D;}
.t-tl{background:rgba(239,68,68,.15);color:#FCA5A5;}
.t-ei{background:rgba(16,185,129,.15);color:#6EE7B7;}
.t-co{background:rgba(59,130,246,.15);color:#93C5FD;}
.t-fe{background:rgba(249,115,22,.15);color:#FDBA74;}
.t-ev{background:rgba(139,92,246,.15);color:#C4B5FD;}
.pr{margin-top:auto;padding-top:12px;border-top:1px solid #2D2D3D;
  display:flex;align-items:center;justify-content:space-between;}
.pr-ok{font-size:1.1rem;font-weight:800;color:#34D399;}
.pr-na{font-size:.85rem;color:#555;font-style:italic;}
.ebtn{background:#7C3AED;color:#fff!important;border-radius:8px;
  padding:5px 13px;font-size:.77rem;font-weight:600;text-decoration:none!important;}
.tr{display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;border-bottom:1px solid #2D2D3D;}
.tr-s{color:#D1D5DB;font-size:.88rem;}
.tr-p{font-weight:700;color:#34D399;font-size:.95rem;}
.tr-sold{color:#EF4444;font-size:.75rem;font-weight:600;}
.tr-n{color:#888;font-size:.75rem;font-style:italic;}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:transparent;}
.stTabs [data-baseweb="tab"]{background:#1A1A24;border:1px solid #2D2D3D;
  border-radius:10px;color:#888;font-weight:600;padding:8px 20px;}
.stTabs [aria-selected="true"]{background:#7C3AED!important;
  border-color:#7C3AED!important;color:#fff!important;}
.stTabs [data-baseweb="tab-panel"]{padding-top:20px;}
.no-res{text-align:center;padding:60px 20px;color:#555;}
.ts{font-size:.75rem;color:#555;text-align:right;margin-top:-8px;margin-bottom:16px;}
</style>""", unsafe_allow_html=True)


# ── Config ────────────────────────────────────────────────────────────────────
SPREADSHEET_ID, GID = "", "0"
try:
    SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") or st.secrets.get("SPREADSHEET_ID", "")
    GID            = os.environ.get("SHEET_GID")      or st.secrets.get("SHEET_GID", "0")
except Exception:
    pass


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    if not SPREADSHEET_ID:
        return pd.DataFrame()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID}"
    try:
        df = pd.read_csv(url, dtype=str).fillna("")
        for c in ["id", "name", "date", "platform", "category", "price_min", "price_max",
                  "url", "image_url", "tickets_json", "tickets_detail", "updated_at", "scraper_status"]:
            if c not in df.columns:
                df[c] = ""
        df["_dt"] = pd.to_datetime(df["date"], errors="coerce")
        return df.sort_values("_dt", na_position="last").reset_index(drop=True)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()


# ── Helpers ───────────────────────────────────────────────────────────────────
def pp(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return 0.0


def pcls(p):
    p = p.lower()
    if "fnac"       in p: return "t-fn"
    if "ticketline" in p: return "t-tl"
    return "t-ei"


def ccls(c):
    c = (c or "").lower()
    if "festival" in c: return "t-fe"
    if "concerto" in c: return "t-co"
    return "t-ev"


def fd(d):
    try:
        dt = datetime.fromisoformat(d)
        mn = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        return f"{dt.day} {mn[dt.month - 1]} {dt.year}"
    except Exception:
        return d or "TBD"


# ── Ticket breakdown ──────────────────────────────────────────────────────────
def render_tickets(tj, td):
    rendered = False
    if tj:
        try:
            data = json.loads(tj)
            for cat in data.get("categories", []):
                for row in cat.get("rows", []):
                    sec  = row.get("sector", "Geral") or "Geral"
                    note = row.get("note", "") or ""
                    sold = row.get("sold_out", False)
                    for p in row.get("prices", [{"price": row.get("price", 0)}]):
                        pv = p.get("price", row.get("price", 0))
                        pn = note or p.get("note", "") or p.get("phase", "") or ""
                        if pn in ("Preco", "Preco", "Preco", ""): pn = ""
                        nh = f'<span class="tr-n"> ({pn})</span>' if pn else ""
                        sh = '<span class="tr-sold"> ESGOTADO</span>' if sold or p.get("sold_out") else ""
                        st.markdown(
                            f'<div class="tr"><span class="tr-s">{sec}{nh}</span>'
                            f'<span class="tr-p">{pv}€{sh}</span></div>',
                            unsafe_allow_html=True,
                        )
                        rendered = True
        except Exception:
            pass

    if not rendered and td:
        for line in td.splitlines():
            line = line.strip()
            if not line or line.startswith("Bilhete"): continue
            parts = line.split(":")
            if len(parts) >= 2:
                st.markdown(
                    f'<div class="tr"><span class="tr-s">{parts[0].strip()}</span>'
                    f'<span class="tr-p">{":".join(parts[1:]).strip()}</span></div>',
                    unsafe_allow_html=True,
                )
                rendered = True

    if not rendered:
        st.markdown(
            '<p style="color:#555;font-size:.85rem;padding:8px 0">Sem preços disponíveis.</p>',
            unsafe_allow_html=True,
        )


# ── Event card ────────────────────────────────────────────────────────────────
def card(row):
    name = row["name"]
    ds   = fd(row["date"]) if row["date"] else "Data TBD"
    plat = row["platform"]
    cat  = row.get("category", "Evento") or "Evento"
    url  = row["url"]
    img  = row["image_url"]
    mn   = pp(row["price_min"])
    mx   = pp(row["price_max"])

    ih  = f'<img class="ec-img" src="{img}">' if img else '<div class="ec-noimg">🎵</div>'
    prh = (
        f'<span class="pr-ok">{mn:.0f}€ – {mx:.0f}€</span>'
        if mn > 0 or mx > 0
        else '<span class="pr-na">Em breve</span>'
    )
    lnk = f'<a href="{url}" target="_blank" class="ebtn">Ver →</a>' if url else ""

    st.markdown(
        f'<div class="ec">{ih}'
        f'<div class="ec-body">'
        f'<div class="ec-name">{name}</div>'
        f'<div class="ec-meta">'
        f'<span class="tag t-dt">📅 {ds}</span>'
        f'<span class="tag {pcls(plat)}">{plat}</span>'
        f'<span class="tag {ccls(cat)}">{cat}</span>'
        f'</div>'
        f'<div class="pr">{prh}{lnk}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("🎫 Preços detalhados"):
        render_tickets(row["tickets_json"], row["tickets_detail"])


# ── Grid ──────────────────────────────────────────────────────────────────────
def grid(df):
    if df.empty:
        st.markdown(
            '<div class="no-res"><div style="font-size:3rem">🔍</div>'
            '<p>Nenhum evento encontrado.</p></div>',
            unsafe_allow_html=True,
        )
        return
    for i in range(0, len(df), 3):
        cols = st.columns(3, gap="medium")
        for j, col in enumerate(cols):
            if i + j < len(df):
                with col:
                    card(df.iloc[i + j])


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown(
        '<div class="tt-hdr">'
        '<div><h1>🎟️ TT Tracker</h1>'
        '<p>Concertos &amp; Festivais em Portugal — preços em tempo real</p></div>'
        '<span class="tt-badge">🇵🇹 Portugal</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("A carregar eventos..."):
        df = load_data()

    if df.empty:
        st.warning("⚙️ Configura o SPREADSHEET_ID nos secrets do Streamlit.")
        st.code('SPREADSHEET_ID = "id-da-tua-sheet"\nSHEET_GID = "0"', language="toml")
        st.stop()

    # Last update timestamp
    last = df["updated_at"].replace("", "NaT")
    last = last[last != "NaT"]
    if not last.empty:
        try:
            ts = pd.to_datetime(last.iloc[0]).strftime("%d/%m/%Y %H:%M")
            st.markdown(f'<div class="ts">🕐 Última actualização: {ts} UTC</div>', unsafe_allow_html=True)
        except Exception:
            pass

    # Filters
    c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
    with c1:
        srch = st.text_input("", "", placeholder="🔍  Pesquisar artista, festival...", label_visibility="collapsed")
    with c2:
        pls = ["Todas as plataformas"] + sorted(df["platform"].dropna().unique().tolist())
        pf  = st.selectbox("", pls, label_visibility="collapsed")
    with c3:
        pf2 = st.selectbox("",
            ["Qualquer preço", "Até 30€", "Até 60€", "Até 100€", "Até 150€", "Mais de 150€"],
            label_visibility="collapsed")
    with c4:
        if st.button("🔄", help="Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Apply filters
    f = df.copy()
    if srch.strip():
        f = f[f["name"].str.contains(srch.strip(), case=False, na=False)]
    if pf != "Todas as plataformas":
        f = f[f["platform"] == pf]
    if pf2 != "Qualquer preço":
        def ok(r):
            mn2, mx2 = pp(r["price_min"]), pp(r["price_max"])
            if mn2 == 0 and mx2 == 0: return True
            p2 = mn2 if mn2 > 0 else mx2
            if   pf2 == "Até 30€":      return p2 <= 30
            elif pf2 == "Até 60€":      return p2 <= 60
            elif pf2 == "Até 100€":     return p2 <= 100
            elif pf2 == "Até 150€":     return p2 <= 150
            elif pf2 == "Mais de 150€": return mx2 > 150
            return True
        f = f[f.apply(ok, axis=1)]

    # Stats
    tot = len(f)
    con = len(f[f["category"].str.contains("Concerto", case=False, na=False)])
    fst = len(f[f["category"].str.contains("Festival", case=False, na=False)])
    oth = tot - con - fst
    wpr = len(f[f["price_min"].str.len() > 0])

    s1, s2, s3, s4, s5 = st.columns(5)
    for col2, n, l in [
        (s1, tot, "Total"), (s2, con, "Concertos"), (s3, fst, "Festivais"),
        (s4, oth, "Outros"), (s5, wpr, "Com preços"),
    ]:
        col2.markdown(
            f'<div class="sp"><div class="n">{n}</div><div class="l">{l}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    t1, t2, t3, t4 = st.tabs([
        f"🎵 Todos ({tot})",
        f"🎤 Concertos ({con})",
        f"🎪 Festivais ({fst})",
        f"🎭 Outros ({oth})",
    ])
    with t1: grid(f)
    with t2: grid(f[f["category"].str.contains("Concerto", case=False, na=False)])
    with t3: grid(f[f["category"].str.contains("Festival", case=False, na=False)])
    with t4: grid(f[~f["category"].str.contains("Concerto|Festival", case=False, na=False)])


if __name__ == "__main__":
    main()
