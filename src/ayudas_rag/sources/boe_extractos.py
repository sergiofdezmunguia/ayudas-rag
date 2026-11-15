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

from ..http import BlockedURLError, CachedFetcher, NotFoundError
from ..models import Document

SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{d}"
TXT = "https://www.boe.es/diario_boe/txt.php?id={id}"

# Señales de que los beneficiarios son personas físicas.
_PF = re.compile(
    r"personas? f[ií]sicas?|estudiantes?|alumn[oa]s|j[oó]venes|deportistas|artistas|creador[ae]s|autor[ae]s|"
    r"investigador[ae]s|personas investigadoras|titulad[oa]s?|graduad[oa]s?|licenciad[oa]s?|doctor[ae]s|escolares|"
    r"mujeres|desemplead[oa]s|aut[oó]nom[oa]s|particulares|propietari[oa]s|arrendatari[oa]s|inquilin[oa]s|"
    r"personas? con discapacidad|becari[oa]s|v[ií]ctimas|profesorado|docentes|funcionari[oa]s|periodistas|"
    r"espa[ñn]oles|nacionalidad|expertos|profesionales|mayores de (edad|\d+)|menores de \d+|"
    # fase 2: «las personas que reúnan...», «ciudadanos/ciudadanía de...»
    r"(las|aquellas) personas que|ciudadan[oa]s|ciudadan[ií]a de",
    re.I,
)
# «Comunidades Autónomas», «Ciudad Autónoma»... no son trabajadores autónomos (falso positivo hallado en la fase 2).
_NO_PF = re.compile(r"\b(comunidad|ciudad|universidad|regi[oó]n)(es)?\s+aut[oó]nom[ao]s?", re.I)
# Beneficiarios que empiezan nombrando a personas («Personas mayores, personas con discapacidad... y entidades»).
_EMPIEZA_PERSONAS = re.compile(
    r"^\W*(\d+\.|[a-z]\))?\s*(las |los )?(personas (?!jur[ií]dicas)|ciudadan|alumn|estudiantes|j[oó]venes|mujeres)",
    re.I)
# Si el texto de beneficiarios empieza hablando de entidades, se descarta salvo mención explícita a personas físicas.
_ENTIDAD = re.compile(
    r"entidad|empresa|organizaci|universidad|administraci|asociaci|fundaci|federaci|liga |ayuntamiento|"
    r"corporaci|centros|personas? jur[ií]dicas?|colegios profesionales|organismos|agrupaciones|cooperativas|consorcio",
    re.I,
)
_BEN_TITLE = re.compile(r"beneficiari|destinatari|candidat|solicitantes|requisit|participantes", re.I)


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


_SECTION = re.compile(
    r"^(Primer[oa]?|Segund[oa]|Tercer[oa]?|Cuart[oa]|Quint[oa]|Sext[oa]|S[eé]ptim[oa]|Octav[oa]|Noven[oa]|D[eé]cim[oa]|\d{1,2})"
    r"\s*[.)-]+\s*(.*)$", re.I)


def beneficiarios(paras: list[str]) -> str:
    """Texto de la sección «Beneficiarios» (o destinatarios/candidatos/requisitos), hasta la siguiente sección.

    Admite el título en su propio párrafo («Segundo. Beneficiarios») o en línea («Primero. Beneficiarios: ...»).
    """
    out, inside = [], False
    for p in paras:
        m = _SECTION.match(p)
        if m:
            rest = m.group(2)
            title, _, inline = rest.partition(":") if ":" in rest[:60] else (rest, "", "")
            if len(title) < 80:
                inside = bool(_BEN_TITLE.search(title))
                if inside and inline.strip():
                    out.append(inline.strip())
                continue
        if inside:
            out.append(p)
    return " ".join(out)


def es_para_personas_fisicas(paras: list[str]) -> bool:
    ben = beneficiarios(paras)
    if not ben:
        return False
    if re.search(r"personas? f[ií]sicas?", ben, re.I) and not re.search(r"no podr[aá]n .{0,40}personas? f[ií]sicas", ben, re.I):
        return True
    ben = _NO_PF.sub(" ", ben)
    if _EMPIEZA_PERSONAS.match(ben):
        return True
    if _ENTIDAD.search(ben[:160]):
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


def fetch_extractos(fetcher: CachedFetcher, end: date, days: int, solo_pf: bool = True,
                    stats: dict | None = None) -> list[Document]:
    """Extractos de los `days` días que acaban en `end`. `stats` (opcional) recibe recuentos: extractos vistos,
    vetados por robots.txt, sin texto y descartados por el filtro de personas físicas."""
    st = stats if stats is not None else {}
    for k in ("vistos", "vetados_robots", "sin_texto", "descartados_filtro", "conservados"):
        st.setdefault(k, 0)
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
            st["vistos"] += 1
            try:
                html = fetcher.get(TXT.format(id=it["identificador"]), accept="text/html").decode("utf-8", "replace")
            except BlockedURLError:
                st["vetados_robots"] += 1  # el BOE veta anuncios concretos en su robots.txt: se respetan
                continue
            doc = parse_extracto(html, it, ds)
            if doc is None:
                st["sin_texto"] += 1
                continue
            _, paras = parse_txt(html)
            if solo_pf and not es_para_personas_fisicas(paras):
                st["descartados_filtro"] += 1
                continue
            st["conservados"] += 1
            docs.append(doc)
    return docs


def evaluar_filtro(etiquetas: dict[str, bool], decision: dict[str, bool]) -> dict:
    """Matriz de confusión del filtro frente a etiquetas manuales (id → incluye personas físicas)."""
    tp = sum(etiquetas[i] and decision[i] for i in etiquetas)
    fp = sum(not etiquetas[i] and decision[i] for i in etiquetas)
    fn = sum(etiquetas[i] and not decision[i] for i in etiquetas)
    tn = len(etiquetas) - tp - fp - fn
    return {"n": len(etiquetas), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else 0.0, "exhaustividad": tp / (tp + fn) if tp + fn else 0.0}
