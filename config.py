"""Shared settings used by every script in the project."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "products.db"
INDEX_PATH = BASE_DIR / "products.faiss"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, small and fast
EMBEDDING_DIM = 384
NUM_PRODUCTS = 200
RANDOM_SEED = 42