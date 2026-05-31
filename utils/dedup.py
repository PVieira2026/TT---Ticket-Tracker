import re, json, logging
from typing import List, Dict
log=logging.getLogger(__name__)
_NOISE=re.compile(r"[^a-z0-9\s]",re.I)
_STOP={"de","da","do","em","e","o","a","os","as","na","no","nas","nos","the","of","in","and","at","live","tour","ao","vivo","pt","portugal","lisboa","porto","braga","coimbra","festival","2025","2026"}
def normalise(name):
    tokens=_NOISE.sub(" ",name.lower()).split(); tokens=[t for t in tokens if t not in _STOP and len(t)>1]; return " ".join(sorted(tokens))
def similarity(a,b):
    ta=set(normalise(a).split()); tb=set(normalise(b).split())
    if not ta or not tb: return 0.0
    return len(ta&tb)/len(ta|tb)
def is_same_event(a,b,threshold=0.65):
    da,db=a.get("date",""),b.get("date","")
    if da and db and da!=db: return False
    return similarity(a.get("name",""),b.get("name",""))>=threshold
def has_detailed_prices(ev):
    tj=ev.get("tickets_json",""); td=ev.get("tickets_detail","")
    if not tj and not td: return False
    if tj:
        try:
            data=json.loads(tj); cats=data.get("categories",[]); all_rows=[row for cat in cats for row in cat.get("rows",[])]
            if len(all_rows)<2: return False
            specific=[r for r in all_rows if r.get("sector","").lower() not in ("geral","","geral (lote)","min (lote)","max (lote)")]
            if specific: return True
            return len({r.get("price",0) for r in all_rows})>=3
        except: pass
    if td:
        lines=[l.strip() for l in td.splitlines() if l.strip() and not l.strip().lower().startswith("bilhete")]
        if len(lines)<2: return False
        return len([l for l in lines if not l.lower().startswith("geral")])>=1
    return False
def quality(ev):
    score=0
    if has_detailed_prices(ev): score+=20
    elif ev.get("price_min"): score+=2
    if ev.get("tickets_json"): score+=3
    if ev.get("image_url"): score+=1
    if ev.get("date"): score+=2
    try:
        d=json.loads(ev.get("tickets_json","") or "{}"); rows=sum(len(c.get("rows",[])) for c in d.get("categories",[])); score+=min(rows,15)
    except: pass
    return score
def dedup_events(events):
    if not events: return []
    groups=[]
    for ev in events:
        placed=False
        for group in groups:
            if is_same_event(ev,group[0]): group.append(ev); placed=True; break
        if not placed: groups.append([ev])
    merged=[]
    for group in groups:
        if len(group)==1: merged.append(group[0]); continue
        group.sort(key=quality,reverse=True); base=dict(group[0])
        for other in group[1:]:
            if not has_detailed_prices(base) and has_detailed_prices(other):
                base["price_min"]=other["price_min"]; base["price_max"]=other["price_max"]
                base["tickets_json"]=other["tickets_json"]; base["tickets_detail"]=other["tickets_detail"]
                base["price_source"]=f"{other.get('price_source','')} via {other['platform']}"
            if not base.get("image_url") and other.get("image_url"): base["image_url"]=other["image_url"]
            if not base.get("date") and other.get("date"): base["date"]=other["date"]
        platforms=list(dict.fromkeys(e["platform"] for e in group))
        if len(platforms)>1: log.info(f"  Merged: {base['name']} from {platforms}")
        merged.append(base)
    log.info(f"Dedup: {len(events)} -> {len(merged)} unique"); return merged
class SheetState:
    def __init__(self,existing_events):
        self._detailed={}; self._no_detail={}
        for ev in existing_events:
            key=normalise(ev.get("name",""))
            if not key: continue
            if has_detailed_prices(ev): self._detailed[key]=ev
            elif ev.get("price_min"): self._no_detail[key]=ev
        log.info(f"SheetState: {len(self._detailed)} detailed, {len(self._no_detail)} min/max only")
    def _fuzzy(self,name,lookup):
        key=normalise(name)
        if key in lookup: return True
        for k in lookup:
            ta=set(key.split()); tb=set(k.split())
            if ta and tb and len(ta&tb)/len(ta|tb)>=0.70: return True
        return False
    def skip_playwright(self,name): return self._fuzzy(name,self._detailed)
    def needs_scraping(self,name): return not self.skip_playwright(name)
    @classmethod
    def from_sheet(cls,spreadsheet_id):
        try:
            from utils.sheets import read_sheet
            return cls(read_sheet(spreadsheet_id).to_dict("records"))
        except Exception as e: log.warning(f"SheetState: {e}"); return cls([])
    @classmethod
    def empty(cls): return cls([])
