"""FastAPI application.  Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import faiss
from fastapi import FastAPI, HTTPException, Query
from app.sanitize import InvalidQueryError
from app.schemas import SearchResponse
from app.search import SearchEngine
from config import DB_PATH, INDEX_PATH, MAX_QUERY_LENGTH, RESULT_LIMIT


def build_default_engine() -> SearchEngine:
    """Loads the real DB, FAISS index and sentence-transformer model (done once at startup)."""
    from app.embedder import SentenceTransformerEncoder
    if not DB_PATH.exists() or not INDEX_PATH.exists():
        raise RuntimeError("products.db / products.faiss not found. Run: python build_project.py")
    return SearchEngine(DB_PATH, faiss.read_index(str(INDEX_PATH)), SentenceTransformerEncoder())


def create_app(engine: SearchEngine | None = None) -> FastAPI:
    """App factory. Tests pass in a small fake engine; production builds the real one."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or build_default_engine()
        yield

    app = FastAPI(title="Hybrid Product Search API", version="1.0.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/search", response_model=SearchResponse)
    def search(
        q: str = Query(..., min_length=1, max_length=MAX_QUERY_LENGTH, description="Natural-language query"),
        limit: int = Query(RESULT_LIMIT, ge=1, le=RESULT_LIMIT, description="Number of products to return"),
    ):
        try:
            return app.state.engine.search(q, limit)
        except InvalidQueryError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/cache/stats")
    def cache_stats():
        return app.state.engine.cache.stats()

    @app.delete("/cache")
    def clear_cache():
        app.state.engine.cache.clear()
        return {"status": "cleared"}

    @app.get("/")
    def home():
        return {"message": "Product Search Engine API"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)