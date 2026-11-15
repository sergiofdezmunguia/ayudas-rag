"""Métricas de recuperación con relevancia binaria a nivel de documento."""

from __future__ import annotations

import math
from typing import Sequence


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return float(bool(set(ranked[:k]) & relevant))


def mrr(ranked: Sequence[str], relevant: set[str], k: int = 10) -> float:
    for i, d in enumerate(ranked[:k]):
        if d in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 2) for i, d in enumerate(ranked[:k]) if d in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def dedupe_to_docs(chunk_doc_ids: Sequence[str]) -> list[str]:
    """Pasa de ranking de fragmentos a ranking de documentos (primera aparición)."""
    seen, out = set(), []
    for d in chunk_doc_ids:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out
