# Calidad del filtro «beneficiarios = personas físicas»

Un solo anotador con el texto delante y sin doble anotación: tómese como orientativo.

## v0.1: revisión de 81 extractos (18-08-2026 a 14-11-2026)

Revisión manual (2026-11-15) de los 81 extractos de convocatorias BDNS publicados en el BOE (sección V-B)
entre el 18-08-2026 y el 14-11-2026, leyendo la sección de beneficiarios de cada uno.

| | etiquetado manual: sí | etiquetado manual: no |
|---|---|---|
| el filtro conserva | 18 | 1 |
| el filtro descarta | 5 | 57 |

- Precisión ≈ 18/19 = 0,95; exhaustividad ≈ 18/23 = 0,78.
- Falso positivo: Programa Auto+ (línea 2), dirigido a empresas.
- Falsos negativos: premios extraordinarios de FP (alumnado), plazas para funcionarios docentes, becas para
  personal del Ejército de Tierra, ayudas a autónomos y pymes de Santiago, becas de Turespaña (extracto sin
  sección de beneficiarios).

## Fase 2: muestra nueva de 80 extractos (20-05-2026 a 17-08-2026)

Los días 91-180 añaden 162 extractos. Saqué una muestra aleatoria de 80 (`random.Random(2026).sample`) y la
etiqueté a mano antes de tocar el filtro. Etiquetas y notas en
[`eval/filtro_muestra_fase2.tsv`](../eval/filtro_muestra_fase2.tsv). Para reproducir la medida:
`uv run ayudas filtro`.

**Filtro de v0.1 sin cambios (cifra fuera de muestra, la honesta):**

| | etiquetado manual: sí | etiquetado manual: no |
|---|---|---|
| el filtro conserva | 15 | 3 |
| el filtro descarta | 11 | 51 |

- Precisión 15/18 = 0,83; exhaustividad 15/26 = 0,58. Es bastante peor que en la muestra de v0.1: el filtro
  se ajustó con aquella muestra y la cifra de v0.1 era optimista.
- Los 3 falsos positivos (subvenciones a ayuntamientos, diputaciones y cabildos) se cuelan por la misma
  razón: «Comunidades Autónomas» casaba con la señal «autónomos».
- Falsos negativos: becas para opositores y para funcionarios en promoción interna, Premios Nacionales de Fin de
  Carrera, premios de investigación, becas para titulados («Titulado», en singular), ayudas a personas mayores
  y con discapacidad de Ceuta y Melilla («Personas mayores… y entidades»), y extractos sin sección de beneficiarios.

**Correcciones (generales, no por caso):** se quitan «Comunidad/Ciudad/Universidad Autónoma» antes de buscar
señales; si la sección empieza nombrando a personas («Personas…», «Ciudadanos…», «Alumnado…», salvo «Personas
jurídicas»), se conserva aunque luego cite entidades; se añaden singulares (titulado, graduado) y
«las personas que…» / «ciudadanos».

**Filtro corregido en la misma muestra (optimista, porque las reglas se escribieron viéndola):**
P 19/20 = 0,95; exhaustividad 19/26 = 0,73. Queda 1 falso positivo (Fundación Biodiversidad, ayuntamientos: la
palabra «entidad» aparece después de los primeros 160 caracteres y «colegios profesionales» activa la señal
«profesionales») y 7 falsos negativos (sobre todo becas para funcionarios y extractos sin sección de beneficiarios).

En todo el periodo de 180 días, la corrección cambia 12 decisiones: 9 extractos pasan a conservarse y 3 a
descartarse. En la ventana de v0.1 (los primeros 90 días) solo cambian 2, y los dos eran falsos negativos de
aquella revisión (premios extraordinarios de FP y autónomos de Santiago). Con las etiquetas de v0.1, el filtro
corregido daría P 20/21 ≈ 0,95 y exhaustividad 20/23 ≈ 0,87. Las dos muestras ya se han visto, así que para
medirlo bien hace falta una tercera.
