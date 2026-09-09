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


# Define Flag Bitmasks
FLAG_NO_CATEGORY        = 1   # 00000001
FLAG_NO_SUBHEADINGS     = 2   # 00000010
FLAG_STRIKING_DISTANCE  = 4   # 00000100
FLAG_NO_POSITION_TECHNICAL_ISSUE         = 8   # 00001000
FLAG_THIN_CONTENT       = 16  # 00010000
FLAG_CRAWLED_NOT_INDEXED= 32  # 00100000
FLAG_NO_POSITION_SUBM_AND_INDEXED = 64 #01000000 
#position 8 10000000 EMPTY


FLAG_NAMES = {
    FLAG_NO_CATEGORY: "no_category",
    FLAG_NO_SUBHEADINGS: "no_subheadings",
    FLAG_STRIKING_DISTANCE: "striking_distance",
    FLAG_THIN_CONTENT: "thin_content",
    FLAG_CRAWLED_NOT_INDEXED: "crawled_not_indexed",
    FLAG_NO_POSITION_SUBM_AND_INDEXED: "submitted_and_indexed_no_traffic",
    FLAG_NO_POSITION_TECHNICAL_ISSUE: "technical_issue",
}
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
 
def step_classify_posts_bitmask(args):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT post_id, category, subheadings, gsc_position, body, coverage_state
        FROM posts
    """)
    posts = cursor.fetchall()

    print("Classifying posts in pipeline.db...")

    for post_id, category, subheadings, gsc_position, body, coverage_state in posts:
        flags = 0
        word_count = len((body or "").split())

        if not category or "uncategorized" in str(category).lower():
            flags |= FLAG_NO_CATEGORY
        if not subheadings or subheadings in ["[]", ""]:
            flags |= FLAG_NO_SUBHEADINGS
        if gsc_position and 8.0 <= gsc_position <= 20.0:
            flags |= FLAG_STRIKING_DISTANCE
        if word_count < 400:
            flags |= FLAG_THIN_CONTENT

        if coverage_state == 'Crawled - currently not indexed':
            flags |= FLAG_CRAWLED_NOT_INDEXED
        elif coverage_state == 'Submitted and indexed':
            flags |= FLAG_NO_POSITION_SUBM_AND_INDEXED
        elif coverage_state is not None:
            flags |= FLAG_NO_POSITION_TECHNICAL_ISSUE

        if flags & FLAG_NO_CATEGORY or flags & FLAG_NO_POSITION_TECHNICAL_ISSUE:
            status = "manual_fix_needed"
        elif flags == 0:
            status = "No_fix_needed"
        else:
            status = "ready_for_rewrite"

        # Human-readable summary, built from whichever flags actually fired
        triggered = [name for flag_val, name in FLAG_NAMES.items() if flags & flag_val]
        summary = ", ".join(triggered) if triggered else "none"
        if coverage_state:
            summary += f" (gsc: {coverage_state})"

        cursor.execute(
            "UPDATE posts SET flags = ?, status = ?, flag_summary = ?, updated_at = ? WHERE post_id = ?",
            (flags, status, summary, now, post_id)
        )

    conn.commit()
    conn.close()
    print("Classification complete.")
    
def step_search_for_not_indexed_posts(args):
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        SELECT post_id, url FROM posts
        WHERE gsc_position IS NULL OR gsc_position = 0
    """)
    no_position_posts = cursor.fetchall()

    if not no_position_posts:
        print("No unranked posts found in database.")
        conn.close()
        return

    results = gsc_adapter.inspect_urls_index_status(no_position_posts)

    for post_id, url, coverage_state in results:
        cursor.execute(
            "UPDATE posts SET coverage_state = ?, updated_at = ? WHERE post_id = ?",
            (coverage_state, now, post_id)
        )

    conn.commit()
    conn.close()
    print(f"Recorded coverage_state for {len(results)} inspected posts.")
 

        
def main():
    parser = argparse.ArgumentParser(description="Freya Art blog automation pipeline")
    parser.add_argument(
        "--step", 
        required=True, 
        choices=["fetch", "rank", "classify", "all", "rewrite", "review", "publish"]
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of posts (handy for testing)"
    )
    args = parser.parse_args()

    if args.step == "fetch":
        step_fetch(args)
    elif args.step == "rank":
        step_update_gsc(args)
    elif args.step == "classify":
        step_search_for_not_indexed_posts(args)
        step_classify_posts_bitmask(args)
        
    elif args.step == "all":
        print("--- Step 1: Fetching WordPress Posts ---")
        step_fetch(args)
        print("\n--- Step 2: Updating GSC Metrics ---")
        step_update_gsc(args)
        print("\n--- Step 3: classifying posts status ---")
        step_search_for_not_indexed_posts(args)
        step_classify_posts_bitmask(args)
        

    else:
        print(f"Step '{args.step}' isn't built yet -- that's the next piece to add.")
if __name__ == "__main__":
    main()
