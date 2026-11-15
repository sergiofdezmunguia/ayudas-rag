from ayudas_rag.evaluate import tune_hybrid_weight, bootstrap_diff, check_questions, evaluate, report_md
from ayudas_rag.pipeline import Searcher, build_chunks

from test_retrieval import DOCS, _fake_encoder


def test_evaluate_y_informe():
    chunks = build_chunks(DOCS)
    emb, enc = _fake_encoder(chunks)
    s = Searcher(DOCS, chunks, emb, enc)
    qs = [
        {"id": "q1", "pregunta": "deducción por alquiler jóvenes", "relevantes": ["N#a1"]},
        {"id": "q2", "pregunta": "donaciones a fundaciones", "relevantes": ["N#a3"]},
    ]
    assert check_questions(qs, set(s.docs)) == []
    assert check_questions([{"id": "x", "relevantes": ["nope"]}], set(s.docs)) == ["x: nope"]
    res = evaluate(s, qs)
    for m in ("bm25", "dense", "hybrid"):
        assert res["modos"][m]["mrr"] == 1.0
        assert res["modos"][m]["recall@1"] == 1.0
    md = report_md(res, qs, {"docs": 3, "chunks": 3, "legislacion": 3, "convocatorias": 0, "normas": 1})
    assert "| hybrid |" in md and "q2" in md
    from ayudas_rag.evaluate import subset_metrics

    extra = evaluate(s, qs, ("bm25x", "hybridx@1.0"))
    subsets = {"v0.1": (2, subset_metrics(res, {"q1", "q2"}))}
    md = report_md(res, qs, {"docs": 3, "chunks": 3, "legislacion": 3, "convocatorias": 0, "normas": 1},
                   extra=extra, subsets=subsets, groups={"v0.1": {"q1", "q2"}}, antes=res)
    assert "## Antes y después" in md and "### Glosario por subconjunto" in md
    assert "| v0.1 | 2 |" in md


def test_bootstrap_diff_sin_diferencias():
    a = [{"mrr": 0.5}, {"mrr": 1.0}]
    d, lo, hi = bootstrap_diff(a, a, "mrr", n=100)
    assert d == lo == hi == 0.0


def test_tune_hybrid_weight_separa_dev_y_test():
    chunks = build_chunks(DOCS)
    emb, enc = _fake_encoder(chunks)
    s = Searcher(DOCS, chunks, emb, enc)
    qs = [{"id": f"q{i}", "pregunta": p, "relevantes": [r]} for i, (p, r) in enumerate([
        ("alquiler jóvenes", "N#a1"), ("hijo nacido", "N#a2"), ("donaciones fundaciones", "N#a3"),
        ("deducir alquiler", "N#a1")])]
    t = tune_hybrid_weight(s, qs)
    assert t["dev_n"] == 2 and t["test_n"] == 2
    assert t["best"].startswith("hybrid@")
    assert set(t["test"]) == {"bm25", "dense", "hybrid@1.0", t["best"]}


def test_expand_query_y_modos_x():
    from ayudas_rag.text import expand_query

    assert "arrendamiento" in expand_query("deducción por alquiler")
    assert expand_query("nada que ampliar") == "nada que ampliar"
    chunks = build_chunks(DOCS)
    emb, enc = _fake_encoder(chunks)
    s = Searcher(DOCS, chunks, emb, enc)
    assert s.search_docs("me quiero desgravar por donar a una ONG", "bm25x")[0].doc.doc_id == "N#a3"
    assert s.search_docs("alquiler", "hybridx@0.5")


def test_subconjuntos_y_confusion_territorial():
    from ayudas_rag.evaluate import confusion_territorial, subset_metrics
    from ayudas_rag.models import Document

    docs = [Document("M#a1", "legislacion", "M", "Tributos Madrid", "Artículo 1. Deducción por alquiler.",
                     "Deducción por alquiler de vivienda habitual en Madrid.", "u", "Autonómico",
                     meta={"departamento": "Comunidad de Madrid"}),
            Document("C#a1", "legislacion", "C", "Tributos Canarias", "Artículo 1. Deducción por alquiler.",
                     "Deducción por alquiler de vivienda habitual en Canarias.", "u", "Autonómico",
                     meta={"departamento": "Comunidad Autónoma de Canarias"}),
            Document("E#a1", "legislacion", "E", "Ley estatal", "Artículo 1. Donativos.",
                     "Donativos a fundaciones.", "u", "Estatal")]
    chunks = build_chunks(docs)
    s = Searcher(docs, chunks)
    qs = [{"id": "c", "pregunta": "deducción alquiler vivienda Canarias", "relevantes": ["C#a1"]},
          {"id": "e", "pregunta": "donativos fundaciones", "relevantes": ["E#a1"]}]
    res = evaluate(s, qs, ("bm25",))
    sub = subset_metrics(res, {"c"})
    assert sub["bm25"]["mrr"] == 1.0
    conf = confusion_territorial(s, res, qs)
    assert conf["n_preguntas"] == 1 and conf["por_ccaa"] == {"Comunidad Autónoma de Canarias": 1}
    # top-5 de la pregunta de Canarias: C#a1, M#a1 (otra CCAA) y quizá E#a1 → al menos 1/3 de confusión
    top = res["por_pregunta"]["bm25"][0]["top5"]
    assert conf["modos"]["bm25"] == sum(d == "M#a1" for d in top) / len(top) > 0
