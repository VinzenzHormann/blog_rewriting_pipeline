import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from adapters.seo_plugins import rankmath

import time

BASE_URL = "https://www.freyartt.com/"
BASE_URL_WP = "https://www.freyartt.com/wp-json/wp/v2"
PER_PAGE = 20  # smaller pages = easier to resume if something breaks mid-fetch
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


#def _strip_html(html):
#    """Turn WP's rendered HTML into plain text."""
#    if not html:
#        return ""
#    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)

def _html_to_markdown(html):
    """Turn WP's rendered HTML into Markdown -- headings stay as ##, ###
    inline, and links stay as [text](url), both in their original position."""
    if not html:
        return ""
    return md(html, heading_style="ATX").strip()

def _extract_subheadings(html):
    """Pull all h2-h6 text out of the post body, joined into one field."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    headings = soup.find_all(["h2", "h3", "h4", "h5", "h6"])
    return " | ".join(h.get_text(strip=True) for h in headings)


def _fetch_category_lookup():
    """WP posts only carry category IDs -- fetch the id->name mapping once."""
    lookup = {}
    page = 1
    while True:
        resp = requests.get(f"{BASE_URL_WP}/categories", params={"per_page": 100, "page": page}, headers=headers)
        if resp.status_code != 200 or not resp.json():
            break
        for cat in resp.json():
            lookup[cat["id"]] = cat["name"]
        page += 1
    return lookup


def fetch_posts(max_pages=None):
    """
    Generator: yields one normalized dict per post, matching the schema:
    {post_id, url, title, h1, subheadings, body, meta_description, category, status}
    """
    with requests.Session() as session:
        #session.headers.update(headers)
        
        categories_lookup = _fetch_category_lookup()
        page = 1
        fetched = 0


        while True:
            start_time = time.perf_counter()
            
            params = {"page": page, "per_page": PER_PAGE, "status": "publish"}
            resp = session.get(f"{BASE_URL_WP}/posts", params=params, headers=headers)
            if resp.status_code != 200:
              print(f"Failed on page {page} with status code {resp.status_code}")
              break

            posts = resp.json()
            if not posts:
                break

            for post in posts:

                title = _html_to_markdown(post["title"]["rendered"])
                body_html = post["content"]["rendered"]
                category_names = ", ".join(
                    categories_lookup.get(cid, str(cid)) for cid in post.get("categories", [])
                )
                yield {
                    "post_id": post["id"],
                    "url": post["link"],
                    "title": title,
                    "subheadings": _extract_subheadings(body_html),
                    "body": _html_to_markdown(body_html),
                    # NOTE: meta description isn't a core WP field -- it's stored by
                    # whichever SEO plugin is active (Yoast/RankMath/etc). Check
                    # which plugin freyartt.com uses and extend this once confirmed.
                    "meta_description": rankmath.get_meta_description(post["link"], BASE_URL, session=session),
                    "category": category_names,
                    "status": "fetched",
                }

                fetched += 1
            # Read the total page count from WordPress headers
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            print(f"Fetched page {page} of {total_pages} ({len(posts)} posts)")

            if page >= total_pages:
              break

            page += 1
            
            end_time = time.perf_counter()
            loop_duration = end_time - start_time
    
            print(f"Iteration took {loop_duration:.4f} seconds.\n")
  
