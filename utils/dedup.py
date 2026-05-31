"""
Deduplication and skip logic for TT Tracker.

Three problems solved:
  1. Same event appears on multiple platforms (FNAC + EIN + TL) → keep best
  2. Event already has prices in sheet → skip Tier 2/3 scraping
  3. New run finds events already in sheet → upsert, don't duplicate rows
"""
import re, logging
from typing import List, Dict, Set, Tuple, Optional

log = logging.getLogger(__name__)


# ── Name normalisation ────────────────────────────────────────

_NOISE = re.compile(r"""[^a-z0-9\s]""", re.I)
_STOP  = {"de","da","do","em","e","o","a","os","as","na","no","nas","nos",
           "the","of","in","and","at","live","tour","ao","vivo","pt",
           "portugal","lisboa","porto","braga","coimbra","festival","2025","2026"}

def normalise(name: str) -> str:
    """Lowercase, strip punctuation, remove stop words, sort tokens."""
    tokens = _NOISE.sub(" ", name.lower()).split()
    tokens = [t for t in tokens if t not in _STOP and len(t) > 1]
    return " ".join(sorted(tokens))

def similarity(a: str, b: str) -> float:
    """Token overlap similarity between two normalised names. 0-1."""
    ta = set(normalise(a).split())
    tb = set(normalise(b).split())
    if not ta or not tb: return 0.0
    return len(ta & tb) / len(ta | tb)

def is_same_event(ev_a: Dict, ev_b: Dict, threshold: float = 0.65) -> bool:
    """True if two events are likely the same real-world event."""
    # Must have matching or empty date
    date_a = ev_a.get("date","")
    date_b = ev_b.get("date","")
    if date_a and date_b and date_a != date_b:
        return False
    return similarity(ev_a.get("name",""), ev_b.get("name","")) >= threshold


# ── Event quality score (higher = better data) ───────────────

def quality(ev: Dict) -> int:
    score = 0
    if ev.get("price_min"):   score += 10
    if ev.get("tickets_json"):score += 5
    if ev.get("image_url"):   score += 2
    if ev.get("date"):        score += 3
    if ev.get("tickets_detail"): score += len(ev["tickets_detail"].splitlines())
    return score


# ── Cross-platform deduplication ─────────────────────────────

def dedup_events(events: List[Dict]) -> List[Dict]:
    """
    Merge duplicate events across platforms.
    Strategy: group by similarity, keep highest-quality record,
    enrich with data from others (prices, image, etc.).
    """
    if not events:
        return []

    groups: List[List[Dict]] = []

    for ev in events:
        placed = False
        for group in groups:
            if is_same_event(ev, group[0]):
                group.append(ev)
                placed = True
                break
        if not placed:
            groups.append([ev])

    merged = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Sort by quality descending — best record is base
        group.sort(key=quality, reverse=True)
        base = dict(group[0])

        # Enrich base with data from others
        for other in group[1:]:
            if not base.get("price_min") and other.get("price_min"):
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
            log.info(f"  Merged '{base['name']}' across {platforms}")

        merged.append(base)

    log.info(f"Dedup: {len(events)} events → {len(merged)} unique")
    return merged


# ── Skip logic: read existing sheet state ────────────────────

class SheetState:
    """
    Loaded once per run. Tracks which events already have prices.
    Used to skip T2/T3 scraping for events that don't need it.
    """
    def __init__(self, existing_events: List[Dict]):
        # Map: normalised_name → event dict
        self._with_prices: Dict[str, Dict]    = {}
        self._without_prices: Dict[str, Dict] = {}

        for ev in existing_events:
            key = normalise(ev.get("name",""))
            if not key: continue
            if ev.get("price_min"):
                self._with_prices[key] = ev
            else:
                self._without_prices[key] = ev

        log.info(f"SheetState: {len(self._with_prices)} events with prices, "
                 f"{len(self._without_prices)} without prices in sheet")

    def has_prices(self, name: str) -> bool:
        """True if this event is already in the sheet WITH prices."""
        key = normalise(name)
        # Direct match
        if key in self._with_prices:
            return True
        # Fuzzy match
        for existing_key in self._with_prices:
            ta = set(key.split()); tb = set(existing_key.split())
            if ta and tb and len(ta & tb) / len(ta | tb) >= 0.7:
                return True
        return False

    def needs_playwright(self, name: str) -> bool:
        """False = event already has prices, skip T2/T3."""
        return not self.has_prices(name)

    @classmethod
    def from_sheet(cls, spreadsheet_id: str) -> "SheetState":
        """Load state from Google Sheet."""
        try:
            from utils.sheets import read_sheet
            df = read_sheet(spreadsheet_id)
            events = df.to_dict("records")
            return cls(events)
        except Exception as e:
            log.warning(f"Could not load sheet state: {e}")
            return cls([])

    @classmethod
    def empty(cls) -> "SheetState":
        return cls([])
