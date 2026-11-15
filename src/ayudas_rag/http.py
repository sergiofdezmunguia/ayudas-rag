"""Descarga educada con caché en disco.

- User-Agent genérico de script personal (sin email).
- Pausa mínima entre peticiones reales (por defecto 1,2 s).
- Caché por URL+Accept: si el fichero existe, no se vuelve a pedir.
- Lista de prefijos prohibidos (p. ej. la API de BDNS, vetada en su robots.txt).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests

USER_AGENT = "Mozilla/5.0 (compatible; script-personal-ayudas-rag/0.1)"

# Rutas que los robots.txt de las fuentes vetan para nuestro uso.
BLOCKED_PREFIXES = (
    "https://www.infosubvenciones.es/bdnstrans/api/",  # robots.txt: "API no permitida"
    "https://www.pap.hacienda.gob.es/",  # robots.txt: Disallow: /
    "https://www.boe.es/diario_boe/xml.php",  # robots.txt BOE
    "https://www.boe.es/datos/pdfs/",
)


class BlockedURLError(RuntimeError):
    pass


class NotFoundError(RuntimeError):
    pass


class CachedFetcher:
    def __init__(self, cache_dir: Path, min_interval: float = 1.2, offline: bool = False):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.offline = offline
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.n_requests = 0

    def _path(self, url: str, accept: str) -> Path:
        h = hashlib.sha256(f"{accept}|{url}".encode()).hexdigest()[:24]
        return self.cache_dir / h[:2] / h

    def get(self, url: str, accept: str = "application/json") -> bytes:
        if url.startswith(BLOCKED_PREFIXES):
            raise BlockedURLError(f"URL vetada por robots.txt: {url}")
        path = self._path(url, accept)
        if path.exists():
            return path.read_bytes()
        miss = path.with_suffix(".404")
        if miss.exists():
            raise NotFoundError(url)
        if self.offline:
            raise FileNotFoundError(f"No está en caché (modo offline): {url}")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, headers={"Accept": accept}, timeout=60)
        self._last = time.monotonic()
        self.n_requests += 1
        if resp.status_code == 404:
            miss.parent.mkdir(parents=True, exist_ok=True)
            miss.touch()  # caché negativa: días sin BOE, etc.
            raise NotFoundError(url)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(resp.content)
        tmp.rename(path)
        return resp.content
