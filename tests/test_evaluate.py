from ayudas_rag.evaluate import bootstrap_diff, check_questions, evaluate, report_md
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
