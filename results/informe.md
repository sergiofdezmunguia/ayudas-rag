# Evaluación de recuperación

- Preguntas: 90
- Corpus: 1638 documentos (1543 preceptos de 14 normas + 95 extractos de convocatorias), 3439 fragmentos
- Unidad evaluada: documento (artículo o extracto); el ranking de fragmentos se deduplica por documento.
- MRR y nDCG con corte en 10; relevancia binaria.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.406 | 0.539 | 0.592 | 0.697 | 0.611 | 0.523 | 0.557 |
| dense | 0.528 | 0.753 | 0.844 | 0.927 | 0.878 | 0.699 | 0.753 |
| hybrid | 0.508 | 0.714 | 0.775 | 0.861 | 0.800 | 0.672 | 0.707 |

## Antes y después (v0.1 → fase 3)

«v0.1» = corpus de v0.1 y sus 42 preguntas (`results/metricas_v0.1.json`); «mismas preguntas» = esas preguntas sobre el corpus ampliado; «todas» = las 90 preguntas sobre el corpus ampliado.

| modo | MRR v0.1 | MRR mismas preguntas | MRR todas | recall@5 v0.1 | recall@5 mismas | recall@5 todas |
|---|---|---|---|---|---|---|
| bm25 | 0.561 | 0.526 | 0.523 | 0.601 | 0.589 | 0.592 |
| dense | 0.711 | 0.675 | 0.699 | 0.833 | 0.821 | 0.844 |
| hybrid | 0.599 | 0.588 | 0.672 | 0.649 | 0.649 | 0.775 |

## Fase 2 → fase 3 (sin reordenar)

«fase 2» = `results/metricas_fase2.json` (70 preguntas, corpus de la fase 2); «mismas preguntas» = esas preguntas sobre el corpus de la fase 3 (con el BOC); «todas» = las 90 preguntas.

| modo | MRR fase 2 | MRR mismas | MRR todas | recall@5 fase 2 | recall@5 mismas | recall@5 todas |
|---|---|---|---|---|---|---|
| bm25 | 0.512 | 0.511 | 0.523 | 0.589 | 0.589 | 0.592 |
| dense | 0.689 | 0.689 | 0.699 | 0.829 | 0.829 | 0.844 |
| hybrid | 0.633 | 0.625 | 0.672 | 0.725 | 0.725 | 0.775 |

## Diferencias pareadas (bootstrap, IC 95 %)

- hybrid − bm25, mrr: +0.148 [+0.088, +0.208]
- hybrid − bm25, recall@5: +0.183 [+0.111, +0.267]
- hybrid − dense, mrr: -0.028 [-0.091, +0.035]
- hybrid − dense, recall@5: -0.069 [-0.153, +0.011]
- dense − bm25, mrr: +0.176 [+0.101, +0.251]
- dense − bm25, recall@5: +0.253 [+0.167, +0.344]

## Fase 3: preceptos vencidos que hacen de «imán» (decidido en dev, medido una vez en test)

Candidatos (ver `pipeline.parse_mode`): «+v<n>» baja n puestos los preceptos cuya vigencia se limita a ejercicios ya pasados (`vigencia.py`); «+l<b>» penaliza documentos con muchos fragmentos (rango efectivo × n^b). Se elige con las preguntas dev y la métrica mrr del modo dense; en test solo se mide la opción elegida.

**Dev** (45 preguntas):

| candidato | mrr | recall@5 | ndcg@10 | preguntas con vencido en top-5 |
|---|---|---|---|---|
| dense | 0.709 | 0.833 | 0.760 | 0.222 |
| dense+v3 | 0.731 | 0.889 | 0.777 | 0.200 |
| dense+v5 | 0.733 | 0.889 | 0.779 | 0.044 |
| dense+v10 | 0.733 | 0.889 | 0.779 | 0.000 |
| dense+vinf | 0.733 | 0.889 | 0.779 | 0.000 |
| dense+l0.25 | 0.712 | 0.856 | 0.757 | 0.200 |
| dense+l0.5 | 0.726 | 0.869 | 0.766 | 0.200 |
| dense+l0.75 | 0.706 | 0.869 | 0.740 | 0.111 |
| dense+l1 | 0.686 | 0.835 | 0.715 | 0.044 |
| dense+vinf+l0.25 | 0.730 | 0.878 | 0.771 | 0.000 |
| dense+vinf+l0.5 | 0.729 | 0.869 | 0.769 | 0.000 |

Elegido: **dense+v5**.

**Test** (45 preguntas, no vistas al elegir):

| modo | recall@1 | recall@5 | mrr | ndcg@10 | preguntas con vencido en top-5 |
|---|---|---|---|---|---|
| bm25 | 0.411 | 0.533 | 0.490 | 0.536 | 0.156 |
| bm25+v5 | 0.433 | 0.533 | 0.502 | 0.545 | 0.000 |
| dense | 0.533 | 0.856 | 0.689 | 0.746 | 0.289 |
| dense+v5 | 0.578 | 0.856 | 0.719 | 0.768 | 0.089 |
| hybrid@0.3 | 0.522 | 0.833 | 0.682 | 0.745 | 0.267 |
| hybrid@0.3+v5 | 0.544 | 0.833 | 0.702 | 0.761 | 0.067 |

Diferencia pareada en test (bootstrap, IC 95 %):

- bm25+v5 − bm25, mrr: +0.012 [+0.000, +0.035]
- bm25+v5 − bm25, recall@5: +0.000 [+0.000, +0.000]
- dense+v5 − dense, mrr: +0.030 [+0.004, +0.063]
- dense+v5 − dense, recall@5: +0.000 [+0.000, +0.000]
- hybrid@0.3+v5 − hybrid@0.3, mrr: +0.021 [+0.003, +0.048]
- hybrid@0.3+v5 − hybrid@0.3, recall@5: +0.000 [+0.000, +0.000]

El «imán» de la fase 2 (DA 4.ª canaria, BOC-j-2009-90008#da-3), en las 20 preguntas de Canarias de la fase 2 (dev y test juntos): preguntas que lo tienen en el top-5

- dense: 11 de 20
- hybrid@0.3: 13 de 20
- dense+v5: 3 de 20
- hybrid@0.3+v5: 4 de 20

## Ajuste del peso de BM25 en el híbrido (dev/test)

Peso elegido con las 45 preguntas impares (dev, mrr): 0.1→0.697, 0.2→0.712, 0.3→0.720, 0.5→0.712, 0.7→0.702, 1.0→0.691. Mejor: **hybrid@0.3**.

Resultados en las 45 preguntas pares (test, no vistas al elegir el peso):

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.411 | 0.478 | 0.533 | 0.700 | 0.533 | 0.490 | 0.536 |
| dense | 0.533 | 0.767 | 0.856 | 0.930 | 0.889 | 0.689 | 0.746 |
| hybrid@1.0 | 0.500 | 0.733 | 0.800 | 0.867 | 0.822 | 0.653 | 0.702 |
| hybrid@0.3 | 0.522 | 0.789 | 0.833 | 0.930 | 0.844 | 0.682 | 0.745 |

## Por subconjunto de preguntas

**v0.1 (q01-q42)** (42 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.417 | 0.524 | 0.589 | 0.625 | 0.619 | 0.526 | 0.540 |
| dense | 0.500 | 0.673 | 0.821 | 0.871 | 0.881 | 0.675 | 0.724 |
| hybrid | 0.423 | 0.589 | 0.649 | 0.762 | 0.690 | 0.588 | 0.615 |
| dense+v5 | 0.500 | 0.673 | 0.833 | 0.871 | 0.881 | 0.675 | 0.725 |

**fase 2: Canarias** (20 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.150 | 0.375 | 0.425 | 0.625 | 0.450 | 0.323 | 0.381 |
| dense | 0.375 | 0.725 | 0.775 | 0.942 | 0.800 | 0.593 | 0.665 |
| hybrid | 0.350 | 0.675 | 0.775 | 0.875 | 0.800 | 0.576 | 0.635 |
| dense+v5 | 0.425 | 0.725 | 0.875 | 0.942 | 0.900 | 0.651 | 0.710 |

**fase 2: convocatorias 91-180 días** (8 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.812 | 0.875 | 1.000 | 1.000 | 1.000 | 0.900 | 0.923 |
| dense | 0.938 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | 0.812 | 1.000 | 1.000 | 1.000 | 1.000 | 0.938 | 0.954 |
| dense+v5 | 0.938 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

**fase 3: Canarias** (10 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.100 | 0.300 | 0.300 | 0.600 | 0.300 | 0.223 | 0.310 |
| dense | 0.300 | 0.800 | 0.900 | 1.000 | 0.900 | 0.558 | 0.668 |
| hybrid | 0.600 | 0.800 | 0.900 | 1.000 | 0.900 | 0.723 | 0.789 |
| dense+v5 | 0.500 | 0.900 | 0.900 | 1.000 | 0.900 | 0.683 | 0.762 |

**fase 3: convocatorias BOC** (10 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.850 | 0.900 | 0.900 | 1.000 | 0.900 | 0.914 | 0.933 |
| dense | 0.850 | 0.900 | 0.900 | 1.000 | 0.900 | 0.914 | 0.933 |
| hybrid | 0.850 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 | 0.963 |
| dense+v5 | 0.850 | 0.900 | 0.900 | 1.000 | 0.900 | 0.914 | 0.933 |


## Confusión entre comunidades autónomas

Preguntas cuyos relevantes son todos normas de una sola CCAA: 43 (Comunidad Autónoma de Canarias: 30, Comunidad de Madrid: 13). Proporción de documentos del top-5 que son normas autonómicas de *otra* comunidad:

- bm25: 0.153
- dense: 0.023
- hybrid: 0.056

## Variante con glosario coloquial → jurídico (post hoc, optimista)

El glosario (`text.GLOSARIO`) se escribió *después* de ver los fallos de BM25 en estas mismas preguntas, así que estas cifras sobrestiman lo que daría con preguntas nuevas.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25x | 0.467 | 0.628 | 0.703 | 0.801 | 0.733 | 0.610 | 0.646 |
| hybridx@1.0 | 0.581 | 0.783 | 0.826 | 0.887 | 0.856 | 0.744 | 0.768 |
| hybridx@0.3 | 0.564 | 0.822 | 0.853 | 0.927 | 0.878 | 0.740 | 0.780 |

### Glosario por subconjunto (MRR)

Las preguntas de las fases 2 y 3 se escribieron *después* del glosario y sin tocarlo, así que para ellas el glosario sí es una variante fuera de muestra.

| subconjunto | n | bm25 | dense | hybrid | bm25x | hybridx@1.0 | hybridx@0.3 | hybridx@1.0 − dense (IC 95 %) |
|---|---|---|---|---|---|---|---|---|
| v0.1 (q01-q42) | 42 | 0.526 | 0.675 | 0.588 | 0.640 | 0.700 | 0.682 | +0.025 [-0.061, +0.110] |
| fase 2: Canarias | 20 | 0.323 | 0.593 | 0.576 | 0.433 | 0.708 | 0.706 | +0.115 [-0.008, +0.258] |
| fase 2: convocatorias 91-180 días | 8 | 0.900 | 1.000 | 0.938 | 0.900 | 0.938 | 1.000 | -0.062 [-0.188, +0.000] |
| fase 3: Canarias | 10 | 0.223 | 0.558 | 0.723 | 0.303 | 0.664 | 0.650 | +0.106 [-0.105, +0.342] |
| fase 3: convocatorias BOC | 10 | 0.914 | 0.914 | 0.950 | 0.912 | 0.920 | 0.933 | +0.006 [+0.000, +0.017] |

## Por pregunta (MRR)

| id | pregunta | bm25 | dense | hybrid |
|---|---|---|---|---|
| q01 | soy asalariado de 30 años en Madrid, ¿qué ayudas o deducciones puedo pedir para alquiler? | 0.20 | 0.33 | 1.00 |
| q02 | ¿Cuánto me puedo desgravar del alquiler en la Comunidad de Madrid si tengo menos de 40 años? | 0.00 | 1.00 | 0.00 |
| q03 | Tengo un piso alquilado a un inquilino en Madrid, ¿puedo deducir los gastos de reparaciones y el seguro de impago? | 1.00 | 1.00 | 1.00 |
| q04 | deducción en Madrid por sacar al alquiler una casa que tenía vacía | 1.00 | 1.00 | 1.00 |
| q05 | ¿hay alguna deducción en la renta de Madrid por tener un bebé? | 0.00 | 1.00 | 0.14 |
| q06 | en Madrid, ¿puedo desgravar lo que pago de seguridad social de la empleada de hogar que cuida a mi hijo de 2 años? | 0.50 | 1.00 | 1.00 |
| q07 | desgravación por gastos de colegio, uniformes y clases de idiomas de mis hijos en Madrid | 1.00 | 1.00 | 1.00 |
| q08 | tengo 32 años y me doy de alta como autónomo por primera vez en Madrid, ¿tengo alguna deducción? | 1.00 | 0.50 | 1.00 |
| q09 | pedí un préstamo para pagar el máster, ¿puedo deducir los intereses? | 1.00 | 1.00 | 1.00 |
| q10 | trabajo y a la vez estudio un grado con 25 años, ¿me puedo deducir la matrícula? | 1.00 | 1.00 | 1.00 |
| q11 | ¿qué deducciones hay por ser familia numerosa? | 0.50 | 0.50 | 0.50 |
| q12 | cuido en casa a mi madre de 70 años, ¿hay deducción autonómica en Madrid? | 0.17 | 1.00 | 1.00 |
| q13 | me voy a vivir a un pueblo pequeño de Madrid en riesgo de despoblación, ¿qué beneficios fiscales tengo? | 0.25 | 0.50 | 0.33 |
| q14 | deducción por los intereses de la hipoteca para jóvenes en la Comunidad de Madrid | 1.00 | 1.00 | 1.00 |
| q15 | ¿qué es la deducción por maternidad de 1.200 euros y quién puede pedirla? | 1.00 | 0.25 | 0.50 |
| q16 | ¿se puede cobrar por adelantado cada mes la deducción por maternidad? | 1.00 | 0.33 | 0.50 |
| q17 | gano unos 16.000 euros brutos al año como asalariado, ¿tengo alguna deducción por sueldo bajo? | 0.00 | 0.00 | 0.00 |
| q18 | si pongo placas solares para autoconsumo en casa, ¿cuánto me desgravo? | 1.00 | 1.00 | 1.00 |
| q19 | desgravación en la renta por comprarme un coche eléctrico | 0.33 | 1.00 | 0.50 |
| q20 | obras para mejorar la eficiencia energética de la vivienda, ¿qué deducción hay en el IRPF? | 1.00 | 1.00 | 1.00 |
| q21 | ¿cuánto me deduzco en la renta por donar dinero a una ONG? | 0.00 | 0.50 | 0.14 |
| q22 | compré mi casa con hipoteca en 2010, ¿sigo teniendo la deducción por vivienda habitual? | 0.00 | 0.25 | 0.12 |
| q23 | ¿puedo deducir el alquiler en la declaración estatal si mi contrato es de 2013? | 0.00 | 0.50 | 0.12 |
| q24 | requisitos para pedir el ingreso mínimo vital | 0.00 | 0.25 | 0.17 |
| q25 | ¿cuánto dinero se cobra del ingreso mínimo vital? | 0.00 | 0.00 | 0.00 |
| q26 | renta mínima de inserción de la Comunidad de Madrid: ¿quién puede pedirla? | 0.12 | 0.33 | 0.33 |
| q27 | ¿cuántos hijos hacen falta para ser familia numerosa? | 1.00 | 1.00 | 1.00 |
| q28 | ¿qué descuentos tiene una familia numerosa en tasas, transporte o matrículas? | 1.00 | 0.20 | 0.50 |
| q29 | bono alquiler joven: requisitos de edad y de ingresos | 1.00 | 1.00 | 1.00 |
| q30 | ¿durante cuánto tiempo se cobra el bono alquiler joven? | 0.00 | 0.00 | 0.00 |
| q31 | ayudas para jóvenes que se compran una casa en un pueblo pequeño | 1.00 | 1.00 | 1.00 |
| q32 | me van a desahuciar, ¿hay alguna ayuda para pagar un alquiler? | 0.00 | 0.25 | 0.00 |
| q33 | ¿las becas de estudio tributan en el IRPF? | 0.50 | 1.00 | 1.00 |
| q34 | ¿cuánto reduce el IRPF el mínimo por cada hijo? | 0.00 | 0.00 | 0.00 |
| q35 | ayudas públicas para rehabilitar mi piso y hacerlo más accesible | 0.00 | 0.17 | 0.00 |
| q36 | ¿cuánto paga al mes la ayuda estatal al alquiler para jóvenes que se emancipan? | 0.00 | 1.00 | 0.33 |
| q37 | ayudas para jóvenes dramaturgos o autores de teatro menores de 35 años | 0.00 | 1.00 | 0.00 |
| q38 | beca para estudiar un máster en Estados Unidos | 0.50 | 0.50 | 0.50 |
| q39 | ayudas sociales para mujeres deportistas o entrenadoras | 1.00 | 1.00 | 1.00 |
| q40 | premio para periodistas sobre comunicación feminista | 1.00 | 1.00 | 1.00 |
| q41 | becas de formación para recién graduados en el Instituto Geográfico Nacional | 1.00 | 1.00 | 1.00 |
| q42 | ayuda de viaje para doctorandos menores de 30 para un congreso de investigación cardiovascular | 1.00 | 1.00 | 1.00 |
| q43 | vivo de alquiler en Tenerife, ¿cuánto me puedo desgravar en la renta? | 0.00 | 0.33 | 0.00 |
| q44 | deducción autonómica en Canarias por el nacimiento de un hijo | 0.14 | 0.33 | 0.50 |
| q45 | ¿en Canarias se puede deducir la guardería del niño? | 0.50 | 0.50 | 0.50 |
| q46 | mi hijo estudia la carrera en Madrid y vivimos en Gran Canaria, ¿hay alguna deducción? | 0.11 | 1.00 | 0.20 |
| q47 | me he mudado de La Palma a Tenerife por trabajo, ¿tengo alguna deducción? | 0.00 | 0.17 | 0.33 |
| q48 | estuve en paro casi todo el año en Canarias, ¿hay alguna deducción para desempleados? | 0.50 | 0.33 | 0.50 |
| q49 | soy madre sola con dos hijos en Lanzarote, ¿qué me puedo deducir? | 0.00 | 0.17 | 0.25 |
| q50 | deducción en Canarias por familia numerosa | 1.00 | 1.00 | 1.00 |
| q51 | gastos del dentista y del médico, ¿se desgravan en Canarias? | 1.00 | 1.00 | 1.00 |
| q52 | tengo 70 años y vivo en Canarias, ¿tengo alguna deducción por edad? | 0.00 | 0.10 | 0.12 |
| q53 | si dono dinero a una ONG en Canarias, ¿cuánto me deduzco además de lo estatal? | 0.00 | 0.25 | 0.11 |
| q54 | ¿quién puede cobrar la renta canaria de ciudadanía? | 0.00 | 0.17 | 0.00 |
| q55 | tengo 20 años, ¿puedo pedir la renta de ciudadanía en Canarias? | 1.00 | 0.50 | 1.00 |
| q56 | ¿cuánto se cobra de renta canaria de ciudadanía? | 0.12 | 1.00 | 1.00 |
| q57 | requisitos para acceder a una vivienda protegida en Canarias | 1.00 | 1.00 | 1.00 |
| q58 | compro mi primera vivienda en Canarias siendo familia numerosa, ¿pago menos impuestos? | 0.25 | 0.50 | 1.00 |
| q59 | ¿qué prestaciones económicas dan los servicios sociales en Canarias? | 0.33 | 0.50 | 0.50 |
| q60 | pongo en alquiler un piso que tenía vacío en Canarias, ¿hay deducción? | 0.00 | 1.00 | 0.50 |
| q61 | tengo un seguro de impago del alquiler de mi piso en Canarias, ¿me lo puedo deducir? | 0.33 | 1.00 | 1.00 |
| q62 | obras para adaptar la casa por discapacidad en Canarias, ¿se deducen? | 0.17 | 1.00 | 1.00 |
| q63 | cumplo 18 años este año, ¿cómo pido el bono cultural joven? | 1.00 | 1.00 | 1.00 |
| q64 | becas para estudiantes de último curso de grado para colaborar en un departamento de la universidad | 1.00 | 1.00 | 1.00 |
| q65 | ayudas de comedor escolar en Melilla | 1.00 | 1.00 | 1.00 |
| q66 | ayudas para personas con discapacidad para formarse o mejorar profesionalmente | 1.00 | 1.00 | 1.00 |
| q67 | soy extranjero y quiero ser auxiliar de conversación en España | 1.00 | 1.00 | 1.00 |
| q68 | soy profesor de instituto, ¿hay cursos online de formación del ministerio? | 0.20 | 1.00 | 0.50 |
| q69 | ayudas para agricultores para conseguir un aval de SAECA | 1.00 | 1.00 | 1.00 |
| q70 | ayuda para el transporte escolar del colegio en Ceuta | 1.00 | 1.00 | 1.00 |
| q71 | ¿me puedo deducir en Canarias los libros de texto y el uniforme del colegio de mis hijos? | 0.50 | 1.00 | 1.00 |
| q72 | tenemos un niño en acogida en Gran Canaria, ¿hay deducción en la renta? | 0.00 | 0.50 | 0.33 |
| q73 | he cambiado las ventanas y puesto aislamiento en mi casa de Tenerife para ahorrar energía, ¿desgrava? | 0.00 | 0.33 | 0.14 |
| q74 | pago la seguridad social de la persona que limpia y cuida en casa, vivo en Canarias, ¿me deduzco algo? | 0.00 | 0.50 | 1.00 |
| q75 | mi padre vive conmigo y tiene una discapacidad del 70 %, ¿hay deducción autonómica canaria? | 0.14 | 0.25 | 1.00 |
| q76 | dono dinero a un cabildo para un proyecto de medio ambiente, ¿me lo deduzco en Canarias? | 1.00 | 1.00 | 1.00 |
| q77 | voy a arreglar un piso en Las Palmas para alquilarlo, ¿puedo deducir los gastos de reparación y de formalizar el contrato? | 0.33 | 1.00 | 1.00 |
| q78 | tengo una discapacidad y me compro un piso en Canarias para vivir, ¿qué impuesto pago por la compra? | 0.00 | 0.33 | 0.25 |
| q79 | estoy pagando la hipoteca de mi vivienda habitual en Canarias, ¿hay deducción autonómica? | 0.14 | 0.17 | 1.00 |
| q80 | ¿quién puede aplicarse las deducciones autonómicas de Canarias en el IRPF? ¿hay que vivir allí? | 0.11 | 0.50 | 0.50 |
| q81 | vivo en La Gomera y mi hija se va a estudiar el grado a Tenerife, ¿hay alguna ayuda para el desplazamiento? | 1.00 | 1.00 | 1.00 |
| q82 | estudio en la Universidad de La Laguna y no me llega para comer, ¿hay ayudas de comedor? | 1.00 | 1.00 | 1.00 |
| q83 | mi hijo tiene TDAH y va a un instituto público en Canarias, ¿hay alguna ayuda? | 1.00 | 1.00 | 1.00 |
| q84 | soy autónomo en Canarias y pedí un préstamo para invertir en el negocio, ¿me pueden ayudar a pagar los intereses? | 0.14 | 0.14 | 0.50 |
| q85 | soy canario y quiero escribir el guion de una película, ¿hay alguna subvención? | 1.00 | 1.00 | 1.00 |
| q86 | tengo unas viñas en Lanzarote para vino con denominación de origen, ¿qué ayuda hay por hectárea? | 1.00 | 1.00 | 1.00 |
| q87 | cultivo tuneras para sacar cochinilla, ¿hay ayudas en Canarias? | 1.00 | 1.00 | 1.00 |
| q88 | soy universitario en Tenerife y me gustaría hacer prácticas en un pueblo, ¿hay becas? | 1.00 | 1.00 | 1.00 |
| q89 | tengo 24 años y hago un curso de formación profesional adaptada en un centro público canario, ¿me dan beca? | 1.00 | 1.00 | 1.00 |
| q90 | ¿hay ayudas para pagar la matrícula del máster o del doctorado en la ULL? | 1.00 | 1.00 | 1.00 |
