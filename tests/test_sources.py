import json
from pathlib import Path

import pytest

from ayudas_rag.http import BlockedURLError, CachedFetcher, NotFoundError
from ayudas_rag.sources import boe_extractos as bx
from ayudas_rag.sources import boe_legislacion as bl

FX = Path(__file__).parent / "fixtures"


def test_parse_texto_elige_version_vigente_y_salta_derogados():
    docs = bl.parse_texto((FX / "texto_norma.xml").read_bytes(), "BOE-A-2099-1", "Ley ficticia", "Estatal",
                          cutoff="20261115")
    ids = [d.doc_id for d in docs]
    assert ids == ["BOE-A-2099-1#a1", "BOE-A-2099-1#a3", "BOE-A-2099-1#da1"]  # a2 derogado, a4 futuro
    assert docs[0].meta["ruta"] == "TÍTULO I"
    assert docs[1].meta["ruta"] == "TÍTULO I > CAPÍTULO I Familias"
    assert docs[2].meta["ruta"] == ""
    a1 = docs[0]
    assert a1.heading == "Artículo 1. Deducción ficticia por alquiler."
    assert "30 por ciento" in a1.text and "alquiler de su vivienda" in a1.text  # texto de <em> incluido
    assert "futura" not in a1.text
    assert "Se modifica" not in a1.text
    assert a1.fecha == "20240101"
    assert a1.url == "https://www.boe.es/buscar/act.php?id=BOE-A-2099-1#a1"


def test_parse_texto_con_corte_antiguo():
    docs = bl.parse_texto((FX / "texto_norma.xml").read_bytes(), "N", "T", cutoff="20210101")
    assert "10 por ciento" in docs[0].text


def test_extractos_en_sumario_solo_5b_y_convocatorias():
    items = bx.extractos_en_sumario(json.loads((FX / "sumario.json").read_text()))
    assert [i["identificador"] for i in items] == ["BOE-B-2099-10", "BOE-B-2099-12"]


def test_parse_extracto_y_filtro_personas_fisicas():
    html = (FX / "extracto_pf.html").read_text()
    title, paras = bx.parse_txt(html)
    assert title.startswith("Extracto de la Resolución")
    assert "Pie de página" not in paras
    assert bx.beneficiarios(paras) == "Personas físicas de entre 18 y 35 años residentes en España."
    assert bx.es_para_personas_fisicas(paras)
    doc = bx.parse_extracto(html, {"identificador": "BOE-B-2099-10", "titulo": "x"}, "20991231")
    assert doc.meta["bdns"] == "123456"
    assert not doc.text.startswith("BDNS")
    assert doc.url.endswith("txt.php?id=BOE-B-2099-10")


def test_filtro_descarta_entidades_aunque_el_objeto_mencione_jovenes():
    _, paras = bx.parse_txt((FX / "extracto_entidades.html").read_text())
    assert not bx.es_para_personas_fisicas(paras)


def test_fetcher_bloquea_api_bdns_y_usa_cache(tmp_path):
    f = CachedFetcher(tmp_path, offline=True)
    with pytest.raises(BlockedURLError):
        f.get("https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda")
    url = "https://www.boe.es/ejemplo"
    p = f._path(url, "application/json")
    p.parent.mkdir(parents=True)
    p.write_bytes(b"hola")
    assert f.get(url) == b"hola"
    with pytest.raises(FileNotFoundError):
        f.get("https://www.boe.es/otra")
    miss = f._path("https://www.boe.es/404", "application/json").with_suffix(".404")
    miss.parent.mkdir(parents=True, exist_ok=True)
    miss.touch()
    with pytest.raises(NotFoundError):
        f.get("https://www.boe.es/404")
    assert f.n_requests == 0


def test_fetch_extractos_offline(tmp_path, monkeypatch):
    from datetime import date

    f = CachedFetcher(tmp_path, offline=True)

    def put(url, accept, data):
        p = f._path(url, accept)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    put(bx.SUMARIO.format(d="20991231"), "application/json", (FX / "sumario.json").read_bytes())
    put(bx.TXT.format(id="BOE-B-2099-10"), "text/html", (FX / "extracto_pf.html").read_bytes())
    put(bx.TXT.format(id="BOE-B-2099-12"), "text/html", (FX / "extracto_entidades.html").read_bytes())
    miss = f._path(bx.SUMARIO.format(d="20991230"), "application/json").with_suffix(".404")
    miss.parent.mkdir(parents=True, exist_ok=True)
    miss.touch()
    docs = bx.fetch_extractos(f, date(2099, 12, 31), days=2)
    assert [d.doc_id for d in docs] == ["BOE-B-2099-10"]


def test_beneficiarios_en_linea_y_titulos_alternativos():
    paras = ["Primero. Beneficiarios: Españoles admitidos en el máster.", "Segundo. Objeto: becas."]
    assert bx.beneficiarios(paras) == "Españoles admitidos en el máster."
    assert bx.es_para_personas_fisicas(paras)
    paras = ["Segundo. Candidatos y sus requisitos.", "Podrán ser candidatos los expertos de nacionalidad española.",
             "Tercero. Dotación.", "10.000 euros."]
    assert bx.beneficiarios(paras) == "Podrán ser candidatos los expertos de nacionalidad española."
    assert bx.es_para_personas_fisicas(paras)
    paras = ["Segundo. Beneficiarios", "Empresas que contraten a jóvenes desempleados."]
    assert not bx.es_para_personas_fisicas(paras)  # habla de entidades al principio


def test_robots_comodines_regla_mas_larga_y_grupo_propio():
    from ayudas_rag.http import Robots

    r = Robots("User-agent: *\nDisallow: /diario_boe/xml.php?\nDisallow: /diario_boe/txt.php?id=BOE-B-2099-5\n"
               "Disallow: /buscar/*lang=en\nDisallow: /privado/\nAllow: /privado/publico\nDisallow: /fin$\n"
               "Disallow:\n")
    assert not r.allowed("/diario_boe/txt.php?id=BOE-B-2099-5")
    assert r.allowed("/diario_boe/txt.php?id=BOE-B-2099-6")
    assert not r.allowed("/diario_boe/xml.php?id=BOE-A-1")
    assert not r.allowed("/buscar/act.php?id=X&lang=en")
    assert r.allowed("/buscar/act.php?id=X")
    assert not r.allowed("/privado/x") and r.allowed("/privado/publico/x")
    assert not r.allowed("/fin") and r.allowed("/final")
    # un grupo propio para nuestro agente sustituye al de «*»
    r2 = Robots("User-agent: *\nDisallow: /\n\nUser-agent: script-personal-ayudas-rag\nDisallow: /api/\n")
    assert r2.allowed("/datos") and not r2.allowed("/api/x")
    assert Robots("").allowed("/lo-que-sea")


def test_fetcher_respeta_robots_en_cache_y_extractos(tmp_path):
    from datetime import date

    f = CachedFetcher(tmp_path, offline=True)
    robots = "User-agent: *\nDisallow: /diario_boe/txt.php?id=BOE-B-2099-10\n"
    p = f._path("https://www.boe.es/robots.txt", "text/plain")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(robots)

    def put(url, accept, data):
        q = f._path(url, accept)
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(data)

    put(bx.SUMARIO.format(d="20991231"), "application/json", (FX / "sumario.json").read_bytes())
    put(bx.TXT.format(id="BOE-B-2099-10"), "text/html", (FX / "extracto_pf.html").read_bytes())
    put(bx.TXT.format(id="BOE-B-2099-12"), "text/html", (FX / "extracto_entidades.html").read_bytes())
    # aunque la página esté en caché, si robots.txt la veta no se sirve
    with pytest.raises(BlockedURLError):
        f.get(bx.TXT.format(id="BOE-B-2099-10"), accept="text/html")
    st: dict = {}
    docs = bx.fetch_extractos(f, date(2099, 12, 31), days=1, stats=st)
    assert docs == []
    assert st == {"vistos": 2, "vetados_robots": 1, "sin_texto": 0, "descartados_filtro": 1, "conservados": 0}
    assert f.n_requests == 0


def test_metadatos_de_norma_y_aviso_de_consolidacion():
    from ayudas_rag.answer import aviso_documento

    docs = bl.parse_texto((FX / "texto_norma.xml").read_bytes(), "N", "T", "Autonómico", cutoff="20261115",
                          norm_meta={"departamento": "Comunidad Autónoma de Canarias",
                                     "estado_consolidacion": "Desactualizado", "fecha_actualizacion": "20260814"})
    assert docs[0].meta["ruta"] == "TÍTULO I"
    assert docs[0].meta["departamento"] == "Comunidad Autónoma de Canarias"
    av = aviso_documento(docs[0])
    assert "desactualizada" in av and "14-08-2026" in av
    docs[0].meta["estado_consolidacion"] = "Finalizado"
    assert aviso_documento(docs[0]) == ""


def test_filtro_fase2_comunidades_autonomas_y_personas_al_principio():
    # «Comunidades Autónomas» no son trabajadores autónomos
    paras = ["Segundo. Beneficiarios", "Diputaciones provinciales de las Comunidades Autónomas afectadas por la borrasca."]
    assert not bx.es_para_personas_fisicas(paras)
    paras = ["Segundo. Beneficiarios", "Trabajadores autónomos dados de alta en el RETA."]
    assert bx.es_para_personas_fisicas(paras)
    # empieza nombrando a personas aunque luego cite entidades
    paras = ["Primero. Beneficiarios", "Personas mayores y personas en situación de dependencia, y entidades sin ánimo de lucro."]
    assert bx.es_para_personas_fisicas(paras)
    paras = ["Primero. Beneficiarios", "Personas jurídicas que ostenten la condición de operador."]
    assert not bx.es_para_personas_fisicas(paras)
    paras = ["Primero. Beneficiarios", "Podrán ser beneficiarios las personas que reúnan los requisitos de la base 3."]
    assert bx.es_para_personas_fisicas(paras)


def test_evaluar_filtro():
    r = bx.evaluar_filtro({"a": True, "b": True, "c": False, "d": False}, {"a": True, "b": False, "c": True, "d": False})
    assert (r["tp"], r["fp"], r["fn"], r["tn"]) == (1, 1, 1, 1)
    assert r["precision"] == 0.5 and r["exhaustividad"] == 0.5
