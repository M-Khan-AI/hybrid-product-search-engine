"""Pydantic models that define the shape of the API response."""
from pydantic import BaseModel


class ProductResult(BaseModel):
    id: int
    title: str
    description: str
    brand: str
    category: str
    price: float
    rating: float | None = None
    bm25_score: float      # normalised keyword score (0-1)
    vector_score: float    # normalised semantic score (0-1)
    score: float           # merged final score (0-1)


class SearchResponse(BaseModel):
    query: str
    count: int
    cached: bool
    results: list[ProductResult]