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
