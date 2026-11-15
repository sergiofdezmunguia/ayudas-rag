# Evaluación de recuperación

- Preguntas: 70
- Corpus: 1607 documentos (1543 preceptos de 14 normas + 64 extractos de convocatorias), 3357 fragmentos
- Unidad evaluada: documento (artículo o extracto); el ranking de fragmentos se deduplica por documento.
- MRR y nDCG con corte en 10; relevancia binaria.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.386 | 0.521 | 0.589 | 0.682 | 0.614 | 0.512 | 0.542 |
| dense | 0.514 | 0.725 | 0.829 | 0.906 | 0.871 | 0.689 | 0.739 |
| hybrid | 0.461 | 0.661 | 0.725 | 0.833 | 0.757 | 0.633 | 0.669 |

## Antes y después (v0.1 → fase 2)

«v0.1» = corpus de v0.1 y sus 42 preguntas (`results/metricas_v0.1.json`); «mismas preguntas» = esas preguntas sobre el corpus ampliado; «todas» = las 70 preguntas sobre el corpus ampliado.

| modo | MRR v0.1 | MRR mismas preguntas | MRR todas | recall@5 v0.1 | recall@5 mismas | recall@5 todas |
|---|---|---|---|---|---|---|
| bm25 | 0.561 | 0.526 | 0.512 | 0.601 | 0.589 | 0.589 |
| dense | 0.711 | 0.675 | 0.689 | 0.833 | 0.821 | 0.829 |
| hybrid | 0.599 | 0.600 | 0.633 | 0.649 | 0.649 | 0.725 |

## Diferencias pareadas (bootstrap, IC 95 %)

- hybrid − bm25, mrr: +0.121 [+0.056, +0.187]
- hybrid − bm25, recall@5: +0.136 [+0.064, +0.214]
- hybrid − dense, mrr: -0.056 [-0.127, +0.016]
- hybrid − dense, recall@5: -0.104 [-0.196, -0.014]
- dense − bm25, mrr: +0.177 [+0.084, +0.274]
- dense − bm25, recall@5: +0.239 [+0.146, +0.339]

## Ajuste del peso de BM25 en el híbrido (dev/test)

Peso elegido con las 35 preguntas impares (dev, mrr): 0.1→0.662, 0.2→0.666, 0.3→0.678, 0.5→0.664, 0.7→0.638, 1.0→0.626. Mejor: **hybrid@0.3**.

Resultados en las 35 preguntas pares (test, no vistas al elegir el peso):

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.386 | 0.471 | 0.543 | 0.700 | 0.543 | 0.480 | 0.528 |
| dense | 0.543 | 0.729 | 0.843 | 0.910 | 0.886 | 0.687 | 0.738 |
| hybrid@1.0 | 0.500 | 0.686 | 0.743 | 0.852 | 0.771 | 0.640 | 0.688 |
| hybrid@0.3 | 0.500 | 0.757 | 0.786 | 0.910 | 0.800 | 0.650 | 0.717 |

## Por subconjunto de preguntas

**v0.1 (q01-q42)** (42 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.417 | 0.524 | 0.589 | 0.625 | 0.619 | 0.526 | 0.540 |
| dense | 0.500 | 0.673 | 0.821 | 0.871 | 0.881 | 0.675 | 0.724 |
| hybrid | 0.446 | 0.589 | 0.649 | 0.774 | 0.690 | 0.600 | 0.628 |

**fase 2: Canarias** (20 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.150 | 0.375 | 0.425 | 0.675 | 0.450 | 0.328 | 0.395 |
| dense | 0.375 | 0.725 | 0.775 | 0.942 | 0.800 | 0.593 | 0.665 |
| hybrid | 0.350 | 0.675 | 0.775 | 0.892 | 0.800 | 0.581 | 0.642 |

**fase 2: convocatorias 91-180 días** (8 preguntas)

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.812 | 0.875 | 1.000 | 1.000 | 1.000 | 0.900 | 0.923 |
| dense | 0.938 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | 0.812 | 1.000 | 1.000 | 1.000 | 1.000 | 0.938 | 0.954 |


## Confusión entre comunidades autónomas

Preguntas cuyos relevantes son todos normas de una sola CCAA: 33 (Comunidad Autónoma de Canarias: 20, Comunidad de Madrid: 13). Proporción de documentos del top-5 que son normas autonómicas de *otra* comunidad:

- bm25: 0.121
- dense: 0.030
- hybrid: 0.073

## Variante con glosario coloquial → jurídico (post hoc, optimista)

El glosario (`text.GLOSARIO`) se escribió *después* de ver los fallos de BM25 en estas mismas preguntas, así que estas cifras sobrestiman lo que daría con preguntas nuevas.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25x | 0.436 | 0.636 | 0.732 | 0.815 | 0.771 | 0.606 | 0.645 |
| hybridx@1.0 | 0.554 | 0.771 | 0.805 | 0.876 | 0.843 | 0.727 | 0.751 |
| hybridx@0.3 | 0.561 | 0.786 | 0.825 | 0.906 | 0.857 | 0.732 | 0.767 |

### Glosario por subconjunto (MRR)

Las preguntas de la fase 2 se escribieron *después* del glosario y sin tocarlo, así que para ellas el glosario sí es una variante fuera de muestra.

| subconjunto | n | bm25 | dense | hybrid | bm25x | hybridx@1.0 | hybridx@0.3 | hybridx@1.0 − dense (IC 95 %) |
|---|---|---|---|---|---|---|---|---|
| v0.1 (q01-q42) | 42 | 0.526 | 0.675 | 0.600 | 0.628 | 0.700 | 0.694 | +0.025 [-0.061, +0.110] |
| fase 2: Canarias | 20 | 0.328 | 0.593 | 0.581 | 0.441 | 0.700 | 0.706 | +0.107 [-0.029, +0.256] |
| fase 2: convocatorias 91-180 días | 8 | 0.900 | 1.000 | 0.938 | 0.900 | 0.938 | 1.000 | -0.062 [-0.188, +0.000] |

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
| q38 | beca para estudiar un máster en Estados Unidos | 0.50 | 0.50 | 1.00 |
| q39 | ayudas sociales para mujeres deportistas o entrenadoras | 1.00 | 1.00 | 1.00 |
| q40 | premio para periodistas sobre comunicación feminista | 1.00 | 1.00 | 1.00 |
| q41 | becas de formación para recién graduados en el Instituto Geográfico Nacional | 1.00 | 1.00 | 1.00 |
| q42 | ayuda de viaje para doctorandos menores de 30 para un congreso de investigación cardiovascular | 1.00 | 1.00 | 1.00 |
| q43 | vivo de alquiler en Tenerife, ¿cuánto me puedo desgravar en la renta? | 0.00 | 0.33 | 0.00 |
| q44 | deducción autonómica en Canarias por el nacimiento de un hijo | 0.14 | 0.33 | 0.50 |
| q45 | ¿en Canarias se puede deducir la guardería del niño? | 0.50 | 0.50 | 0.50 |
| q46 | mi hijo estudia la carrera en Madrid y vivimos en Gran Canaria, ¿hay alguna deducción? | 0.11 | 1.00 | 0.20 |
| q47 | me he mudado de La Palma a Tenerife por trabajo, ¿tengo alguna deducción? | 0.10 | 0.17 | 0.33 |
| q48 | estuve en paro casi todo el año en Canarias, ¿hay alguna deducción para desempleados? | 0.50 | 0.33 | 0.50 |
| q49 | soy madre sola con dos hijos en Lanzarote, ¿qué me puedo deducir? | 0.00 | 0.17 | 0.25 |
| q50 | deducción en Canarias por familia numerosa | 1.00 | 1.00 | 1.00 |
| q51 | gastos del dentista y del médico, ¿se desgravan en Canarias? | 1.00 | 1.00 | 1.00 |
| q52 | tengo 70 años y vivo en Canarias, ¿tengo alguna deducción por edad? | 0.00 | 0.10 | 0.12 |
| q53 | si dono dinero a una ONG en Canarias, ¿cuánto me deduzco además de lo estatal? | 0.00 | 0.25 | 0.10 |
| q54 | ¿quién puede cobrar la renta canaria de ciudadanía? | 0.00 | 0.17 | 0.11 |
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
