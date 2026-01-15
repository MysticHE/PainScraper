"""
SQLite database module for storing scraped posts and classifications.
"""
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from config import DATABASE_PATH


def get_content_hash(source: str, title: str, content: str) -> str:
    """Generate unique hash for deduplication."""
    combined = f"{source}:{title}:{content[:500]}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database with required tables and indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                url TEXT,
                author TEXT,
                post_timestamp TEXT,
                scraped_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Classifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER UNIQUE NOT NULL,
                is_pain_point BOOLEAN NOT NULL,
                category TEXT,
                audience TEXT,
                intensity INTEGER,
                automation_potential TEXT,
                suggested_solution TEXT,
                keywords TEXT,
                summary TEXT,
                raw_response TEXT,
                classified_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_scraped_at ON posts(scraped_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_content_hash ON posts(content_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classifications_category ON classifications(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classifications_intensity ON classifications(intensity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classifications_automation ON classifications(automation_potential)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classifications_is_pain_point ON classifications(is_pain_point)")

        conn.commit()
        print(f"Database initialized at: {DATABASE_PATH}")


def post_exists(content_hash: str) -> bool:
    """Check if post already exists (deduplication)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM posts WHERE content_hash = ?", (content_hash,))
        return cursor.fetchone() is not None


def insert_post(
    source: str,
    title: str,
    content: str,
    url: Optional[str] = None,
    author: Optional[str] = None,
    post_timestamp: Optional[str] = None,
) -> Optional[int]:
    """
    Insert a new post. Returns post_id or None if duplicate.
    """
    content_hash = get_content_hash(source, title, content)

    if post_exists(content_hash):
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (content_hash, source, title, content, url, author, post_timestamp, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_hash,
            source,
            title,
            content,
            url,
            author,
            post_timestamp,
            datetime.now().isoformat(),
        ))
        conn.commit()
        return cursor.lastrowid


def insert_classification(
    post_id: int,
    is_pain_point: bool,
    category: Optional[str] = None,
    audience: Optional[str] = None,
    intensity: Optional[int] = None,
    automation_potential: Optional[str] = None,
    suggested_solution: Optional[str] = None,
    keywords: Optional[list] = None,
    summary: Optional[str] = None,
    raw_response: Optional[str] = None,
) -> int:
    """Insert classification result for a post."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO classifications
            (post_id, is_pain_point, category, audience, intensity, automation_potential,
             suggested_solution, keywords, summary, raw_response, classified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id,
            is_pain_point,
            category,
            audience,
            intensity,
            automation_potential,
            suggested_solution,
            json.dumps(keywords) if keywords else None,
            summary,
            raw_response,
            datetime.now().isoformat(),
        ))
        conn.commit()
        return cursor.lastrowid


def get_unclassified_posts(limit: int = 100) -> list:
    """Get posts that haven't been classified yet."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.* FROM posts p
            LEFT JOIN classifications c ON p.id = c.post_id
            WHERE c.id IS NULL
            ORDER BY p.scraped_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_pain_points(
    category: Optional[str] = None,
    min_intensity: int = 1,
    audience: Optional[str] = None,
    automation_potential: Optional[str] = None,
    limit: int = 100,
) -> list:
    """Query pain points with filters."""
    with get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT p.*, c.category, c.audience, c.intensity, c.automation_potential,
                   c.suggested_solution, c.keywords, c.summary
            FROM posts p
            JOIN classifications c ON p.id = c.post_id
            WHERE c.is_pain_point = 1 AND c.intensity >= ?
        """
        params = [min_intensity]

        if category:
            query += " AND c.category = ?"
            params.append(category)

        if audience:
            query += " AND c.audience = ?"
            params.append(audience)

        if automation_potential:
            query += " AND c.automation_potential = ?"
            params.append(automation_potential)

        query += " ORDER BY c.intensity DESC, p.scraped_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get("keywords"):
                item["keywords"] = json.loads(item["keywords"])
            results.append(item)
        return results


def get_category_stats() -> dict:
    """Get pain point counts by category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count, AVG(intensity) as avg_intensity
            FROM classifications
            WHERE is_pain_point = 1 AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        return {row["category"]: {"count": row["count"], "avg_intensity": round(row["avg_intensity"], 1)}
                for row in cursor.fetchall()}


def get_automation_opportunities(min_intensity: int = 6, limit: int = 20) -> list:
    """Get high-potential automation opportunities."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.title, p.source, p.url, c.category, c.intensity,
                   c.automation_potential, c.suggested_solution, c.summary
            FROM posts p
            JOIN classifications c ON p.id = c.post_id
            WHERE c.is_pain_point = 1
              AND c.automation_potential = 'high'
              AND c.intensity >= ?
            ORDER BY c.intensity DESC
            LIMIT ?
        """, (min_intensity, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_recent_vs_previous(days_recent: int = 7, days_previous: int = 14) -> dict:
    """Compare recent pain points vs previous period for trending analysis."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Recent period
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM posts p
            JOIN classifications c ON p.id = c.post_id
            WHERE c.is_pain_point = 1
              AND date(p.scraped_at) >= date('now', ?)
            GROUP BY category
        """, (f"-{days_recent} days",))
        recent = {row["category"]: row["count"] for row in cursor.fetchall()}

        # Previous period
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM posts p
            JOIN classifications c ON p.id = c.post_id
            WHERE c.is_pain_point = 1
              AND date(p.scraped_at) >= date('now', ?)
              AND date(p.scraped_at) < date('now', ?)
            GROUP BY category
        """, (f"-{days_previous} days", f"-{days_recent} days"))
        previous = {row["category"]: row["count"] for row in cursor.fetchall()}

        return {"recent": recent, "previous": previous}


def get_total_stats() -> dict:
    """Get overall database statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM posts")
        total_posts = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM classifications WHERE is_pain_point = 1")
        total_pain_points = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(DISTINCT source) as total FROM posts")
        total_sources = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT source, COUNT(*) as count FROM posts GROUP BY source
        """)
        by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_posts": total_posts,
            "total_pain_points": total_pain_points,
            "total_sources": total_sources,
            "posts_by_source": by_source,
        }


if __name__ == "__main__":
    init_database()
    print("Database ready!")
