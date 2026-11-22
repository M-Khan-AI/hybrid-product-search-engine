"""Shared settings used by every script in the project."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "products.db"
INDEX_PATH = BASE_DIR / "products.faiss"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, small and fast
EMBEDDING_DIM = 384
NUM_PRODUCTS = 200
RANDOM_SEED = 42

CANDIDATE_K = 50        # how many BM25 candidates to fetch before re-ranking
RESULT_LIMIT = 10       # how many products the API returns at most
BM25_WEIGHT = 0.4       # final score = 0.4 * keyword + 0.6 * semantic
VECTOR_WEIGHT = 0.6
CACHE_SIZE = 128        # how many recent queries the LRU cache remembers
MAX_QUERY_LENGTH = 200  # longer queries are rejected