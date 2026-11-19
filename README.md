A FastAPI service that takes a natural-language query and returns the best 10 products by
combining BM25 keyword search (SQLite FTS5) with FAISS semantic similarity.

## How a search works

```
query -> sanitise -> LRU cache hit? -> yes: return cached result
                          | no
                          v
        BM25 on FTS5 -> top 50 candidates
                          v
        FAISS cosine similarity for those candidates only
                          v
        normalise both scores to 0-1, merge: 0.4*BM25 + 0.6*vector
                          v
        sort, take top 10, load product rows, store in cache, return
```

If BM25 finds nothing (for example, a query using words that never appear in the catalog),
the service falls back to pure semantic search over the whole FAISS index.

## Run it

```bash
pip install -r requirements.txt
python build_project.py              # only needed once (creates products.db and products.faiss)
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API page.

```bash
curl "http://127.0.0.1:8000/search?q=cheap+laptop+for+students"
curl "http://127.0.0.1:8000/search?q=wireless+headphones&limit=5"
curl "http://127.0.0.1:8000/cache/stats"
```

| Route | Purpose |
|---|---|
| `GET /search?q=...&limit=10` | Hybrid search (limit 1-10) |
| `GET /health` | Liveness check |
| `GET /cache/stats` | LRU cache size, hits and misses |
| `DELETE /cache` | Clear the cache |

## Input sanitisation

- Unicode normalised, control characters removed, whitespace collapsed
- Rejected: empty, punctuation-only, non-text, or longer than 200 characters
- The query is split into plain word tokens and each is wrapped in quotes before it reaches FTS5,
  so operators such as `OR`, `NOT`, `NEAR`, `*` and `"` cannot change the query
- SQL values are always passed as bound parameters

## Cache

`cachetools.LRUCache` (128 entries) behind a lock. The key is the cleaned token list plus the limit,
so `"Gaming  MONITOR!"` and `"gaming monitor"` share one entry.

## Tests

```bash
python -m pytest -v
```

43 tests cover normal queries, ranking, limits, cache hits and LRU eviction, empty and over-long input,
punctuation-only input, SQL/FTS injection attempts, unicode and API status codes. Tests use a small fake
encoder, so they run in under a second and need no model download.

## Files added in Task 2

```
app/main.py        FastAPI app and routes
app/search.py      BM25 -> FAISS re-rank -> merge pipeline
app/sanitize.py    input cleaning and safe FTS5 query building
app/cache.py       thread-safe LRU cache with hit/miss counters
app/embedder.py    sentence-transformers wrapper
app/schemas.py     response models
tests/             conftest.py, test_sanitize.py, test_search_engine.py, test_api.py
pytest.ini
```