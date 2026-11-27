
"""Pydantic models that define the shape of the API response."""

from pydantic import BaseModel


class ProductResult(BaseModel):
    id: int
    title: str
    name: str
    image_url: str | None = None
    description: str
    brand: str
    category: str
    price: float
    rating: float | None = None
    bm25_score: float
    vector_score: float
    score: float


class SearchResponse(BaseModel):
    query: str
    count: int
    cached: bool
    results: list[ProductResult]
