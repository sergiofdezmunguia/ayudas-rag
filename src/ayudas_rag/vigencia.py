"""Vigencia temporal de un precepto: ¿se limita expresamente a ejercicios fiscales o años que ya pasaron?

Muchas disposiciones adicionales y transitorias son medidas temporales («Durante el período impositivo 2022 y
2023, ...», «Escalas ... aplicables en 2015», «... hasta el 31 de diciembre de 2022»). Siguen en el texto
consolidado, pero ya no se aplican a la declaración en curso. Esta regla se escribió a partir de la *forma* de
esas cláusulas (encabezado y arranque del texto), no de las preguntas de evaluación.

Reglas (conservadoras: ante la duda, no se marca):
- Solo se mira el encabezado y el arranque de los tres primeros párrafos del cuerpo; las disposiciones
  finales que modifican otra norma se ignoran (el año suele ser del título de esa otra norma).
- Años en listas («2021 y 2022», «2023, 2024 y 2025») o rangos («2016 a 2024») tras «período(s) impositivo(s)»,
  «ejercicio(s)» o «año(s)»; o tras «en», «durante», «para» en el encabezado; o «hasta el ... de AAAA».
- Se ignoran los años precedidos de «a partir de», «desde» o «con anterioridad»/«anterior(es) a» (no acotan
  el final de la medida).
- Vencida = el último año que aparece es anterior a (año de corte − 1). Con corte en noviembre de 2026, la
  última declaración presentada es la del ejercicio 2025; un precepto limitado a 2024 o antes ya no se aplica
  a ninguna declaración ordinaria (aunque podría servir para una complementaria: por eso se rebaja, no se borra).
"""

from __future__ import annotations

import re

_LISTA = r"((?:19|20)\d\d(?:\s*(?:,|y|e|a|al|-)\s*(?:19|20)\d\d)*)"
_NOMBRE = re.compile(r"(?:per[ií]odos?\s+impositivos?|ejercicios?|años?)\s+" + _LISTA, re.I)
_PREP = re.compile(r"\b(?:en|durante|para)\s+(?:el\s+|los\s+)?" + _LISTA + r"\b", re.I)
_HASTA = re.compile(r"\bhasta el \d{1,2} de [a-zé]+ de ((?:19|20)\d\d)\b", re.I)
_INICIO = re.compile(r"^(?:[A-Z][a-zé]+\.\s*)?(?:\d+\.\s*)?(?:Durante|Para|En)\s+(?:el|los)\s+"
                     r"(?:per[ií]odos?\s+impositivos?|ejercicios?|años?)\s+" + _LISTA, re.I)
_ABIERTO = re.compile(r"(a partir del?|desde el?|desde|anterior(?:es)? a|con anterioridad a(?:l)?)\s*"
                      r"(?:\d{1,2} de [a-zé]+ de\s*)?(?:(?:los|las|el|la)\s+)?"
                      r"(?:per[ií]odos?\s+impositivos?\s+|ejercicios?\s+|años?\s+)?$", re.I)
_ANIO = re.compile(r"(?:19|20)\d\d")
_MODIFICA = re.compile(r"^Disposici[oó]n final [a-zé ]+\. Modificaci[oó]n", re.I)


def _anios(lista: str) -> list[int]:
    ys = [int(y) for y in _ANIO.findall(lista)]
    if re.search(r"\d\s*(?:a|al|-)\s*\d", lista) and len(ys) == 2 and ys[0] < ys[1]:
        return list(range(ys[0], ys[1] + 1))
    return ys


def _de(texto: str, pats) -> list[int]:
    out = []
    for pat in pats:
        for m in pat.finditer(texto):
            if _ABIERTO.search(texto[max(0, m.start() - 60):m.start()]):
                continue
            out += _anios(m.group(1))
    return out


def ejercicios_acotados(heading: str, text: str) -> list[int]:
    """Años a los que el precepto se limita expresamente (lista vacía si no se limita)."""
    if _MODIFICA.search(heading):
        return []  # «Modificación de la Ley 6/2018 ... para el año 2018»: el año es del nombre de otra norma
    years = _de(heading, (_NOMBRE, _PREP, _HASTA))
    for p in [p for p in text.split("\n") if p.strip()][:3]:
        m = _INICIO.match(p.strip()[:250])
        if m:
            years += _anios(m.group(1))
    return sorted(set(years))


def vencido(heading: str, text: str, anio_corte: int) -> bool:
    ys = ejercicios_acotados(heading, text)
    return bool(ys) and max(ys) < anio_corte - 1
