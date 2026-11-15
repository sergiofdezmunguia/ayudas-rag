"""Construcción del corpus e índices, y buscador listo para usar."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from .http import CachedFetcher
from .metrics import dedupe_to_docs
from .models import Chunk, Document, read_jsonl, write_jsonl
from .retrieval import BM25, Dense, Hybrid
from .sources import boe_extractos, boe_legislacion
from .text import chunk_document

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
        ed = boe_extractos.fetch_extractos(fetcher, end, ex["dias"], ex.get("solo_personas_fisicas", True))
        print(f"  extractos BDNS en BOE: {len(ed)}")
        docs.extend(ed)
    return docs


def build_chunks(docs: list[Document]) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d)]


@dataclass
class Hit:
    doc: Document
    chunk: Chunk
    score: float


class Searcher:
    def __init__(self, docs: list[Document], chunks: list[Chunk], embeddings: np.ndarray | None = None,
                 encode_query=None):
        self.docs = {d.doc_id: d for d in docs}
        self.chunks = chunks
        texts = [c.index_text() for c in chunks]
        self.bm25 = BM25(texts)
        self.dense = Dense(embeddings, encode_query) if embeddings is not None else None
        self.hybrid = Hybrid([self.bm25, self.dense]) if self.dense else None

    def retriever(self, mode: str):
        r = {"bm25": self.bm25, "dense": self.dense, "hybrid": self.hybrid}[mode]
        if r is None:
            raise ValueError(f"Modo '{mode}' no disponible (¿faltan embeddings?)")
        return r

    def search_chunks(self, query: str, mode: str = "hybrid", k: int = 50) -> list[Hit]:
        out = []
        for i, s in self.retriever(mode).search(query, k):
            c = self.chunks[i]
            out.append(Hit(self.docs[c.doc_id], c, s))
        return out

    def search_docs(self, query: str, mode: str = "hybrid", k: int = 10, depth: int = 60) -> list[Hit]:
        """Ranking de documentos: el mejor fragmento de cada documento."""
        hits = self.search_chunks(query, mode, depth)
        order = dedupe_to_docs([h.chunk.doc_id for h in hits])[:k]
        best = {}
        for h in hits:
            best.setdefault(h.chunk.doc_id, h)
        return [best[d] for d in order]


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
        enc = encoder.query
    return Searcher(docs, chunks, emb, enc)


def save_corpus(docs: list[Document], chunks: list[Chunk]) -> None:
    write_jsonl(CORPUS, docs)
    write_jsonl(CHUNKS, chunks)
