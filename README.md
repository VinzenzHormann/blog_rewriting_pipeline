# Blog Rewrite Pipeline

This pipeline automates post rewrites to make them consistent in language style, SEO quality, SEO conventions, length, and formatting.

The initial target for this project is the live website **freyaart.com**. Over time, FreyaArt has accumulated over 700 blog posts written with inconsistent tone, structure, and SEO quality. Rewriting all of them manually is impractical.

The project is actively developed to be extensible to other clients and platforms beyond WordPress.

## Planned Pipeline

* **Fetch** — Pull each post's URL, title, subheadings, body, meta description, and category from the live site. Starts with the WordPress REST API, with plans to incorporate custom scraping and support for third-party provider APIs (e.g., Blogspot, Shopify, Wix).
* **Normalize** — Convert all ingested data into a common internal schema independent of the source platform, ensuring downstream steps remain decoupled from platform-specific quirks.
* **Rank** — Rank the posts by SEO performance using Google Search Console data.
* **AI Rewrite** — Pass the title, subheadings, and body through a consistent prompt (backed by a written style guide and few-shot examples) to unify tone, SEO structure, and length. Images are validated separately (file size/format) and deferred to a later phase.
* **Human Review** — Store original and rewritten versions side by side in a local database, exposing a simple review UI to approve or reject changes before publishing.
* **Publish** — Push approved rewrites back to the live site via the platform's API.

## Architecture

The system is structured so that only isolated adapter components change per client or platform:

```text
core/                  -- Platform-agnostic logic (schema, AI rewrite, review UI)
adapters/              -- Platform adapters; converts raw site data to/from the common schema
adapters/seo_plugins/  -- Plugin adapters (RankMath, Yoast, etc.) to handle distinct meta description formats
run.py                 -- CLI entry point: `python run.py --step fetch|rewrite|review|publish`
```


Data is staged in a local SQLite database (`pipeline.db`) rather than a flat CSV file so that each post can track its state (`fetched` → `rewritten` → `reviewed` → `published`). This structure enables the pipeline to resume safely without reprocessing content from scratch after an interruption.

## Current Status

### Implemented
* **WordPress REST API Connector (`adapters/wp_freyaart.py`):** Fetches posts and categories from `wp-json/wp/v2` without requiring credentials for published content.
* **HTML to Markdown Conversion:** Transforms post bodies while keeping headings (`##`) and internal links inline in their original positions, avoiding hard-to-resync split fields.
* **Subheading Extraction Utility:** Extracts subheadings independently of the Markdown conversion for potential use in downstream validation.
* **RankMath Meta Description Extraction (`adapters/seo_plugins/rankmath.py`):** Retrieves meta descriptions via RankMath's `getHead` endpoint, bridging a gap in WordPress's core REST API.
* **SQLite Schema (`core/schema.py`):** Features per-post status tracking and separate columns for original and AI-rewritten content.

## Next Steps
* Begin implementing the ranking step of the pipeline.
