"""Step 3: embed title + description with sentence-transformers and save a FAISS index."""
import sqlite3

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import DB_PATH, EMBEDDING_DIM, INDEX_PATH, MODEL_NAME


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, title, description FROM products ORDER BY id").fetchall()
    conn.close()

    ids = np.array([r[0] for r in rows], dtype="int64")
    texts = [f"{title}. {description}" for _, title, description in rows]

    print(f"[build_embeddings] Loading model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(texts, batch_size=32, show_progress_bar=True,
                           convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    assert vectors.shape[1] == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM} dims, got {vectors.shape[1]}"

    # Vectors are normalized, so inner product == cosine similarity.
    # IndexIDMap lets us store the SQLite product id directly inside FAISS.
    index = faiss.IndexIDMap(faiss.IndexFlatIP(EMBEDDING_DIM))
    index.add_with_ids(vectors, ids)
    faiss.write_index(index, str(INDEX_PATH))
    print(f"[build_embeddings] Saved {index.ntotal} vectors to {INDEX_PATH.name}")

    # Verify the file loads without errors
    loaded = faiss.read_index(str(INDEX_PATH))
    print(f"[build_embeddings] Reload check OK: {loaded.ntotal} vectors, dim={loaded.d}")


if __name__ == "__main__":
    main()