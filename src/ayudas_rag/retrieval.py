"""Recuperadores: BM25 (propio), denso (e5 multilingüe) e híbrido (RRF)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Protocol, Sequence

import numpy as np

from .text import tokenize


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[tuple[int, float]]: ...


class BM25:
    def __init__(self, texts: Sequence[str], k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lens = np.array([sum(d.values()) for d in self.docs], dtype=float)
        self.avgdl = float(self.lens.mean()) if len(self.lens) else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        # índice invertido para no recorrer todo el corpus
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for i, d in enumerate(self.docs):
            for t, tf in d.items():
                self.postings.setdefault(t, []).append((i, tf))

    def scores(self, query: str) -> np.ndarray:
        s = np.zeros(len(self.docs))
        for t in set(tokenize(query)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, tf in self.postings[t]:
                norm = self.k1 * (1 - self.b + self.b * self.lens[i] / self.avgdl)
                s[i] += idf * tf * (self.k1 + 1) / (tf + norm)
        return s

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        s = self.scores(query)
        idx = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in idx if s[i] > 0]


class Dense:
    """Similitud coseno sobre embeddings normalizados. `encode_query` es inyectable (tests sin modelo)."""

    def __init__(self, embeddings: np.ndarray, encode_query):
        self.emb = embeddings.astype(np.float32)
        self.encode_query = encode_query

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        q = self.encode_query(query)
        s = self.emb @ q
        idx = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in idx]


class Hybrid:
    """Reciprocal Rank Fusion (Cormack et al., 2009) de varios recuperadores."""

    def __init__(self, retrievers: Sequence[Retriever], k_rrf: int = 60, depth: int = 100,
                 weights: Sequence[float] | None = None):
        self.retrievers = list(retrievers)
        self.k_rrf, self.depth = k_rrf, depth
        self.weights = list(weights) if weights else [1.0] * len(self.retrievers)

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        fused: dict[int, float] = {}
        for r, w in zip(self.retrievers, self.weights):
            for rank, (i, _) in enumerate(r.search(query, self.depth)):
                fused[i] = fused.get(i, 0.0) + w / (self.k_rrf + rank + 1)
        return sorted(fused.items(), key=lambda x: -x[1])[:k]


class E5Encoder:
    """intfloat/multilingual-e5-small con prefijos «query: »/«passage: »."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", device: str | None = None,
                 threads: int = 4):
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(threads)
        self.model = SentenceTransformer(model_name, device=device or "cpu")

    def passages(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        return self.model.encode([f"passage: {t}" for t in texts], batch_size=batch_size,
                                 normalize_embeddings=True, show_progress_bar=True,
                                 convert_to_numpy=True)

    def query(self, text: str) -> np.ndarray:
        return self.model.encode([f"query: {text}"], normalize_embeddings=True, convert_to_numpy=True)[0]
