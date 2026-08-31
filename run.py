"""
CLI entry point for the pipeline.

Usage:
    python run.py --step fetch                # fetch all posts
    python run.py --step fetch --limit 10      # fetch just 10, for testing
"""
import argparse
import datetime

from core.schema import init_db, get_connection
from adapters import wp_freyaart


def step_fetch(args):
    init_db()
    conn = get_connection()
    now = datetime.datetime.utcnow().isoformat()

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

    conn.commit()
    conn.close()
    print(f"\nDone. {count} posts stored in pipeline.db")


def main():
    parser = argparse.ArgumentParser(description="Freya Art blog automation pipeline")
    parser.add_argument(
        "--step", required=True, choices=["fetch", "rewrite", "review", "publish"]
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of posts (handy for testing)"
    )
    args = parser.parse_args()

    if args.step == "fetch":
        step_fetch(args)
    else:
        print(f"Step '{args.step}' isn't built yet -- that's the next piece to add.")


if __name__ == "__main__":
    main()
