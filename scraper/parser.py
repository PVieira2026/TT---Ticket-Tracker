import re, json
from typing import List, Dict, Optional

MONTHS_PT = {
    "jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,
    "set":9,"out":10,"nov":11,"dez":12,"janeiro":1,"fevereiro":2,
    "marco":3,"abril":4,"maio":5,"junho":6,"julho":7,"agosto":8,
    "setembro":9,"outubro":10,"novembro":11,"dezembro":12,
}
FESTIVAL_KW = ["festival","fest","alive","super bock","meo","vodafone",
               "paredes de coura","primavera sound","rock in rio","summer",
               "open air","outdoor","nos alive"]
CONCERT_KW  = ["tour","concerto","ao vivo","live","arena","coliseu","pavilhao"]


def detect_category(name: str, url: str = "") -> str:
    t = (name + " " + url).lower()
    if any(k in t for k in FESTIVAL_KW): return "Festival"
    if any(k in t for k in CONCERT_KW):  return "Concerto"
    return "Evento"


def strip_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>",   " ", html, flags=re.I)
    html = re.sub(r"<br\s*/?>",                "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8364;", "\u20ac")
    return re.sub(r"[ \t]+", " ", html).strip()


def parse_date(raw: str) -> Optional[str]:
    if not raw: return None
    try:
        from datetime import datetime
        d = datetime.fromisoformat(raw.strip().split("T")[0])
        if d.year > 2020: return d.strftime("%Y-%m-%d")
    except Exception: pass
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})", raw, re.I)
    if m:
        mon = MONTHS_PT.get(m.group(2).lower()) or MONTHS_PT.get(m.group(2)[:3].lower())
        if mon: return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return None


def extract_prices(text: str) -> List[Dict]:
    rows, seen = [], set()

    def add(sector, price, note="", sold=False):
        key = f"{sector.strip()}|{price}"
        if key in seen or price < 1 or price > 2500 or len(sector.strip()) < 2: return
        if re.match(r"^(menu|login|faq|home|ajuda|contacto|newsletter)$", sector.strip(), re.I): return
        seen.add(key)
        rows.append({"sector": sector.strip(), "price": round(price, 2),
                     "note": note.strip().strip("()[]"), "sold_out": sold})

    # A: single-dash  "Sector - 45E"  (EIN format)
    for m in re.finditer(
        r"([A-Za-z\u00c0-\u017e][^\n\u20ac\-]{1,60}?)\s*-\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,80})?",
        text, re.M
    ):
        n = m.group(3) or ""
        add(m.group(1), float(m.group(2).replace(",", ".")), n, bool(re.search(r"esgotado|sold.?out", n, re.I)))

    # B: em-dash  "Sector -- 45E"  (FNAC format)
    for m in re.finditer(
        r"([A-Za-z\u00c0-\u017e][^\n\u20ac\u2014\u2013]{1,60}?)\s*[\u2014\u2013]\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,80})?",
        text, re.M
    ):
        n = m.group(3) or ""
        add(m.group(1), float(m.group(2).replace(",", ".")), n, bool(re.search(r"esgotado|sold.?out", n, re.I)))

    if not rows:
        for m in re.finditer(
            r"([A-Za-z\u00c0-\u017e][^\u20ac:\n]{2,50}):\s*(\d+(?:[,.]\d+)?)\s*\u20ac([^\n\u20ac]{0,60})?",
            text, re.M
        ):
            add(m.group(1), float(m.group(2).replace(",", ".")), (m.group(3) or "").strip())

    if not rows:
        for m in re.finditer(r"de\s*(\d+(?:[,.]\d+)?)\s*\u20ac\s*a\s*(\d+(?:[,.]\d+)?)\s*\u20ac", text, re.I):
            add("Minimo (lote)", float(m.group(1).replace(",", ".")))
            add("Maximo (lote)", float(m.group(2).replace(",", ".")))

    if not rows:
        for m in re.finditer(r"(\d+(?:[,.]\d+)?)\s*\u20ac", text):
            add("Geral", float(m.group(1).replace(",", ".")))

    return rows


def build_tickets_detail(rows: List[Dict]) -> str:
    if not rows: return ""
    lines = ["Bilhetes"]
    for r in rows:
        note = f" ({r['note']})" if r["note"] else ""
        sold = " ESGOTADO" if r["sold_out"] else ""
        lines.append(f"  {r['sector']}: {r['price']}\u20ac{note}{sold}")
    return "\n".join(lines)


def build_tickets_json(rows: List[Dict]) -> str:
    if not rows: return ""
    prices = [r["price"] for r in rows]
    return json.dumps({
        "summary": {"min": min(prices), "max": max(prices), "currency": "EUR"},
        "categories": [{"name": "Bilhetes", "rows": rows}]
    }, ensure_ascii=False)
