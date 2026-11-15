"""Extractos de convocatorias de la BDNS publicados en el BOE (sección V-B).

La API de infosubvenciones.es está vetada en su robots.txt ("API no permitida"),
así que las convocatorias se obtienen de los extractos que el BOE publica por
obligación del art. 20.8 de la Ley 38/2003 (llevan "BDNS (Identif.)").

1. Sumario diario: https://www.boe.es/datosabiertos/api/boe/sumario/AAAAMMDD
2. Texto HTML del anuncio: https://www.boe.es/diario_boe/txt.php?id=BOE-B-...
3. Filtro heurístico: beneficiarios que incluyan personas físicas.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Iterator

from ..http import CachedFetcher, NotFoundError
from ..models import Document

SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{d}"
TXT = "https://www.boe.es/diario_boe/txt.php?id={id}"

# Beneficiarios que son (o incluyen) personas físicas.
_PF = re.compile(
    r"personas? f[ií]sicas?|estudiantes?|alumn[oa]s|j[oó]venes|deportistas|artistas|creador[ae]s|"
    r"investigador[ae]s|titulad[oa]s|doctor[ae]s|familias|mujeres|desemplead[oa]s|trabajador[ae]s|"
    r"aut[oó]nom[oa]s|particulares|propietari[oa]s|arrendatari[oa]s|inquilin[oa]s|personas? con discapacidad|"
    r"personas? (mayores|residentes|beneficiarias|solicitantes|interesadas)|becari[oa]s|víctimas|profesorado|docentes",
    re.I,
)


def iter_items(node) -> Iterator[dict]:
    if isinstance(node, list):
        for n in node:
            yield from iter_items(n)
    elif isinstance(node, dict):
        if "identificador" in node and "titulo" in node:
            yield node
        else:
            for v in node.values():
                if isinstance(v, (list, dict)):
                    yield from iter_items(v)


def extractos_en_sumario(sumario_json: dict) -> list[dict]:
    """Ítems de la sección 5B cuyo título es un extracto de convocatoria de ayudas."""
    out = []
    diarios = sumario_json["data"]["sumario"]["diario"]
    diarios = diarios if isinstance(diarios, list) else [diarios]
    for di in diarios:
        secs = di.get("seccion", [])
        secs = secs if isinstance(secs, list) else [secs]
        for sec in secs:
            if sec.get("codigo") != "5B":
                continue
            for it in iter_items(sec):
                t = it["titulo"].lower()
                if t.startswith("extracto") and re.search(r"convoca|ayuda|subvenci|beca|premio", t):
                    out.append(it)
    return out


class _TxtParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.paras: list[str] = []
        self._in_title = False
        self._depth_texto = 0  # >0 dentro de div#textoxslt
        self._in_p = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h3" and "documento-tit" in (a.get("class") or ""):
            self._in_title = True
        if tag == "div":
            if self._depth_texto:
                self._depth_texto += 1
            elif a.get("id") == "textoxslt":
                self._depth_texto = 1
        if tag == "p" and self._depth_texto:
            self._in_p, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == "h3":
            self._in_title = False
        if tag == "div" and self._depth_texto:
            self._depth_texto -= 1
        if tag == "p" and self._in_p:
            self._in_p = False
            t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if t:
                self.paras.append(t)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_p:
            self._buf.append(data)


def parse_txt(html: str) -> tuple[str, list[str]]:
    p = _TxtParser()
    p.feed(html)
    return re.sub(r"\s+", " ", p.title).strip(), p.paras


_SECTION = re.compile(r"^(Primer[oa]?|Segund[oa]|Tercer[oa]?|Cuart[oa]|Quint[oa]|Sext[oa]|S[eé]ptim[oa]|Octav[oa]|Noven[oa]|D[eé]cim[oa])\.?\s*(.*)$", re.I)


def beneficiarios(paras: list[str]) -> str:
    """Texto de la sección «Beneficiarios» (hasta la siguiente sección numerada)."""
    out, inside = [], False
    for p in paras:
        m = _SECTION.match(p)
        if m and len(p) < 120:
            inside = "beneficiari" in m.group(2).lower()
            continue
        if inside:
            out.append(p)
    return " ".join(out)


def es_para_personas_fisicas(paras: list[str]) -> bool:
    ben = beneficiarios(paras)
    if not ben:
        return False
    return bool(_PF.search(ben))


def parse_extracto(html: str, item: dict, fecha: str) -> Document | None:
    title, paras = parse_txt(html)
    if not paras:
        return None
    bdns = ""
    m = re.search(r"BDNS\s*\(?Identif\.?\)?:?\s*(\d+)", " ".join(paras[:3]))
    if m:
        bdns = m.group(1)
    title = title or item["titulo"]
    body = [p for p in paras if not p.startswith("BDNS")]
    return Document(
        doc_id=item["identificador"],
        source="convocatoria",
        norm_id=item["identificador"],
        norm_title=title,
        heading=title,
        text="\n".join(body),
        url=TXT.format(id=item["identificador"]),
        ambito="",
        fecha=fecha,
        meta={"bdns": bdns, "beneficiarios": beneficiarios(paras)[:500]},
    )


def fetch_extractos(fetcher: CachedFetcher, end: date, days: int, solo_pf: bool = True) -> list[Document]:
    docs = []
    for i in range(days):
        d = end - timedelta(days=i)
        ds = d.strftime("%Y%m%d")
        try:
            raw = fetcher.get(SUMARIO.format(d=ds), accept="application/json")
        except NotFoundError:
            continue  # domingos/festivos sin BOE → 404
        try:
            items = extractos_en_sumario(json.loads(raw))
        except (KeyError, json.JSONDecodeError):
            continue
        for it in items:
            html = fetcher.get(TXT.format(id=it["identificador"]), accept="text/html").decode("utf-8", "replace")
            doc = parse_extracto(html, it, ds)
            if doc is None:
                continue
            _, paras = parse_txt(html)
            if solo_pf and not es_para_personas_fisicas(paras):
                continue
            docs.append(doc)
    return docs
