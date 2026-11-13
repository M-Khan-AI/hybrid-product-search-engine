# Electronics Product Search: Data Model, Embeddings and FAISS Index

Task 1 of a hybrid product-search system. It builds a 200-item electronics catalog in SQLite,
adds BM25 keyword search (FTS5), generates sentence-transformer embeddings, stores them in a
local FAISS index, and documents the FAISS vs Qdrant decision.

## What gets built

| Output | Description |
|---|---|
| `products.db` | SQLite DB with a `products` table (200 rows) and a `products_fts` FTS5 virtual table |
| `products.faiss` | FAISS index (384-dim, cosine similarity) whose ids equal `products.id` |
| `docs/decision_log.pdf` | 1-page architecture decision log: FAISS on-device vs Qdrant free tier |

## Project structure

```
config.py              shared paths and settings
generate_products.py   creates products.db and 200 sample products
build_fts.py           creates the FTS5 table (BM25 keyword search)
build_embeddings.py    embeds title + description, builds and saves the FAISS index
rebuild_all.py         runs the three steps above in order
search_demo.py         optional: compare keyword vs semantic results
docs/decision_log.py   regenerates the PDF
docs/decision_log.pdf       the decision log
requirements.txt
```

## Setup and rebuild

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python rebuild_all.py
```

The first run downloads the `all-MiniLM-L6-v2` model (about 90 MB), so it needs internet once.
The data is generated with a fixed random seed, so every rebuild gives the same catalog.

## Try it

```bash
python search_demo.py "wireless headphones with noise cancellation"
python search_demo.py "something to listen to music while running"
```

Keyword search matches exact words; the semantic search also finds products with related meaning.

You can also query the database directly:

```sql
SELECT p.title, bm25(products_fts) AS score
FROM products_fts JOIN products p ON p.id = products_fts.rowid
WHERE products_fts MATCH 'gaming monitor' ORDER BY score LIMIT 5;
```

## Design choices

- **Embedding text** = `title. description`, so both brand/model and features influence meaning.
- **Normalized vectors + `IndexFlatIP`** = exact cosine similarity; fine for 200 items.
- **`IndexIDMap`** stores SQLite product ids inside FAISS, so no separate id lookup file is needed.
- **FTS5 external-content table** indexes `products` without duplicating text; Porter stemming is enabled.
- **Decision:** FAISS on-device, see `docs/decision_log.pdf` for the trade-offs.