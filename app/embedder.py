"""Wraps the sentence-transformers model so the rest of the app only needs encode(text)."""
import numpy as np

from config import MODEL_NAME


class SentenceTransformerEncoder:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer  # imported lazily (slow import)
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:
        """Returns a normalised float32 vector of shape (1, dim)."""
        vec = self.model.encode([text], normalize_embeddings=True, convert_to_numpy=True)
        return vec.astype("float32")