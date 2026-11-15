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


MAIN_MODES = ("bm25", "dense", "hybrid")
GRID = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0)


def evaluate(searcher: Searcher, questions: list[dict], modes=MAIN_MODES) -> dict:
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


def tune_hybrid_weight(searcher: Searcher, questions: list[dict], base: str = "hybrid",
                       metric: str = "mrr") -> dict:
    """Elige el peso de BM25 en la fusión con las preguntas impares (dev) y lo mide en las pares (test)."""
    dev = [q for i, q in enumerate(questions) if i % 2 == 0]
    test = [q for i, q in enumerate(questions) if i % 2 == 1]
    modes = [f"{base}@{w}" for w in GRID]
    rdev = evaluate(searcher, dev, modes)
    best = max(modes, key=lambda m: rdev["modos"][m][metric])
    rtest = evaluate(searcher, test, ("bm25", "dense", f"{base}@1.0", best))
    return {"dev_n": len(dev), "test_n": len(test), "metric": metric,
            "dev": {m: rdev["modos"][m][metric] for m in modes}, "best": best,
            "test": rtest["modos"]}


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


def report_md(res: dict, questions: list[dict], corpus_stats: dict, tuning: dict | None = None,
              extra: dict | None = None) -> str:
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
    if tuning:
        L += ["", "## Ajuste del peso de BM25 en el híbrido (dev/test)", "",
              f"Peso elegido con las {tuning['dev_n']} preguntas impares (dev, {tuning['metric']}): "
              + ", ".join(f"{m.split('@')[1]}→{v:.3f}" for m, v in tuning["dev"].items())
              + f". Mejor: **{tuning['best']}**.", "",
              f"Resultados en las {tuning['test_n']} preguntas pares (test, no vistas al elegir el peso):", "",
              "| modo | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for m, agg in tuning["test"].items():
            L.append(f"| {m} | " + " | ".join(f"{agg[c]:.3f}" for c in cols) + " |")
    if extra:
        L += ["", "## Variante con glosario coloquial → jurídico (post hoc, optimista)", "",
              "El glosario (`text.GLOSARIO`) se escribió *después* de ver los fallos de BM25 en estas mismas "
              "preguntas, así que estas cifras sobrestiman lo que daría con preguntas nuevas.", "",
              "| modo | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for m, agg in extra["modos"].items():
            L.append(f"| {m} | " + " | ".join(f"{agg[c]:.3f}" for c in cols) + " |")
    L += ["", "## Por pregunta (MRR)", "", "| id | pregunta | " + " | ".join(modes) + " |",
          "|---|---|" + "---|" * len(modes)]
    byid = {m: {r["id"]: r for r in res["por_pregunta"][m]} for m in modes}
    for q in questions:
        L.append(f"| {q['id']} | {q['pregunta']} | " + " | ".join(f"{byid[m][q['id']]['mrr']:.2f}" for m in modes) + " |")
    return "\n".join(L) + "\n"
