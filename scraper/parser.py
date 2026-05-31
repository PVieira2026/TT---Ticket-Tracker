import re, json
from typing import List, Dict, Optional
MONTHS_PT={"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12,"janeiro":1,"fevereiro":2,"marco":3,"abril":4,"maio":5,"junho":6,"julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12}
FESTIVAL_KW=["festival","fest","alive","super bock","meo","vodafone","paredes de coura","primavera sound","rock in rio","summer","open air","outdoor","nos alive","neopop","boom"]
CONCERT_KW=["tour","concerto","ao vivo","live","arena","coliseu","pavilhao","altice arena","campo pequeno","digressao"]
FNAC_BOILERPLATE={1.0,1.5,10.0,25.0,50.0,75.0,120.0}
SECTOR_BLACKLIST={"sinopse","espetaculo","espet\u00e1culo","descri","informa","sobre","notas","nota:","aviso","termos","politica","privaci","cookies","rgpd","seguran","reserva","seguro bilheteira","chamada","acesso","publicidade"}
HIGH_REL=["coldplay","radiohead","ed sheeran","billie eilish","taylor swift","the weeknd","beyonce","rihanna","adele","harry styles","depeche mode","the national","arcade fire","arctic monkeys","metallica","iron maiden","foo fighters","red hot chili peppers","guns n roses","blur","oasis","placebo","laura pausini","anitta","anastacia","brandi carlile","dua lipa","imagine dragons","maroon 5","lana del rey","the cure","massive attack","nos alive","super bock","mares vivas","neopop","paredes de coura","primavera sound","rock in rio","evillive","meo mares","sudowoodo"]
def score_relevance(name,url=""):
    t=(name+" "+url).lower()
    if any(k in t for k in HIGH_REL): return 3
    if any(k in t for k in ["festival","altice","coliseu","pavilh","campo pequeno","arena"]): return 2
    return 1
def is_valid_sector(sector):
    s=sector.lower().strip()
    if len(s)<2: return False
    for term in SECTOR_BLACKLIST:
        if s.startswith(term) or term in s: return False
    if re.match(r"^(menu|login|faq|home|ajuda|contacto|newsletter|cookies|privacidade)$",s,re.I): return False
    return True
def detect_category(name,url=""):
    t=(name+" "+url).lower()
    if any(k in t for k in FESTIVAL_KW): return "Festival"
    if any(k in t for k in CONCERT_KW): return "Concerto"
    return "Evento"
def strip_html(html):
    html=re.sub(r"<script[\s\S]*?</script>"," ",html,flags=re.I)
    html=re.sub(r"<style[\s\S]*?</style>"," ",html,flags=re.I)
    html=re.sub(r"<br\s*/?>","\n",html,flags=re.I)
    html=re.sub(r"<[^>]+"," ",html)
    html=html.replace("&nbsp;"," ").replace("&amp;","&").replace("&#8364;","\u20ac")
    return re.sub(r"[ \t]+"," ",html).strip()
def parse_date(raw):
    if not raw: return None
    try:
        from datetime import datetime
        d=datetime.fromisoformat(raw.strip().split("T")[0])
        if d.year>2020: return d.strftime("%Y-%m-%d")
    except: pass
    m=re.search(r"(\d{2})/(\d{2})/(\d{4})",raw)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m=re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})",raw,re.I)
    if m:
        mon=MONTHS_PT.get(m.group(2).lower()) or MONTHS_PT.get(m.group(2)[:3].lower())
        if mon: return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return None

def extract_prices(text, filter_boilerplate=False):
    rows, seen = [], set()
    def add(sector, price, note="", sold=False):
        sector = sector.strip()
        if not is_valid_sector(sector): return
        key = f"{sector}|{price}"
        if key in seen or price < 1 or price > 2500: return
        if 2020 < price < 2030: return
        if filter_boilerplate and price in FNAC_BOILERPLATE: return
        seen.add(key)
        rows.append({"sector": sector, "price": round(price, 2),
                     "note": note.strip().strip("()[]"), "sold_out": bool(sold)})

    # A: "Sector - 45\u20ac"  \u2190 single dash
    for m in re.finditer(
        r"([A-Za-z\u00c0-\u017e][^\n\u20ac\-]{1,60}?)\s*-\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,80})?",
        text, re.M
    ):
        n = m.group(3) or ""
        add(m.group(1), float(m.group(2).replace(",",".")), n, bool(re.search(r"esgotado|sold.?out",n,re.I)))

    # B: "Sector \u2014 45\u20ac"  \u2190 em-dash
    for m in re.finditer(
        r"([A-Za-z\u00c0-\u017e][^\n\u20ac\u2014\u2013]{1,60}?)\s*[\u2014\u2013]\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,80})?",
        text, re.M
    ):
        n = m.group(3) or ""
        add(m.group(1), float(m.group(2).replace(",",".")), n, bool(re.search(r"esgotado|sold.?out",n,re.I)))

    # C: "Sector | 45\u20ac"  \u2190 PIPE separator (FNAC descriptions)
    # THIS WAS THE MISSING PATTERN.
    # Festival Panda: "Bilhete Individual | 23\u20ac"  "Pack 3 bilhetes |  64,50\u20ac"
    for m in re.finditer(
        r"([A-Za-z\u00c0-\u017e][^\n\u20ac|]{1,60}?)\s*\|\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,80})?",
        text, re.M
    ):
        n = m.group(3) or ""
        add(m.group(1), float(m.group(2).replace(",",".")), n, bool(re.search(r"esgotado|sold.?out",n,re.I)))

    # ── Fallbacks (only if A+B+C found nothing) ──────────────────────────────

    # D: "Sector: 45\u20ac"
    if not rows:
        for m in re.finditer(
            r"([A-Za-z\u00c0-\u017e][^\u20ac:\n]{2,50}):\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,60})?",
            text, re.M
        ):
            add(m.group(1), float(m.group(2).replace(",",".")), (m.group(3) or "").strip())

    # E: "de X\u20ac a Y\u20ac"  \u2190 price range
    if not rows:
        for m in re.finditer(r"de\s*(\d+(?:[,.]\d+)?)\s*\u20ac\s*a\s*(\d+(?:[,.]\d+)?)\s*\u20ac",text,re.I):
            add("Min (lote)", float(m.group(1).replace(",",".")))
            add("Max (lote)", float(m.group(2).replace(",",".")))

    # F: "XX,XX\u20ac"  \u2190 generic, absolute last resort
    if not rows:
        for m in re.finditer(r"(\d+[,.]\d{2})\s*\u20ac", text):
            add("Geral", float(m.group(1).replace(",",".")))

    return rows

def build_tickets_detail(rows):
    if not rows: return ""
    lines=["Bilhetes"]
    for r in rows:
        note=(" ("+r["note"]+")") if r["note"] else ""; sold=" ESGOTADO" if r["sold_out"] else ""
        lines.append("  "+r["sector"]+": "+str(r["price"])+"\u20ac"+note+sold)
    return "\n".join(lines)

def build_tickets_json(rows):
    if not rows: return ""
    prices=[r["price"] for r in rows]
    return json.dumps({"summary":{"min":min(prices),"max":max(prices),"currency":"EUR"},
                       "categories":[{"name":"Bilhetes","rows":rows}]},ensure_ascii=False)
