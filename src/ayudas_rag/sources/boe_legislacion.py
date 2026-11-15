"""Legislación consolidada del BOE (API de datos abiertos).

Docs: https://www.boe.es/datosabiertos/documentos/APIconsolidada.pdf
Se pide el texto completo de cada norma (1 petición) y se trocea por bloques
de tipo "precepto" (artículos, disposiciones adicionales/transitorias...).
De cada bloque se toma la última versión vigente a la fecha de corte.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date

from ..http import CachedFetcher
from ..models import Document

API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id}"
HUMAN_URL = "https://www.boe.es/buscar/act.php?id={id}#{block}"

_EMPTY = re.compile(r"^\s*\(?(sin contenido|derogad[oa]|suprimid[oa])", re.I)
_EMPTY_HEADING = re.compile(r"\((sin contenido|derogad[oa]|suprimid[oa])\)", re.I)


def _p_text(p: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(p.itertext())).strip()


def pick_version(block: ET.Element, cutoff: str) -> ET.Element | None:
    """Última versión con fecha_vigencia <= cutoff (AAAAMMDD)."""
    best = None
    for v in block.findall("version"):
        fv = v.get("fecha_vigencia") or v.get("fecha_publicacion") or "0"
        if fv <= cutoff:
            best = v
    return best


def parse_texto(xml_bytes: bytes, norm_id: str, norm_title: str, ambito: str = "",
                cutoff: str | None = None) -> list[Document]:
    cutoff = cutoff or date.today().strftime("%Y%m%d")
    root = ET.fromstring(xml_bytes)
    docs: list[Document] = []
    for block in root.iter("bloque"):
        if block.get("tipo") != "precepto":
            continue
        v = pick_version(block, cutoff)
        if v is None:
            continue
        paras = [t for t in (_p_text(p) for p in v.iter("p")) if t]
        if not paras:
            continue
        heading = paras[0]
        body = paras[1:]
        body_text = "\n".join(body)
        if not body or _EMPTY.match(body_text) or _EMPTY_HEADING.search(heading):
            continue  # derogado o sin contenido
        bid = block.get("id")
        docs.append(Document(
            doc_id=f"{norm_id}#{bid}",
            source="legislacion",
            norm_id=norm_id,
            norm_title=norm_title,
            heading=heading,
            text=body_text,
            url=HUMAN_URL.format(id=norm_id, block=bid),
            ambito=ambito,
            fecha=v.get("fecha_vigencia") or "",
        ))
    return docs


def fetch_norm(fetcher: CachedFetcher, norm_id: str, cutoff: str | None = None) -> list[Document]:
    meta_raw = fetcher.get(API.format(id=norm_id) + "/metadatos", accept="application/json")
    meta = json.loads(meta_raw)["data"][0]
    if meta.get("estatus_derogacion") == "S":
        return []
    xml = fetcher.get(API.format(id=norm_id) + "/texto", accept="application/xml")
    return parse_texto(xml, norm_id, meta["titulo"], meta.get("ambito", {}).get("texto", ""), cutoff)
