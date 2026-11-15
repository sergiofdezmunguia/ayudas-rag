"""Construcción del corpus e índices, y buscador listo para usar."""

from __future__ import annotations

import functools
import json
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from .http import CachedFetcher
from .metrics import dedupe_to_docs
from .models import Chunk, Document, read_jsonl, write_jsonl
from .retrieval import BM25, Dense, ExpandedQuery, Hybrid
from .sources import boc_extractos, boe_extractos, boe_legislacion
from .text import chunk_document
from .vigencia import vencido

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CACHE = DATA / "cache"
CORPUS = DATA / "corpus.jsonl"
CHUNKS = DATA / "chunks.jsonl"
EMB = DATA / "embeddings.npy"
EMB_META = DATA / "embeddings.json"


def load_config(path: Path = ROOT / "config" / "fuentes.toml") -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def build_corpus(cfg: dict, fetcher: CachedFetcher) -> list[Document]:
    cutoff = cfg["fecha_corte"]
    docs: list[Document] = []
    for n in cfg.get("norma", []):
        nd = boe_legislacion.fetch_norm(fetcher, n["id"], cutoff)
        print(f"  {n['id']}: {len(nd)} preceptos")
        docs.extend(nd)
    ex = cfg.get("extractos")
    if ex:
        end = datetime.strptime(cutoff, "%Y%m%d").date()
        st: dict = {}
        ed = boe_extractos.fetch_extractos(fetcher, end, ex["dias"], ex.get("solo_personas_fisicas", True), st)
        print(f"  extractos BDNS en BOE ({ex['dias']} días): {len(ed)} conservados de {st['vistos']} "
              f"({st['vetados_robots']} vetados por robots.txt, {st['descartados_filtro']} descartados por el filtro)")
        docs.extend(ed)
    eb = cfg.get("extractos_boc")
    if eb:
        end = datetime.strptime(cutoff, "%Y%m%d").date()
        st = {}
        bd = boc_extractos.fetch_extractos(fetcher, end, eb["dias"], eb.get("solo_personas_fisicas", True), st)
        print(f"  extractos BDNS en BOC ({eb['dias']} días): {len(bd)} conservados de {st['vistos']} "
              f"({st['vetados_robots']} vetados por robots.txt, {st['descartados_filtro']} descartados por el filtro)")
        docs.extend(bd)
    return docs


def build_chunks(docs: list[Document]) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d)]


@dataclass
class Hit:
    doc: Document
    chunk: Chunk
    score: float


def parse_mode(mode: str) -> tuple[str, dict]:
    """«dense+v5+l0.5» → ("dense", {"v": 5.0, "l": 0.5}). Sufijos de reordenación de documentos (fase 3):
    +v<n>: baja n puestos los preceptos con vigencia vencida («+vinf»: al final);
    +l<b>: penaliza documentos largos, rango efectivo = rango × n_fragmentos^b."""
    base, *opts = mode.split("+")
    post = {}
    for o in opts:
        if not o or o[0] not in "vl":
            raise ValueError(f"Opción de modo desconocida: +{o}")
        post[o[0]] = float(o[1:])  # float("inf") vale para +vinf
    return base, post


def rerank_docs(order: list[str], best_rank: dict[str, int], post: dict, n_chunks: dict[str, int],
                vencidos: set[str]) -> list[str]:
    """Reordena el ranking de documentos (sin reordenar = mismo orden de entrada).

    - Longitud («l»): un documento con n fragmentos tiene n oportunidades de que alguno quede arriba por azar;
      se compara por rango efectivo (rango del mejor fragmento + 1) × n^b. b=0 no cambia nada; b=1 es la
      corrección completa tipo Bonferroni.
    - Vigencia («v»): los preceptos vencidos bajan v puestos (estable; los demás no se mueven entre sí).
    """
    out = list(order)
    b = post.get("l", 0.0)
    if b:
        out.sort(key=lambda d: (best_rank[d] + 1) * n_chunks.get(d, 1) ** b)
    v = post.get("v", 0.0)
    if v:
        pos = {d: i + (v if d in vencidos else 0) for i, d in enumerate(out)}
        out.sort(key=lambda d: (pos[d], d in vencidos))
    return out


class Searcher:
    def __init__(self, docs: list[Document], chunks: list[Chunk], embeddings: np.ndarray | None = None,
                 encode_query=None, anio_corte: int | None = None):
        self.docs = {d.doc_id: d for d in docs}
        self.chunks = chunks
        self.anio_corte = anio_corte
        self.n_chunks: dict[str, int] = {}
        for c in chunks:
            self.n_chunks[c.doc_id] = self.n_chunks.get(c.doc_id, 0) + 1
        self.vencidos = ({d.doc_id for d in docs if d.source == "legislacion"
                          and vencido(d.heading, d.text, anio_corte)} if anio_corte else set())
        texts = [c.index_text() for c in chunks]
        self.bm25 = BM25(texts)
        self.bm25x = ExpandedQuery(self.bm25)
        self.dense = Dense(embeddings, encode_query) if embeddings is not None else None

    def retriever(self, mode: str):
        """Modos: bm25, bm25x (con glosario), dense, hybrid, hybridx. Sufijo «@w» = peso de BM25 en la fusión RRF
        (el denso pesa 1), p. ej. «hybrid@0.5»."""
        base, _, w = parse_mode(mode)[0].partition("@")
        if base == "bm25":
            return self.bm25
        if base == "bm25x":
            return self.bm25x
        if self.dense is None:
            raise ValueError(f"Modo '{mode}' no disponible (¿faltan embeddings?)")
        if base == "dense":
            return self.dense
        if base in ("hybrid", "hybridx"):
            lex = self.bm25 if base == "hybrid" else self.bm25x
            return Hybrid([lex, self.dense], weights=[float(w) if w else 1.0, 1.0])
        raise ValueError(f"Modo desconocido: {mode}")

    def search_chunks(self, query: str, mode: str = "hybrid", k: int = 50) -> list[Hit]:
        out = []
        for i, s in self.retriever(mode).search(query, k):
            c = self.chunks[i]
            out.append(Hit(self.docs[c.doc_id], c, s))
        return out

    def search_docs(self, query: str, mode: str = "hybrid", k: int = 10, depth: int = 60) -> list[Hit]:
        """Ranking de documentos: el mejor fragmento de cada documento (y reordenación opcional, ver parse_mode)."""
        base, post = parse_mode(mode)
        hits = self.search_chunks(query, base, depth)
        best, best_rank = {}, {}
        for r, h in enumerate(hits):
            if h.chunk.doc_id not in best:
                best[h.chunk.doc_id], best_rank[h.chunk.doc_id] = h, r
        order = dedupe_to_docs([h.chunk.doc_id for h in hits])
        if post:
            order = rerank_docs(order, best_rank, post, self.n_chunks, self.vencidos)
        return [best[d] for d in order[:k]]


def load_searcher(with_dense: bool = True, encoder=None) -> Searcher:
    docs = read_jsonl(CORPUS, Document)
    chunks = read_jsonl(CHUNKS, Chunk)
    emb = None
    enc = None
    if with_dense:
        emb = np.load(EMB)
        meta = json.loads(EMB_META.read_text())
        if meta["n"] != len(chunks):
            raise RuntimeError("embeddings desalineados con chunks: ejecuta `ayudas index`")
        if encoder is None:
            from .retrieval import E5Encoder
            encoder = E5Encoder(meta["model"])
        enc = functools.lru_cache(maxsize=4096)(encoder.query)  # misma pregunta en varios modos
    return Searcher(docs, chunks, emb, enc, anio_corte=int(load_config()["fecha_corte"][:4]))


def save_corpus(docs: list[Document], chunks: list[Chunk]) -> None:
    write_jsonl(CORPUS, docs)
    write_jsonl(CHUNKS, chunks)
