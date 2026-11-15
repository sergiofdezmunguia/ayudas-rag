"""CLI: `ayudas ingest | index | ask | eval`."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time


def _limit_threads(n: int = 4) -> None:
    # En WSL, BLAS con todos los hilos va muy lento.
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(v, str(n))
    from threadpoolctl import threadpool_limits

    threadpool_limits(n)


def cmd_ingest(args) -> None:
    from .http import CachedFetcher
    from .pipeline import CACHE, build_chunks, build_corpus, load_config, save_corpus

    cfg = load_config()
    f = CachedFetcher(CACHE, offline=args.offline)
    t = time.time()
    docs = build_corpus(cfg, f)
    chunks = build_chunks(docs)
    save_corpus(docs, chunks)
    print(f"{len(docs)} documentos, {len(chunks)} fragmentos; {f.n_requests} peticiones nuevas; {time.time()-t:.0f}s")


def cmd_index(args) -> None:
    import numpy as np

    from .models import Chunk, read_jsonl
    from .pipeline import CHUNKS, EMB, EMB_META
    from .retrieval import E5Encoder

    chunks = read_jsonl(CHUNKS, Chunk)
    enc = E5Encoder(args.model, device=args.device)
    t = time.time()
    emb = enc.passages([c.index_text() for c in chunks])
    np.save(EMB, emb.astype(np.float32))
    EMB_META.write_text(json.dumps({"model": args.model, "n": len(chunks), "dim": int(emb.shape[1])}))
    print(f"{len(chunks)} embeddings en {time.time()-t:.0f}s")


def cmd_ask(args) -> None:
    from .answer import answer, format_answer
    from .pipeline import load_searcher

    s = load_searcher(with_dense=args.mode != "bm25")
    print(format_answer(args.pregunta, answer(s, args.pregunta, args.mode, args.n)))


def cmd_eval(args) -> None:
    from pathlib import Path

    from .evaluate import check_questions, evaluate, load_questions, report_md
    from .pipeline import ROOT, load_searcher

    qs = load_questions(Path(args.preguntas))
    s = load_searcher(with_dense=True)
    missing = check_questions(qs, set(s.docs))
    if missing:
        sys.exit("Ids relevantes inexistentes en el corpus:\n" + "\n".join(missing))
    res = evaluate(s, qs)
    docs = list(s.docs.values())
    stats = {"docs": len(docs), "chunks": len(s.chunks),
             "legislacion": sum(d.source == "legislacion" for d in docs),
             "convocatorias": sum(d.source == "convocatoria" for d in docs),
             "normas": len({d.norm_id for d in docs if d.source == "legislacion"})}
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "metricas.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (out / "informe.md").write_text(report_md(res, qs, stats))
    for m, agg in res["modos"].items():
        print(m, " ".join(f"{k}={v:.3f}" for k, v in agg.items() if k in ("recall@5", "mrr", "ndcg@10")))


def main(argv=None) -> None:
    _limit_threads()
    p = argparse.ArgumentParser(prog="ayudas", description="Buscador de ayudas y deducciones (datos BOE)")
    sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("ingest", help="descarga (con caché) y construye el corpus")
    a.add_argument("--offline", action="store_true", help="solo caché, sin red")
    a.set_defaults(func=cmd_ingest)
    a = sp.add_parser("index", help="calcula embeddings")
    a.add_argument("--model", default="intfloat/multilingual-e5-small")
    a.add_argument("--device", default=None, help="cpu (por defecto) o cuda")
    a.set_defaults(func=cmd_index)
    a = sp.add_parser("ask", help="pregunta y respuesta extractiva con citas")
    a.add_argument("pregunta")
    a.add_argument("--mode", default="hybrid", choices=["bm25", "dense", "hybrid"])
    a.add_argument("-n", type=int, default=4)
    a.set_defaults(func=cmd_ask)
    a = sp.add_parser("eval", help="evaluación de recuperación")
    a.add_argument("--preguntas", default="eval/preguntas.jsonl")
    a.set_defaults(func=cmd_eval)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
