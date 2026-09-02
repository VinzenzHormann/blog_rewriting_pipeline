"""
CLI entry point for the pipeline.

Usage:
    python run.py --step fetch                # fetch all posts
    python run.py --step fetch --limit 10      # fetch just 10, for testing
"""
import argparse
from datetime import datetime, timezone

from core.schema import init_db, get_connection
from adapters import wp_freyaart, gsc_adapter
BASE_URL = "https://www.freyartt.com/"

def step_fetch(args):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    count = 0
    for post in wp_freyaart.fetch_posts(max_pages=args.limit):
        conn.execute(
            """
            INSERT INTO posts (post_id, url, title, subheadings, body,
                                meta_description, category, status, fetched_at, updated_at)
            VALUES (:post_id, :url, :title, :subheadings, :body,
                    :meta_description, :category, :status, :fetched_at, :updated_at)
            ON CONFLICT(post_id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                subheadings=excluded.subheadings,
                body=excluded.body,
                category=excluded.category,
                updated_at=excluded.updated_at
            """,
            {**post, "fetched_at": now, "updated_at": now},
        )
        count += 1
        print(f"  fetched [{post['post_id']}] {post['title'][:60]}")
    print(f"\nDone. {count} posts stored in pipeline.db")
    conn.commit()

def step_update_gsc(args):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    seo_data = gsc_adapter.fetch_page_seo_data(BASE_URL)   
    
    for url, data in seo_data.items():
        
        # Convert list of keywords to JSON string if returned as a list
        keywords = json.dumps(data['top_keywords']) if isinstance(data['top_keywords'], list) else data['top_keywords']
        conn.execute(
            "UPDATE posts SET gsc_position = ?, top_keywords = ? WHERE url = ?",
            (data['position'], keywords, url)
        )
        
    
    conn.commit()
    conn.close()
    print(f"\nDone. Updated posts with GSC positions and keywords.")
    
def step_search_for_not_indexed_posts(args):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT post_id, url 
        FROM posts 
        WHERE gsc_position IS NULL OR gsc_position = 0
    """)
    no_position_no_keyword_posts = cursor.fetchall()
    
    if not no_position_no_keyword_posts:
        print("No unranked posts found in database.")
        conn.close()
        return
    
    unindexed_status_results = gsc_adapter.inspect_urls_index_status(no_position_no_keyword_posts)
    
#    for url in unindexed_status_results["indexed"]:
#        conn.execute(
#            "UPDATE posts SET status = 'zero_traffic', updated_at = ? WHERE url = ?",
#            now, url)
#        )
    
    for url, coverage_state in unindexed_status_results["not_indexed"]:
        conn.execute(
            "UPDATE posts SET status = 'not_indexed', updated_at = ? WHERE url = ?",
            (now, url)
        )
    
    conn.commit()
    conn.close()
    
    print(f"\nSuccessfully updated database status for {len(unranked_posts)} posts:")
    print(f" - {len(results['indexed'])} marked as 'zero_traffic'")
    print(f" - {len(results['not_indexed'])} marked as 'not_indexed'")

def main():
    parser = argparse.ArgumentParser(description="Freya Art blog automation pipeline")
    parser.add_argument(
        "--step", 
        required=True, 
        choices=["fetch", "rank", "all", "inspect_not_listed", "rewrite", "review", "publish"]
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of posts (handy for testing)"
    )
    args = parser.parse_args()

    if args.step == "fetch":
        step_fetch(args)
    elif args.step == "rank":
        step_update_gsc(args)
    elif args.step == "inspect_not_listed":
        step_search_for_not_indexed_posts(args)
    elif args.step == "all":
        print("--- Step 1: Fetching WordPress Posts ---")
        step_fetch(args)
        print("\n--- Step 2: Updating GSC Metrics ---")
        step_update_gsc(args)
        print("\n--- Step 3: Chanking not indexed posts---")
        step_search_for_not_indexed_posts(args)
    else:
        print(f"Step '{args.step}' isn't built yet -- that's the next piece to add.")
if __name__ == "__main__":
    main()
