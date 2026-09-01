import os
from google.oauth2 import service_account
from googleapiclient.discovery import build


import datetime
from dateutil.relativedelta import relativedelta

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CREDENTIALS_FILE = 'gsc_credentials.json'

now = datetime.datetime.now(datetime.UTC)
now_date = now.date()
three_months_ago = now - relativedelta(months=3)
three_months_ago_date = three_months_ago.date()

def fetch_page_seo_data(site_url, top_n=5):
    """
    Fetches per-page SEO data from Google Search Console: average position
    (from a page-level query, GSC's own aggregate) and top search keywords
    (from a page+query breakdown, grouped and ranked locally by impressions).

    Returns: {url: {'position': float, 'top_keywords': str}}
    """
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Missing credentials file: {CREDENTIALS_FILE} in project root.")

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    service = build('searchconsole', 'v1', credentials=creds)

    # --- Call 1: page-level positions (GSC's own aggregate, not a naive average) ---
    position_request = {
        'startDate': str(three_months_ago_date),
        'endDate': str(now_date),
        'dimensions': ['page'],
        'rowLimit': 25000,
    }
    position_response = service.searchanalytics().query(siteUrl=site_url, body=position_request).execute()

    positions = {}
    for row in position_response.get('rows', []):
        url = row['keys'][0]
        positions[url] = round(row['position'], 2)

    # --- Call 2: page+query breakdown, paginated, for keyword grouping ---
    all_rows = []
    start_row = 0
    page_size = 25000

    while True:
        keyword_request = {
            'startDate': str(three_months_ago_date),
            'endDate': str(now_date),
            'dimensions': ['page', 'query'],
            'rowLimit': page_size,
            'startRow': start_row,
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=keyword_request).execute()
        rows = response.get('rows', [])
        all_rows.extend(rows)

        if len(rows) < page_size:
            break
        start_row += page_size

    grouped = {}
    for row in all_rows:
        url = row['keys'][0]
        query = row['keys'][1]
        impressions = row['impressions']
        grouped.setdefault(url, []).append((query, impressions))

    keywords = {}
    for url, queries in grouped.items():
        top_queries = sorted(queries, key=lambda q: q[1], reverse=True)[:top_n]
        keywords[url] = ", ".join(query for query, impressions in top_queries)

    # --- Merge: one dict per URL, from either data source, missing pieces as None ---
    all_urls = set(positions) | set(keywords)
    results = {
        url: {
            'position': positions.get(url),
            'top_keywords': keywords.get(url),
        }
        for url in all_urls
    }

    print(f"length of dict: {len(results)}")
    return results