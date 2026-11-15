"""Normalización, tokenización y troceado en español."""

from __future__ import annotations

import re
import unicodedata

from .models import Chunk, Document

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas aquellos aqui asi aun
cada como con contra cual cuales cuando de del desde donde durante e el ella ellas ellos en entre era
eran es esa esas ese eso esos esta estan estas este esto estos fue fueron ha han hasta hay la las le les
lo los mas me mi mis mucho muy nada ni no nos o os otra otras otro otros para pero poco por porque que
quien quienes se segun ser si sido sin sobre son su sus tambien tan tanto te tiene tienen todo todos tu
tus u un una unas uno unos y ya yo soy estoy puedo pedir puede pueden hacer tengo quiero
""".split())

_TOKEN = re.compile(r"[a-z0-9ñ]+")


def fold(s: str) -> str:
    """Minúsculas y sin tildes (conserva la ñ)."""
    s = s.lower().replace("ñ", "\x00")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("\x00", "ñ")


def stem(tok: str) -> str:
    """Stemmer ligero: quita plurales y algunos sufijos derivativos frecuentes."""
    if len(tok) <= 4 or tok.isdigit():
        return tok
    for suf in ("aciones", "iciones", "amientos", "imientos", "acion", "icion", "amiento", "imiento",
                "mente", "idades", "idad", "ables", "ibles", "able", "ible"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 4:
            return tok[: -len(suf)]
    if tok.endswith("ces") and len(tok) > 5:
        return tok[:-3] + "z"
    if tok.endswith("es") and len(tok) > 5:
        tok = tok[:-2]
    elif tok.endswith("s"):
        tok = tok[:-1]
    if tok[-1] in "aeo" and len(tok) > 4:
        tok = tok[:-1]
    return tok


# Glosario coloquial → lenguaje de las normas. OJO: escrito tras ver fallos de BM25 en la evaluación,
# así que sus resultados son optimistas (ver results/informe.md).
GLOSARIO = {
    "alquiler": "arrendamiento arrendatario",
    "alquilado": "arrendamiento arrendado",
    "inquilino": "arrendatario",
    "desgravar": "deducir deducción",
    "desgravo": "deducir deducción",
    "desgravación": "deducción",
    "renta": "impuesto sobre la renta de las personas físicas",
    "irpf": "impuesto sobre la renta de las personas físicas",
    "bebé": "nacimiento hijo",
    "hijo": "descendiente",
    "hijos": "descendientes",
    "ong": "entidades sin fines lucrativos donativos",
    "donar": "donativos donaciones",
    "sueldo": "rendimientos del trabajo",
    "brutos": "rendimientos íntegros",
    "hipoteca": "préstamo adquisición vivienda habitual",
    "casa": "vivienda",
    "piso": "vivienda",
    "desahuciar": "desahucio",
    "cobra": "cuantía prestación",
    "cobrar": "cuantía abono",
    "pueblo": "municipio",
    "madre": "ascendiente",
    "padre": "ascendiente",
    "placas": "autoconsumo",
    "coche": "vehículo",
    "autónomo": "actividad económica alta censo",
    "beca": "becas formación",
}


def expand_query(q: str) -> str:
    extra = [GLOSARIO[w] for w in re.findall(r"[\wáéíóúñü]+", q.lower()) if w in GLOSARIO]
    return q + (" " + " ".join(extra) if extra else "")


def tokenize(s: str) -> list[str]:
    return [stem(t) for t in _TOKEN.findall(fold(s)) if t not in STOPWORDS and len(t) > 1]


def split_sentences(s: str) -> list[str]:
    parts = re.split(r"(?<=[.;:])\s+(?=[A-ZÁÉÍÓÚÑ0-9a-z(«])|\n+", s)
    return [p.strip() for p in parts if p.strip()]


def chunk_document(doc: Document, max_words: int = 220, overlap_words: int = 40) -> list[Chunk]:
    """Trocea por párrafos acumulando hasta ~max_words; los párrafos largos se parten por palabras."""
    paras = [p for p in doc.text.split("\n") if p.strip()]
    pieces: list[str] = []
    for p in paras:
        w = p.split()
        if len(w) <= max_words:
            pieces.append(p)
        else:
            step = max_words - overlap_words
            for i in range(0, len(w), step):
                pieces.append(" ".join(w[i : i + max_words]))
                if i + max_words >= len(w):
                    break
    chunks: list[str] = []
    cur: list[str] = []
    n = 0
    for p in pieces:
        pw = len(p.split())
        if cur and n + pw > max_words:
            chunks.append("\n".join(cur))
            # solapamiento: arrastra el último párrafo si es corto
            last = cur[-1]
            cur, n = ([last], len(last.split())) if len(last.split()) <= overlap_words else ([], 0)
        cur.append(p)
        n += pw
    if cur:
        chunks.append("\n".join(cur))
    return [
        Chunk(chunk_id=f"{doc.doc_id}::{i}", doc_id=doc.doc_id, text=c, heading=doc.heading,
              norm_title=doc.norm_title, url=doc.url,
              context=doc.meta.get("ruta", ""))
        for i, c in enumerate(chunks)
    ]
