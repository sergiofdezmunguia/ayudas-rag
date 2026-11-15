# ayudas-rag

Buscador de **ayudas, subvenciones y deducciones fiscales para particulares en España** construido sobre datos
públicos oficiales del BOE. Ante una pregunta del tipo *«soy asalariado de 30 años en Madrid, ¿qué ayudas o
deducciones puedo pedir para alquiler?»* o *«vivo de alquiler en Tenerife, ¿cuánto me puedo desgravar?»* devuelve los artículos y convocatorias más relevantes, con fragmentos
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
  - **Canarias** (fase 2): texto refundido de tributos cedidos (deducciones autonómicas del IRPF y tipos reducidos
    del ITP), Ley 5/2022 de la Renta Canaria de Ciudadanía, Ley 2/2003 de Vivienda de Canarias y Ley 16/2019 de
    Servicios Sociales de Canarias. Tres de ellas tienen en el BOE la consolidación en estado **«Desactualizado»**
    (pueden faltar modificaciones recientes): el estado se guarda con cada artículo y la respuesta lo avisa.
  - Extractos de convocatorias de la BDNS que el BOE publica en la sección V-B (últimos **180 días**; en v0.1 eran
    90), filtrados por una heurística de «beneficiarios = personas físicas».
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
uv run pytest                 # tests sin red con fixtures inventadas
```

## Evaluación

70 preguntas en lenguaje coloquial (`eval/preguntas.jsonl`):
- **42 de v0.1**: 34 sobre deducciones y prestaciones reguladas en las normas y 8 sobre ayudas concretas
  (6 convocatorias y 2 programas del Plan de Vivienda).
- **20 de Canarias** (fase 2): deducciones autonómicas, Renta Canaria de Ciudadanía, vivienda protegida,
  servicios sociales e ITP. Una de ellas, a propósito, menciona Madrid («mi hijo estudia en Madrid y vivimos en Gran Canaria»).
- **8 de convocatorias** publicadas entre 91 y 180 días antes del corte (fase 2).

Informe completo en [`results/informe.md`](results/informe.md); ejemplos de respuestas en
[`results/ejemplos.md`](results/ejemplos.md).

**Cómo se fijaron los documentos relevantes.** Las preguntas y sus artículos relevantes los escribí yo (el autor)
leyendo los títulos y el texto de los artículos del corpus, *antes* de ejecutar ningún recuperador sobre ellas.
Cada pregunta apunta a los 1-4 artículos o extractos que hay que leer para responderla. Las de la fase 2 se
añadieron al final del fichero, así que el reparto dev/test por posición (impares/pares) de v0.1 no cambia y las
nuevas se reparten a medias. Riesgos: un único anotador, relevancia binaria y documentos relevantes
alternativos sin marcar. Esto último pesa más ahora: preguntas de v0.1 sin comunidad, como «¿qué deducciones hay
por ser familia numerosa?», tienen en Canarias una respuesta válida que no está marcada.

| modo | MRR v0.1 (42 preg.) | MRR mismas 42, corpus nuevo | MRR 70 preg. | recall@5 70 preg. | MRR Canarias (20) |
|---|---|---|---|---|---|
| BM25 | 0,56 | 0,53 | 0,51 | 0,59 | 0,33 |
| e5-small (denso) | **0,71** | **0,68** | **0,69** | **0,83** | 0,59 |
| híbrido RRF (pesos iguales) | 0,60 | 0,60 | 0,63 | 0,73 | 0,58 |
| híbrido + glosario | 0,72 | 0,70 | 0,73 | 0,81 | **0,70** |

- **El denso sigue ganando** a BM25 (MRR +0,18, IC 95 % [+0,08, +0,27]) y al híbrido con pesos iguales, aunque
  frente al híbrido la diferencia en MRR ya no es significativa (−0,06 [−0,13, +0,02]).
- **Ampliar el corpus baja un poco las preguntas antiguas** (denso 0,71 → 0,68). Hay 3 preguntas que pasan de MRR 1
  a 0,5 porque una deducción canaria sube por delante. En dos de ellas («familia numerosa» y «donar a una ONG»)
  la pregunta no dice comunidad y el artículo canario es una respuesta razonable sin marcar. La tercera pide la
  «declaración estatal», así que ahí sí es un error.
- **Ajuste dev/test del peso de BM25** (35/35 preguntas): el mejor peso en dev es 0,3, y en test queda por debajo
  del denso (MRR 0,65 frente a 0,69). Igual que en v0.1, la fusión ajustada no gana.
- **Canarias es más difícil** (denso 0,59). El fallo principal es un artículo «imán»: la disposición adicional cuarta
  del texto refundido canario (medidas extraordinarias por la inflación para 2022-2023, 4.800 palabras, 27
  fragmentos) aparece en el top 5 del denso en 11 de las 20 preguntas canarias, y en 4 de ellas la primera. El
  siguiente paso sería normalizar por número de fragmentos o marcar las medidas con ejercicio ya pasado, pero no
  lo he hecho para no ajustar contra estas mismas preguntas.
- **Glosario fuera de muestra**: el glosario coloquial → jurídico de v0.1 se escribió viendo las 42 preguntas
  antiguas y no lo he tocado. Con las 20 canarias, el híbrido con glosario sube a MRR 0,70 frente al 0,59 del
  denso (+0,11, IC [−0,03, +0,26]). Apunta a que el glosario generaliza, pero el intervalo incluye el cero, y las
  preguntas las escribió la misma persona que el glosario.
- **Confusión entre comunidades**: en las 33 preguntas cuyos relevantes son de una sola comunidad (20 de Canarias,
  13 de Madrid), el 3 % de los documentos del top 5 del denso son normas de la *otra* comunidad (BM25: 12 %,
  híbrido: 7 %).
- **Convocatorias nuevas**: las 8 preguntas salen casi perfectas (denso MRR 1,0). Son demasiado fáciles, porque
  el título de cada extracto ya nombra la ayuda; no las tomo como prueba de nada.
- **Filtro de convocatorias** ([`results/filtro_convocatorias.md`](results/filtro_convocatorias.md)): en una
  muestra nueva de 80 extractos etiquetados a mano, el filtro de v0.1 da P 0,83 y exhaustividad 0,58, bastante
  peor que el 0,95/0,78 de v0.1, que era optimista. Tras tres correcciones generales llega a P 0,95 y
  exhaustividad 0,73 en esa misma muestra (también optimista). Con el filtro corregido quedan 64 de 243 extractos.

Fallos del denso (MRR < 0,2): «¿cuánto se cobra del IMV?» (la cuantía está repartida en un artículo largo),
«deducción por sueldo bajo», «¿cuánto reduce el mínimo por hijo?», «¿cuánto dura el bono alquiler joven?» y
«ayudas para rehabilitar mi piso». En Canarias: «madre sola con dos hijos» (familias monoparentales), «tengo
70 años», «me mudo de La Palma a Tenerife por trabajo» y «¿quién puede cobrar la renta canaria?». En las tres primeras aparece en el top 5 el artículo imán de 2022-2023.

## Limitaciones honestas

- **Corpus pequeño y con fecha de corte** (15-11-2026): 14 normas (estatales, Madrid y Canarias) y 64
  convocatorias de 180 días. Faltan las demás CCAA,
  los ayuntamientos, las prestaciones de la Seguridad Social (nacimiento, desempleo), las órdenes que convocan
  cada año las ayudas del Plan de Vivienda en cada comunidad y los anexos de las normas (que no son «preceptos»).
- **No razona sobre requisitos**: no cruza tu edad, renta o comunidad con los requisitos; solo recupera textos. Una
  respuesta puede citar una deducción a la que no tienes derecho.
- **Vigencia**: se toma la versión de cada artículo vigente a la fecha de corte, pero no se comprueba si una
  convocatoria sigue abierta (los plazos suelen contarse desde la publicación).
- **Consolidación desactualizada**: tres normas canarias están marcadas así en el BOE. Las cuantías pueden no ser
  las vigentes (las deducciones canarias cambian casi cada año con la ley de presupuestos).
- **Convocatorias autonómicas**: las de Canarias se publican en el BOC, no en el BOE, así que no están. Del BOE solo
  salen las estatales (y algunas de Ceuta y Melilla).
- **Evaluación modesta**: 70 preguntas de un solo anotador; los intervalos de confianza son anchos.
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
eval/filtro_muestra_fase2.tsv  muestra etiquetada a mano para medir el filtro de convocatorias
results/                   informe de evaluación
```
