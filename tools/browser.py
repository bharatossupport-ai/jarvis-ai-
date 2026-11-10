"""NOVA browser tools via Playwright, in a dedicated JARVIS browser profile."""
from security.policy import Risk
from storage.paths import sub
from .registry import tool

_settings = None


def configure(settings):
    global _settings
    _settings = settings


def _page_text(url, wait="domcontentloaded"):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        import sys
        kw = dict(headless=bool(_settings and _settings.get("browser_headless")))
        # Windows 11 always has Edge, so the installer doesn't need to ship Chromium
        channels = ["msedge", None] if sys.platform.startswith("win") else [None, "chrome"]
        last = None
        for ch in channels:
            try:
                ctx = p.chromium.launch_persistent_context(str(sub("browser_profile")),
                                                           **({"channel": ch} if ch else {}), **kw)
                break
            except Exception as e:
                last = e
        else:
            raise RuntimeError(f"No browser available: {last}")
        try:
            page = ctx.new_page()
            page.goto(url, wait_until=wait, timeout=45000)
            text = page.inner_text("body")
            links = page.eval_on_selector_all(
                "a[href^='http']", "els => els.slice(0,15).map(e => [e.innerText.trim(), e.href])")
            return text, links
        finally:
            ctx.close()


@tool("browser_search", "Search the web and return result titles and links", {"query": str}, Risk.EXTERNAL,
      preview=lambda a: f"Open browser and search: {a['query']}")
def browser_search(query):
    from urllib.parse import quote_plus
    text, links = _page_text(f"https://duckduckgo.com/html/?q={quote_plus(query)}")
    return [{"title": t[:120], "url": u} for t, u in links if t][:10]


@tool("browser_read", "Read the text of a web page", {"url": str}, Risk.EXTERNAL,
      preview=lambda a: f"Open and read: {a['url']}")
def browser_read(url):
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are allowed")
    text, _ = _page_text(url)
    return text[:15000]
