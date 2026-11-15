from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Document:
    """Unidad recuperable con significado propio: un artículo/disposición o un extracto de convocatoria."""

    doc_id: str  # p. ej. "BOCM-m-2010-90068#a8" o "BOE-B-2026-37127"
    source: str  # "legislacion" | "convocatoria"
    norm_id: str
    norm_title: str
    heading: str  # "Artículo 8. Deducción por arrendamiento de vivienda habitual."
    text: str
    url: str
    ambito: str = ""  # "Estatal" | "Autonómico" | ...
    fecha: str = ""  # vigencia de la versión (AAAAMMDD) o fecha de publicación
    meta: dict = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str  # texto del fragmento (sin cabecera)
    heading: str
    norm_title: str
    url: str
    context: str = ""  # ruta de encabezados: "CAPÍTULO IV ... > Sección 1.ª Ayuda al alquiler de vivienda"

    def index_text(self) -> str:
        """Texto que se indexa: cabecera + ruta + título de la norma + fragmento."""
        parts = [self.heading, self.context, self.norm_title, self.text]
        return "\n".join(p for p in parts if p)


def write_jsonl(path: Path, rows: Iterable) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path, cls):
    with open(path, encoding="utf-8") as f:
        return [cls(**json.loads(line)) for line in f if line.strip()]
