"""Deterministic fake embeddings for offline Chroma tests.

This is intentionally not a production semantic embedding model. It gives
stable vectors without API keys so v0.1 tests and smoke runs can prove the RAG
plumbing before real provider choices are introduced.
"""

import math
import re
from hashlib import sha256


class HashEmbeddingFunction:
    """Small Chroma-compatible hash embedding function.

    Args:
        dimensions: Number of vector dimensions to produce.

    Outputs:
        Normalized float vectors derived from token hashes.
    """

    def __init__(self, dimensions: int = 64):
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.dimensions = dimensions

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Embed a batch of document strings."""

        return [self._embed(text) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        """Embed query strings using the same fake embedding path."""

        return self.__call__(input)

    @staticmethod
    def name() -> str:
        """Return Chroma adapter name.

        Chroma v1.x calls this method while checking collection embedding
        compatibility. Returning `default` avoids provider-specific config drift
        for this local fake adapter.
        """

        return "default"

    def get_config(self) -> dict:
        """Return serializable Chroma embedding configuration."""

        return {"dimensions": self.dimensions}

    @staticmethod
    def build_from_config(config: dict) -> "HashEmbeddingFunction":
        """Rebuild the fake embedding adapter from Chroma config."""

        return HashEmbeddingFunction(dimensions=int(config.get("dimensions", 64)))

    def is_legacy(self) -> bool:
        """Tell current Chroma versions this adapter supports config methods."""

        return False

    def default_space(self) -> str:
        """Use cosine distance as the default vector comparison space."""

        return "cosine"

    def supported_spaces(self) -> list[str]:
        """Return spaces Chroma can use with this adapter."""

        return ["cosine", "l2", "ip"]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"\w+", text.lower())

        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]
