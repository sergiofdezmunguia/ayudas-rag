"""Evaluación de recuperación: BM25 vs denso vs híbrido."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from .metrics import hit_at_k, mrr, ndcg_at_k, recall_at_k
from .pipeline import Searcher

KS = (1, 3, 5, 10)


def load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def check_questions(questions: list[dict], doc_ids: set[str]) -> list[str]:
    """Devuelve los ids relevantes que no existen en el corpus (errores del conjunto de evaluación)."""
    return [f"{q['id']}: {r}" for q in questions for r in q["relevantes"] if r not in doc_ids]


def evaluate(searcher: Searcher, questions: list[dict], modes=("bm25", "dense", "hybrid")) -> dict:
    res = {"n_preguntas": len(questions), "modos": {}, "por_pregunta": {}}
    for mode in modes:
        per = []
        for q in questions:
            rel = set(q["relevantes"])
            ranked = [h.doc.doc_id for h in searcher.search_docs(q["pregunta"], mode, k=10)]
            row = {"id": q["id"], "top5": ranked[:5], "mrr": mrr(ranked, rel, 10)}
            for k in KS:
                row[f"recall@{k}"] = recall_at_k(ranked, rel, k)
                row[f"hit@{k}"] = hit_at_k(ranked, rel, k)
            row["ndcg@10"] = ndcg_at_k(ranked, rel, 10)
            per.append(row)
        agg = {m: mean(r[m] for r in per) for m in per[0] if m not in ("id", "top5")}
        res["modos"][mode] = agg
        res["por_pregunta"][mode] = per
    return res


def bootstrap_diff(per_a: list[dict], per_b: list[dict], metric: str, n: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Diferencia media (b - a) con IC 95 % por bootstrap pareado sobre preguntas."""
    import random

    rnd = random.Random(seed)
    diffs = [b[metric] - a[metric] for a, b in zip(per_a, per_b)]
    boots = []
    for _ in range(n):
        s = [diffs[rnd.randrange(len(diffs))] for _ in diffs]
        boots.append(mean(s))
    boots.sort()
    return mean(diffs), boots[int(0.025 * n)], boots[int(0.975 * n)]


def report_md(res: dict, questions: list[dict], corpus_stats: dict) -> str:
    modes = list(res["modos"])
    cols = ["recall@1", "recall@3", "recall@5", "recall@10", "hit@5", "mrr", "ndcg@10"]
    L = ["# Evaluación de recuperación", "",
         f"- Preguntas: {res['n_preguntas']}",
         f"- Corpus: {corpus_stats['docs']} documentos ({corpus_stats['legislacion']} preceptos de "
         f"{corpus_stats['normas']} normas + {corpus_stats['convocatorias']} extractos de convocatorias), "
         f"{corpus_stats['chunks']} fragmentos",
         "- Unidad evaluada: documento (artículo o extracto); el ranking de fragmentos se deduplica por documento.",
         "- MRR y nDCG con corte en 10; relevancia binaria.", "",
         "| modo | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for m in modes:
        L.append(f"| {m} | " + " | ".join(f"{res['modos'][m][c]:.3f}" for c in cols) + " |")
    L += ["", "## Diferencias pareadas (bootstrap, IC 95 %)", ""]
    pairs = [("bm25", "hybrid"), ("dense", "hybrid"), ("bm25", "dense")]
    for a, b in pairs:
        if a in res["por_pregunta"] and b in res["por_pregunta"]:
            for metric in ("mrr", "recall@5"):
                d, lo, hi = bootstrap_diff(res["por_pregunta"][a], res["por_pregunta"][b], metric)
                L.append(f"- {b} − {a}, {metric}: {d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    L += ["", "## Por pregunta (MRR)", "", "| id | pregunta | " + " | ".join(modes) + " |",
          "|---|---|" + "---|" * len(modes)]
    byid = {m: {r["id"]: r for r in res["por_pregunta"][m]} for m in modes}
    for q in questions:
        L.append(f"| {q['id']} | {q['pregunta']} | " + " | ".join(f"{byid[m][q['id']]['mrr']:.2f}" for m in modes) + " |")
    return "\n".join(L) + "\n"
