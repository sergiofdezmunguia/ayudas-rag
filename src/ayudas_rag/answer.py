"""Respuesta extractiva con citas: no genera texto nuevo, solo selecciona frases literales."""

from __future__ import annotations

from dataclasses import dataclass

from .pipeline import Hit, Searcher
from .text import expand_query, split_sentences, tokenize

AVISO = ("Aviso: esto no es asesoramiento fiscal ni jurídico. Son fragmentos literales de normas y "
         "anuncios oficiales que pueden no aplicarse a tu caso, haber cambiado o tener requisitos "
         "adicionales. Consulta la fuente oficial o a un profesional. "
         "Basado en datos de la Agencia Estatal Boletín Oficial del Estado (https://www.boe.es).")


@dataclass
class Citation:
    heading: str
    context: str
    norm_title: str
    url: str
    fecha: str
    source: str
    sentences: list[str]
    score: float


def best_sentences(query: str, text: str, idf: dict[str, float], n: int = 2) -> list[str]:
    """Las n frases con más solapamiento (ponderado por IDF) con la pregunta, en orden original."""
    sents = split_sentences(text)
    if not sents:
        return []
    q = set(tokenize(expand_query(query)))  # el glosario ayuda a casar «alquiler» con «arrendamiento»
    scored = [(sum(idf.get(t, 0.0) for t in q & set(tokenize(s))), i) for i, s in enumerate(sents)]
    top = [i for sc, i in sorted(scored, key=lambda x: (-x[0], x[1]))[:n] if sc > 0]
    if not top:
        top = [0]
    return [sents[i] for i in sorted(top)]


def answer(searcher: Searcher, query: str, mode: str = "hybrid", n_docs: int = 4) -> list[Citation]:
    hits: list[Hit] = searcher.search_docs(query, mode, k=n_docs)
    out = []
    for h in hits:
        out.append(Citation(
            heading=h.doc.heading, context=h.chunk.context, norm_title=h.doc.norm_title, url=h.doc.url,
            fecha=h.doc.fecha, source=h.doc.source,
            sentences=best_sentences(query, h.chunk.text, searcher.bm25.idf),
            score=h.score,
        ))
    return out


def format_answer(query: str, cites: list[Citation]) -> str:
    lines = [f"Pregunta: {query}", ""]
    if not cites:
        lines.append("No he encontrado fragmentos relevantes en el corpus.")
    for i, c in enumerate(cites, 1):
        tipo = "Convocatoria (extracto BDNS en BOE)" if c.source == "convocatoria" else "Norma"
        fecha = f"publicado {c.fecha}" if c.source == "convocatoria" else f"versión vigente desde {c.fecha}"
        lines.append(f"[{i}] {c.heading}")
        if c.heading != c.norm_title:
            lines.append(f"    {c.norm_title[:160]}")
        if c.context:
            lines.append(f"    {c.context[:200]}")
        lines.append(f"    {tipo} · {fecha}")
        for s in c.sentences:
            lines.append(f"    «{s}»")
        lines.append(f"    Fuente: {c.url}")
        lines.append("")
    lines.append(AVISO)
    return "\n".join(lines)
