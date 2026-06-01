import re, os, time, logging
import requests
from typing import List, Dict
from scraper.parser import extract_prices, build_tickets_detail, build_tickets_json

log=logging.getLogger(__name__)
SERPER_KEY=os.environ.get("SERPER_API_KEY","")

def _clean_query(name,year=""):
    q=re.sub(r'[\|\(\)\[\]\{\}]',' ',name); q=re.sub(r'\s+',' ',q).strip()
    if year and year not in q: q+=f" {year}"
    return q+" preço bilhetes"

def _search_serper(query):
    try:
        resp=requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY":SERPER_KEY,"Content-Type":"application/json"},
            json={"q":query,"gl":"pt","hl":"pt","num":5},timeout=10)
        if resp.status_code!=200: return []
        return [{"title":r.get("title",""),"snippet":r.get("snippet",""),"link":r.get("link","")}
                for r in resp.json().get("organic",[])]
    except Exception as e: log.warning(f"Serper: {e}"); return []

def _search_duckduckgo(query):
    try:
        resp=requests.get("https://api.duckduckgo.com/",
            params={"q":query,"format":"json","no_html":1,"skip_disambig":1},timeout=10)
        data=resp.json(); results=[]
        if data.get("AbstractText"):
            results.append({"title":data.get("Heading",""),"snippet":data["AbstractText"],"link":data.get("AbstractURL","")})
        for t in data.get("RelatedTopics",[])[:4]:
            if isinstance(t,dict) and t.get("Text"):
                results.append({"title":"","snippet":t["Text"],"link":t.get("FirstURL","")})
        return results
    except Exception as e: log.warning(f"DDG: {e}"); return []

def _search_google(query):
    try:
        import urllib.parse
        url=f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=pt&gl=pt&num=5"
        resp=requests.get(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)","Accept-Language":"pt-PT,pt;q=0.9"},timeout=10)
        snippets=re.findall(r'<div[^>]+data-sncf[^>]*>(.*?)</div>',resp.text,re.S)
        results=[]
        for s in snippets[:5]:
            text=re.sub(r'<[^>]+>',' ',s).strip()
            if text and len(text)>20: results.append({"title":"","snippet":text,"link":""})
        return results
    except Exception as e: log.warning(f"Google: {e}"); return []

def search_prices(event_name,event_date=""):
    year=event_date[:4] if event_date else ""
    query=_clean_query(event_name,year)
    log.info(f"[WebSearch] {repr(query)}")
    if SERPER_KEY: snippets=_search_serper(query)
    else:
        snippets=_search_duckduckgo(query)
        if not snippets: snippets=_search_google(query)
    if not snippets: return []
    combined=" | ".join(s["snippet"] for s in snippets if s.get("snippet"))
    rows=extract_prices(combined)
    if rows: log.info(f"[WebSearch] {len(rows)} prices for '{event_name}'"  ); return rows
    m=re.search(r'(\d+(?:[,.]\d+)?)\s*\u20ac[^€]*?(\d+(?:[,.]\d+)?)\s*\u20ac',combined)
    if m:
        lo,hi=float(m.group(1).replace(",",".")),float(m.group(2).replace(",","."))
        if 1<=lo<=2000 and lo!=hi:
            rows=[{"sector":"Pre\u00e7o m\u00ednimo","price":min(lo,hi),"note":"web search","sold_out":False},
                  {"sector":"Pre\u00e7o m\u00e1ximo","price":max(lo,hi),"note":"web search","sold_out":False}]
            log.info(f"[WebSearch] Range {lo}-{hi}\u20ac for '{event_name}'"  )
    return rows
