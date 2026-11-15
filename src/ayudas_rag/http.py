"""Descarga educada con caché en disco.

- User-Agent genérico de script personal (sin email).
- Pausa mínima entre peticiones reales (por defecto 1,2 s).
- Caché por URL+Accept: si el fichero existe, no se vuelve a pedir.
- Lista de prefijos prohibidos (p. ej. la API de BDNS, vetada en su robots.txt).
- Cumplimiento de robots.txt de cada host (RFC 9309: comodines «*» y «$», gana la regla más larga y, a igualdad,
  Allow). Se comprueba también antes de servir desde caché: si una página pasa a estar vetada (el BOE veta
  anuncios concretos, p. ej. por protección de datos), deja de usarse aunque se descargara antes.
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

USER_AGENT = "Mozilla/5.0 (compatible; script-personal-ayudas-rag/0.1)"

# Rutas que los robots.txt de las fuentes vetan para nuestro uso.
BLOCKED_PREFIXES = (
    "https://www.infosubvenciones.es/bdnstrans/api/",  # robots.txt: "API no permitida"
    "https://www.pap.hacienda.gob.es/",  # robots.txt: Disallow: /
    "https://www.boe.es/diario_boe/xml.php",  # robots.txt BOE
    "https://www.boe.es/datos/pdfs/",
)


ROBOTS_TTL = 24 * 3600  # segundos que se reutiliza un robots.txt descargado
_UA_TOKEN = "script-personal-ayudas-rag"


class Robots:
    """Reglas de robots.txt aplicables a nuestro agente (grupo propio si existe; si no, «User-agent: *»)."""

    def __init__(self, text: str, agent: str = _UA_TOKEN):
        groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
        agents: list[str] = []
        rules: list[tuple[bool, str]] = []
        in_rules = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip().lower(), val.strip()
            if key == "user-agent":
                if in_rules:
                    groups.append((agents, rules))
                    agents, rules, in_rules = [], [], False
                agents.append(val.lower())
            elif key in ("allow", "disallow"):
                in_rules = True
                if val:  # «Disallow:» vacío no veta nada
                    rules.append((key == "allow", val))
        if agents:
            groups.append((agents, rules))
        own = [r for a, r in groups if any(x != "*" and x in agent.lower() for x in a)]
        star = [r for a, r in groups if "*" in a]
        chosen = own or star
        self.rules = [r for rs in chosen for r in rs]
        self._plain = [(allow, pat) for allow, pat in self.rules if "*" not in pat and not pat.endswith("$")]
        self._wild = [(allow, pat, self._compile(pat)) for allow, pat in self.rules
                      if "*" in pat or pat.endswith("$")]

    @staticmethod
    def _compile(pat: str) -> re.Pattern:
        end = pat.endswith("$")
        body = re.escape(pat[:-1] if end else pat).replace(r"\*", ".*")
        return re.compile(body + ("$" if end else ""))

    def allowed(self, path: str) -> bool:
        best_len, best_allow = -1, True
        for allow, pat in self._plain:
            if path.startswith(pat) and (len(pat) > best_len or (len(pat) == best_len and allow)):
                best_len, best_allow = len(pat), allow
        for allow, pat, rx in self._wild:
            if rx.match(path) and (len(pat) > best_len or (len(pat) == best_len and allow)):
                best_len, best_allow = len(pat), allow
        return best_allow


class BlockedURLError(RuntimeError):
    pass


class NotFoundError(RuntimeError):
    pass


class CachedFetcher:
    def __init__(self, cache_dir: Path, min_interval: float = 1.2, offline: bool = False, robots: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.offline = offline
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.n_requests = 0
        self.check_robots = robots
        self._robots: dict[str, Robots] = {}

    def robots_for(self, url: str) -> Robots:
        """robots.txt del host, con caché en disco de 24 h (en modo offline, la última copia que haya)."""
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base in self._robots:
            return self._robots[base]
        rurl = base + "/robots.txt"
        path = self._path(rurl, "text/plain")
        fresh = path.exists() and (time.time() - path.stat().st_mtime) < ROBOTS_TTL
        if path.exists() and (fresh or self.offline):
            text = path.read_text("utf-8", "replace")
        elif self.offline:
            text = ""  # sin copia local: solo aplica la lista fija BLOCKED_PREFIXES
        else:
            resp = self._request(rurl, "text/plain")
            if resp.status_code in (404, 410):
                text = ""  # sin robots.txt: todo permitido
            else:
                resp.raise_for_status()  # ante otros errores, mejor no seguir que ignorar el robots.txt
                text = resp.text
            self._store(path, text.encode("utf-8"))
        self._robots[base] = Robots(text)
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        if url.startswith(BLOCKED_PREFIXES):
            return False
        if not self.check_robots:
            return True
        parts = urlsplit(url)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        return self.robots_for(url).allowed(path)

    def _request(self, url: str, accept: str) -> requests.Response:
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, headers={"Accept": accept}, timeout=60)
        self._last = time.monotonic()
        self.n_requests += 1
        return resp

    @staticmethod
    def _store(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def _path(self, url: str, accept: str) -> Path:
        h = hashlib.sha256(f"{accept}|{url}".encode()).hexdigest()[:24]
        return self.cache_dir / h[:2] / h

    def get(self, url: str, accept: str = "application/json") -> bytes:
        if not self.allowed(url):
            raise BlockedURLError(f"URL vetada por robots.txt: {url}")
        path = self._path(url, accept)
        if path.exists():
            return path.read_bytes()
        miss = path.with_suffix(".404")
        if miss.exists():
            raise NotFoundError(url)
        if self.offline:
            raise FileNotFoundError(f"No está en caché (modo offline): {url}")
        resp = self._request(url, accept)
        if resp.status_code == 404:
            miss.parent.mkdir(parents=True, exist_ok=True)
            miss.touch()  # caché negativa: días sin BOE, etc.
            raise NotFoundError(url)
        resp.raise_for_status()
        self._store(path, resp.content)
        return resp.content
