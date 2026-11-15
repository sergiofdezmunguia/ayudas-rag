"""Fase 3: fuente BOC, vigencia temporal de preceptos y reordenación de documentos."""

from datetime import date
from pathlib import Path

import pytest

from ayudas_rag.answer import aviso_documento, format_answer, Citation
from ayudas_rag.http import CachedFetcher
from ayudas_rag.models import Document
from ayudas_rag.pipeline import Searcher, build_chunks, parse_mode, rerank_docs
from ayudas_rag.sources import boc_extractos as bc
from ayudas_rag.vigencia import ejercicios_acotados, vencido

FX = Path(__file__).parent / "fixtures"


# --- BOC ---

def test_boc_indice_anual_y_sumario():
    assert bc.boletines_del_anio((FX / "boc_anio.html").read_text()) == [
        (1, date(2099, 1, 2)), (2, date(2099, 1, 5)), (3, date(2099, 12, 31))]
    items = bc.extractos_en_boletin((FX / "boc_boletin.html").read_text())
    assert [i["path"] for i in items] == ["/boc/2099/002/11.html"]  # la resolución de justificación no es extracto
    assert items[0]["titulo"].startswith("EXTRACTO de la Orden")


def test_boc_parse_extracto_y_filtro():
    html = (FX / "boc_extracto.html").read_text()
    title, cve, paras = bc.parse_anuncio(html)
    assert cve == "BOC-A-2099-002-11"
    assert title.startswith("EXTRACTO de la Orden") and "Descargar" not in title and "páginas" not in title
    assert paras[0].startswith("BDNS") and "Pie" not in paras
    assert "ATENCION" not in " ".join(paras)
    doc = bc.parse_extracto(html, {"titulo": "x"}, "20990105", "https://www.gobiernodecanarias.org/boc/2099/002/11.html")
    assert doc.doc_id == "BOC-A-2099-002-11" and doc.meta["bdns"] == "999001"
    assert bc.url_de_cve(doc.doc_id) == doc.url
    assert doc.meta["boletin"] == "BOC"
    assert doc.meta["pdf_oficial"] == "https://sede.gobiernodecanarias.org/boc/boc-a-2099-002-11.pdf"
    assert doc.meta["beneficiarios"].startswith("Estudiantes universitarios")
    assert not doc.text.startswith("BDNS") and "máster" in doc.text
    assert bc.es_para_personas_fisicas(paras)


def test_boc_fetch_respeta_ventana_y_robots(tmp_path):
    f = CachedFetcher(tmp_path, offline=True)

    def put(url, name):
        f._store(f._path(url, "text/html"), (FX / name).read_bytes())

    put(bc.ANIO.format(y=2099), "boc_anio.html")
    put(bc.BOLETIN.format(y=2099, n=2), "boc_boletin.html")
    put(bc.BASE + "/boc/2099/002/11.html", "boc_extracto.html")
    f._store(f._path(bc.BASE + "/robots.txt", "text/plain"), b"User-agent: *\nDisallow: /*.pdf$\n")
    st = {}
    docs = bc.fetch_extractos(f, date(2099, 1, 10), 7, True, st)  # ventana 4-10 ene: solo el boletín 2
    assert [d.doc_id for d in docs] == ["BOC-A-2099-002-11"] and docs[0].fecha == "20990105"
    assert st["vistos"] == 1 and st["conservados"] == 1
    f._robots.clear()
    f._store(f._path(bc.BASE + "/robots.txt", "text/plain"), b"User-agent: *\nDisallow: /boc/2099/002/11.html\n")
    st = {}
    assert bc.fetch_extractos(f, date(2099, 1, 10), 7, True, st) == [] and st["vetados_robots"] == 1


def test_aviso_boc_y_fuente():
    d = Document("BOC-A-2099-002-11", "convocatoria", "x", "t", "t", "x",
                 "https://www.gobiernodecanarias.org/boc/2099/002/11.html", "Autonómico", "20990105",
                 {"boletin": "BOC", "pdf_oficial": "https://sede.gobiernodecanarias.org/boc/boc-a-2099-002-11.pdf"})
    assert "no oficial" in aviso_documento(d) and "boc-a-2099-002-11.pdf" in aviso_documento(d)
    c = Citation("t", "", "t", d.url, d.fecha, "convocatoria", ["x"], 1.0)
    txt = format_answer("q", [c])
    assert "extracto BDNS en BOC" in txt and "Boletín Oficial de Canarias" in txt


# --- vigencia ---

@pytest.mark.parametrize("heading,text,years", [
    ("Disposición adicional cuarta. Medidas extraordinarias por la situación inflacionaria.",
     "Uno. Mejora de la deducción.\n1. Durante el período impositivo 2022 y 2023, los contribuyentes podrán...", [2022, 2023]),
    ("Disposición adicional primera. Medidas por la erupción.",
     "Uno. Deducción.\nPara los períodos impositivos 2021 y 2022, los contribuyentes...", [2021, 2022]),
    ("Disposición transitoria sexta. Reducción por movilidad geográfica aplicable en 2015.", "Texto.", [2015]),
    ("Disposición transitoria trigésimo segunda. Límites en los ejercicios 2016 a 2019.", "Texto.",
     [2016, 2017, 2018, 2019]),
    ("Disposición transitoria primera. Prestaciones transitorias hasta el 31 de diciembre de 2022.", "Texto.", [2022]),
    # no acotan el final de la medida
    ("Disposición adicional sexta. Actividades excluidas a partir de 2016.", "Texto.", []),
    ("Disposición transitoria vigésima novena. Transmisiones anteriores a 1 de enero de 2017.", "Texto.", []),
    ("Disposición final quinta. Modificación de la Ley 6/2018 de Presupuestos para el año 2018.", "Texto.", []),
    ("Artículo 7. Deducción por gastos de estudios.", "1. Los contribuyentes podrán deducirse 1.500 euros desde 2015.", []),
])
def test_ejercicios_acotados(heading, text, years):
    assert ejercicios_acotados(heading, text) == years


def test_vencido_segun_anio_de_corte():
    h, t = "Disposición adicional. Medida aplicable en 2024.", "x"
    assert not vencido(h, t, 2025)  # la del ejercicio 2024 se declara en 2025
    assert vencido(h, t, 2026)
    assert not vencido("Artículo 1. Deducción por alquiler.", "x", 2026)


# --- reordenación ---

def test_parse_mode():
    assert parse_mode("dense") == ("dense", {})
    assert parse_mode("hybrid@0.3+v5+l0.5") == ("hybrid@0.3", {"v": 5.0, "l": 0.5})
    assert parse_mode("dense+vinf")[1]["v"] == float("inf")
    with pytest.raises(ValueError):
        parse_mode("dense+x1")


def test_rerank_vencidos_y_longitud():
    order = ["A", "B", "C", "D"]
    rank = {"A": 0, "B": 1, "C": 2, "D": 3}
    n = {"A": 27, "B": 1, "C": 1, "D": 1}
    assert rerank_docs(order, rank, {}, n, {"A"}) == order
    assert rerank_docs(order, rank, {"v": 2}, n, {"A"}) == ["B", "C", "A", "D"]
    assert rerank_docs(order, rank, {"v": float("inf")}, n, {"A"}) == ["B", "C", "D", "A"]
    assert rerank_docs(order, rank, {"l": 0.5}, n, set()) == ["B", "C", "D", "A"]  # 1×27^0.5 ≈ 5,2 > 4
    assert rerank_docs(order, rank, {"l": 0.1}, n, set()) == ["A", "B", "C", "D"]  # 27^0.1 ≈ 1,39 < 2


def test_searcher_marca_vencidos_y_los_baja():
    docs = [
        Document("N#da", "legislacion", "N", "Ley ficticia", "Disposición adicional. Deducción por alquiler aplicable en 2015.",
                 "Los jóvenes podrán deducir el alquiler de vivienda habitual.", "u1"),
        Document("N#a1", "legislacion", "N", "Ley ficticia", "Artículo 1. Deducción por alquiler de vivienda.",
                 "Los jóvenes podrán deducir el 30 por ciento del alquiler.", "u2"),
    ]
    s = Searcher(docs, build_chunks(docs), anio_corte=2026)
    assert s.vencidos == {"N#da"}
    q = "deducción alquiler aplicable jóvenes vivienda habitual"
    assert s.search_docs(q, "bm25")[0].doc.doc_id == "N#da"
    assert s.search_docs(q, "bm25+vinf")[0].doc.doc_id == "N#a1"
    assert Searcher(docs, build_chunks(docs)).vencidos == set()  # sin año de corte no se marca nada
