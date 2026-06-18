"""TT Tracker v3 — Merged & Upgraded."""
import os, json, re
from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd

def set_state_value(key, val):
    st.session_state[key] = val

def pop_state_value(key):
    st.session_state.pop(key, None)

def trigger_update_click(confirm_key, updating_key):
    st.session_state.pop(confirm_key, None)
    st.session_state[updating_key] = True

# Inject Streamlit secrets into environment variables so sub-modules can access them
for k in ["SPREADSHEET_ID", "SHEET_GID", "GOOGLE_SERVICE_ACCOUNT_JSON", "SERPER_API_KEY", "SERPER_API_KEY_2", "N8N_WEBHOOK_URL"]:
    try:
        val = st.secrets.get(k) or st.secrets.get(k.lower())
        if val and not os.environ.get(k):
            os.environ[k] = str(val)
    except Exception:
        pass

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
    "[data-testid='stAppViewContainer'],[data-testid='stHeader'],[data-testid='stSidebar'],[data-testid='stSidebarUserContent']{background-color:var(--bg)!important;background:var(--bg)!important;}"
    "div[data-testid='stWidgetLabel'] p,div[data-testid='stMarkdownContainer'] > p,div[data-testid='stMarkdownContainer'] > ul > li,div[data-testid='stMarkdownContainer'] > h1,div[data-testid='stMarkdownContainer'] > h2,div[data-testid='stMarkdownContainer'] > h3,div[data-testid='stMarkdownContainer'] > h4,.stMarkdown > p,.stMarkdown > span,.stMarkdown > li{color:var(--text)!important;}"
    "#MainMenu,footer,header{visibility:hidden;}"
    ".block-container{padding-top:0!important;max-width:1440px;}"
    "/* ── Hero ── */"
    ".tt-hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#1A0533 0%,#2D0B5A 30%,#4A1070 55%,#2D0B5A 80%,#1A0533 100%);border-radius:20px;margin-bottom:16px;padding:0;border:1px solid rgba(139,92,246,.3);box-shadow:0 20px 60px rgba(139,92,246,.2),0 0 0 1px rgba(255,92,53,.15);}"
    ".tt-hero-glow{position:absolute;top:-40%;left:-10%;width:50%;height:200%;background:radial-gradient(ellipse,rgba(255,92,53,.18) 0%,transparent 65%);pointer-events:none;}"
    ".tt-hero-glow2{position:absolute;top:-20%;right:-5%;width:40%;height:180%;background:radial-gradient(ellipse,rgba(139,92,246,.2) 0%,transparent 65%);pointer-events:none;}"
    ".tt-hero-inner{position:relative;z-index:1;padding:36px 40px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:12px;}"
    ".tt-logo-mark{width:56px;height:56px;border-radius:14px;flex-shrink:0;background:linear-gradient(135deg,#FF5C35,#FF9A3C);display:flex;align-items:center;justify-content:center;font-size:1.7rem;box-shadow:0 8px 24px rgba(255,92,53,.4);margin:0;}"
    ".tt-title-block{min-width:0;}"
    ".tt-title{font-family:'Outfit',sans-serif;font-weight:900;font-size:2.6rem;line-height:1.1;background:linear-gradient(90deg,#FF9A3C 0%,#FF5C35 40%,#C084FC 80%,#818CF8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin:0 0 5px;letter-spacing:-1px;}"
    ".tt-sub{font-size:.87rem;color:rgba(240,235,248,.55);font-weight:400;margin:0;letter-spacing:.3px;}"
    ".tt-tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:6px;}"
    ".tt-tag{font-size:.68rem;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;padding:3px 10px;border-radius:20px;border:1px solid;}"
    ".tt-tag-hot{background:rgba(255,92,53,.15);color:#FF7A5C;border-color:rgba(255,92,53,.35);}"
    ".tt-tag-live{background:rgba(0,214,143,.12);color:#00D68F;border-color:rgba(0,214,143,.3);animation:pulse-dot 2s infinite;}"
    ".tt-tag-pt{background:rgba(139,92,246,.15);color:#A78BFA;border-color:rgba(139,92,246,.35);}"
    "@keyframes pulse-dot{0%,100%{box-shadow:0 0 0 0 rgba(0,214,143,.3);}50%{box-shadow:0 0 0 6px rgba(0,214,143,0);}}"
    "/* ── Action buttons ── */"
    ".action-bar{display:flex;gap:10px;align-items:center;margin-bottom:18px;}"
    "button[data-testid='baseButton-primary']{background:linear-gradient(135deg,#FF5C35,#FF9A3C)!important;border:none!important;border-radius:10px!important;color:#fff!important;font-weight:700!important;box-shadow:0 4px 15px rgba(255,92,53,.35)!important;transition:all .2s!important;}"
    "button[data-testid='baseButton-primary']:hover{transform:translateY(-2px)!important;box-shadow:0 8px 25px rgba(255,92,53,.5)!important;}"
    "button[data-testid='baseButton-secondary']{background:rgba(139,92,246,.1)!important;border:1px solid rgba(139,92,246,.35)!important;border-radius:10px!important;color:var(--text)!important;font-weight:600!important;transition:all .2s!important;}"
    "button[data-testid='baseButton-secondary']:hover{background:rgba(139,92,246,.25)!important;border-color:rgba(139,92,246,.6)!important;transform:translateY(-1px)!important;}"
    "/* ── Inputs ── */"
    ".stTextInput input{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:10px!important;color:var(--text)!important;padding:10px 16px!important;}"
    ".stTextInput input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(255,92,53,.15)!important;}"
    ".stSelectbox>div>div{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:10px!important;color:var(--text)!important;}"
    ".stTextArea textarea{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:10px!important;color:var(--text)!important;}"
    "/* ── Tabs ── */"
    ".stTabs [data-baseweb='tab-list']{gap:8px;background:transparent;border-bottom:1px solid var(--border)!important;}"
    ".stTabs [data-baseweb='tab']{background:transparent;border:none;border-radius:8px 8px 0 0;color:var(--muted);font-weight:700;padding:14px 28px;font-size:1.05rem;transition:color .15s;}"
    ".stTabs [data-baseweb='tab']:hover{color:var(--text)!important;}"
    ".stTabs [aria-selected='true']{background:var(--card)!important;color:#fff!important;border-top:2px solid var(--accent)!important;}"
    ".stTabs [data-baseweb='tab-panel']{padding-top:18px;background:transparent;}"
    "/* ── Event cards ── */"
    ".ev-concerto{--c-accent:#1E6FFF;--c-accent-rgb:30,111,255;}"
    ".ev-festival{--c-accent:#FF6B2B;--c-accent-rgb:255,107,43;}"
    ".ev-evento{--c-accent:#8B5CF6;--c-accent-rgb:139,92,246;}"
    ".ev-card{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;display:flex;flex-direction:column;height:100%;position:relative;}"
    ".ev-card:hover{transform:translateY(-4px);border-color:var(--c-accent)!important;box-shadow:0 12px 40px rgba(var(--c-accent-rgb),.25),0 2px 8px rgba(0,0,0,.4);}"
    ".ev-img-wrap{position:relative;overflow:hidden;flex-shrink:0;}"
    ".ev-img{width:100%;height:200px;object-fit:cover;display:block;transition:filter .3s,opacity .3s;}"
    ".ev-noimg{width:100%;height:200px;display:flex;align-items:center;justify-content:center;font-size:3.5rem;background:linear-gradient(135deg,#1A0D35 0%,#2D1060 50%,#1A0D35 100%);}"
    ".ev-img-link{display:block;}"
    ".ev-img-link:hover .ev-img,.ev-img-link:hover .ev-noimg{opacity:.85;}"
    "/* ── Past event styles ── */"
    ".past-card{border-color:var(--past-border)!important;}"
    ".past-card:hover{transform:none!important;border-color:var(--past-border)!important;box-shadow:none!important;}"
    ".past-card .ev-img{filter:grayscale(55%) brightness(0.6);}"
    ".past-stamp{position:absolute;top:26px;left:-36px;width:180px;text-align:center;transform:rotate(-35deg);background:rgba(185,15,15,.93);color:#fff;font-family:'Outfit',sans-serif;font-weight:900;font-size:.7rem;letter-spacing:2.5px;padding:7px 0;text-transform:uppercase;z-index:5;box-shadow:0 3px 16px rgba(0,0,0,.6);border-top:1px solid rgba(255,120,120,.25);border-bottom:1px solid rgba(255,120,120,.25);white-space:nowrap;}"
    "/* ── Card inner ── */"
    ".ev-ribbon{color:#fff;font-size:.68rem;font-weight:700;letter-spacing:.8px;padding:5px 12px;text-transform:uppercase;}"
    ".r-concerto{background:#1E6FFF;}"
    ".r-festival{background:#FF6B2B;}"
    ".r-evento{background:#8B5CF6;}"
    ".hot-badge{background:rgba(0,0,0,0.35);color:#FFFFFF;font-size:.62rem;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:8px;letter-spacing:.5px;border:1px solid rgba(255,255,255,0.3);}"
    ".manual-badge{background:rgba(0,214,143,.1);color:#00D68F;font-size:.6rem;font-weight:700;padding:1px 7px;border-radius:10px;margin-left:5px;border:1px solid rgba(0,214,143,.3);}"
    ".ev-body{padding:16px;flex:1;display:flex;flex-direction:column;}"
    ".ev-name{font-size:1.05rem;font-weight:700;color:#fff;margin:0 0 5px;line-height:1.3;}"
    ".ev-title-link{color:#fff!important;text-decoration:none!important;display:block;margin-bottom:5px;}"
    ".ev-title-link:hover{color:var(--accent)!important;}"
    ".ev-date-row{font-size:.82rem;font-weight:600;color:var(--accent2);margin-bottom:6px;display:flex;align-items:center;gap:5px;}"
    ".ev-date-row.past-date{color:var(--muted);font-weight:500;}"
    ".ev-meta{display:flex;gap:8px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin-bottom:12px;}"
    ".ev-meta .soon{color:#00D68F;font-weight:600;}"
    ".ev-meta .past-txt{color:#5A4D6E;}"
    "/* ── Prices ── */"
    ".ev-prices{background:var(--tag-bg);border:1px solid rgba(42,31,69,.8);border-radius:10px;padding:10px 12px;margin-bottom:12px;flex:1;}"
    ".ev-prices-hdr{font-size:.67rem;font-weight:700;letter-spacing:1px;color:var(--accent);text-transform:uppercase;margin-bottom:8px;}"
    ".pr-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(42,31,69,.8);font-size:.82rem;}"
    ".pr-row:last-child{border-bottom:none;}"
    ".pr-sec{color:var(--text);font-weight:500;}"
    ".pr-val{color:var(--green);font-weight:700;font-size:.9rem;white-space:nowrap;}"
    ".pr-sold{color:#EF4444;font-size:.72rem;font-weight:600;margin-left:4px;}"
    ".pr-note{color:var(--muted);font-size:.72rem;font-style:italic;margin-left:4px;}"
    ".no-price{color:var(--muted);font-size:.82rem;font-style:italic;padding:4px 0;}"
    ".ver-mais-btn{background:none;border:none;color:var(--muted);font-size:.72rem;padding:5px 0 0;cursor:pointer;text-align:left;width:100%;transition:color .15s;}"
    ".ver-mais-btn:hover{color:var(--accent);}"
    "/* ── Card footer ── */"
    ".ev-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:8px;}"
    ".src-link{color:var(--muted);font-size:.72rem;text-decoration:none!important;transition:color .15s;}"
    ".src-link:hover{color:var(--accent)!important;}"
    "/* ── Add form section ── */"
    ".add-section{background:linear-gradient(135deg,#130826 0%,#1E0D40 100%);border:1px solid rgba(139,92,246,.35);border-radius:16px;padding:28px 32px;margin-bottom:24px;box-shadow:0 8px 32px rgba(139,92,246,.12);}"
    ".add-section-title{font-family:'Outfit',sans-serif;font-weight:800;font-size:1.4rem;background:linear-gradient(90deg,#C084FC,#818CF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin:0 0 4px;}"
    ".add-section-sub{color:var(--muted);font-size:.85rem;margin:0 0 22px;}"
    ".add-divider{border:none;border-top:1px solid rgba(139,92,246,.2);margin:20px 0;}"
    ".add-field-label{font-size:.82rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin:16px 0 6px;}"
    "/* ── CSS Checkbox Hack for Prices Toggle ── */"
    ".toggle-trigger{display:none!important;}"
    ".extra-prices{display:none;}"
    ".btn-hide{display:none;}"
    ".toggle-trigger:checked ~ .extra-prices{display:block!important;}"
    ".toggle-trigger:checked ~ .btn-show{display:none!important;}"
    ".toggle-trigger:checked ~ .btn-hide{display:block!important;}"
    "/* ── Misc ── */"
    ".no-res{text-align:center;padding:60px 20px;color:var(--muted);}"
    ".ts{font-size:.72rem;color:var(--muted);text-align:right;margin-top:4px;margin-bottom:14px;}"
    ".stButton>button{transition:all .2s!important;}"
    "/* ── Clippy Retro Assistant ── */"
    ".clippy-wrapper{position:absolute;right:-280px;top:20px;width:240px;display:flex;flex-direction:column;align-items:center;z-index:999;font-family:'Tahoma','MS Sans Serif',sans-serif!important;}"
    "@media(max-width:1280px){.clippy-wrapper{position:relative;right:0;top:0;width:100%;margin-bottom:20px;flex-direction:row;justify-content:center;gap:15px;}}"
    ".clippy-bubble{background:#FFFFE1!important;color:#000000!important;border:1px solid #000000!important;border-radius:8px;padding:12px;position:relative;box-shadow:3px 3px 0px rgba(0,0,0,0.2);margin-bottom:12px;font-size:12px!important;line-height:1.4!important;text-align:left;}"
    ".clippy-bubble::after{content:'';position:absolute;bottom:-10px;left:30px;border-width:10px 10px 0;border-style:solid;border-color:#FFFFE1 transparent;display:block;width:0;}"
    ".clippy-bubble::before{content:'';position:absolute;bottom:-11px;left:30px;border-width:10px 10px 0;border-style:solid;border-color:#000000 transparent;display:block;width:0;z-index:-1;}"
    "@media(max-width:1280px){.clippy-bubble{margin-bottom:0;}.clippy-bubble::after{bottom:15px;left:-10px;border-width:10px 10px 10px 0;border-color:transparent #FFFFE1;}.clippy-bubble::before{bottom:15px;left:-11px;border-width:10px 10px 10px 0;border-color:transparent #000000;}}"
    ".clippy-title{font-weight:bold;margin-bottom:6px;display:flex;align-items:center;gap:5px;border-bottom:1px solid rgba(0,0,0,0.1);padding-bottom:4px;color:#000!important;}"
    ".clippy-text{margin-bottom:8px;color:#333!important;}"
    ".clippy-input-group{display:flex;gap:6px;}"
    ".clippy-search-input{flex:1;background:#FFF!important;color:#000!important;border:1px solid #7F9DB9!important;padding:4px 6px!important;font-size:11px!important;height:24px!important;border-radius:2px!important;}"
    ".clippy-search-btn{background:#F0F0F0!important;color:#000!important;border:1px solid #707070!important;border-radius:3px!important;padding:2px 10px!important;font-size:11px!important;cursor:pointer!important;font-weight:600!important;height:24px!important;display:flex;align-items:center;justify-content:center;box-shadow:inset 0 1px 0 #fff,0 1px 2px rgba(0,0,0,0.1);}"
    ".clippy-search-btn:hover{background:#E5E5E5!important;border-color:#3C3C3C!important;}"
    ".clippy-avatar-box{animation:clippy-float 3s ease-in-out infinite;cursor:pointer;width:65px;height:65px;display:flex;align-items:center;justify-content:center;}"
    "@keyframes clippy-float{0%,100%{transform:translateY(0);}50%{transform:translateY(-5px);}}"
    "/* ── Hourglass Rotation ── */"
    "@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}"
    ".rotating-hourglass{display:inline-block;animation:spin 2s linear infinite;font-size:1.2rem;margin-right:8px;vertical-align:middle;}"
    ".loader-text{font-size:1rem;vertical-align:middle;}"
    ".card-container-wrap{position:relative;height:100%;}"
    ".card-container-wrap div.stButton{position:absolute;bottom:24px;right:16px;z-index:99;}"
    ".card-container-wrap div.stButton button{background:transparent!important;border:none!important;color:var(--muted)!important;font-size:.72rem!important;font-weight:500!important;padding:0!important;margin:0!important;height:auto!important;min-height:auto!important;line-height:normal!important;box-shadow:none!important;transition:color .15s!important;cursor:pointer!important;}"
    ".card-container-wrap div.stButton button:hover{color:var(--accent)!important;background:transparent!important;transform:none!important;box-shadow:none!important;}"
    "/* ── Glow Card Styles ── */"
    ".ev-card[data-glow]{"
    "  --radius:14;"
    "  --border:3;"
    "  --backdrop:rgba(240,235,248,0.03);"
    "  --backup-border:var(--backdrop);"
    "  --size:200;"
    "  --outer:1;"
    "  --border-size:calc(var(--border,2)*1px);"
    "  --spotlight-size:calc(var(--size,150)*1px);"
    "  --hue:calc(var(--base)+(var(--xp,0)*var(--spread,0)));"
    "  position:relative;"
    "  touch-action:none;"
    "  background-color:var(--backdrop,transparent);"
    "  background-image:radial-gradient("
    "    var(--spotlight-size) var(--spotlight-size) at"
    "    calc(var(--x,0)*1px)"
    "    calc(var(--y,0)*1px),"
    "    hsl(var(--hue,210) calc(var(--saturation,100)*1%) calc(var(--lightness,70)*1%)/var(--bg-spot-opacity,0.15)),transparent"
    "  );"
    "  background-size:calc(100%+(2*var(--border-size))) calc(100%+(2*var(--border-size)));"
    "  background-position:50% 50%;"
    "  background-attachment:fixed;"
    "  border:var(--border-size) solid var(--backup-border);"
    "  border-radius:16px;"
    "  backdrop-filter:blur(5px);"
    "  --base:220;"
    "  --spread:200;"
    "  --saturation:100;"
    "  --lightness:70;"
    "  --bg-spot-opacity:0.12;"
    "  --border-spot-opacity:1;"
    "  --border-light-opacity:1;"
    "}"
    ".ev-card.ev-concerto[data-glow]{--base:220;--spread:200;}"
    ".ev-card.ev-festival[data-glow]{--base:30;--spread:200;}"
    ".ev-card.ev-evento[data-glow]{--base:280;--spread:300;}"
    "[data-glow]::before,"
    "[data-glow]::after{"
    "  pointer-events:none;"
    "  content:'';"
    "  position:absolute;"
    "  inset:calc(var(--border-size)*-1);"
    "  border:var(--border-size) solid transparent;"
    "  border-radius:calc(var(--radius)*1px);"
    "  background-attachment:fixed;"
    "  background-size:calc(100%+(2*var(--border-size))) calc(100%+(2*var(--border-size)));"
    "  background-repeat:no-repeat;"
    "  background-position:50% 50%;"
    "  mask:linear-gradient(transparent,transparent),linear-gradient(white,white);"
    "  mask-clip:padding-box,border-box;"
    "  mask-composite:intersect;"
    "  -webkit-mask:linear-gradient(transparent,transparent),linear-gradient(white,white);"
    "  -webkit-mask-clip:padding-box,border-box;"
    "  -webkit-mask-composite:source-in,xor;"
    "}"
    "[data-glow]::before{"
    "  background-image:radial-gradient("
    "    calc(var(--spotlight-size)*0.75) calc(var(--spotlight-size)*0.75) at"
    "    calc(var(--x,0)*1px)"
    "    calc(var(--y,0)*1px),"
    "    hsl(var(--hue,210) calc(var(--saturation,100)*1%) calc(var(--lightness,50)*1%)/var(--border-spot-opacity,1)),transparent 100%"
    "  );"
    "  filter:brightness(1.8);"
    "}"
    "[data-glow]::after{"
    "  background-image:radial-gradient("
    "    calc(var(--spotlight-size)*0.5) calc(var(--spotlight-size)*0.5) at"
    "    calc(var(--x,0)*1px)"
    "    calc(var(--y,0)*1px),"
    "    hsl(0 100% 100%/var(--border-light-opacity,0.8)),transparent 100%"
    "  );"
    "}"
    "[data-glow] [data-glow]{"
    "  position:absolute;"
    "  inset:0;"
    "  will-change:filter;"
    "  opacity:var(--outer,1);"
    "  border-radius:calc(var(--radius)*1px);"
    "  border-width:calc(var(--border-size)*20);"
    "  filter:blur(calc(var(--border-size)*10));"
    "  background:none;"
    "  pointer-events:none;"
    "  border:none;"
    "}"
    "[data-glow]>[data-glow]::before{"
    "  inset:-10px;"
    "  border-width:10px;"
    "}"
    "</style>"
    "<img src=\"x\" onerror=\""
    "if(!window.glowInitialized){"
    "  window.glowInitialized=true;"
    "  document.addEventListener('pointermove',(e)=>{"
    "    const x=e.clientX;const y=e.clientY;"
    "    document.querySelectorAll('.ev-card').forEach(card=>{"
    "      card.style.setProperty('--x',x.toFixed(2));"
    "      card.style.setProperty('--xp',(x/window.innerWidth).toFixed(2));"
    "      card.style.setProperty('--y',y.toFixed(2));"
    "      card.style.setProperty('--yp',(y/window.innerHeight).toFixed(2));"
    "    });"
    "  });"
    "}"
    "\" style=\"display:none;\">"
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
COLS = ["id","name","date","platform","category","price_min","price_max",
        "url","image_url","tickets_json","tickets_detail","updated_at","scraper_status","highlight"]
HIGH_REL = [
    "coldplay","radiohead","ed sheeran","billie eilish","taylor swift","the weeknd",
    "beyonce","rihanna","adele","harry styles","depeche mode","the national","arcade fire",
    "arctic monkeys","metallica","iron maiden","foo fighters","red hot chili peppers",
    "guns n roses","blur","oasis","placebo","laura pausini","anitta","anastacia",
    "brandi carlile","dua lipa","imagine dragons","maroon 5","lana del rey","the cure",
    "massive attack","nos alive","super bock","mares vivas","neopop","paredes de coura",
    "primavera sound","rock in rio","evillive","meo mares","sudowoodo"
]

def relevance(row):
    highlight_val = str(row.get("highlight", "")).strip().lower()
    if highlight_val in ["true", "1", "x", "yes", "sim", "destaque"]:
        return 3
    if highlight_val in ["false", "no", "não", "0"]:
        name = str(row.get("name", ""))
        url = str(row.get("url", ""))
        t = (name + " " + url).lower()
        if any(k in t for k in ["festival","altice","coliseu","pavilh","campo pequeno","arena"]): return 2
        return 1
    name = str(row.get("name", ""))
    url = str(row.get("url", ""))
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
            df["_rel"] = df.apply(relevance, axis=1)
            df = _dedup_display(df)
            return df.sort_values(["_dt","_row_idx"], na_position="last").reset_index(drop=True)
        except Exception as e:
            print(f"load_data: gspread failed, falling back to CSV. Error: {e}")
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
        df["_rel"] = df.apply(relevance, axis=1)
        df = _dedup_display(df)
        return df.sort_values(["_dt","_row_idx"], na_position="last").reset_index(drop=True)
    except Exception as e:
        print(f"load_data: fallback CSV failed. Error: {e}")
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

def _parse_n8n_response(parsed):
    """Robust parser to clean and extract keys from n8n response in case of stringified JSON in 'answer'."""
    if not parsed:
        return {}
    if 'answer' in parsed and isinstance(parsed['answer'], str):
        try:
            import json
            clean_text = parsed['answer'].replace("```json", "").replace("```", "").strip()
            nested = json.loads(clean_text)
            if isinstance(nested, dict):
                return nested
        except Exception:
            pass
    if 'answer' in parsed and isinstance(parsed['answer'], dict):
        return parsed['answer']
    return parsed

def _ask_n8n_ai(query, existing_data=None, progress_slot=None):
    """
    Sends a query to n8n webhook and returns parsed JSON.
    
    Performs Google search and image retrieval locally in Python first to build 
    a search context. This context is sent to n8n, allowing Toqan to extract 
    the details in a single-shot step without calling tools, completing in <10 seconds.
    """
    import requests as _req
    import time, os, threading
    try:
        webhook_url = os.environ.get('N8N_WEBHOOK_URL') or st.secrets.get('N8N_WEBHOOK_URL', '')
    except Exception:
        webhook_url = os.environ.get('N8N_WEBHOOK_URL', '')

    if not webhook_url:
        st.error("URL do Webhook n8n não configurado no .streamlit/secrets.toml (chave N8N_WEBHOOK_URL)!")
        return None
        
    result = {}
    
    def request_worker():
        import socket
        import urllib.parse
        
        # Parse host to force IPv4 resolution, bypassing Windows IPv6 lookup timeout delays
        try:
            parsed_url = urllib.parse.urlparse(webhook_url)
            hostname = parsed_url.hostname
        except Exception:
            hostname = None

        original_getaddrinfo = socket.getaddrinfo
        patched = False

        if hostname:
            def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
                if host == hostname:
                    return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
                return original_getaddrinfo(host, port, family, type, proto, flags)
            
            socket.getaddrinfo = ipv4_getaddrinfo
            patched = True

        try:
            # 1. Fetch search context locally to save Toqan 60+ seconds of searching
            from scraper.sources.web_search_fallback import (
                _clean_query, _search_serper, _search_duckduckgo, 
                _search_google_direct, _active_serper_key, search_image,
                scrape_urls_for_context
            )
            
            search_q = _clean_query(query)
            snippets = []
            
            if _active_serper_key():
                snippets = _search_serper(search_q)
            if not snippets:
                snippets = _search_duckduckgo(search_q)
            if not snippets:
                snippets = _search_google_direct(search_q)
                
            context = ""
            official_img = ""
            
            # Prioritize existing_data URL if present
            if existing_data and existing_data.get('url'):
                try:
                    ext_text, off_img = scrape_urls_for_context([{'link': existing_data['url']}])
                    if ext_text:
                        context += f"\n--- OFFICIAL PAGE ({existing_data['url']}) ---\n{ext_text}\n"
                    if off_img:
                        official_img = off_img
                except Exception:
                    pass

            for i, s in enumerate(snippets[:6]):
                title = s.get('title', '')
                link = s.get('link', '')
                snippet = s.get('snippet', '')
                context += f"Result {i+1}:\nTitle: {title}\nLink: {link}\nSnippet: {snippet}\n\n"
                
            # Scrape full text and official image from the best URLs found
            if snippets:
                text_content, o_img = scrape_urls_for_context(snippets)
                context += "\n" + text_content
                if o_img and not official_img:
                    official_img = o_img
                
            # Fetch image URL (prefer official over Bing)
            img_url = official_img
            if not img_url:
                try:
                    img_url = search_image(query)
                except Exception:
                    pass
            
            # 2. Call n8n webhook passing the massive context to bypass Toqan 60s timeout
            payload = {
                'query': query,
                'search_context': context,
                'pre_fetched_image': img_url,
                'spreadsheet_id': SPREADSHEET_ID
            }
            if existing_data:
                payload['existing_data'] = existing_data
            
            resp = _req.post(
                webhook_url,
                json=payload,
                timeout=(10, 90),  # Increased timeout since Claude + Web Search takes ~50s
                proxies={"http": None, "https": None}  # Skip system proxy autodiscovery delays
            )
            result['status_code'] = resp.status_code
            result['text'] = resp.text
            try:
                result['json'] = resp.json()
            except Exception:
                result['json'] = None
        except _req.exceptions.Timeout:
            result['error'] = 'timeout'
        except Exception as e:
            result['error'] = str(e)
            try:
                with open(r"c:\Users\Pedro\Downloads\Ticket Tracker\debug_search.txt", "w", encoding="utf-8") as f_dbg:
                    f_dbg.write(f"Exception occurred: {str(e)}\n")
            except Exception:
                pass
        finally:
            if patched:
                socket.getaddrinfo = original_getaddrinfo

    # Start network call in a background thread so Streamlit thread is not blocked
    thread = threading.Thread(target=request_worker)
    thread.start()

    if progress_slot is None:
        progress_slot = st.empty()
    start = time.time()

    # Poll the thread status and update the UI elapsed timer every second
    while thread.is_alive():
        elapsed = int(time.time() - start)
        progress_slot.markdown(
            f'<div style="text-align: center; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 8px;">'
            f'<span class="rotating-hourglass" style="margin: 0;">⏳</span>'
            f'<span class="loader-text">A consultar a Inteligência Artificial... ({elapsed}s)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        time.sleep(1)

    thread.join()

    elapsed = int(time.time() - start)

    # Check for timeout or gateway timeout (504, 502, etc.)
    is_timeout = False
    status_code = result.get('status_code')
    text = result.get('text', '')

    if 'error' in result and result['error'] == 'timeout':
        is_timeout = True
    elif status_code in (504, 502, 503):
        is_timeout = True
    elif text and any(x in text for x in ["504 Gateway Time-out", "504 Gateway Timeout", "502 Bad Gateway", "503 Service Temporarily Unavailable"]):
        is_timeout = True

    if is_timeout:
        progress_slot.empty()
        st.warning("⏱️ A consulta está a demorar mais tempo do que o previsto. No entanto, o processo continuará a correr em segundo plano e a informação será actualizada automaticamente no Google Sheets em breve. Não é necessário tentar novamente!")
        return None

    if 'error' in result:
        progress_slot.empty()
        st.error(f"Erro ao ligar ao n8n: {result['error']}")
        return None

    if status_code == 200:
        progress_slot.markdown(
            f'<div style="text-align: center; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 8px;">'
            f'<span style="font-size: 1.2rem; margin: 0; vertical-align: middle;">✅</span>'
            f'<span class="loader-text">Pedido enviado para a Inteligência Artificial. Info e preços serão actualizados em breve</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        return _parse_n8n_response(result.get('json'))
    else:
        progress_slot.empty()
        st.error(f"Erro do n8n: {status_code} - {text[:300]}")
        return None



# ── Sheet operations ──────────────────────────────────────────────────────────

def _update_event_in_sheet(ev_id, updated_data, existing_data):
    """Update event row in Google Sheets with merged n8n and existing data."""
    if not SA_JSON or len(SA_JSON) < 50:
        st.error("GOOGLE_SERVICE_ACCOUNT_JSON não configurado.")
        return False
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive.readonly"]
        creds = Credentials.from_service_account_info(json.loads(SA_JSON), scopes=SCOPES)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Eventos")
        
        existing = ws.get_all_records()
        row_num = None
        for i, r in enumerate(existing):
            if str(r.get('id','')) == str(ev_id):
                row_num = i + 2  # +1 header, +1 0-indexed
                break
        
        if not row_num:
            # Fallback to name match if id mismatch
            nm_to_match = existing_data.get('name', '')
            for i, r in enumerate(existing):
                if str(r.get('name','')).strip().lower() == nm_to_match.strip().lower():
                    row_num = i + 2
                    break
                    
        if not row_num:
            st.error(f"Evento '{existing_data.get('name')}' não encontrado no Sheet.")
            return False

        existing_highlight = str(existing[row_num - 2].get("highlight", ""))

        # Merge values with fallbacks
        nm = updated_data.get('name') or existing_data.get('name') or ''
        plat = updated_data.get('platform') or existing_data.get('platform') or ''
        cat = updated_data.get('category') or existing_data.get('category') or ''
        
        # date parsing
        ds = updated_data.get('date_start') or updated_data.get('date') or existing_data.get('date') or ''
        de = updated_data.get('date_end') or ''
        
        try:
            ds_str = ds[:10] if ds else ""
            de_str = de[:10] if de else ""
            if de_str and ds_str and de_str > ds_str:
                date_to_save = f"{ds_str}/{de_str}"
            else:
                date_to_save = ds_str
        except Exception:
            date_to_save = ds

        ev_url = updated_data.get('url') or existing_data.get('url') or ''
        ev_img = updated_data.get('image_url') or existing_data.get('image_url') or ''
        
        pmin = str(updated_data.get('price_min') if updated_data.get('price_min') is not None else (existing_data.get('price_min') or ''))
        pmax = str(updated_data.get('price_max') if updated_data.get('price_max') is not None else (existing_data.get('price_max') or ''))
        
        detail = updated_data.get('tickets_detail')
        if detail is None:
            detail = existing_data.get('tickets_detail') or ''
        if isinstance(detail, list):
            detail = '\n'.join(detail)

        # build tickets_json
        lo = float(pmin.replace(',','.')) if pmin else 0.0
        hi = float(pmax.replace(',','.')) if pmax else lo
        rows_d = []
        if detail:
            for ln in detail.splitlines():
                m3 = re.search(r'([^:]+):\s*(\d+(?:[,.]?\d+)?)\s*€', ln)
                if m3:
                    rows_d.append({'sector': m3.group(1).strip(),
                                   'price': float(m3.group(2).replace(',','.')),
                                   'note': '', 'sold_out': False})
            seen = set()
            uniq_rows_d = []
            for r2 in rows_d:
                k = (r2['sector'].strip().lower(), r2['price'])
                if k not in seen:
                    seen.add(k)
                    uniq_rows_d.append(r2)
            rows_d = uniq_rows_d
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

        row_data = [
            ev_id, nm.strip(), date_to_save, plat, cat,
            str(min(prices_d)) if prices_d else pmin,
            str(max(prices_d)) if prices_d else pmax,
            ev_url, ev_img, tj_save, detail,
            datetime.utcnow().isoformat(), 'manual',
            existing_highlight
        ]

        ws.update(f'A{row_num}', [row_data])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao actualizar o Sheet: {e}")
        return False

def _trigger_update_action(row, ev_id, progress_slot=None):
    """Initiate the background update call via n8n webhook and update the sheet."""
    name = str(row.get("name","") or "")
    plat = str(row.get("platform","") or "")
    cat  = str(row.get("category","Evento") or "Evento")
    url  = str(row.get("url","") or "")
    img  = str(row.get("image_url","") or "")
    td   = str(row.get("tickets_detail","") or "")
    price_min = str(row.get("price_min","") or "")
    price_max = str(row.get("price_max","") or "")
    
    existing_data = {
        "name": name,
        "date": row.get("date", ""),
        "platform": plat,
        "category": cat,
        "url": url,
        "image_url": img,
        "price_min": price_min,
        "price_max": price_max,
        "tickets_detail": td
    }
    
    parsed = _ask_n8n_ai(name, existing_data, progress_slot=progress_slot)
    if parsed:
        if _update_event_in_sheet(ev_id, parsed, existing_data):
            st.toast(f"✅ Evento '{name}' atualizado com sucesso!")
            st.rerun()

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

def trigger_delete_click(confirm_key, ev_id, ev_name):
    st.session_state.pop(confirm_key, None)
    if _delete_row_from_sheet(ev_id, ev_name):
        st.toast(f"🗑️ Evento '{ev_name}' removido com sucesso!", icon="🗑️")

# ── Display helpers ───────────────────────────────────────────────────────────

def pp(v):
    try: return float(str(v).replace(",",".").strip())
    except: return 0.0

def is_past_event(d_start, d_end=""):
    """True if event has already finished (using end date if available, otherwise start date)."""
    try:
        ref_date = d_end.strip() if d_end and d_end.strip() else d_start.strip()
        return datetime.fromisoformat(str(ref_date)).date() < date.today()
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
        if rows:
            seen = set()
            uniq = []
            for r in rows:
                k = (r["sector"].strip().lower(), r["price"])
                if k not in seen:
                    seen.add(k)
                    uniq.append(r)
            return uniq
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
            if rows:
                seen = set()
                uniq = []
                for r in rows:
                    k = (r["sector"].strip().lower(), r["price"])
                    if k not in seen:
                        seen.add(k)
                        uniq.append(r)
                return uniq
        except: pass
    return []

def toggle_highlight_action(ev_id, is_highlighted):
    """Toggle the highlight status of an event in Google Sheets."""
    if not SPREADSHEET_ID or not SA_JSON or len(SA_JSON) < 50:
        st.error("Configurações do Google Sheets não encontradas.")
        return
    try:
        import gspread
        import json
        from google.oauth2.service_account import Credentials
        SCOPES = ["https://www.googleapis.com/auth/sheets" if "sheets" in SA_JSON else "https://www.googleapis.com/auth/spreadsheets"]
        # Use standard scopes
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(json.loads(SA_JSON), scopes=SCOPES)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Eventos")
        
        # Get headers to find the column index for "highlight"
        headers = [h.strip().lower() for h in ws.row_values(1)]
        if "highlight" not in headers:
            ws.update_cell(1, len(headers) + 1, "highlight")
            headers.append("highlight")
            
        col_idx = headers.index("highlight") + 1
        
        existing = ws.get_all_records()
        id_map = {str(r.get('id','')): i + 2 for i, r in enumerate(existing)}
        
        if ev_id in id_map:
            row_num = id_map[ev_id]
            new_val = "FALSE" if is_highlighted else "TRUE"
            ws.update_cell(row_num, col_idx, new_val)
            # Success toast
            if is_highlighted:
                st.toast("⭐ Destaque removido com sucesso!", icon="⭐")
            else:
                st.toast("🔥 Evento destacado com sucesso!", icon="🔥")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao atualizar destaque: {e}")

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
    past = is_past_event(d_start, d_end) if d_start else False
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
    mb = ""
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
    prows = sorted(price_rows(tj, td), key=lambda x: x["price"])
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
        if len(prows) > VISIBLE:
            n_extra = len(prows) - VISIBLE
            pb = (f'<div class="ev-prices">'
                  f'<div class="ev-prices-hdr">🎫 Bilhetes</div>'
                  f'<input type="checkbox" id="toggle-{_uid}" class="toggle-trigger">'
                  f'{visible_lines}'
                  f'<div class="extra-prices">{extra_lines}</div>'
                  f'<label for="toggle-{_uid}" class="ver-mais-btn btn-show">▼ +{n_extra} categorias</label>'
                  f'<label for="toggle-{_uid}" class="ver-mais-btn btn-hide">▲ ver menos</label>'
                  f'</div>')
        else:
            pb = (f'<div class="ev-prices">'
                  f'<div class="ev-prices-hdr">🎫 Bilhetes</div>'
                  f'{visible_lines}</div>')
    else:
        pb = '<div class="ev-prices"><span class="no-price">Preços em breve</span></div>'

    # Footer link
    lk = f'<a href="{url}" target="_blank" class="src-link">ver fonte ↗</a>' if url else ""
    footer = f'<div class="ev-footer">{lk}</div>'

    # Render card (includes dynamic category class and data-glow)
    st.markdown(
        f'<div class="ev-card{card_cat_cls}{past_cls}" data-glow>'
        f'<div data-glow></div>'
        f'<div class="ev-img-wrap" style="z-index: 2; position: relative;">{img_block}{stamp}</div>'
        f'<div style="z-index: 2; position: relative;">{rb}</div>'
        f'<div class="ev-body" style="z-index: 2; position: relative;">'
        f'{name_html}'
        f'{date_row}'
        f'<div class="ev-meta">{meta_html}</div>'
        f'{pb}{footer}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Action buttons (only if SA_JSON and SPREADSHEET_ID are set) ────────────────
    if ev_id and SA_JSON and len(SA_JSON) > 50:
        up_key = f"up_{ev_id}_{card_idx}"
        del_key = f"del_{ev_id}_{card_idx}"
        confirm_up_key = f"confirm_up_{ev_id}_{card_idx}"
        confirm_del_key = f"confirm_del_{ev_id}_{card_idx}"
        updating_key = f"updating_{ev_id}_{card_idx}"
        
        if st.session_state.get(updating_key):
            # Surgical overwrite to clear buttons and subtitle immediately from the browser
            co1, co2 = st.columns(2)
            with co1:
                st.empty()
            with co2:
                st.empty()
            st.markdown('<div style="display:none;"></div>', unsafe_allow_html=True)
            
            # Now show the progress slot at full width
            progress_slot = st.empty()
            st.session_state.pop(updating_key, None)
            _trigger_update_action(row, ev_id, progress_slot=progress_slot)
        elif past:
            if st.session_state.get(confirm_up_key):
                co1, co2 = st.columns(2)
                with co1:
                    st.button("✅ Confirmar", key=f"yes_{up_key}", use_container_width=True, type="primary", on_click=trigger_update_click, args=(confirm_up_key, updating_key))
                with co2:
                    st.button("❌ Cancelar", key=f"no_{up_key}", use_container_width=True, on_click=pop_state_value, args=(confirm_up_key,))
                st.markdown('<p style="font-size:0.75rem;font-weight:600;margin-top:6px;color:var(--muted);text-align:center;letter-spacing:0.5px;text-transform:uppercase;">Confirmar actualização</p>', unsafe_allow_html=True)
            elif st.session_state.get(confirm_del_key):
                co1, co2 = st.columns(2)
                with co1:
                    st.button(
                        "✅ Confirmar",
                        key=f"yes_{del_key}",
                        use_container_width=True,
                        type="primary",
                        on_click=trigger_delete_click,
                        args=(confirm_del_key, ev_id, name)
                    )
                with co2:
                    st.button("❌ Cancelar", key=f"no_{del_key}", use_container_width=True, on_click=pop_state_value, args=(confirm_del_key,))
                st.markdown('<p style="font-size:0.75rem;font-weight:600;margin-top:6px;color:var(--danger);text-align:center;letter-spacing:0.5px;text-transform:uppercase;">Confirmar remoção</p>', unsafe_allow_html=True)
            else:
                col_up, col_dest, col_del = st.columns([1.2, 1.2, 1])
                with col_up:
                    st.button("🔄 Atualizar", key=up_key, use_container_width=True, on_click=set_state_value, args=(confirm_up_key, True))
                with col_dest:
                    is_currently_highlighted = (rel == 3)
                    dest_label = "⭐ Destacado" if is_currently_highlighted else "☆ Destacar"
                    st.button(dest_label, key=f"dest_{ev_id}_{card_idx}", use_container_width=True, on_click=toggle_highlight_action, args=(ev_id, is_currently_highlighted))
                with col_del:
                    st.button("🗑️ Remover", key=del_key, use_container_width=True, on_click=set_state_value, args=(confirm_del_key, True))
        else:
            if st.session_state.get(confirm_up_key):
                co1, co2 = st.columns(2)
                with co1:
                    st.button("✅ Confirmar", key=f"yes_{up_key}", use_container_width=True, type="primary", on_click=trigger_update_click, args=(confirm_up_key, updating_key))
                with co2:
                    st.button("❌ Cancelar", key=f"no_{up_key}", use_container_width=True, on_click=pop_state_value, args=(confirm_up_key,))
                st.markdown('<p style="font-size:0.75rem;font-weight:600;margin-top:6px;color:var(--muted);text-align:center;letter-spacing:0.5px;text-transform:uppercase;">Confirmar actualização</p>', unsafe_allow_html=True)
            else:
                col_up, col_dest = st.columns(2)
                with col_up:
                    st.button("🔄 Atualizar Info", key=up_key, use_container_width=True, on_click=set_state_value, args=(confirm_up_key, True))
                with col_dest:
                    is_currently_highlighted = (rel == 3)
                    dest_label = "⭐ Destacado" if is_currently_highlighted else "☆ Destacar"
                    st.button(dest_label, key=f"dest_{ev_id}_{card_idx}", use_container_width=True, on_click=toggle_highlight_action, args=(ev_id, is_currently_highlighted))


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

def _get_assistant_avatar(state="hello"):
    """Returns a base64 inline SVG of an emoji based on the assistant state."""
    import base64
    def _svg(emoji):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y="80" font-size="80">{emoji}</text></svg>'
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"
    
    if state == "success":
        return _svg("😎")
    elif state == "thinking":
        return _svg("🤔")
    else:
        return _svg("👋")

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

    # ── Assistant Avatar (Dynamic Emoji) ──────────────────────────────────
    is_searching = st.session_state.get('ms', False) and st.session_state.get('mq', '').strip()
    
    if is_searching:
        msg = "Hmm... deixa-me procurar na internet e analisar os resultados da Inteligência Artificial..."
        avatar_img = _get_assistant_avatar("thinking")
    elif 'mr' in st.session_state:
        msg = "O pedido foi enviado para a IA, aguarda pela nova linha no google sheet."
        avatar_img = _get_assistant_avatar("success")
    else:
        msg = "Olá! Sou o assistente do TT. Escreve o nome de um concerto ou festival e eu pesquiso na internet para te ajudar a preencher os dados automaticamente!"
        avatar_img = _get_assistant_avatar("hello")

    clippy_html = f"""
    <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 20px; font-family: 'Comic Sans MS', 'Chalkboard SE', 'Comic Neue', sans-serif;">
      <div style="width: 80px; flex-shrink: 0;">
        <img src="{avatar_img}" width="80" style="animation: clippy-float 3s ease-in-out infinite;">
      </div>
      <div style="background-color: #FFFFCC; border: 2px solid #000; border-radius: 8px; padding: 12px 16px; position: relative; max-width: 500px; color: #000; box-shadow: 2px 2px 0px #000; font-size: 14px; font-weight: 500;">
        <div style="position: absolute; left: -14px; top: 20px; width: 0; height: 0; border-top: 10px solid transparent; border-bottom: 10px solid transparent; border-right: 14px solid #000;"></div>
        <div style="position: absolute; left: -10px; top: 20px; width: 0; height: 0; border-top: 10px solid transparent; border-bottom: 10px solid transparent; border-right: 14px solid #FFFFCC;"></div>
        {msg}
      </div>
    </div>
    <style>
      @keyframes clippy-float {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-5px); }}
      }}
    </style>
    """
    st.markdown(clippy_html, unsafe_allow_html=True)
    
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        q = st.text_input('Pesquisar evento...', placeholder='Ex: NOS Alive 2026, Placebo Lisboa...',
                          label_visibility='collapsed', key='mq')
    with sc2:
        go = st.button('Ir', use_container_width=True, key='ms')
            
        if go and q.strip():
            parsed = _ask_n8n_ai(q.strip())
            if parsed:
                st.session_state['mr'] = parsed
                st.session_state['mn'] = q.strip()
                
                # Explicitly populate Streamlit widget keys to bypass cached empty state values on rerun
                st.session_state['mm_n'] = parsed.get('name') or q.strip()
                st.session_state['mm_u'] = parsed.get('url', '')
                st.session_state['mm_img'] = parsed.get('image_url', '')
                
                # Align platform selectbox
                plat = parsed.get('platform') or 'Outro'
                if plat not in ['FNAC Bilheteira','Ticketline','Everything Is New','BOL','Blueticket','Outro']:
                    plat = 'Outro'
                st.session_state['mm_p'] = plat
                
                # Align category selectbox
                cat = parsed.get('category') or 'Evento'
                if cat not in ['Festival','Concerto','Evento']:
                    cat = 'Evento'
                st.session_state['mm_c'] = cat
                
                # Parse start and end dates
                from datetime import date
                try:
                    ds = parsed.get('date_start')
                    if ds:
                        st.session_state['mm_d_start'] = date.fromisoformat(ds[:10])
                except Exception:
                    pass
                    
                try:
                    de = parsed.get('date_end')
                    if de:
                        st.session_state['mm_d_end'] = date.fromisoformat(de[:10])
                    else:
                        st.session_state['mm_d_end'] = None
                except Exception:
                    st.session_state['mm_d_end'] = None
                
                # Sync prices and detailed list
                st.session_state['mm_pn'] = str(parsed.get('price_min', ''))
                st.session_state['mm_px'] = str(parsed.get('price_max', ''))
                
                det = parsed.get('tickets_detail', '')
                if isinstance(det, list):
                    det = '\n'.join(det)
                st.session_state['mm_det'] = det
                
                st.rerun()

        if 'mr' in st.session_state:
            r0 = st.session_state['mr']
            with st.expander("Dados Extraídos pelo n8n", expanded=False):
                st.json(r0)

    # Pre-fill values from web search
    r = st.session_state.get('mr', {})
    _prefill_name = r.get('name') or st.session_state.get('mn', '')
    _prefill_url  = r.get('url', '')
    _prefill_date_start = r.get('date_start', '')
    _prefill_date_end = r.get('date_end', '')
    
    _platform_val = r.get('platform') or 'Outro'
    if _platform_val not in ['FNAC Bilheteira','Ticketline','Everything Is New','BOL','Blueticket','Outro']:
        _platform_val = 'Outro'
        
    _category_val = r.get('category') or 'Evento'
    if _category_val not in ['Festival','Concerto','Evento']:
        _category_val = 'Evento'

    # ── Row 1: Name ───────────────────────────────────────────────────────
    st.markdown('<div class="add-field-label">Nome do Evento</div>', unsafe_allow_html=True)
    nm = st.text_input('Nome do evento *', value=_prefill_name,
                       placeholder='Ex: NOS Alive 2026',
                       label_visibility='collapsed', key='mm_n')

    # ── Row 2: Platform + Category ────────────────────────────────────────
    pc1, pc2 = st.columns(2)
    with pc1:
        plat_idx = ['FNAC Bilheteira','Ticketline','Everything Is New','BOL','Blueticket','Outro'].index(_platform_val)
        plat = st.selectbox('Plataforma', ['FNAC Bilheteira','Ticketline','Everything Is New',
                                            'BOL','Blueticket','Outro'], index=plat_idx, key='mm_p')
    with pc2:
        cat_idx = ['Festival','Concerto','Evento'].index(_category_val)
        cat = st.selectbox('Categoria', ['Festival','Concerto','Evento'], index=cat_idx, key='mm_c')

    # ── Row 3: Dates (own row so calendar doesn't overlap) ────────────────
    st.markdown('<div class="add-field-label">📅 Datas</div>', unsafe_allow_html=True)
    # Give dates plenty of space with a 3-column layout
    dcol1, dcol2, dcol_spacer = st.columns([1.4, 1.4, 2])
    with dcol1:
        _dt_default = None
        try:
            if _prefill_date_start:
                _dt_default = date.fromisoformat(_prefill_date_start[:10])
        except: pass
        dt_start = st.date_input(
            'Data de início *',
            value=_dt_default,
            format='DD/MM/YYYY',
            key='mm_d_start'
        )
    with dcol2:
        _dt_end_default = None
        try:
            if _prefill_date_end:
                _dt_end_default = date.fromisoformat(_prefill_date_end[:10])
        except: pass
        dt_end = st.date_input(
            'Data de fim (opcional)',
            value=_dt_end_default,
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
                               value=r.get('image_url') or st.session_state.get('mm_img_v',''),
                               placeholder='https://...', key='mm_img')
    if ev_img:
        try: st.image(ev_img, width=180, caption='Preview')
        except: st.markdown(f'`{ev_img[:80]}`')

    # ── Row 5: Prices ─────────────────────────────────────────────────────
    st.markdown('<div class="add-field-label">💰 Preços</div>', unsafe_allow_html=True)
    pr1, pr2, pr3 = st.columns([1, 1, 2])
    with pr1:
        pmin = st.text_input('Preço mínimo (€)', value=str(r.get('price_min','')), placeholder='25', key='mm_pn')
    with pr2:
        pmax = st.text_input('Preço máximo (€)', value=str(r.get('price_max','')), placeholder='85', key='mm_px')
    with pr3:
        detail_val = r.get('tickets_detail', '')
        if isinstance(detail_val, list):
            detail_val = '\n'.join(detail_val)
        detail = st.text_area('Bilhetes (linha por linha)', detail_val, height=90,
                             placeholder='Bilhete Diário: 25€\nPasse 3 dias: 75€', key='mm_det')

    # ── Row 6: Highlight ──────────────────────────────────────────────────
    _prefill_highlight = r.get('highlight', '') in ['TRUE', '1', 'x', 'yes', 'sim', 'destaque']
    is_highlight = st.checkbox("🔥 Destacar este evento", value=_prefill_highlight, key='mm_highlight')

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
                        seen = set()
                        uniq_rows_d = []
                        for r2 in rows_d:
                            k = (r2['sector'].strip().lower(), r2['price'])
                            if k not in seen:
                                seen.add(k)
                                uniq_rows_d.append(r2)
                        rows_d = uniq_rows_d
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
                        datetime.utcnow().isoformat(), 'manual',
                        "TRUE" if is_highlight else ""
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

    # ── PRIMARY CONTROLS (Centered & Merged) ──────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2.5, 3.5, 4])
    with col1:
        add_lbl = "✖ Fechar Formulário" if st.session_state['show_add'] else "➕ Adicionar Evento"
        if st.button(add_lbl, key="hero_add", type="primary", use_container_width=True):
            st.session_state['show_add'] = not st.session_state['show_add']
            st.rerun()
    with col2:
        if st.button("🔄 Forçar Actualização do Sheet", key="hero_refresh", use_container_width=True):
            get_data(force=True)
            st.toast("✅ Dados actualizados!", icon="🔄")
            st.rerun()
    with col3:
        srch = st.text_input("", "", placeholder="🔍 Procurar Evento, Festival ou Concerto",
                             label_visibility="collapsed", key="srch")

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

    # Apply sort/filter to full dataset
    f = df_all.sort_values("_dt", na_position="last").reset_index(drop=True)

    # Apply search to the active dataset
    if srch.strip():
        f = f[f["name"].str.contains(srch.strip(), case=False, na=False)]

    # Dynamic counts for tab headers based on the current filtered dataset f
    tot = len(f)
    hot = len(f[f["_rel"] == 3])
    con = len(f[f["category"].str.contains("Concerto", case=False, na=False)])
    fst = len(f[f["category"].str.contains("Festival", case=False, na=False)])
    oth = tot - con - fst

    # ── TABS ──────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        f"🔥 Destaques ({hot})",
        f"🎤 Concertos ({con})",
        f"🎪 Festivais ({fst})",
        f"🎭 Eventos ({oth})",
        f"🎵 Todos ({tot})"
    ], key="main_tabs")

    with t1: render_grid(f[f["_rel"] == 3], base_idx=5000)
    with t2: render_grid(f[f["category"].str.contains("Concerto", case=False, na=False)], base_idx=1000)
    with t3: render_grid(f[f["category"].str.contains("Festival", case=False, na=False)], base_idx=2000)
    with t4: render_grid(f[~f["category"].str.contains("Concerto|Festival", case=False, na=False)], base_idx=3000)
    with t5: render_grid(f, base_idx=0)

if __name__ == "__main__":
    main()
