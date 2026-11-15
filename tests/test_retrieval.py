import math

import numpy as np
import pytest

from ayudas_rag.answer import answer, best_sentences, format_answer
from ayudas_rag.metrics import dedupe_to_docs, hit_at_k, mrr, ndcg_at_k, recall_at_k
from ayudas_rag.models import Document
from ayudas_rag.pipeline import Searcher, build_chunks
from ayudas_rag.retrieval import BM25, Hybrid
from ayudas_rag.text import chunk_document, fold, stem, tokenize

DOCS = [
    Document("N#a1", "legislacion", "N", "Ley ficticia", "Artículo 1. Deducción por alquiler de vivienda habitual.",
             "Los jóvenes menores de treinta y cinco años podrán deducir el 30 por ciento del alquiler.\nLímite de 1.000 euros.",
             "https://www.boe.es/buscar/act.php?id=N#a1", "Autonómico", "20240101"),
    Document("N#a2", "legislacion", "N", "Ley ficticia", "Artículo 2. Deducción por nacimiento de hijos.",
             "Por cada hijo nacido o adoptado se deducirán 600 euros.", "https://www.boe.es/buscar/act.php?id=N#a2"),
    Document("N#a3", "legislacion", "N", "Ley ficticia", "Artículo 3. Deducción por donativos.",
             "Las donaciones a fundaciones darán derecho a deducir el 15 por ciento.", "https://www.boe.es/buscar/act.php?id=N#a3"),
]


def test_fold_y_tokenize():
    assert fold("Señora ÁRBOL") == "señora arbol"
    toks = tokenize("Las deducciones por alquileres de viviendas")
    assert "las" not in toks
    assert stem("deducciones") == stem("deducción".replace("ó", "o"))
    assert stem("viviendas") == stem("vivienda")
    assert stem("alquileres") == stem("alquiler")


def test_chunking_respeta_tamano_y_conserva_texto():
    long_text = "\n".join(" ".join(f"p{j}w{i}" for i in range(80)) for j in range(6))
    d = Document("D", "legislacion", "D", "T", "H", long_text, "u")
    chunks = chunk_document(d, max_words=200, overlap_words=40)
    assert len(chunks) >= 3
    assert all(len(c.text.split()) <= 200 for c in chunks)
    allw = set(w for c in chunks for w in c.text.split())
    assert allw == set(long_text.split())
    assert chunks[0].chunk_id == "D::0" and chunks[0].doc_id == "D"


def test_chunking_parrafo_gigante():
    d = Document("D", "legislacion", "D", "T", "H", " ".join(f"w{i}" for i in range(1000)), "u")
    chunks = chunk_document(d, max_words=220, overlap_words=40)
    assert all(len(c.text.split()) <= 220 for c in chunks)
    assert "w999" in chunks[-1].text


def test_bm25_ordena_por_relevancia():
    bm = BM25([d.heading + " " + d.text for d in DOCS])
    top = bm.search("deducción alquiler vivienda jóvenes", 3)
    assert top[0][0] == 0
    assert bm.search("palabrainexistente", 3) == []


def test_bm25_idf_mayor_en_terminos_raros():
    bm = BM25(["alquiler deduccion", "hijo deduccion", "donativo deduccion"])
    assert bm.idf[stem("alquiler")] > bm.idf[stem("deduccion")]


class FakeRetriever:
    def __init__(self, ranking):
        self.ranking = ranking

    def search(self, q, k):
        return [(i, 1.0) for i in self.ranking[:k]]


def test_rrf_fusiona():
    h = Hybrid([FakeRetriever([0, 1, 2]), FakeRetriever([1, 3, 0])], k_rrf=60)
    res = h.search("x", 3)
    assert res[0][0] == 1  # 2.º y 1.º gana a 1.º y 3.º
    assert [i for i, _ in res] == [1, 0, 3]


def test_metricas():
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, {"b", "z"}, 2) == 0.5
    assert hit_at_k(ranked, {"c"}, 2) == 0.0
    assert mrr(ranked, {"c"}) == pytest.approx(1 / 3)
    assert mrr(ranked, {"z"}) == 0.0
    assert ndcg_at_k(["a"], {"a"}, 10) == 1.0
    assert ndcg_at_k(["x", "a"], {"a"}, 10) == pytest.approx(1 / math.log2(3))
    assert dedupe_to_docs(["a", "a", "b", "a", "c"]) == ["a", "b", "c"]


def _fake_encoder(chunks):
    """Embeddings 'bag of words' deterministas para probar la ruta densa sin modelo."""
    vocab = sorted({t for c in chunks for t in tokenize(c.index_text())})
    idx = {t: i for i, t in enumerate(vocab)}

    def enc(text):
        v = np.zeros(len(vocab), dtype=np.float32)
        for t in tokenize(text):
            if t in idx:
                v[idx[t]] += 1
        n = np.linalg.norm(v)
        return v / n if n else v

    return np.stack([enc(c.index_text()) for c in chunks]), enc


def test_searcher_modos_y_respuesta_extractiva():
    chunks = build_chunks(DOCS)
    emb, enc = _fake_encoder(chunks)
    s = Searcher(DOCS, chunks, emb, enc)
    for mode in ("bm25", "dense", "hybrid"):
        hits = s.search_docs("¿qué deducción hay por el alquiler para jóvenes?", mode, k=3)
        assert hits[0].doc.doc_id == "N#a1", mode
        assert len({h.doc.doc_id for h in hits}) == len(hits)
    cites = answer(s, "deducción por nacimiento de un hijo", "hybrid", n_docs=2)
    assert cites[0].url.endswith("#a2")
    assert "600 euros" in cites[0].sentences[0]
    txt = format_answer("q", cites)
    assert "no es asesoramiento" in txt and "https://www.boe.es" in txt


def test_searcher_sin_embeddings_solo_bm25():
    s = Searcher(DOCS, build_chunks(DOCS))
    assert s.search_docs("donativos fundaciones", "bm25")[0].doc.doc_id == "N#a3"
    with pytest.raises(ValueError):
        s.search_docs("x", "dense")


def test_best_sentences_orden_original():
    text = "Primera frase sin nada. El alquiler se deduce. Otra cosa. Límite del alquiler de 1.000 euros."
    bm = BM25([text])
    out = best_sentences("alquiler", text, bm.idf, n=2)
    assert out == ["El alquiler se deduce.", "Límite del alquiler de 1.000 euros."]
