"""
Playwright engine — optimised for speed.
Key improvement: browser launched ONCE, pages reused per event.
T3 cart navigation capped globally.
"""
import re, asyncio, logging
from typing import List, Dict, Optional
from scraper.parser import extract_prices, strip_html, FNAC_BOILERPLATE

log = logging.getLogger(__name__)
UA  = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

PRICE_WAIT_SELECTORS = [
    "[class*=price]","[class*=preco]","[class*=tarif]","[class*=ticket-type]",
    ".bt-widget",".seat-map","[data-price]","[data-amount]",
    "[class*=ticket]","[class*=bilhete]",
]
BUY_SELECTORS = [
    "a:has-text('Comprar')",  "button:has-text('Comprar')",
    "a:has-text('Buy')",      "button:has-text('Buy')",
    "a:has-text('Bilhetes')", "a:has-text('Tickets')",
    "[class*=buy]","[class*=comprar]","a[href*=compra]","a[href*=ticket]",
]


async def _dom_prices(page) -> List[Dict]:
    """Extract prices from live DOM via JS evaluation."""
    try:
        raw = await page.evaluate(r"""() => {
            const rows = [], seen = new Set();
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const t = node.textContent.trim();
                if (!t.includes('\u20ac')) continue;
                const m = t.match(/(\d+(?:[,.]\d+)?)\s*\u20ac/);
                if (!m) continue;
                const price = parseFloat(m[1].replace(',','.'));
                if (price < 1 || price > 2500) continue;
                if (price > 2020 && price < 2030) continue;
                let label = '';
                const el = node.parentElement;
                if (el) {
                    const anc = el.closest('[class*="sector"],[class*="categoria"],[class*="zona"],[class*="tarif"],[class*="row"],[class*="item"],[class*="type"]');
                    if (anc) label = anc.innerText.split('\n')[0].trim().substring(0,60);
                }
                const key = (label||'Geral')+'|'+price;
                if (seen.has(key)) continue;
                seen.add(key);
                rows.push({sector:label||'Geral', price:price, note:'', sold_out:false});
            }
            return rows;
        }""")
        return raw or []
    except Exception:
        return []


class BrowserSession:
    """
    Reusable browser session. Launch once, process many URLs.
    Usage:
        async with BrowserSession() as session:
            rows = await session.render(url)
            rows = await session.cart(url)
    """
    def __init__(self, timeout: int = 20000):
        self.timeout  = timeout
        self._pw      = None
        self._browser = None
        self._ctx     = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._pw      = await async_playwright().__aenter__()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox",
                  "--disable-dev-shm-usage","--disable-gpu","--single-process"]
        )
        self._ctx = await self._browser.new_context(
            user_agent=UA, viewport={"width":1280,"height":800},
            locale="pt-PT",
            extra_http_headers={"Accept-Language":"pt-PT,pt;q=0.9,en;q=0.8"}
        )
        return self

    async def __aexit__(self, *_):
        try:
            await self._browser.close()
            await self._pw.__aexit__(None, None, None)
        except Exception:
            pass

    async def render(self, url: str, filter_bp: bool = False) -> List[Dict]:
        """Tier 2 — render JS, extract prices."""
        page = await self._ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            # Try waiting for a price element
            for sel in PRICE_WAIT_SELECTORS:
                try:
                    await page.wait_for_selector(sel, timeout=4000)
                    break
                except Exception:
                    pass
            await page.wait_for_timeout(2500)
            # DOM extraction
            rows = await _dom_prices(page)
            # Fallback regex
            if not rows:
                rows = extract_prices(strip_html(await page.content()), filter_bp)
            return rows
        except Exception as e:
            log.warning(f"[T2] render failed {url}: {e}")
            return []
        finally:
            await page.close()

    async def cart(self, url: str) -> List[Dict]:
        """Tier 3 — click Buy, read ticket selection prices."""
        page = await self._ctx.new_page()
        try:
            log.info(f"[T3] {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            await page.wait_for_timeout(2000)
            # Click buy button
            for sel in BUY_SELECTORS:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        await page.wait_for_timeout(4000)
                        log.info(f"[T3] Clicked {sel}")
                        break
                except Exception:
                    pass
            await page.wait_for_timeout(2000)
            rows = await _dom_prices(page)
            if not rows:
                rows = extract_prices(strip_html(await page.content()))
            log.info(f"[T3] {len(rows)} prices from {url}")
            return rows
        except Exception as e:
            log.warning(f"[T3] cart failed {url}: {e}")
            return []
        finally:
            await page.close()


async def _batch_render(urls: List[str], filter_bp: bool = False) -> Dict[str, List[Dict]]:
    """Render multiple URLs with ONE browser instance."""
    results = {}
    async with BrowserSession() as session:
        for url in urls:
            results[url] = await session.render(url, filter_bp)
    return results


async def _batch_cart(urls: List[str]) -> Dict[str, List[Dict]]:
    """Cart-navigate multiple URLs with ONE browser instance."""
    results = {}
    async with BrowserSession() as session:
        for url in urls:
            results[url] = await session.cart(url)
    return results


# ── Public sync API ───────────────────────────────────────────

def batch_render(urls: List[str], filter_boilerplate: bool = False) -> Dict[str, List[Dict]]:
    """Tier 2 batch — ONE browser for all URLs. Much faster than per-event."""
    return asyncio.run(_batch_render(urls, filter_boilerplate))


def batch_cart(urls: List[str]) -> Dict[str, List[Dict]]:
    """Tier 3 batch — ONE browser for all cart navigations."""
    return asyncio.run(_batch_cart(urls))


def render_one(url: str, filter_boilerplate: bool = False) -> List[Dict]:
    """Single URL convenience wrapper."""
    return batch_render([url], filter_boilerplate).get(url, [])


def cart_one(url: str) -> List[Dict]:
    """Single URL cart wrapper."""
    return batch_cart([url]).get(url, [])
