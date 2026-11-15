"""Extractos de convocatorias publicados en el Boletín Oficial de Canarias (BOC).

Las convocatorias autonómicas de Canarias no salen en el BOE: salen en el BOC. El BOC no tiene API de datos
abiertos, pero sí páginas HTML estables que su robots.txt permite (veta los PDF y boletines concretos por
protección de datos, no el HTML en general). El aviso legal del Gobierno de Canarias autoriza la reproducción
«siempre que se cite la fuente» (ver README). La versión HTML no es la oficial: cada documento guarda también
el enlace al PDF oficial, que no se descarga (robots.txt veta «/*.pdf$»).

1. Índice del año: https://www.gobiernodecanarias.org/boc/AAAA/index.html (número y fecha de cada boletín).
2. Sumario del boletín: https://www.gobiernodecanarias.org/boc/AAAA/NNN/index.html
3. Texto HTML del anuncio: https://www.gobiernodecanarias.org/boc/AAAA/NNN/XXXX.html
4. Mismo filtro de personas físicas que con el BOE (los extractos BDNS tienen la misma estructura).
"""

from __future__ import annotations

import html as htmllib
import re
from datetime import date, timedelta

from ..http import BlockedURLError, CachedFetcher, NotFoundError
from ..models import Document
from .boe_extractos import beneficiarios, es_para_personas_fisicas

BASE = "https://www.gobiernodecanarias.org"
ANIO = BASE + "/boc/{y}/index.html"
BOLETIN = BASE + "/boc/{y}/{n:03d}/index.html"
PDF = "https://sede.gobiernodecanarias.org/boc/{cve}.pdf"
FUENTE = "Boletín Oficial de Canarias (Gobierno de Canarias), https://www.gobiernodecanarias.org/boc/"

_MESES = {m: i for i, m in enumerate(("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                      "septiembre", "octubre", "noviembre", "diciembre"), 1)}
_ANIO_LINK = re.compile(r'href="/boc/(\d{4})/(\d{3})/index\.html"[^>]*>\s*BOC N[ºo°]\s*\d+\s*-\s*(\d{1,2}) de '
                        r'([a-zé]+) de (\d{4})', re.I)
_ITEM = re.compile(r'<li class="justificado_boc">(.*?)</li>', re.S)
_ITEM_PDF_TITLE = re.compile(r'<a href="[^"]+\.pdf">\s*(.*?)\s*</a>', re.S)
_ITEM_HTML = re.compile(r'href="(/boc/\d{4}/\d{3}/(\d+)\.html)"')
_CVE = re.compile(r"BOC-A-\d{4}-\d{3}-\d+")
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(_TAG.sub(" ", s))).strip()


def url_de_cve(cve: str) -> str:
    """BOC-A-2026-227-3924 → https://www.gobiernodecanarias.org/boc/2026/227/3924.html"""
    _, _, y, n, num = cve.split("-")
    return f"{BASE}/boc/{y}/{n}/{num}.html"


def boletines_del_anio(html: str) -> list[tuple[int, date]]:
    """(número, fecha) de cada boletín del índice anual."""
    out = []
    for y, n, d, mes, y2 in _ANIO_LINK.findall(html):
        m = _MESES.get(mes.lower())
        if m:
            out.append((int(n), date(int(y2), m, int(d))))
    return out


def es_extracto_convocatoria(titulo: str) -> bool:
    """Mismo criterio que en el BOE: «EXTRACTO de ...» que convoca ayudas, subvenciones, becas o premios."""
    t = titulo.lower()
    return t.startswith("extracto") and bool(re.search(r"convoca|ayuda|subvenci|beca|premio", t))


def extractos_en_boletin(html: str) -> list[dict]:
    """Ítems del sumario de un boletín que son extractos de convocatoria: {"titulo", "path", "num"}."""
    out = []
    for m in _ITEM.finditer(html):
        b = m.group(1)
        t = _ITEM_PDF_TITLE.findall(b)
        h = _ITEM_HTML.search(b)
        if not t or not h:
            continue
        titulo = _clean(t[0])
        if es_extracto_convocatoria(titulo):
            out.append({"titulo": titulo, "path": h.group(1), "num": h.group(2)})
    return out


def parse_anuncio(html: str) -> tuple[str, str, list[str]]:
    """(título, CVE, párrafos del cuerpo) de la página HTML de un anuncio."""
    m = re.search(r"<h3[^>]*>(.*?)</h3>", html, re.S)
    title, cve = "", ""
    if m:
        h3 = m.group(1)
        c = _CVE.search(h3)
        cve = c.group(0) if c else ""
        head = re.split(r'<p class="justificado"', h3, maxsplit=1)[0]
        title = re.sub(r"^\d+\s+", "", _clean(head))
        body_html = html[m.end():]
    else:
        body_html = html
    body_html = body_html.split('<div id="pie"', 1)[0]
    paras = [_clean(p) for p in re.findall(r'<p class="justificado">(.*?)</p>', body_html, re.S)]
    return title, cve, [p for p in paras if p]


def parse_extracto(html: str, item: dict, fecha: str, url: str) -> Document | None:
    title, cve, paras = parse_anuncio(html)
    if not paras or not cve:
        return None
    bdns = ""
    mb = re.search(r"BDNS\s*\(?Identif\.?\)?:?\s*(\d+)", " ".join(paras[:3]))
    if mb:
        bdns = mb.group(1)
    title = title or item["titulo"]
    body = [p for p in paras if not p.startswith("BDNS")]
    return Document(
        doc_id=cve,
        source="convocatoria",
        norm_id=cve,
        norm_title=title,
        heading=title,
        text="\n".join(body),
        url=url,
        ambito="Autonómico",
        fecha=fecha,
        meta={"bdns": bdns, "beneficiarios": beneficiarios(paras)[:500], "boletin": "BOC",
              "departamento": "Comunidad Autónoma de Canarias", "pdf_oficial": PDF.format(cve=cve.lower())},
    )


def fetch_extractos(fetcher: CachedFetcher, end: date, days: int, solo_pf: bool = True,
                    stats: dict | None = None) -> list[Document]:
    """Extractos del BOC de los `days` días que acaban en `end` (mismos recuentos que la fuente del BOE)."""
    st = stats if stats is not None else {}
    for k in ("vistos", "vetados_robots", "sin_texto", "descartados_filtro", "conservados"):
        st.setdefault(k, 0)
    start = end - timedelta(days=days - 1)
    docs = []
    for y in range(start.year, end.year + 1):
        try:
            idx = fetcher.get(ANIO.format(y=y), accept="text/html").decode("utf-8", "replace")
        except NotFoundError:
            continue
        for n, d in sorted(boletines_del_anio(idx)):
            if not start <= d <= end:
                continue
            try:
                bol = fetcher.get(BOLETIN.format(y=y, n=n), accept="text/html").decode("utf-8", "replace")
            except (NotFoundError, BlockedURLError):
                continue
            for it in extractos_en_boletin(bol):
                st["vistos"] += 1
                url = BASE + it["path"]
                try:
                    page = fetcher.get(url, accept="text/html").decode("utf-8", "replace")
                except BlockedURLError:
                    st["vetados_robots"] += 1
                    continue
                except NotFoundError:
                    st["sin_texto"] += 1
                    continue
                doc = parse_extracto(page, it, d.strftime("%Y%m%d"), url)
                if doc is None:
                    st["sin_texto"] += 1
                    continue
                if solo_pf and not es_para_personas_fisicas(parse_anuncio(page)[2]):
                    st["descartados_filtro"] += 1
                    continue
                st["conservados"] += 1
                docs.append(doc)
    return docs
