"""Shared test fixtures: a small temporary DB + FAISS index and a fake (offline) encoder."""
import hashlib
import re
import sqlite3

import faiss
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.search import SearchEngine
from build_fts import create_fts
from generate_products import build_products, create_products_table, insert_products

DIM = 64


class FakeEncoder:
    """Bag-of-words hashing embedding: texts sharing words get similar vectors.
    Lets tests run instantly without downloading the real sentence-transformers model."""

    def encode(self, text: str) -> np.ndarray:
        vec = np.zeros(DIM, dtype="float32")
        for word in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % DIM] += 1.0
        norm = np.linalg.norm(vec)
        if norm:
            vec /= norm
        return vec.reshape(1, -1)


@pytest.fixture(scope="session")
def engine_parts(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_products.db"
    conn = sqlite3.connect(db_path)
    create_products_table(conn)
    insert_products(conn, build_products())
    conn.commit()
    create_fts(conn)
    rows = conn.execute("SELECT id, title, description FROM products ORDER BY id").fetchall()
    conn.close()

    enc = FakeEncoder()
    vectors = np.vstack([enc.encode(f"{t}. {d}") for _, t, d in rows]).astype("float32")
    index = faiss.IndexIDMap(faiss.IndexFlatIP(DIM))
    index.add_with_ids(vectors, np.array([r[0] for r in rows], dtype="int64"))
    return db_path, index, enc


@pytest.fixture()
def engine(engine_parts):
    db_path, index, enc = engine_parts
    return SearchEngine(db_path, index, enc, cache_size=3)   # tiny cache so eviction is testable


@pytest.fixture()
def client(engine):
    with TestClient(create_app(engine)) as c:   # 'with' runs the lifespan startup
        yield c