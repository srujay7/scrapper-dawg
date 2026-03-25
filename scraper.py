import json
import random
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────────────────
ASINS = [
    "B0B4T65TYG", "B0F499FLML", "B0DHLN49LB", "B0CWMMGWQM", "B09FFTFLMZ",
    "B098KLGTLY", "B0C231FV5L", "B0CLWBCNZS", "B0DX22ZY1W", "B000A3I3PQ",
    "B012OV0QTW", "B0B2DB5QQM", "B077SX9BFW", "B0DNJRMK6L", "B07RL5Z85M",
    "B0DBHHR1SH", "B0DFWNQZVW", "B0D49CSNS7", "B0FT2C44M9", "B0DZCKT2MD",
    "B0FL6YNJN5", "B08YGXS9PZ", "B0BZJVFHHW", "B08419RPNS", "B01ETP2O6Y",
    "B0DX23HNCK", "B08PJ6R61W", "B0B41B9VPN", "B000JWFCGG", "B0F9ZKD914",
    "B0CKZ4ZWYG", "B07HQFXZCW", "B07M8NV1ZJ", "B0787P86ZZ", "B0FB8SWBQJ",
    "B0DS279YBH", "B0FFJS1CJ8", "B0DQ1GTVMQ", "B0FPCW85GM", "B09K5VR88R",
    "B0D2Q1NBBL", "B0F5VTHLKG", "B0D93X4QBG", "B0DZ2D5SL6", "B0D7ZL881N",
    "B0FX7SMCZV", "B0FYM6QT23", "B07RHXY7Y6", "B07YH25WWQ", "B01LI4INCS",
    "B0DHG9NLBS", "B094WBJG6W", "B0BRY7Q1FS", "B0CR18M23H", "B0DZWRB1G3",
    "B0G2XRDG6M", "B089S1LPWD", "B0CWNZWQ5L", "B0CBC69D6Y", "B07BJKY3JG",
    "B07YF5CR4V", "B07BKVF1MX", "B0GCF8X68K", "B09V28SJ2D", "B00JUM2VAQ",
    "B0DN63QCQK", "B0DSJG1LWQ", "B07L741RTN", "B0C76R6B42", "B08WWDSL4C",
    "B0CJ4GL4JN", "B0CYP43961", "B0D3LDBY1T",
]

BASE_URL = "https://www.amazon.com/dp/"
PAGE_LOAD_WAIT = 4  # fallback max wait if smart wait fails
SMART_WAIT_TIMEOUT = 10000  # ms — max time to wait for product title to appear
RESULTS_FILE = "results.json"
LEARNINGS_FILE = "learnings.md"
BRAND_CACHE_FILE = "asin_brand_cache.json"

# OpenAI API key
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"

# Expander sections that may contain brand info
BRAND_SECTIONS = ["Top highlights", "Features & Specs", "Item details", "Product information"]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]


def load_brand_cache() -> dict:
    """Load existing ASIN-to-brand cache from file."""
    try:
        with open(BRAND_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_brand_cache(cache: dict):
    """Save ASIN-to-brand cache to file."""
    with open(BRAND_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def log_error(asin: str, error: str, resolution: str = "Pending"):
    """Append an error entry to learnings.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## Error - {timestamp}\n"
        f"- **ASIN:** {asin}\n"
        f"- **Error:** {error}\n"
        f"- **Resolution:** {resolution}\n"
    )
    with open(LEARNINGS_FILE, "a") as f:
        f.write(entry)
    print(f"  [logged error to {LEARNINGS_FILE}]")


def ask_llm_for_brand(product_title: str) -> str | None:
    """Use OpenAI to infer the brand from a product title."""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Given an Amazon product title, reply with ONLY the brand name. Nothing else. If you cannot determine the brand, reply with UNKNOWN."},
                {"role": "user", "content": f"Product title: {product_title}"},
            ],
            max_tokens=50,
        )
        brand = response.choices[0].message.content.strip()
        if brand and brand.upper() != "UNKNOWN":
            return brand
        return None
    except Exception as e:
        print(f"  OpenAI API error: {e}")
        return None


def expand_and_extract_brand(page, section_names: list[str]) -> tuple[str | None, str | None]:
    """Click relevant expander sections and extract Brand value."""
    for section_name in section_names:
        clicked = page.evaluate(f"""
            (() => {{
                const headers = Array.from(document.querySelectorAll('a.a-expander-header'));
                const match = headers.find(el => el.textContent.trim().includes('{section_name}'));
                if (match) {{
                    match.click();
                    return '{section_name}';
                }}
                return null;
            }})()
        """)
        if clicked:
            print(f"  Expanded: {clicked}")

    time.sleep(1)

    brand = page.evaluate("""
        (() => {
            const contents = document.querySelectorAll('.a-expander-content');
            for (const content of contents) {
                const style = window.getComputedStyle(content);
                if (style.display === 'none' || style.visibility === 'hidden') continue;

                const boldSpans = content.querySelectorAll('span.a-size-base.a-text-bold, span.a-text-bold');
                for (const span of boldSpans) {
                    if (span.textContent.trim() === 'Brand') {
                        const td = span.closest('td');
                        if (td && td.nextElementSibling) {
                            const val = td.nextElementSibling.textContent.trim();
                            if (val) return val;
                        }
                        const parent = span.parentElement;
                        if (parent && parent.nextElementSibling) {
                            const val = parent.nextElementSibling.textContent.trim();
                            if (val) return val;
                        }
                    }
                }

                const rows = content.querySelectorAll('tr');
                for (const row of rows) {
                    const th = row.querySelector('th');
                    const td = row.querySelector('td');
                    if (th && td && th.textContent.trim() === 'Brand') {
                        return td.textContent.trim();
                    }
                }
            }
            return null;
        })()
    """)

    if brand:
        return brand, "expander_section"
    return None, None


def extract_brand_product_overview(page) -> str | None:
    """Fallback: try the product overview table."""
    return page.evaluate("""
        (() => {
            const overview = document.querySelector('#productOverview_feature_div');
            if (!overview) return null;
            const rows = overview.querySelectorAll('tr');
            for (const row of rows) {
                const label = row.querySelector('td span.a-text-bold');
                if (label && label.textContent.trim() === 'Brand') {
                    const valueCell = label.closest('td').nextElementSibling;
                    if (valueCell) return valueCell.textContent.trim();
                }
            }
            return null;
        })()
    """)


def extract_brand_detail_table(page) -> str | None:
    """Fallback: try the product details technical spec table."""
    return page.evaluate("""
        (() => {
            const tables = document.querySelectorAll(
                '#productDetails_techSpec_section_1, #productDetails_detailBullets_sections1, .prodDetTable'
            );
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const th = row.querySelector('th');
                    const td = row.querySelector('td');
                    if (th && td && th.textContent.trim().includes('Brand')) {
                        return td.textContent.trim();
                    }
                }
            }

            const bullets = document.querySelectorAll('#detailBullets_feature_div li');
            for (const li of bullets) {
                const spans = li.querySelectorAll('span span');
                if (spans.length >= 2 && spans[0].textContent.trim().includes('Brand')) {
                    return spans[1].textContent.trim();
                }
            }

            return null;
        })()
    """)


def extract_brand_byline(page) -> str | None:
    """Fallback: try the byline info (Visit the X Store)."""
    return page.evaluate("""
        (() => {
            const byline = document.querySelector('#bylineInfo');
            if (!byline) return null;
            let text = byline.textContent.trim();
            text = text.replace(/^Visit the\\s+/i, '').replace(/\\s+Store$/i, '');
            text = text.replace(/^Brand:\\s*/i, '');
            return text || null;
        })()
    """)


def get_product_title(page) -> str | None:
    """Extract the product title from the page."""
    el = page.query_selector("#productTitle")
    if el:
        return el.text_content().strip()
    # Fallback to page title (strip " : Amazon.com" suffix)
    title = page.title()
    if title and "Amazon.com" in title:
        return title.split(":")[0].strip() if ":" in title else title
    return None


def scrape_brand(page, asin: str) -> dict:
    """Scrape the brand for a single ASIN using multiple methods."""
    url = f"{BASE_URL}{asin}"
    result = {"asin": asin, "brand": None, "method": None, "error": None}

    print(f"\n{'='*60}")
    print(f"Scraping ASIN: {asin}")
    print(f"URL: {url}")

    try:
        page.goto(url, wait_until="domcontentloaded")

        # Smart wait: wait for product title element to appear instead of fixed delay
        try:
            page.wait_for_selector("#productTitle, #title, form[action='/errors/validateCaptcha']", timeout=SMART_WAIT_TIMEOUT)
            # Small buffer for remaining JS to settle
            time.sleep(1)
        except Exception:
            # Fallback to fixed wait if smart wait times out
            print(f"  Smart wait timed out, falling back to {PAGE_LOAD_WAIT}s fixed wait...")
            time.sleep(PAGE_LOAD_WAIT)

        title = page.title()
        print(f"  Page title: {title}")

        # Check for blank page (transient Amazon issue) — retry once
        if title == "Amazon.com" and not page.query_selector("#productTitle"):
            print("  Blank page detected — retrying...")
            time.sleep(3)
            page.reload(wait_until="domcontentloaded")
            try:
                page.wait_for_selector("#productTitle, #title", timeout=SMART_WAIT_TIMEOUT)
                time.sleep(1)
            except Exception:
                time.sleep(PAGE_LOAD_WAIT)
            title = page.title()
            print(f"  Page title after retry: {title}")

        # Check for CAPTCHA or blocked page
        if "Robot Check" in title or "Sorry" in title:
            error_msg = f"Blocked by Amazon (page title: {title})"
            result["error"] = error_msg
            print(f"  BLOCKED: {error_msg}")
            log_error(asin, error_msg)
            return result

        if "Page Not Found" in title:
            error_msg = "Product page not found (invalid ASIN?)"
            result["error"] = error_msg
            print(f"  ERROR: {error_msg}")
            log_error(asin, error_msg)
            return result

        # Handle 503 / Service Unavailable — retry up to 2 times
        retries = 0
        while ("503" in title or "Service Unavailable" in title) and retries < 2:
            retries += 1
            wait = 10 * retries
            print(f"  Got 503 — retrying in {wait}s (attempt {retries}/2)...")
            time.sleep(wait)
            page.reload(wait_until="domcontentloaded")
            try:
                page.wait_for_selector("#productTitle, #title", timeout=SMART_WAIT_TIMEOUT)
                time.sleep(1)
            except Exception:
                time.sleep(PAGE_LOAD_WAIT)
            title = page.title()
            print(f"  Page title after retry: {title}")

        if "503" in title or "Service Unavailable" in title:
            error_msg = f"Amazon returned 503 after {retries} retries"
            result["error"] = error_msg
            print(f"  ERROR: {error_msg}")
            log_error(asin, error_msg)
            return result

        # Method 1: Expand sections (Top highlights, Features & Specs, etc.)
        print(f"  Trying: Expander sections {BRAND_SECTIONS}...")
        brand, method = expand_and_extract_brand(page, BRAND_SECTIONS)
        if brand:
            result["brand"] = brand
            result["method"] = method
            print(f"  Brand found ({method}): {brand}")
            return result

        # Method 2: Product Overview table
        print("  Trying: Product Overview table...")
        brand = extract_brand_product_overview(page)
        if brand:
            result["brand"] = brand
            result["method"] = "product_overview"
            print(f"  Brand found (Product Overview): {brand}")
            return result

        # Method 3: Product Details technical spec table
        print("  Trying: Product Details table...")
        brand = extract_brand_detail_table(page)
        if brand:
            result["brand"] = brand
            result["method"] = "detail_table"
            print(f"  Brand found (Detail Table): {brand}")
            return result

        # Method 4: Byline info
        print("  Trying: Byline info...")
        brand = extract_brand_byline(page)
        if brand:
            result["brand"] = brand
            result["method"] = "byline"
            print(f"  Brand found (Byline): {brand}")
            return result

        # Method 5: Use OpenAI to infer brand from product title
        product_title = get_product_title(page)
        if product_title:
            print(f"  Trying: OpenAI LLM (product title: '{product_title[:60]}...')")
            brand = ask_llm_for_brand(product_title)
            if brand:
                result["brand"] = brand
                result["method"] = "openai_llm"
                print(f"  Brand found (OpenAI LLM): {brand}")
                return result

        # No brand found
        error_msg = "Brand not found using any method (including OpenAI)"
        result["error"] = error_msg
        print(f"  WARNING: {error_msg}")
        log_error(asin, error_msg)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        result["error"] = error_msg
        print(f"  ERROR: {error_msg}")
        log_error(asin, error_msg)

    return result


def main():
    if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        print("WARNING: Please set your OpenAI API key in scraper.py (OPENAI_API_KEY)")
        print("The scraper will still work but the OpenAI fallback won't be available.\n")

    print("Amazon PDP Brand Scraper")

    # Load existing cache
    brand_cache = load_brand_cache()
    cached_count = 0
    asins_to_scrape = []

    for asin in ASINS:
        if asin in brand_cache:
            cached_count += 1
        else:
            asins_to_scrape.append(asin)

    print(f"Total ASINs: {len(ASINS)} | Cached: {cached_count} | To scrape: {len(asins_to_scrape)}\n")

    results = []

    # Add cached results first
    for asin in ASINS:
        if asin in brand_cache:
            result = {"asin": asin, "brand": brand_cache[asin], "method": "cache", "error": None}
            results.append(result)
            print(f"  [cache] {asin} -> {brand_cache[asin]}")

    # Scrape only new ASINs
    if asins_to_scrape:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()

            for i, asin in enumerate(asins_to_scrape):
                if i > 0:
                    delay = random.uniform(3, 7)
                    print(f"\n  Waiting {delay:.1f}s before next request...")
                    time.sleep(delay)

                result = scrape_brand(page, asin)
                results.append(result)

                # Update cache if brand was found
                if result["brand"]:
                    brand_cache[result["asin"]] = result["brand"]
                    save_brand_cache(brand_cache)

            browser.close()

    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = r["brand"] if r["brand"] else f"NOT FOUND ({r.get('error', 'unknown')})"
        method = f" [{r['method']}]" if r["method"] else ""
        print(f"  {r['asin']} -> {status}{method}")

    # Save to JSON (with proper unicode)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {RESULTS_FILE}")
    print(f"Brand cache updated: {BRAND_CACHE_FILE} ({len(brand_cache)} entries)")


if __name__ == "__main__":
    main()
