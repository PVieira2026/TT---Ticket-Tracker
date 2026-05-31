"""
Playwright engine — Tier 2 (JS rendering) + Tier 3 (cart navigation).
"""
import re, asyncio, logging
from typing import List, Dict, Optional
from scraper.parser import extract_prices, strip_html, FNAC_BOILERPLATE

log = logging.getLogger(__name__)
UA  = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BUY_SELECTORS = [
    "a:has-text('Comprar')",  "button:has-text('Comprar')",
    "a:has-text('Buy')",      "button:has-text('Buy')",
    "a:has-text('Bilhetes')", "button:has-text('Bilhetes')",
    "a:has-text('Tickets')",  "[class*=buy]", "[class*=comprar]",
    "a[href*=compra]",        "a[href*=ticket]", "a[href*=bilhete]",
]
WAIT_SELECTORS = [
    "[class*=price]","[class*=preco]","[class*=tarif]","[class*=ticket-type]",
    ".bt-widget",".blueticket",".seat-map","[data-price]","[data-amount]",
]


async def _launch():
    from playwright.async_api import async_playwright
    p   = await async_playwright().__aenter__()
    br  = await p.chromium.launch(
        headless=True,
        args=["--no-sandbox","--disable-setuid-sandbox",
              "--disable-dev-shm-usage","--disable-gpu","--single-process"]
    )
    ctx = await br.new_context(
        user_agent=UA, viewport={"width":1280,"height":800},
        locale="pt-PT",
        extra_http_headers={"Accept-Language":"pt-PT,pt;q=0.9,en;q=0.8"}
    )
    return p, br, ctx


async def _dom_prices(page) -> List[Dict]:
    """Extract prices from live DOM via JS."""
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
                if (price < 1 || price > 2500 || price > 2020 && price < 2030) continue;
                // Try to find label
                let label = '';
                const el = node.parentElement;
                if (el) {
                    const ancestor = el.closest('[class*="sector"],[class*="categoria"],[class*="zona"],[class*="tarif"],[class*="row"],[class*="item"]');
                    if (ancestor) label = ancestor.innerText.split('\n')[0].trim().substring(0,60);
                }
                const key = (label||'Geral')+'|'+price;
                if (seen.has(key)) continue;
                seen.add(key);
                rows.push({sector: label||'Geral', price: price, note: '', sold_out: false});
            }
            return rows;
        }""")
        return raw or []
    except Exception:
        return []


async def _render(url: str, timeout: int = 25000) -> str:
    """Load page with JS, return rendered HTML."""
    p, br, ctx = await _launch()
    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        # Try waiting for any price-like selector
        for sel in WAIT_SELECTORS:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                break
            except Exception:
                pass
        await page.wait_for_timeout(3000)
        return await page.content()
    except Exception as e:
        log.warning(f"[T2] render failed {url}: {e}")
        return ""
    finally:
        await br.close()
        await p.__aexit__(None, None, None)


async def _cart(url: str) -> List[Dict]:
    """Navigate to event → click Buy → read ticket prices."""
    p, br, ctx = await _launch()
    rows = []
    try:
        page = await ctx.new_page()
        log.info(f"[T3] Loading {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)

        # Click buy button
        for sel in BUY_SELECTORS:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    log.info(f"[T3] Clicked {sel}")
                    await page.wait_for_timeout(5000)
                    break
            except Exception:
                pass

        # Wait for ticket selection to appear
        for sel in WAIT_SELECTORS:
            try:
                await page.wait_for_selector(sel, timeout=6000)
                break
            except Exception:
                pass
        await page.wait_for_timeout(2000)

        # Try DOM extraction first
        rows = await _dom_prices(page)

        # Fallback: regex on rendered HTML
        if not rows:
            html  = await page.content()
            rows  = extract_prices(strip_html(html))

        log.info(f"[T3] {len(rows)} prices found at {url}")
    except Exception as e:
        log.warning(f"[T3] cart_nav failed {url}: {e}")
    finally:
        await br.close()
        await p.__aexit__(None, None, None)
    return rows


def render_and_extract(url: str, filter_boilerplate: bool = False) -> List[Dict]:
    """Tier 2 — sync wrapper."""
    html = asyncio.run(_render(url))
    if not html: return []
    rows = extract_prices(strip_html(html), filter_boilerplate)
    return rows


def cart_navigate(url: str) -> List[Dict]:
    """Tier 3 — sync wrapper."""
    return asyncio.run(_cart(url))
