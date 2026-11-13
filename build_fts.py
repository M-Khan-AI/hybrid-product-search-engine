"""Step 2: add an FTS5 virtual table so products can be searched by keyword (BM25)."""
import sqlite3

from config import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        DROP TABLE IF EXISTS products_fts;
        -- 'content=products' means FTS5 indexes the products table without copying the text
        CREATE VIRTUAL TABLE products_fts USING fts5(
            title, description, brand, category,
            content='products', content_rowid='id',
            tokenize='porter unicode61'   -- porter = stemming ("laptops" matches "laptop")
        );
        INSERT INTO products_fts(products_fts) VALUES('rebuild');
    """)
    conn.commit()

    # Quick self-test: bm25() returns lower (more negative) = better match
    rows = conn.execute("""
        SELECT p.title, bm25(products_fts) AS score
        FROM products_fts JOIN products p ON p.id = products_fts.rowid
        WHERE products_fts MATCH ? ORDER BY score LIMIT 3
    """, ("wireless noise cancellation",)).fetchall()
    conn.close()
    print("[build_fts] FTS5 table 'products_fts' created. Test query 'wireless noise cancellation':")
    for title, score in rows:
        print(f"    {score:8.3f}  {title}")


if __name__ == "__main__":
    main()