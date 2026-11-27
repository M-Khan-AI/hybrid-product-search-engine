
"""The hybrid search pipeline: BM25 candidates -> FAISS re-rank -> merge scores -> top 10."""

import sqlite3

import faiss
import numpy as np

from app.cache import QueryCache
from app.sanitize import build_fts_query, sanitize
from config import (
    BM25_WEIGHT,
    CACHE_SIZE,
    CANDIDATE_K,
    RESULT_LIMIT,
    VECTOR_WEIGHT,
)


def min_max(values: list[float]) -> list[float]:
    """Scale scores to 0-1. If all values are equal, everyone gets 1.0."""

    if not values:
        return []

    lo, hi = min(values), max(values)

    if hi - lo < 1e-9:
        return [1.0] * len(values)

    return [(v - lo) / (hi - lo) for v in values]


class SearchEngine:

    def __init__(self, db_path, index, encoder, cache_size: int = CACHE_SIZE):
        self.db_path = str(db_path)
        self.index = index
        self.encoder = encoder
        self.cache = QueryCache(cache_size)

    # ---- Step 1: Keyword search --------------------------------------------

    def bm25_candidates(
        self,
        tokens: list[str],
        k: int = CANDIDATE_K
    ) -> dict[int, float]:

        """Returns {product_id: bm25_score}. Higher = better."""

        match = build_fts_query(tokens)
        conn = sqlite3.connect(self.db_path)

        try:
            rows = conn.execute(
                "SELECT rowid, bm25(products_fts) FROM products_fts "
                "WHERE products_fts MATCH ? ORDER BY bm25(products_fts) LIMIT ?",
                (match, k),
            ).fetchall()

        finally:
            conn.close()

        return {int(pid): -float(score) for pid, score in rows}

    # ---- Step 2: Semantic search -------------------------------------------

    def vector_scores(
        self,
        query_vec: np.ndarray,
        candidate_ids: list[int] | None,
        k: int
    ) -> dict[int, float]:

        """Returns semantic similarity scores using FAISS."""

        if self.index.ntotal == 0:
            return {}

        if candidate_ids is not None:

            params = faiss.SearchParameters()

            params.sel = faiss.IDSelectorBatch(
                np.array(candidate_ids, dtype="int64")
            )

            scores, ids = self.index.search(
                query_vec,
                min(k, len(candidate_ids)),
                params=params
            )

        else:

            scores, ids = self.index.search(
                query_vec,
                min(k, self.index.ntotal)
            )

        return {
            int(i): float(s)
            for s, i in zip(scores[0], ids[0])
            if i != -1
        }

    # ---- Step 3: Hybrid score merging --------------------------------------

    def _hybrid(
        self,
        text: str,
        tokens: list[str],
        limit: int
    ) -> list[dict]:

        query_vec = self.encoder.encode(text)

        bm25 = self.bm25_candidates(tokens)

        if bm25:

            vec = self.vector_scores(
                query_vec,
                list(bm25),
                k=len(bm25)
            )

        else:

            # If no keyword matches, use semantic search.
            vec = self.vector_scores(
                query_vec,
                None,
                k=CANDIDATE_K
            )

        ids = list(dict.fromkeys(list(bm25) + list(vec)))

        if not ids:
            return []

        bm25_norm = (
            dict(zip(ids, min_max([bm25.get(i, 0.0) for i in ids])))
            if bm25
            else {i: 0.0 for i in ids}
        )

        vec_norm = dict(
            zip(ids, min_max([vec.get(i, 0.0) for i in ids]))
        )

        # Semantic search carries the full weight if BM25 has no matches.
        w_b, w_v = (
            (BM25_WEIGHT, VECTOR_WEIGHT)
            if bm25
            else (0.0, 1.0)
        )

        merged = {
            i: w_b * bm25_norm[i] + w_v * vec_norm[i]
            for i in ids
        }

        top = sorted(
            ids,
            key=lambda i: (-merged[i], i)
        )[:limit]

        return self._load_products(
            top,
            bm25_norm,
            vec_norm,
            merged
        )

    # ---- Step 4: Load product information ----------------------------------

    def _load_products(
        self,
        ids,
        bm25_norm,
        vec_norm,
        merged
    ) -> list[dict]:

        """Load product details, including name and image URL, from SQLite."""

        conn = sqlite3.connect(self.db_path)

        conn.row_factory = sqlite3.Row

        try:

            marks = ",".join("?" * len(ids))

            rows = {
                r["id"]: r
                for r in conn.execute(
                    f"""
                    SELECT
                        id,
                        title,
                        title AS name,
                        NULL AS image_url,
                        description,
                        brand,
                        category,
                        price,
                        rating
                    FROM products
                    WHERE id IN ({marks})
                    """,
                    ids
                )
            }

        finally:
            conn.close()

        results = []

        for pid in ids:

            if pid not in rows:
                continue

            r = rows[pid]

            results.append({

                "id": r["id"],
                "title": r["title"],
                "name": r["name"],
                "image_url": r["image_url"],

                "description": r["description"],
                "brand": r["brand"],
                "category": r["category"],

                "price": r["price"],
                "rating": r["rating"],

                "bm25_score": round(bm25_norm[pid], 4),
                "vector_score": round(vec_norm[pid], 4),
                "score": round(merged[pid], 4),

            })

        return results

    # ---- Step 5: Public search method with LRU cache -----------------------

    def search(
        self,
        raw_query: str,
        limit: int = RESULT_LIMIT
    ) -> dict:

        """Execute hybrid search and return product results."""

        text, tokens = sanitize(raw_query)

        limit = max(
            1,
            min(int(limit), RESULT_LIMIT)
        )

        key = (" ".join(tokens), limit)

        # Check cache first.
        cached = self.cache.get(key)

        if cached is not None:
            return {**cached, "cached": True}

        # Execute hybrid search.
        results = self._hybrid(
            text,
            tokens,
            limit
        )

        response = {
            "query": text,
            "count": len(results),
            "cached": False,
            "results": results
        }

        # Store results in cache.
        self.cache.set(key, response)

        return response
