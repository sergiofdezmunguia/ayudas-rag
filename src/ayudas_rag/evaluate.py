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


# Fase 3: reordenación de documentos contra el «imán» (ver pipeline.parse_mode). Del más simple al más complejo:
# a igualdad en dev gana el primero.
RERANK_GRID = ("", "+v3", "+v5", "+v10", "+vinf", "+l0.25", "+l0.5", "+l0.75", "+l1", "+vinf+l0.25", "+vinf+l0.5")


def split_dev_test(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Mismo protocolo que en fases anteriores: posiciones impares (1.ª, 3.ª...) = dev; pares = test."""
    return ([q for i, q in enumerate(questions) if i % 2 == 0], [q for i, q in enumerate(questions) if i % 2 == 1])


def con_vencido_top5(searcher: Searcher, res: dict) -> dict:
    """Por modo, proporción de preguntas con algún precepto vencido (vigencia.vencido) en el top-5."""
    return {m: mean(any(d in searcher.vencidos for d in r["top5"]) for r in per) if per else 0.0
            for m, per in res["por_pregunta"].items()}


def tune_rerank(searcher: Searcher, questions: list[dict], base: str = "dense", metric: str = "mrr",
                test_bases=("bm25", "dense", "hybrid@0.3")) -> dict:
    """Elige la reordenación con dev (métrica `metric` del modo `base`) y la mide UNA vez en test, junto a la
    versión sin reordenar de cada modo de `test_bases`."""
    dev, test = split_dev_test(questions)
    modes = [base + r for r in RERANK_GRID]
    rdev = evaluate(searcher, dev, modes)
    best = max(RERANK_GRID, key=lambda r: rdev["modos"][base + r][metric])
    tmodes = [m for b in test_bases for m in ((b, b + best) if best else (b,))]
    rtest = evaluate(searcher, test, tmodes)
    return {"dev_n": len(dev), "test_n": len(test), "metric": metric, "base": base, "best": best,
            "dev": {base + r: rdev["modos"][base + r] for r in RERANK_GRID},
            "dev_vencido_top5": con_vencido_top5(searcher, rdev),
            "test": rtest["modos"], "test_vencido_top5": con_vencido_top5(searcher, rtest),
            "test_por_pregunta": rtest["por_pregunta"]}


def subset_metrics(res: dict, ids: set[str]) -> dict:
    """Media de cada métrica por modo restringida a las preguntas `ids`."""
    out = {}
    for mode, per in res["por_pregunta"].items():
        rows = [r for r in per if r["id"] in ids]
        if rows:
            out[mode] = {m: mean(r[m] for r in rows) for m in rows[0] if m not in ("id", "top5")}
    return out


def territorio(doc) -> str:
    """Comunidad autónoma de un documento autonómico ("" si es estatal o convocatoria)."""
    if doc.source != "legislacion" or doc.ambito != "Autonómico":
        return ""
    return doc.meta.get("departamento", "") or "?"


def confusion_territorial(searcher: Searcher, res: dict, questions: list[dict], k: int = 5) -> dict:
    """Para las preguntas cuyos relevantes son todos de una misma CCAA, proporción de documentos del top-k que son
    normas autonómicas de *otra* CCAA (p. ej. una pregunta de Canarias que devuelve deducciones de Madrid)."""
    qterr = {}
    for q in questions:
        ts = {territorio(searcher.docs[r]) for r in q["relevantes"] if r in searcher.docs}
        if len(ts) == 1 and "" not in ts:
            qterr[q["id"]] = ts.pop()
    out = {"n_preguntas": len(qterr), "por_ccaa": {}, "modos": {}}
    for t in sorted(set(qterr.values())):
        out["por_ccaa"][t] = sum(v == t for v in qterr.values())
    for mode, per in res["por_pregunta"].items():
        tot = wrong = 0
        for r in per:
            if r["id"] not in qterr:
                continue
            for d in r["top5"][:k]:
                tot += 1
                t = territorio(searcher.docs[d])
                wrong += bool(t) and t != qterr[r["id"]]
        out["modos"][mode] = wrong / tot if tot else 0.0
    return out


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
              extra: dict | None = None, subsets: dict | None = None, confusion: dict | None = None,
              groups: dict | None = None, antes: dict | None = None, rerank: dict | None = None,
              iman: dict | None = None, fase: str = "fase 3", antes_f2: dict | None = None) -> str:
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
    if antes and subsets:
        base = next(iter(subsets.values()))[1]  # primer subconjunto = preguntas de v0.1
        L += ["", f"## Antes y después (v0.1 → {fase})", "",
              f"«v0.1» = corpus de v0.1 y sus {antes['n_preguntas']} preguntas (`results/metricas_v0.1.json`); "
              "«mismas preguntas» = esas preguntas sobre el corpus ampliado; «todas» = las "
              f"{res['n_preguntas']} preguntas sobre el corpus ampliado.", "",
              "| modo | MRR v0.1 | MRR mismas preguntas | MRR todas | recall@5 v0.1 | recall@5 mismas | recall@5 todas |",
              "|---|---|---|---|---|---|---|"]
        for m in modes:
            if m in antes["modos"] and m in base:
                a, b, c = antes["modos"][m], base[m], res["modos"][m]
                L.append(f"| {m} | {a['mrr']:.3f} | {b['mrr']:.3f} | {c['mrr']:.3f} | {a['recall@5']:.3f} | "
                         f"{b['recall@5']:.3f} | {c['recall@5']:.3f} |")
    if antes_f2:
        ids = {r["id"] for r in next(iter(antes_f2["por_pregunta"].values()))}
        same = subset_metrics(res, ids)
        L += ["", "## Fase 2 → fase 3 (sin reordenar)", "",
              f"«fase 2» = `results/metricas_fase2.json` ({antes_f2['n_preguntas']} preguntas, corpus de la fase 2); "
              "«mismas preguntas» = esas preguntas sobre el corpus de la fase 3 (con el BOC); «todas» = las "
              f"{res['n_preguntas']} preguntas.", "",
              "| modo | MRR fase 2 | MRR mismas | MRR todas | recall@5 fase 2 | recall@5 mismas | recall@5 todas |",
              "|---|---|---|---|---|---|---|"]
        for m in modes:
            if m in antes_f2["modos"] and m in same:
                a, b, c = antes_f2["modos"][m], same[m], res["modos"][m]
                L.append(f"| {m} | {a['mrr']:.3f} | {b['mrr']:.3f} | {c['mrr']:.3f} | {a['recall@5']:.3f} | "
                         f"{b['recall@5']:.3f} | {c['recall@5']:.3f} |")
    L += ["", "## Diferencias pareadas (bootstrap, IC 95 %)", ""]
    pairs = [("bm25", "hybrid"), ("dense", "hybrid"), ("bm25", "dense")]
    for a, b in pairs:
        if a in res["por_pregunta"] and b in res["por_pregunta"]:
            for metric in ("mrr", "recall@5"):
                d, lo, hi = bootstrap_diff(res["por_pregunta"][a], res["por_pregunta"][b], metric)
                L.append(f"- {b} − {a}, {metric}: {d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    if rerank:
        L += _rerank_md(rerank, iman)
    if tuning:
        L += ["", "## Ajuste del peso de BM25 en el híbrido (dev/test)", "",
              f"Peso elegido con las {tuning['dev_n']} preguntas impares (dev, {tuning['metric']}): "
              + ", ".join(f"{m.split('@')[1]}→{v:.3f}" for m, v in tuning["dev"].items())
              + f". Mejor: **{tuning['best']}**.", "",
              f"Resultados en las {tuning['test_n']} preguntas pares (test, no vistas al elegir el peso):", "",
              "| modo | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for m, agg in tuning["test"].items():
            L.append(f"| {m} | " + " | ".join(f"{agg[c]:.3f}" for c in cols) + " |")
    if subsets:
        L += ["", "## Por subconjunto de preguntas", ""]
        for name, (n, agg) in subsets.items():
            L += [f"**{name}** ({n} preguntas)", "", "| modo | " + " | ".join(cols) + " |",
                  "|---" * (len(cols) + 1) + "|"]
            for m, a in agg.items():
                L.append(f"| {m} | " + " | ".join(f"{a[c]:.3f}" for c in cols) + " |")
            L.append("")
    if confusion:
        L += ["", "## Confusión entre comunidades autónomas", "",
              f"Preguntas cuyos relevantes son todos normas de una sola CCAA: {confusion['n_preguntas']} ("
              + ", ".join(f"{t}: {n}" for t, n in confusion["por_ccaa"].items()) + "). Proporción de documentos "
              "del top-5 que son normas autonómicas de *otra* comunidad:", ""]
        L += [f"- {m}: {v:.3f}" for m, v in confusion["modos"].items()]
    if extra:
        L += ["", "## Variante con glosario coloquial → jurídico (post hoc, optimista)", "",
              "El glosario (`text.GLOSARIO`) se escribió *después* de ver los fallos de BM25 en estas mismas "
              "preguntas, así que estas cifras sobrestiman lo que daría con preguntas nuevas.", "",
              "| modo | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
        for m, agg in extra["modos"].items():
            L.append(f"| {m} | " + " | ".join(f"{agg[c]:.3f}" for c in cols) + " |")
    if extra and groups:
        both = {**res["por_pregunta"], **extra["por_pregunta"]}
        L += ["", "### Glosario por subconjunto (MRR)", "",
              "Las preguntas de las fases 2 y 3 se escribieron *después* del glosario y sin tocarlo, así que para ellas "
              "el glosario sí es una variante fuera de muestra.", "",
              "| subconjunto | n | " + " | ".join(both) + " | hybridx@1.0 − dense (IC 95 %) |",
              "|---|---|" + "---|" * (len(both) + 1)]
        for name, ids in groups.items():
            rows = {m: [r for r in per if r["id"] in ids] for m, per in both.items()}
            if not rows["dense"]:
                continue
            cells = " | ".join(f"{mean(r['mrr'] for r in rows[m]):.3f}" for m in both)
            diff = ""
            if "hybridx@1.0" in rows:
                d, lo, hi = bootstrap_diff(rows["dense"], rows["hybridx@1.0"], "mrr")
                diff = f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]"
            L.append(f"| {name} | {len(rows['dense'])} | {cells} | {diff} |")
    L += ["", "## Por pregunta (MRR)", "", "| id | pregunta | " + " | ".join(modes) + " |",
          "|---|---|" + "---|" * len(modes)]
    byid = {m: {r["id"]: r for r in res["por_pregunta"][m]} for m in modes}
    for q in questions:
        L.append(f"| {q['id']} | {q['pregunta']} | " + " | ".join(f"{byid[m][q['id']]['mrr']:.2f}" for m in modes) + " |")
    return "\n".join(L) + "\n"


def _rerank_md(rr: dict, iman: dict | None) -> list[str]:
    b, best = rr["base"], rr["best"]
    L = ["", "## Fase 3: preceptos vencidos que hacen de «imán» (decidido en dev, medido una vez en test)", "",
         "Candidatos (ver `pipeline.parse_mode`): «+v<n>» baja n puestos los preceptos cuya vigencia se limita a "
         "ejercicios ya pasados (`vigencia.py`); «+l<b>» penaliza documentos con muchos fragmentos (rango efectivo "
         "× n^b). Se elige con las preguntas dev y la métrica "
         f"{rr['metric']} del modo {b}; en test solo se mide la opción elegida.", "",
         f"**Dev** ({rr['dev_n']} preguntas):", "",
         "| candidato | mrr | recall@5 | ndcg@10 | preguntas con vencido en top-5 |", "|---|---|---|---|---|"]
    for m, a in rr["dev"].items():
        L.append(f"| {m} | {a['mrr']:.3f} | {a['recall@5']:.3f} | {a['ndcg@10']:.3f} | "
                 f"{rr['dev_vencido_top5'][m]:.3f} |")
    L += ["", f"Elegido: **{b + best if best else b + ' (sin reordenar)'}**.", "",
          f"**Test** ({rr['test_n']} preguntas, no vistas al elegir):", "",
          "| modo | recall@1 | recall@5 | mrr | ndcg@10 | preguntas con vencido en top-5 |", "|---|---|---|---|---|---|"]
    for m, a in rr["test"].items():
        L.append(f"| {m} | {a['recall@1']:.3f} | {a['recall@5']:.3f} | {a['mrr']:.3f} | {a['ndcg@10']:.3f} | "
                 f"{rr['test_vencido_top5'][m]:.3f} |")
    if best:
        L += ["", "Diferencia pareada en test (bootstrap, IC 95 %):", ""]
        tp = rr["test_por_pregunta"]
        for m in tp:
            if not m.endswith(best) and m + best in tp:
                for metric in ("mrr", "recall@5"):
                    d, lo, hi = bootstrap_diff(tp[m], tp[m + best], metric)
                    L.append(f"- {m + best} − {m}, {metric}: {d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    if iman:
        L += ["", f"El «imán» de la fase 2 ({iman['doc']}), en las {iman['n']} preguntas de Canarias de la fase 2 "
              "(dev y test juntos): preguntas que lo tienen en el top-5", ""]
        L += [f"- {m}: {v} de {iman['n']}" for m, v in iman["modos"].items()]
    return L
