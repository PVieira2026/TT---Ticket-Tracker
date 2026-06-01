import re, time, html as _html
from datetime import date, timedelta, datetime
from typing import List, Dict
import requests
from scraper.parser import strip_html, parse_date, extract_prices, build_tickets_detail, build_tickets_json, detect_category

PLATFORM="Everything Is New"
API="https://everythingisnew.pt/wp-json/wp/v2/posts"
PRMS={"per_page":100,"_fields":"title,link,date,content","_embed":"true","orderby":"modified","order":"desc"}
HDRS={"User-Agent":"Mozilla/5.0 (compatible; TTTracker/2.0)","Accept":"application/json"}
GENERIC_IMGS=["EverythingIsNew.png","fundo","mobile"]

def _get_image(post):
    try:
        media=post.get("_embedded",{}).get("wp:featuredmedia",[])
        if media and isinstance(media,list):
            src=(media[0].get("source_url","") or media[0].get("media_details",{}).get("sizes",{}).get("full",{}).get("source_url",""))
            if src and not any(g in src for g in GENERIC_IMGS): return src
    except: pass
    content=_html.unescape(post.get("content",{}).get("rendered",""))
    for img in re.findall(r'<img[^>]+src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',content,re.I):
        if not any(g in img for g in GENERIC_IMGS): return img
    return ""

def scrape(sheet_state=None):
    today,horizon=date.today(),date.today()+timedelta(days=180)
    posts=[]
    for page in range(1,4):
        try:
            r=requests.get(API,params={**PRMS,"page":page},headers=HDRS,timeout=20)
            batch=r.json()
            if not isinstance(batch,list) or not batch: break
            posts.extend(batch); time.sleep(0.4)
        except: break
    results=[]
    for post in posts:
        name=strip_html(post.get("title",{}).get("rendered","")).strip()
        url=post.get("link",""); slug=url.rstrip("/").split("/")[-1]
        content_html=_html.unescape(post.get("content",{}).get("rendered",""))
        text=strip_html(content_html)
        if not name or len(name)<2: continue
        event_date=None
        for pat in [r"(\d{1,2})\s+(?:de\s+)?([a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00e7]+)(?:\s+de)?\s+(\d{4})",r"(\d{4})-(\d{2})-(\d{2})",r"(\d{2})/(\d{2})/(\d{4})"]:
            for m in re.finditer(pat,text,re.I):
                p=parse_date(m.group(0))
                if p:
                    try:
                        d=date.fromisoformat(p)
                        if today<=d<=horizon: event_date=p; break
                    except: pass
            if event_date: break
        if not event_date: continue
        rows=extract_prices(text); prices=[r["price"] for r in rows]
        results.append({"id":f"ein-{slug}","name":name,"date":event_date,
            "platform":PLATFORM,"category":detect_category(name,url),
            "price_min":str(min(prices)) if prices else "","price_max":str(max(prices)) if prices else "",
            "url":url,"image_url":_get_image(post),
            "tickets_json":build_tickets_json(rows),"tickets_detail":build_tickets_detail(rows),
            "updated_at":datetime.utcnow().isoformat(),
            "scraper_status":"ok" if prices else "ok_no_prices","price_source":"static" if prices else ""})
    return results
