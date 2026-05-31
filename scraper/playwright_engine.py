import re, asyncio, logging
from typing import List, Dict
from scraper.parser import extract_prices, strip_html, FNAC_BOILERPLATE

log=logging.getLogger(__name__)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PRICE_WAIT=["#venueZonesList","ul.list_zone_list","[class*=price]","[class*=preco]"]
BUY_SELS=["a:has-text('Comprar')","a:has-text('Bilhetes')","a[href*='/sessao/']","[class*=buy]"]

# Ticketline zone extractor — verified from DevTools
# Structure: ul#venueZonesList > li.clearfix[.soldout] > a > p.zone, p.price > span.session-generic
TL_ZONE_JS = (
    "() => {"
    "  const rows=[], seen=new Set();"
    "  const el=document.querySelector('#venueZonesList,ul.list_zone_list');"
    "  if(!el) return rows;"
    "  el.querySelectorAll('li:not(.list_header)').forEach(li=>{"
    "    const sold=li.classList.contains('soldout');"
    "    const ze=li.querySelector('p.zone');"
    "    const pe=li.querySelector('p.price');"
    "    if(!ze||!pe) return;"
    "    const sec=ze.textContent.trim();"
    "    let price=0;"
    "    const sp=pe.querySelector('span.session-generic,span[class*=session]');"
    "    if(sp){const m2=sp.textContent.match(/\\((\\d+(?:[,.]\\d+)?)/);if(m2)price=parseFloat(m2[1].replace(',','.'));}"
    "    if(!price){const rt=Array.from(pe.childNodes).filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join('');const m=rt.match(/(\\d+(?:[,.]\\d+)?)/);if(m)price=parseFloat(m[1].replace(',','.'));}"
    "    if(!sec||!price||price<1||price>2500) return;"
    "    const k=sec+'|'+price; if(seen.has(k)) return; seen.add(k);"
    "    rows.push({sector:sec, price, note:'', sold_out:sold});"
    "  });"
    "  return rows;"
    "}"
)

GENERIC_JS = (
    "() => {"
    "  const rows=[],seen=new Set();"
    "  const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);"
    "  let node;"
    "  while((node=w.nextNode())){"
    "    const t=node.textContent.trim();"
    "    if(!t.includes('\u20ac')) continue;"
    "    const m=t.match(/(\\d+(?:[,.]\\d+)?)\\s*\u20ac/); if(!m) continue;"
    "    const price=parseFloat(m[1].replace(',','.')); if(price<1||price>2500||(price>2020&&price<2030)) continue;"
    "    let label=''; const el=node.parentElement;"
    "    if(el){const anc=el.closest('[class*=sector],[class*=zona],[class*=tarif],[class*=row],[class*=item]');if(anc)label=anc.innerText.split('\n')[0].trim().substring(0,60);}"
    "    const k=(label||'Geral')+'|'+price; if(seen.has(k)) continue; seen.add(k);"
    "    rows.push({sector:label||'Geral', price, note:'', sold_out:false});"
    "  }"
    "  return rows;"
    "}"
)

def _is_tl(url): return "ticketline" in url.lower()

async def _launch():
    from playwright.async_api import async_playwright
    p=await async_playwright().__aenter__()
    br=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"])
    ctx=await br.new_context(user_agent=UA,viewport={"width":1280,"height":800},locale="pt-PT",extra_http_headers={"Accept-Language":"pt-PT,pt;q=0.9,en;q=0.8"})
    return p,br,ctx


class BrowserSession:
    def __init__(self,timeout=22000): self.timeout=timeout; self._pw=self._browser=self._ctx=None
    async def __aenter__(self): self._pw,self._browser,self._ctx=await _launch(); return self
    async def __aexit__(self,*_):
        try: await self._browser.close(); await self._pw.__aexit__(None,None,None)
        except: pass

    async def render(self,url,filter_bp=False):
        page=await self._ctx.new_page()
        try:
            await page.goto(url,wait_until="domcontentloaded",timeout=self.timeout)
            if _is_tl(url):
                try: await page.wait_for_selector("#venueZonesList,ul.list_zone_list",timeout=8000)
                except: pass
            else:
                for sel in PRICE_WAIT:
                    try: await page.wait_for_selector(sel,timeout=3500); break
                    except: pass
            await page.wait_for_timeout(2500)
            if _is_tl(url):
                rows=await page.evaluate(TL_ZONE_JS)
                if rows: log.info(f"[TL zones] {len(rows)} from {url}"); return rows
            rows=await page.evaluate(GENERIC_JS)
            if rows: return rows
            return extract_prices(strip_html(await page.content()),filter_bp)
        except Exception as e: log.warning(f"[T2] {url}: {e}"); return []
        finally: await page.close()

    async def cart(self,url):
        page=await self._ctx.new_page()
        try:
            log.info(f"[T3] {url}")
            await page.goto(url,wait_until="domcontentloaded",timeout=self.timeout)
            await page.wait_for_timeout(2000)
            if _is_tl(url):
                try: await page.wait_for_selector("#venueZonesList",timeout=8000)
                except: pass
                await page.wait_for_timeout(2000)
                rows=await page.evaluate(TL_ZONE_JS)
                if rows: log.info(f"[T3/TL] {len(rows)} zones"); return rows
            for sel in BUY_SELS:
                try:
                    btn=page.locator(sel).first
                    if await btn.is_visible(timeout=1500): await btn.click(); await page.wait_for_timeout(4000); break
                except: pass
            await page.wait_for_timeout(2000)
            rows=await page.evaluate(GENERIC_JS)
            if not rows: rows=extract_prices(strip_html(await page.content()))
            return rows
        except Exception as e: log.warning(f"[T3] {url}: {e}"); return []
        finally: await page.close()


async def _b_render(urls,fp=False):
    res={}
    async with BrowserSession() as s:
        for u in urls: res[u]=await s.render(u,fp)
    return res

async def _b_cart(urls):
    res={}
    async with BrowserSession() as s:
        for u in urls: res[u]=await s.cart(u)
    return res

def batch_render(urls,filter_boilerplate=False): return asyncio.run(_b_render(urls,filter_boilerplate))
def batch_cart(urls): return asyncio.run(_b_cart(urls))
def render_one(url,filter_boilerplate=False): return batch_render([url],filter_boilerplate).get(url,[])
def cart_one(url): return batch_cart([url]).get(url,[])
