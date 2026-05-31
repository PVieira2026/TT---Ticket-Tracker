"""
Deduplication and skip logic for TT Tracker.

SKIP RULE (strict):
  An event is considered "complete" ONLY if it has a detailed
  ticket breakdown — sector names + individual prices.
  A bare min/max summary (e.g. "45€-195€") is NOT sufficient.
"""
import re, json, logging
from typing import List, Dict

log = logging.getLogger(__name__)

_NOISE = re.compile(r"[^a-z0-9\s]", re.I)
_STOP  = {"de","da","do","em","e","o","a","os","as","na","no","nas","nos",
           "the","of","in","and","at","live","tour","ao","vivo","pt",
           "portugal","lisboa","porto","braga","coimbra","festival","2025","2026"}


def normalise(name: str) -> str:
    tokens = _NOISE.sub(" ", name.lower()).split()
    tokens = [t for t in tokens if t not in _STOP and len(t) > 1]
    return " ".join(sorted(tokens))


def similarity(a: str, b: str) -> float:
    ta = set(normalise(a).split())
    tb = set(normalise(b).split())
    if not ta or not tb: return 0.0
    return len(ta & tb) / len(ta | tb)


def is_same_event(a: Dict, b: Dict, threshold: float = 0.65) -> bool:
    da, db = a.get("date",""), b.get("date","")
    if da and db and da != db: return False
    return similarity(a.get("name",""), b.get("name","")) >= threshold


# ── The key function — defines what "has prices" really means ─

def has_detailed_prices(ev: Dict) -> bool:
    """
    Returns True ONLY if the event has a DETAILED ticket breakdown:
    - At least 2 distinct price rows
    - At least 1 row has a non-generic sector name (not just "Geral")
    
    Returns False if:
    - No prices at all
    - Only min/max summary without breakdown
    - Only 1 generic "Geral: X€" row
    - tickets_detail is empty or has only 1 line
    """
    tj = ev.get("tickets_json","")
    td = ev.get("tickets_detail","")

    if not tj and not td:
        return False

    # ── Check tickets_json (most reliable)
    if tj:
        try:
            data = json.loads(tj)
            cats = data.get("categories",[])
            all_rows = [row for cat in cats for row in cat.get("rows",[])]

            if len(all_rows) < 2:
                return False  # need at least 2 price tiers

            # Check if at least 1 row has a specific sector name
            specific_sectors = [
                r for r in all_rows
                if r.get("sector","").lower() not in ("geral","","geral (lote)","min (lote)","max (lote)")
            ]
            if specific_sectors:
                return True  # has named sectors → detailed ✅

            # If all rows are "Geral" but there are 3+ distinct prices → acceptable
            prices = list({r.get("price",0) for r in all_rows})
            return len(prices) >= 3

        except Exception:
            pass

    # ── Fallback: check tickets_detail text
    if td:
        lines = [l.strip() for l in td.splitlines()
                 if l.strip() and not l.strip().startswith("Bilhete")]
        if len(lines) < 2:
            return False

        # At least 1 line should have a specific sector (not just "Geral")
        specific = [l for l in lines if not l.lower().startswith("geral")]
        return len(specific) >= 1 and len(lines) >= 2

    return False


def quality(ev: Dict) -> int:
    score = 0
    if has_detailed_prices(ev): score += 20  # detailed breakdown = gold
    elif ev.get("price_min"):   score += 2   # min/max only = barely useful
    if ev.get("tickets_json"):  score += 3
    if ev.get("image_url"):     score += 1
    if ev.get("date"):          score += 2
    # Count ticket rows
    try:
        d = json.loads(ev.get("tickets_json","") or "{}")
        rows = sum(len(c.get("rows",[])) for c in d.get("categories",[]))
        score += min(rows, 15)  # more rows = better, cap at 15
    except Exception:
        pass
    return score


def dedup_events(events: List[Dict]) -> List[Dict]:
    """Merge duplicate events across platforms, keeping best data."""
    if not events: return []

    groups: List[List[Dict]] = []
    for ev in events:
        placed = False
        for group in groups:
            if is_same_event(ev, group[0]):
                group.append(ev); placed = True; break
        if not placed:
            groups.append([ev])

    merged = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0]); continue

        group.sort(key=quality, reverse=True)
        base = dict(group[0])

        for other in group[1:]:
            # Upgrade prices only if current base doesn't have detailed breakdown
            if not has_detailed_prices(base) and has_detailed_prices(other):
                base["price_min"]      = other["price_min"]
                base["price_max"]      = other["price_max"]
                base["tickets_json"]   = other["tickets_json"]
                base["tickets_detail"] = other["tickets_detail"]
                base["price_source"]   = f"{other.get('price_source','')} via {other['platform']}"
            if not base.get("image_url") and other.get("image_url"):
                base["image_url"] = other["image_url"]
            if not base.get("date") and other.get("date"):
                base["date"] = other["date"]

        platforms = list(dict.fromkeys(e["platform"] for e in group))
        if len(platforms) > 1:
            log.info(f"  Merged: '{base['name']}' from {platforms}")
        merged.append(base)

    log.info(f"Dedup: {len(events)} → {len(merged)} unique events")
    return merged


class SheetState:
    """
    Pre-loaded sheet state. Used to skip scraping for events
    that ALREADY have detailed price breakdowns.
    """
    def __init__(self, existing_events: List[Dict]):
        self._detailed: Dict[str,Dict]    = {}  # normalised_name → event
        self._no_detail: Dict[str,Dict]   = {}  # has prices but no breakdown

        for ev in existing_events:
            key = normalise(ev.get("name",""))
            if not key: continue
            if has_detailed_prices(ev):
                self._detailed[key] = ev
            elif ev.get("price_min"):
                self._no_detail[key] = ev

        log.info(
            f"SheetState: "
            f"{len(self._detailed)} with detailed prices (will skip), "
            f"{len(self._no_detail)} with min/max only (will re-scrape for detail), "
            f"{len(existing_events)-len(self._detailed)-len(self._no_detail)} no prices"
        )

    def _fuzzy_match(self, name: str, lookup: Dict) -> bool:
        key = normalise(name)
        if key in lookup: return True
        for k in lookup:
            ta = set(key.split()); tb = set(k.split())
            if ta and tb and len(ta & tb) / len(ta | tb) >= 0.70:
                return True
        return False

    def skip_playwright(self, name: str) -> bool:
        """
        True = event already has DETAILED prices → skip T2/T3.
        False = needs scraping (no prices OR only min/max summary).
        """
        return self._fuzzy_match(name, self._detailed)

    def needs_scraping(self, name: str) -> bool:
        """Inverse of skip_playwright."""
        return not self.skip_playwright(name)

    @classmethod
    def from_sheet(cls, spreadsheet_id: str) -> "SheetState":
        try:
            from utils.sheets import read_sheet
            df = read_sheet(spreadsheet_id)
            return cls(df.to_dict("records"))
        except Exception as e:
            log.warning(f"Could not load sheet state: {e}")
            return cls([])

    @classmethod
    def empty(cls) -> "SheetState":
        return cls([])
