# ayudas-rag

Buscador de **ayudas, subvenciones y deducciones fiscales para particulares en España** construido sobre datos
públicos oficiales del BOE. Ante una pregunta del tipo *«soy asalariado de 30 años en Madrid, ¿qué ayudas o
deducciones puedo pedir para alquiler?»* devuelve los artículos y convocatorias más relevantes, con fragmentos
literales y enlace a la fuente oficial.

> **Aviso.** Esto no es asesoramiento fiscal ni jurídico. El sistema solo localiza y cita textos oficiales; no
> comprueba si cumples los requisitos, puede devolver normas que no te aplican y el corpus es un subconjunto
> pequeño y con fecha de corte. Antes de decidir nada, lee la fuente oficial o consulta a un profesional.

Basado en datos de la Agencia Estatal Boletín Oficial del Estado (<https://www.boe.es>).

## Qué hace

```
BOE datos abiertos ──► ingesta con caché ──► documentos (artículo / extracto) ──► fragmentos (~220 palabras)
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
  - Extractos de convocatorias de la BDNS que el BOE publica en la sección V-B (últimos 90 días), filtrados por
    una heurística de «beneficiarios = personas físicas».
- **Unidad recuperable**: un artículo/disposición o un extracto. Cada fragmento lleva la ruta de encabezados
  (p. ej. *Capítulo IV … > Sección 3.ª Ayuda al alquiler para la emancipación de las personas jóvenes*), que es
  clave en normas como el Plan de Vivienda donde decenas de artículos se titulan «Personas beneficiarias».
- **Recuperación**: BM25 implementado a mano (tokenización con plegado de tildes, stopwords y un stemmer ligero),
  embeddings `intfloat/multilingual-e5-small` en CPU y un híbrido por Reciprocal Rank Fusion con peso configurable
  (`--mode hybrid@0.3`). El modo por defecto es el denso porque fue el mejor en la evaluación.
- **Respuesta**: extractiva, sin LLM. Para cada documento recuperado se eligen las frases con más solapamiento
  (ponderado por IDF) con la pregunta y se cita el enlace al artículo en boe.es.

## Fuentes y condiciones de uso

| Fuente | Decisión | Motivo |
|---|---|---|
| BOE, API de datos abiertos (legislación consolidada y sumarios) | **Sí** | Reutilización permitida citando la fuente ([aviso legal](https://www.boe.es/informacion/aviso_legal/index.php)). |
| BOE, `diario_boe/txt.php` (texto HTML de anuncios) | **Sí** | Permitido en robots.txt (solo se vetan variantes de idioma, `xml.php` y PDF). |
| BDNS / infosubvenciones.es, API | **No** | Su `robots.txt` dice `Disallow: /api/  # API no permitida`. Se sustituye por los extractos BDNS que publica el BOE. |

Descarga educada: User-Agent genérico de script personal, ≥1,2 s entre peticiones, caché en disco (incluida
caché negativa de 404), y las URL vetadas están bloqueadas en el propio cliente (`http.py`).

## Uso

```bash
uv sync
uv run ayudas ingest          # descarga (con caché) y construye data/corpus.jsonl y data/chunks.jsonl
uv run ayudas index           # embeddings e5-small (CPU)
uv run ayudas ask "soy asalariado de 30 años en Madrid, ¿qué ayudas o deducciones puedo pedir para alquiler?"
uv run ayudas eval            # results/informe.md y results/metricas.json
uv run pytest                 # tests sin red con fixtures inventadas
```

## Evaluación

42 preguntas en lenguaje coloquial (`eval/preguntas.jsonl`): 34 sobre deducciones y prestaciones reguladas en las
normas y 8 sobre ayudas concretas (6 convocatorias y 2 programas del Plan de Vivienda). Informe completo en
[`results/informe.md`](results/informe.md); ejemplos de respuestas en [`results/ejemplos.md`](results/ejemplos.md).

**Cómo se fijaron los documentos relevantes.** Las preguntas y sus artículos relevantes los escribí yo (el autor)
leyendo los títulos y el texto de los artículos del corpus, *antes* de ejecutar ningún recuperador. Cada pregunta
apunta a los 1-4 artículos o extractos que hay que leer para responderla (p. ej. la deducción por alquiler de
Madrid → art. 8 del texto refundido). Riesgos: un único anotador, relevancia binaria y documentos relevantes
alternativos que pueden no estar marcados (eso penaliza a todos los modos por igual, pero baja las cifras absolutas).

| modo (42 preguntas) | recall@5 | recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| BM25 | 0,60 | 0,64 | 0,56 | 0,57 |
| e5-small (denso) | **0,83** | **0,87** | **0,71** | **0,75** |
| híbrido RRF (pesos iguales) | 0,65 | 0,77 | 0,60 | 0,63 |

- **El denso gana con claridad** (MRR +0,15 frente a BM25, IC 95 % por bootstrap pareado [+0,02, +0,29]). La causa
  principal es el desajuste de vocabulario: la gente dice «alquiler», «desgravar», «bebé» u «ONG» y las normas dicen
  «arrendamiento», «deducción», «nacimiento» y «entidades sin fines lucrativos».
- **El híbrido con pesos iguales empeora al denso** (MRR −0,11, IC [−0,23, −0,01]): BM25 mete demasiado ruido.
  Al elegir el peso de BM25 con la mitad de las preguntas y medirlo en la otra mitad, el mejor peso (0,1, el
  extremo de la rejilla) solo empata con el denso en test (MRR 0,650 frente a 0,648). Con este corpus y estas
  preguntas, la fusión no aporta.
- Un glosario coloquial → jurídico sube BM25 a MRR 0,66 y el híbrido a 0,72, pero lo escribí después de ver los
  fallos, así que esas cifras son optimistas y no las tomo como resultado.
- El filtro de convocatorias para personas físicas tiene una precisión ≈0,95 y una exhaustividad ≈0,78 en una
  revisión manual de 81 extractos ([`results/filtro_convocatorias.md`](results/filtro_convocatorias.md)).

Fallos que persisten en todos los modos: «¿cuánto se cobra del IMV?» (la cuantía está repartida en un artículo
largo), «deducción por sueldo bajo» (la norma dice «rendimientos del trabajo inferiores a…») y «¿cuánto reduce el
mínimo por hijo?».

## Limitaciones honestas

- **Corpus pequeño y con fecha de corte** (15-11-2026): 10 normas y 19 convocatorias de 90 días. Faltan otras CCAA,
  los ayuntamientos, las prestaciones de la Seguridad Social (nacimiento, desempleo), las órdenes que convocan
  cada año las ayudas del Plan de Vivienda en cada comunidad y los anexos de las normas (que no son «preceptos»).
- **No razona sobre requisitos**: no cruza tu edad, renta o comunidad con los requisitos; solo recupera textos. Una
  respuesta puede citar una deducción a la que no tienes derecho.
- **Vigencia**: se toma la versión de cada artículo vigente a la fecha de corte, pero no se comprueba si una
  convocatoria sigue abierta (los plazos suelen contarse desde la publicación).
- **Evaluación modesta**: 42 preguntas de un solo anotador; los intervalos de confianza son anchos.
- **Sin generación**: la respuesta es extractiva a propósito (no inventa importes), pero se lee peor que un texto redactado.
- **BDNS no se consulta directamente** porque su robots.txt prohíbe la API; solo se ven las convocatorias cuyo
  extracto se publica en el BOE (sobre todo, las estatales).

## Estructura

```
src/ayudas_rag/
  http.py                  cliente con caché, pausas y URL vetadas
  sources/boe_legislacion  API de legislación consolidada → artículos vigentes con ruta de encabezados
  sources/boe_extractos    sumarios diarios → extractos BDNS → filtro personas físicas
  text.py                  normalización, stemmer ligero, troceado
  retrieval.py             BM25, denso (e5), híbrido RRF
  pipeline.py              corpus, índices y buscador
  answer.py                respuesta extractiva con citas
  evaluate.py / metrics.py recall@k, MRR, nDCG, bootstrap pareado
eval/preguntas.jsonl       preguntas con documentos relevantes
results/                   informe de evaluación
```
