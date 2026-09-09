# Blog Rewrite Pipeline

This pipeline automates post rewrites to make them consistent in language style, SEO quality, SEO conventions, length, and formatting.

The initial target for this project is the live website **freyartt.com**. Over time, FreyaArt has accumulated over 700 blog posts written with inconsistent tone, structure, and SEO quality. Rewriting all of them manually is impractical.

The project is actively developed to be extensible to other clients and platforms beyond WordPress.

## Architecture & Core Principles
Data is staged in a local SQLite database (pipeline.db) rather than flat CSV files.

**Architectural Decision:** Pure API Ingestion over CSV Exports
During initial development, an unindexed CSV import from Google Search Console was evaluated. However, Search Console CSV exports contain historical redirects (e.g., legacy permalinks like /nedir/...), category hub archives, and stale URL noise.

To eliminate string mismatches and URL canonicalization bugs, pipeline.db was established as the single source of truth. All content is fetched directly via the WordPress REST API, and GSC performance/inspection metrics are mapped cleanly to live post IDs via pure API calls.

The system is structured so that only isolated adapter components change per client or platform:

```text
core/                  -- Platform-agnostic logic (schema, AI rewrite, review UI)
adapters/              -- Platform adapters; converts raw site data to/from the common schema
adapters/seo_plugins/  -- Plugin adapters (RankMath, Yoast, etc.) to handle distinct meta description formats
run.py                 -- CLI entry point: `python run.py --step fetch|rewrite|review|publish`
```

## Planned Pipeline

* **Fetch** — Pulls live content inventory (posts and pages) containing URL, title, body markdown, subheadings, and category structure.. Starts with the WordPress REST API, with plans to incorporate custom scraping and support for third-party provider APIs (e.g., Blogspot, Shopify, Wix).
* **Meta Description Enrichment** Retrieves RankMath/Yoast meta descriptions via dedicated API adapters.
* **GSC Performance Ingestion** Pulls average position, impressions, and clicks for each live URL via the Google Search Console API.
* **GSC Inspection API Sync** Executes targeted inspection queries for zero-impression/no-position posts to retrieve exact coverage states (Crawled - currently not indexed, Submitted and indexed, Server error (5xx), etc.).
* **Bitmask Classification** Evaluates content against structural, quality, and performance criteria, assigning an 8-bit integer bitmask (flags) and updating the post pipeline status.
* **Dynamic AI Rewrite** Evaluates bitmasks in step_rewrite to generate dynamic Gemini prompt instructions tailored specifically to each post's flagged issues.
* **Human Review** — Store original and rewritten versions side by side in a local database, exposing a simple review UI to approve or reject changes before publishing.
* **Publish** — Push approved rewrites back to the live site via the platform's API.

---

## 🔢 Bitmask Flags Specification

| Bit | Value | Constant Name | Category | Pipeline Routing |
| :---: | :---: | :--- | :--- | :--- |
| `00000001` | **1** | `FLAG_NO_CATEGORY` | WordPress Structure | `manual_fix_needed` |
| `00000010` | **2** | `FLAG_NO_SUBHEADINGS` | SEO Structure | `ready_for_rewrite` |
| `00000100` | **4** | `FLAG_STRIKING_DISTANCE` | Ranking Optimization | `ready_for_rewrite` |
| `00001000` | **8** | `FLAG_UNINDEXED` | Search Visibility | `ready_for_rewrite` |
| `00010000` | **16** | `FLAG_THIN_CONTENT` | Content Depth | `ready_for_rewrite` |
| `00100000` | **32** | `FLAG_CRAWLED_NOT_INDEXED` | GSC Indexation | `ready_for_rewrite` |
| `01000000` | **64** | `FLAG_NO_POSITION_TECHNICAL_ISSUE` | GSC Technical Block | `manual_fix_needed` |
| `10000000` | **128** | `FLAG_RESERVED` | Future Expansion | N/A |

---

## Current Status

### Implemented
* **WordPress REST API Connector (`adapters/wp_freyaart.py`):** Fetches posts and categories from `wp-json/wp/v2` without requiring credentials for published content.
* **HTML to Markdown Conversion:** Transforms post bodies while keeping headings (`##`) and internal links inline in their original positions, avoiding hard-to-resync split fields.
* **Subheading Extraction Utility:** Extracts subheadings independently of the Markdown conversion for potential use in downstream validation.
* **RankMath Meta Description Extraction (`adapters/seo_plugins/rankmath.py`):** Retrieves meta descriptions via RankMath's `getHead` endpoint, bridging a gap in WordPress's core REST API.
* **SQLite Schema (`core/schema.py`):** Features per-post status tracking and separate columns for original and AI-rewritten content.
* **Automated GSC URL Inspection:** Execute automated inspection calls for zero-position posts to distinguish Submitted and indexed pages from Crawled - currently not indexed.
* **Bitmask Classification:** Evaluate and assign bitmask flags (flags) to each post, appending a concatenated flag_summary text string to maintain readability in pipeline.db.
## Next Steps
* **GSC Performance Threshold Refinement:** Finalize GSC query filters to explicitly flag posts with positions > 8.0 having low engagement (clicks between 0–10 and impressions between 0–1000).
* **Bitmask Prompt Builder (step_rewrite):** Build the dynamic Gemini prompt generator that reads integer bitmasks and combines targeted system instructions:
