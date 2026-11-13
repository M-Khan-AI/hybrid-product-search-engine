
"""
Hybrid Product Search Engine

Features:
1. Keyword Search using SQLite FTS5 / BM25
2. Semantic Search using FAISS
3. Hybrid Search using Reciprocal Rank Fusion (RRF)

Usage:
    python search_demo.py

Or:
    python search_demo.py "wireless headphones"
"""

import sqlite3
import sys

import faiss
from sentence_transformers import SentenceTransformer

from config import DB_PATH, INDEX_PATH, MODEL_NAME


# Number of results to retrieve
TOP_K = 5

# RRF constant used to combine search rankings
RRF_K = 60


# --------------------------------------------------
# 1. KEYWORD SEARCH
# --------------------------------------------------

def keyword_search(conn, query, k=TOP_K):

    # Prepare query for SQLite FTS5
    words = query.replace('"', " ").split()

    if not words:
        return []

    match = " OR ".join(f'"{word}"' for word in words)

    results = conn.execute("""
        SELECT p.id, p.title
        FROM products_fts
        JOIN products p
            ON p.id = products_fts.rowid
        WHERE products_fts MATCH ?
        ORDER BY bm25(products_fts)
        LIMIT ?
    """, (match, k)).fetchall()

    return results


# --------------------------------------------------
# 2. SEMANTIC SEARCH
# --------------------------------------------------

def semantic_search(conn, model, index, query, k=TOP_K):

    if index.ntotal == 0:
        return []

    # Convert query into a numerical embedding
    vec = model.encode(
        [query],
        normalize_embeddings=True
    ).astype("float32")

    # Search similar vectors in FAISS
    search_k = min(k, index.ntotal)

    scores, ids = index.search(vec, search_k)

    results = []

    for score, pid in zip(scores[0], ids[0]):

        # FAISS returns -1 when no valid result exists
        if pid < 0:
            continue

        row = conn.execute(
            "SELECT title FROM products WHERE id = ?",
            (int(pid),)
        ).fetchone()

        if row is not None:
            results.append((
                int(pid),
                row[0],
                float(score)
            ))

    return results


# --------------------------------------------------
# 3. HYBRID SEARCH (RECIPROCAL RANK FUSION)
# --------------------------------------------------

def hybrid_search(keyword_results, semantic_results):

    # Store combined scores by product ID
    combined_scores = {}

    # Add keyword search rankings
    for rank, (pid, title) in enumerate(keyword_results, start=1):

        combined_scores[pid] = {
            "title": title,
            "score": 0.0,
            "keyword_rank": rank,
            "semantic_rank": None
        }

        combined_scores[pid]["score"] += (
            1 / (RRF_K + rank)
        )

    # Add semantic search rankings
    for rank, (pid, title, similarity) in enumerate(
        semantic_results, start=1
    ):

        if pid not in combined_scores:

            combined_scores[pid] = {
                "title": title,
                "score": 0.0,
                "keyword_rank": None,
                "semantic_rank": rank
            }

        else:
            combined_scores[pid]["semantic_rank"] = rank

        combined_scores[pid]["score"] += (
            1 / (RRF_K + rank)
        )

    # Sort products by combined RRF score
    ranked_results = sorted(
        combined_scores.items(),
        key=lambda item: item[1]["score"],
        reverse=True
    )

    return ranked_results[:TOP_K]


# --------------------------------------------------
# 4. DISPLAY RESULTS
# --------------------------------------------------

def display_results(keyword_results, semantic_results, hybrid_results):

    print("\n" + "=" * 55)
    print("          HYBRID PRODUCT SEARCH RESULTS")
    print("=" * 55)

    # Keyword results
    print("\n1. KEYWORD SEARCH (FTS5 / BM25)")
    print("-" * 55)

    if keyword_results:
        for rank, (pid, title) in enumerate(keyword_results, start=1):
            print(f"{rank}. {title} [ID: {pid}]")
    else:
        print("No keyword matches found.")

    # Semantic results
    print("\n2. SEMANTIC SEARCH (FAISS)")
    print("-" * 55)

    if semantic_results:
        for rank, (pid, title, score) in enumerate(
            semantic_results, start=1
        ):
            print(
                f"{rank}. {title} "
                f"[ID: {pid}] [Similarity: {score:.4f}]"
            )
    else:
        print("No semantic results found.")

    # Hybrid results
    print("\n3. FINAL HYBRID SEARCH RESULTS")
    print("-" * 55)

    if hybrid_results:

        for rank, (pid, data) in enumerate(
            hybrid_results, start=1
        ):

            print(f"\n{rank}. {data['title']}")
            print(f"   Product ID: {pid}")
            print(f"   Combined Score: {data['score']:.6f}")

            print(
                f"   Keyword Rank: "
                f"{data['keyword_rank'] or 'Not found'}"
            )

            print(
                f"   Semantic Rank: "
                f"{data['semantic_rank'] or 'Not found'}"
            )

    else:
        print("No matching products found.")

    print("\n" + "=" * 55)


# --------------------------------------------------
# 5. RUN SEARCH
# --------------------------------------------------

def run_search(conn, model, index, query):

    if not query.strip():
        print("Please enter a valid product search query.")
        return

    print(f"\nSearching for: {query}")

    # Perform keyword search
    keyword_results = keyword_search(conn, query)

    # Perform semantic search
    semantic_results = semantic_search(
        conn, model, index, query
    )

    # Combine both search techniques
    hybrid_results = hybrid_search(
        keyword_results,
        semantic_results
    )

    # Display all results
    display_results(
        keyword_results,
        semantic_results,
        hybrid_results
    )


# --------------------------------------------------
# 6. MAIN FUNCTION
# --------------------------------------------------

def main():

    print("\nLoading product search engine...")

    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)

    # Load FAISS index
    index = faiss.read_index(str(INDEX_PATH))

    # Load embedding model
    model = SentenceTransformer(MODEL_NAME)

    print("\nProduct Search Engine is ready!")

    try:

        # If a query is supplied through the command line
        if len(sys.argv) > 1:

            query = " ".join(sys.argv[1:])

            run_search(conn, model, index, query)

        else:

            # Interactive search mode
            while True:

                query = input(
                    "\nEnter product name "
                    "(or type 'exit' to quit): "
                ).strip()

                if query.lower() in ("exit", "quit"):
                    print("\nExiting Product Search Engine.")
                    break

                run_search(conn, model, index, query)

    finally:
        conn.close()


# --------------------------------------------------
# 7. EXECUTION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()
