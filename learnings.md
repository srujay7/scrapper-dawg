# Learnings - Amazon PDP Brand Scraper

This file tracks errors encountered during scraping and lessons learned.

## Learning 1 - 2026-03-25
- **Issue:** Initial scraper only looked for "Top highlights" section, but many products use different section names like "Features & Specs", "Item details", etc.
- **Resolution:** Updated scraper to search multiple expander sections: Top highlights, Features & Specs, Item details, Product information. Also added fallback methods (Product Overview table, Detail table, Byline info).

## Learning 2 - 2026-03-25
- **Issue:** Sample ASINs (B0DGHRC1GQ, B0F1WYN3LM, B0DJXMHQXY) returned "Page Not Found" — these were placeholder/invalid ASINs.
- **Resolution:** Always test with real, verified ASINs. Added page title check to detect "Page Not Found" early.

## Learning 3 - 2026-03-25
- **Issue:** Need to check expanded content visibility (display !== 'none') when searching for Brand, since collapsed sections still exist in DOM.
- **Resolution:** Added CSS visibility check before searching expanded section content.

## Learning 4 - 2026-03-25
- **Issue:** Some ASINs return 503 Service Unavailable due to Amazon rate limiting.
- **Resolution:** Added retry logic (up to 2 retries with increasing backoff: 10s, 20s).

## Learning 5 - 2026-03-25
- **Issue:** Some products don't have Brand explicitly listed in any page section (or page fails to load).
- **Resolution:** Added Gemini AI fallback — extracts the product title and asks Gemini to infer the brand from it.

## Error - 2026-03-25 19:24:03
- **ASIN:** B0DJXMHQXY
- **Error:** Brand not found / page returned 503 then Page Not Found
- **Resolution:** ASIN appears to be invalid or removed from Amazon. Added 503 retry logic and Gemini fallback for future cases.

## Learning 6 - 2026-03-25 (Switched from Gemini to OpenAI)
- **Issue:** Gemini free tier quota was exhausted (429 RESOURCE_EXHAUSTED, limit: 0). Also `google.generativeai` SDK is deprecated.
- **Resolution:** Switched LLM fallback to OpenAI (gpt-4o-mini). Works reliably. If Gemini is needed in future, use the newer `google-genai` package.

## Learning 7 - 2026-03-25 (Brand extraction locations on Amazon PDP)
From scraping 15+ ASINs, here are the places where Brand can be found, in order of reliability:

### Priority 1: Expander Sections (most common)
- **Selector:** `a.a-expander-header` → click to expand → look inside `.a-expander-content`
- **Brand label:** `span.a-size-base.a-text-bold` or `span.a-text-bold` with text "Brand"
- **Brand value:** sibling `td` of the label's parent `td`, OR `th`/`td` pairs in table rows
- **Section names vary by product category:**
  - "Top highlights" — common on Beauty, Personal Care, Clothing
  - "Features & Specs" — common on Home, Kitchen, Electronics, Automotive
  - "Item details" — often present but may not contain Brand
  - "Product information" — less common
- **Example ASINs:** B0F3DPKTVT (Yankee Candle), B01MXEG3PY (Alpecin), B0CY6TTR3C (Sonos), B0D92ZNWK3 (STANLEY)

### Priority 2: Product Overview Table
- **Selector:** `#productOverview_feature_div` → `tr` rows → `td span.a-text-bold` with text "Brand" → next sibling `td`
- **When it works:** Products where expander sections exist but don't have Brand attribute inside
- **Example ASINs:** B004969RCI (ACDelco), B0DNL9SDYL (Charbroil), B0000DBIKI (HENCKELS), B0D79QCMF5 (Google)

### Priority 3: Product Details Technical Spec Table
- **Selectors:** `#productDetails_techSpec_section_1`, `#productDetails_detailBullets_sections1`, `.prodDetTable`
- **Structure:** `th` with "Brand" → sibling `td` has the value
- **Also check:** `#detailBullets_feature_div li` → nested `span span` pairs
- **When it works:** Products where Brand is not in expanders or overview, but exists in the detailed specs table further down the page
- **Example ASINs:** B0F4WK6YMH (adidas), B0DXR5HLJX (Samsonite), B0F38TC7RF (Electric Picks), B082RV1SVH (American Eagle Shirts Apparel)

### Priority 4: Byline Info
- **Selector:** `#bylineInfo` — the "Visit the X Store" or "Brand: X" link near the product title
- **Parsing:** Strip "Visit the " prefix and " Store" suffix, or "Brand: " prefix
- **Caveat:** Less precise — the store name may differ from the actual brand name
- **When it works:** Last HTML-based resort before LLM fallback

### Priority 5: OpenAI LLM Fallback
- **When it works:** Page loaded but no Brand found in any HTML section (rare), or page structure is unusual
- **Model:** gpt-4o-mini — fast and cheap
- **Input:** Product title extracted from `#productTitle` or page `<title>`

## Learning 8 - 2026-03-25 (Transient Amazon errors)
- **Issue:** Same ASIN can return different results on different attempts — B004969RCI returned blank "Amazon.com" page on first try, then loaded correctly on retry.
- **Resolution:** Transient failures are normal. The 503 retry logic helps, but blank pages without 503 status are harder to detect. Could add a check for `#productTitle` presence as a page-loaded validation.

## Error - 2026-03-25 19:57:13
- **ASIN:** B004969RCI
- **Error:** Brand not found — page loaded as blank "Amazon.com" with no product content
- **Resolution:** Transient Amazon issue. Succeeded on subsequent run (Brand: ACDelco via Product Overview table).

## Learning 9 - 2026-03-25 (56 ASIN batch run — 100% success rate)
- **Result:** All 56 ASINs returned a brand. 54/56 via expander_section, 2/56 via product_overview.
- **Observation:** For Grocery & Food category products, "Top highlights" is almost always present and contains Brand. This is the most reliable method for this category.

## Learning 10 - 2026-03-25 (Brand value may not match the expected brand)
- **Issue:** The "Brand" attribute on Amazon PDP is set by the seller, not Amazon. This means:
  - **Reseller brands:** B0B847SZ72 — product is "Voortman Sugar Free Wafers" but Brand shows "Circle of Drink" (a 3rd party reseller bundling it).
  - **Reseller brands:** B0CKFBGT9S — product is "Keebler Fudge Stripes" but Brand shows "KEZATAAK" (another reseller).
  - **Generic listings:** B0G1XFD9KB — Brand is literally "Generic" (no specific brand on this listing).
- **Takeaway:** The scraper correctly extracts what Amazon displays as the brand, but for data quality, consumers of this data should be aware that the brand value may reflect the seller, not the manufacturer. A post-processing step comparing brand to product title could flag mismatches.

## Learning 11 - 2026-03-25 (Performance at scale)
- **56 ASINs completed in ~12 minutes** with 7s page wait + 3-7s random delay between requests.
- **No 503 errors or CAPTCHAs** encountered in this batch — the anti-bot measures (headful mode, user-agent, random delays) are working well.
- **Bottleneck:** The 7s fixed wait per page is the main time cost. Could potentially reduce to 5s for faster runs, but 7s is safe.

## Learning 12 - 2026-03-25 (Unicode encoding fix)
- **Issue:** Python's `json.dump` defaults to `ensure_ascii=True`, which escapes non-ASCII characters like "ä" → "\u00e4". This caused "Schär" to appear as "Sch\u00e4r" in results.json.
- **Resolution:** Added `ensure_ascii=False` and `encoding="utf-8"` to all `json.dump` and file open calls. Always review output files for encoding issues before delivering final results.

## Learning 13 - 2026-03-25 (ASIN-to-brand cache)
- **Issue:** Re-scraping previously fetched ASINs wastes time and increases risk of being rate-limited.
- **Resolution:** Added `asin_brand_cache.json` — a persistent ASIN→brand lookup file. The scraper checks this cache before scraping. If a brand is already cached, it skips the scrape. New brands are added to the cache after each successful extraction. This also serves as a master reference file for all scraped brands.
