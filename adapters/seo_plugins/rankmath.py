import requests
from bs4 import BeautifulSoup
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
def get_meta_description(post_url, base_url, session=None):
    """
    Fetch the meta description RankMath generated for a given post,
    using RankMath's getHead endpoint (requires Headless CMS Support
    enabled in RankMath's General Settings).
    """
    endpoint = f"{base_url}/wp-json/rankmath/v1/getHead"
    params = {"url": post_url}
    if session is None:
        print(f"[DEBUG] Session is None! Opening brand new TCP connection for {post_url}")
    
    requester = session if session is not None else requests
    
    try:
        resp = requester.get(endpoint, params=params, headers=headers, timeout=10)
        resp.raise_for_status()  # turns a bad status code (404, 500...) into an exception
        resp_content = resp.json().get("head", "")
        soup = BeautifulSoup(resp_content, "html.parser")
        meta_tag = soup.find("meta", attrs={"name": "description"})
        time.sleep(0.2) #A small delay between requests for rate-limiting        
        return meta_tag["content"] if meta_tag else None
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError) as e:
        print(f"  [warning] meta description fetch failed for {post_url}: {e}")
        return None
