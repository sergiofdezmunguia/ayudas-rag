# ayudas-rag

Buscador de **ayudas, subvenciones y deducciones fiscales para particulares en España** construido sobre datos
públicos oficiales del BOE y, para las convocatorias canarias, del Boletín Oficial de Canarias (BOC). Ante una pregunta del tipo *«soy asalariado de 30 años en Madrid, ¿qué ayudas o
deducciones puedo pedir para alquiler?»* o *«vivo de alquiler en Tenerife, ¿cuánto me puedo desgravar?»* devuelve los artículos y convocatorias más relevantes, con fragmentos
literales y enlace a la fuente oficial.

> **Aviso.** Esto no es asesoramiento fiscal ni jurídico. El sistema solo localiza y cita textos oficiales; no
> comprueba si cumples los requisitos, puede devolver normas que no te aplican y el corpus es un subconjunto
> pequeño y con fecha de corte. Antes de decidir nada, lee la fuente oficial o consulta a un profesional.

Basado en datos de la Agencia Estatal Boletín Oficial del Estado (<https://www.boe.es>). Convocatorias canarias:
fuente Boletín Oficial de Canarias, Gobierno de Canarias (<https://www.gobiernodecanarias.org/boc/>).

## Qué hace

```
BOE datos abiertos ─┐
BOC (HTML) ─────────┴► ingesta con caché ──► documentos (artículo / extracto) ──► fragmentos (~220 palabras)
                                                                                   │
   pregunta ──► e5-small (por defecto) ─┐
            ├─► BM25 propio ────────────┼─► [opcional: fusión RRF] ──► top documentos ──► respuesta extractiva
            └─► BM25 + glosario ────────┘                                                (frases literales + enlace)
```

- **Corpus** (`config/fuentes.toml`):
  - Legislación consolidada del BOE, una petición por norma, versión vigente de cada artículo a la fecha de corte:
    Ley y Reglamento del IRPF, texto refundido de tributos cedidos de la Comunidad de Madrid (deducciones
    autonómicas), Plan Estatal de Vivienda 2026-2030, Bono Alquiler Joven (RD 42/2022), Ley por el derecho a la
    vivienda, Ingreso Mínimo Vital, Renta Mínima de Inserción de Madrid, Ley de familias numerosas y Ley de mecenazgo.
  - **Canarias** (fase 2): texto refundido de tributos cedidos (deducciones autonómicas del IRPF y tipos reducidos
    del ITP), Ley 5/2022 de la Renta Canaria de Ciudadanía, Ley 2/2003 de Vivienda de Canarias y Ley 16/2019 de
    Servicios Sociales de Canarias. Tres de ellas tienen en el BOE la consolidación en estado **«Desactualizado»**
    (pueden faltar modificaciones recientes): el estado se guarda con cada artículo y la respuesta lo avisa.
  - Extractos de convocatorias de la BDNS que el BOE publica en la sección V-B (últimos **180 días**; en v0.1 eran
    90), filtrados por una heurística de «beneficiarios = personas físicas».
  - **BOC** (fase 3): extractos BDNS de convocatorias de la Comunidad Autónoma, cabildos y universidades canarias
    de los mismos 180 días, con el mismo filtro (31 de 92). Se usa la versión HTML del BOC, que no es la oficial;
    cada cita lleva también el enlace al PDF oficial.
- **Unidad recuperable**: un artículo/disposición o un extracto. Cada fragmento lleva la ruta de encabezados
  (p. ej. *Capítulo IV … > Sección 3.ª Ayuda al alquiler para la emancipación de las personas jóvenes*), que es
  clave en normas como el Plan de Vivienda donde decenas de artículos se titulan «Personas beneficiarias».
- **Recuperación**: BM25 implementado a mano (tokenización con plegado de tildes, stopwords y un stemmer ligero),
  embeddings `intfloat/multilingual-e5-small` en CPU y un híbrido por Reciprocal Rank Fusion con peso configurable
  (`--mode hybrid@0.3`).
- **Reordenación por vigencia** (fase 3): los preceptos que se limitan expresamente a ejercicios ya pasados
  («Durante el período impositivo 2022 y 2023…», «aplicables en 2015») se detectan con reglas sobre el
  encabezado y el arranque del texto (`vigencia.py`, 28 de 1.543 preceptos) y bajan cinco puestos (`+v5`); no se
  borran, porque aún sirven para declaraciones de esos años, y la respuesta lo avisa. El modo por defecto es
  `dense+v5`, el mejor en la evaluación.
- **Respuesta**: extractiva, sin LLM. Para cada documento recuperado se eligen las frases con más solapamiento
  (ponderado por IDF) con la pregunta y se cita el enlace al artículo en boe.es.

## Fuentes y condiciones de uso

| Fuente | Decisión | Motivo |
|---|---|---|
| BOE, API de datos abiertos (legislación consolidada y sumarios) | **Sí** | Reutilización permitida citando la fuente ([aviso legal](https://www.boe.es/informacion/aviso_legal/index.php)). |
| BOE, `diario_boe/txt.php` (texto HTML de anuncios) | **Sí** | Permitido en robots.txt (solo se vetan variantes de idioma, `xml.php` y PDF). |
| BOC, páginas HTML (`/boc/AAAA/index.html`, sumario de cada boletín y `/boc/AAAA/NNN/XXXX.html`) | **Sí** | No tiene API ni datos abiertos (solo RSS por sección). Su `robots.txt` (compartido con gobiernodecanarias.org) veta todos los PDF (`/*.pdf$`) y ~700 rutas de boletines y anuncios concretos, no el HTML en general. El [aviso legal](https://www.gobiernodecanarias.org/principal/avisolegal/) autoriza la reproducción «siempre que se cite la fuente». Los PDF oficiales se enlazan, no se descargan. |
| BDNS / infosubvenciones.es, API | **No** | Su `robots.txt` dice `Disallow: /api/  # API no permitida`. Se sustituye por los extractos BDNS que publica el BOE. |

Descarga educada: User-Agent genérico de script personal, ≥1,2 s entre peticiones, caché en disco (incluida
caché negativa de 404), y las URL vetadas están bloqueadas en el propio cliente (`http.py`). Desde la fase 2 el
cliente lee además el `robots.txt` completo de cada host (caché de 24 h; comodines `*`/`$`; gana la regla más
larga) y lo aplica también a lo que ya estaba en caché. El del BOE veta unos 1.700 anuncios `txt.php?id=…`
concretos; en estos 180 días no ha caído ningún extracto de convocatoria, pero el cliente los saltaría.

## Uso

```bash
uv sync
uv run ayudas ingest          # descarga (con caché) y construye data/corpus.jsonl y data/chunks.jsonl
uv run ayudas index           # embeddings e5-small (CPU)
uv run ayudas ask "soy asalariado de 30 años en Madrid, ¿qué ayudas o deducciones puedo pedir para alquiler?"
uv run ayudas eval            # results/informe.md y results/metricas.json
uv run ayudas filtro          # precisión del filtro de convocatorias frente a la muestra etiquetada
uv run ayudas filtro --etiquetas eval/filtro_muestra_boc_fase3.tsv   # lo mismo con los 92 extractos del BOC
uv run pytest                 # tests sin red con fixtures inventadas
```

## Evaluación

90 preguntas en lenguaje coloquial (`eval/preguntas.jsonl`):
- **42 de v0.1**: 34 sobre deducciones y prestaciones reguladas en las normas y 8 sobre ayudas concretas
  (6 convocatorias y 2 programas del Plan de Vivienda).
- **20 de Canarias** (fase 2): deducciones autonómicas, Renta Canaria de Ciudadanía, vivienda protegida,
  servicios sociales e ITP. Una de ellas, a propósito, menciona Madrid («mi hijo estudia en Madrid y vivimos en Gran Canaria»).
- **8 de convocatorias** publicadas entre 91 y 180 días antes del corte (fase 2).
- **10 de Canarias** (fase 3), sobre artículos del texto refundido canario que no tenían pregunta (libros y
  uniforme escolar, acogimiento, empleada de hogar, rehabilitación energética…), escritas antes de probar la
  reordenación.
- **10 de convocatorias del BOC** (fase 3), redactadas sin copiar el título del extracto («cultivo tuneras para
  sacar cochinilla», «mi hijo tiene TDAH y va a un instituto público»).

**Cómo se fijaron los documentos relevantes.** Las preguntas y sus artículos relevantes los escribí yo (el autor)
leyendo los títulos y el texto de los artículos del corpus, *antes* de ejecutar ningún recuperador sobre ellas.
Cada pregunta apunta a los 1-4 artículos o extractos que hay que leer para responderla. Las de las fases 2 y 3
se añadieron al final del fichero, así que el reparto dev/test por posición (impares/pares) de v0.1 no cambia y las
nuevas se reparten a medias. Riesgos: un único anotador, relevancia binaria y documentos relevantes
alternativos sin marcar. Esto último pesa más ahora: preguntas de v0.1 sin comunidad, como «¿qué deducciones hay
por ser familia numerosa?», tienen en Canarias una respuesta válida que no está marcada.

| modo | MRR v0.1 (42 preg.) | MRR fase 2 (70 preg.) | MRR fase 3 (90 preg.) | recall@5 (90) | MRR Canarias (30) |
|---|---|---|---|---|---|
| BM25 | 0,56 | 0,51 | 0,52 | 0,59 | 0,29 |
| e5-small (denso) | 0,71 | 0,69 | 0,70 | 0,84 | 0,58 |
| **denso + vigencia (`dense+v5`, por defecto)** | — | — | **0,73** | **0,87** | **0,66** |
| híbrido RRF (pesos iguales) | 0,60 | 0,63 | 0,67 | 0,78 | 0,63 |
| híbrido + glosario | 0,72 | 0,73 | 0,74 | 0,83 | 0,69 |

La fila `dense+v5` usa las 90 preguntas, la mitad de las cuales sirvió para elegirla; la cifra limpia es la de
test, más abajo.

- **El «imán» canario, arreglado con un método general** (fase 3). En la fase 2, la disposición adicional cuarta
  del texto refundido canario (medidas por la inflación para 2022-2023, 27 fragmentos) salía en el top 5 del denso
  en 11 de las 20 preguntas canarias. Probé dos familias de arreglo, ambas sin mirar preguntas concretas:
  rebajar los preceptos con vigencia vencida (`+v3`…`+vinf`) y penalizar documentos con muchos fragmentos
  (`+l0.25`…`+l1`). La deduplicación o MMR por disposición no aplica: la evaluación ya cuenta cada documento una
  sola vez, así que la DA 4.ª ocupaba un único puesto. El problema era que ese puesto estaba por encima del artículo
  bueno. Elegí con las 45 preguntas dev (MRR del denso): `+v5` (0,709 → 0,733; `+v10` y `+vinf` empatan y gana
  el más suave; la mejor penalización por longitud, `+l0.5`, se queda en 0,726). **Medido una sola vez en las 45
  de test: denso 0,689 → 0,719 (+0,030, IC 95 % [+0,004, +0,063])**, recall@5 igual (0,856), y las preguntas de
  test con algún precepto vencido en el top 5 bajan del 29 % al 9 %. Con el híbrido: 0,682 → 0,702. La DA 4.ª
  pasa de 11 a 3 de las 20 preguntas canarias de la fase 2.
- **El denso sigue ganando** a BM25 (MRR +0,18, IC [+0,10, +0,25]); frente al híbrido con pesos iguales la
  diferencia no es significativa (−0,03 [−0,09, +0,04]). El peso de BM25 elegido en dev vuelve a ser 0,3, y en
  test (0,68) queda por debajo del denso (0,69).
- **Añadir el BOC no estropea lo anterior**: las 70 preguntas de la fase 2 dan exactamente lo mismo con el denso
  (0,689) y casi lo mismo con el híbrido (0,633 → 0,625).
- **Convocatorias del BOC**: las 10 preguntas dan MRR 0,91 con el denso. Aunque las redacté sin copiar el título,
  siguen siendo fáciles: cada extracto trata de una sola cosa y el vocabulario («cochinilla», «TDAH») es muy
  específico.
- **Canarias fase 3**: las 10 preguntas nuevas dan 0,56 con el denso y 0,68 con `dense+v5` (descriptivo: la mitad
  son dev). El híbrido llega a 0,72 en este subconjunto.
- **Glosario fuera de muestra**: no lo he tocado desde v0.1. Con las 30 canarias (fases 2 y 3), el híbrido con
  glosario mejora al denso (+0,12 [−0,01, +0,26] y +0,11 [−0,11, +0,34]), pero los intervalos incluyen el cero.
- **Confusión entre comunidades**: en las 43 preguntas cuyos relevantes son normas de una sola comunidad, el
  2 % de los documentos del top 5 del denso son normas de la *otra* comunidad (BM25: 15 %, híbrido: 6 %).
- **Filtro de convocatorias** ([`results/filtro_convocatorias.md`](results/filtro_convocatorias.md)): en el BOE,
  P 0,83 y exhaustividad 0,58 fuera de muestra (fase 2). En los 92 extractos del BOC, sin tocar el filtro:
  **P 1,00 y exhaustividad 0,45**. No se cuela nada que no sea para particulares, pero se pierden más de la mitad:
  ayudas agrarias a «ganaderos» y «productores», becas y premios universitarios para «el alumnado» y extractos
  de ampliación de plazo sin sección de beneficiarios.

Fallos del denso (MRR < 0,2): «¿cuánto se cobra del IMV?» (la cuantía está repartida en un artículo largo),
«deducción por sueldo bajo», «¿cuánto reduce el mínimo por hijo?», «¿cuánto dura el bono alquiler joven?» y
«ayudas para rehabilitar mi piso». En Canarias: «madre sola con dos hijos» (familias monoparentales), «tengo
70 años», «me mudo de La Palma a Tenerife por trabajo» y «¿quién puede cobrar la renta canaria?». La
reordenación quita del top 5 el artículo imán, pero no sube el artículo bueno en estas preguntas.

## Limitaciones honestas

- **Corpus pequeño y con fecha de corte** (15-11-2026): 14 normas (estatales, Madrid y Canarias), 64
  convocatorias del BOE y 31 del BOC de 180 días. Faltan las demás CCAA,
  los ayuntamientos, las prestaciones de la Seguridad Social (nacimiento, desempleo), las órdenes que convocan
  cada año las ayudas del Plan de Vivienda en cada comunidad y los anexos de las normas (que no son «preceptos»).
- **No razona sobre requisitos**: no cruza tu edad, renta o comunidad con los requisitos; solo recupera textos. Una
  respuesta puede citar una deducción a la que no tienes derecho.
- **Vigencia**: se toma la versión de cada artículo vigente a la fecha de corte, pero no se comprueba si una
  convocatoria sigue abierta (los plazos suelen contarse desde la publicación). La detección de medidas temporales
  vencidas es por reglas sobre la redacción: solo ve los años del encabezado y del arranque del texto, así que
  una medida temporal redactada de otra forma no se marca.
- **Consolidación desactualizada**: tres normas canarias están marcadas así en el BOE. Las cuantías pueden no ser
  las vigentes (las deducciones canarias cambian casi cada año con la ley de presupuestos).
- **Convocatorias autonómicas**: de Canarias solo están las que el BOC publica como extracto BDNS, y el filtro
  pierde más de la mitad (exhaustividad 0,45). Las de los demás boletines autonómicos no están. El índice anual del
  BOC se guarda en caché: para mover la fecha de corte hay que borrar esa entrada. Se usa la versión HTML del BOC,
  que no es la oficial (lo es el PDF, que el robots.txt veta descargar).
- **Evaluación modesta**: 90 preguntas de un solo anotador; los intervalos de confianza son anchos.
- **Sin generación**: la respuesta es extractiva a propósito (no inventa importes), pero se lee peor que un texto redactado.
- **BDNS no se consulta directamente** porque su robots.txt prohíbe la API; solo se ven las convocatorias cuyo
  extracto se publica en el BOE (sobre todo, las estatales) o en el BOC (las canarias).

## Estructura

```
src/ayudas_rag/
  http.py                  cliente con caché, pausas y URL vetadas
  sources/boe_legislacion  API de legislación consolidada → artículos vigentes con ruta de encabezados
  sources/boe_extractos    sumarios diarios → extractos BDNS → filtro personas físicas
  sources/boc_extractos    índice anual y sumarios del BOC → extractos BDNS (mismo filtro)
  vigencia.py              preceptos limitados a ejercicios ya pasados
  text.py                  normalización, stemmer ligero, troceado
  retrieval.py             BM25, denso (e5), híbrido RRF
  pipeline.py              corpus, índices, buscador y reordenación de documentos (+v / +l)
  answer.py                respuesta extractiva con citas
  evaluate.py / metrics.py recall@k, MRR, nDCG, bootstrap pareado
eval/preguntas.jsonl       preguntas con documentos relevantes
eval/filtro_muestra_fase2.tsv  muestra etiquetada a mano para medir el filtro de convocatorias (BOE)
eval/filtro_muestra_boc_fase3.tsv  los 92 extractos del BOC etiquetados a mano
results/                   informe de evaluación
```
