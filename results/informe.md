# Evaluación de recuperación

- Preguntas: 42
- Corpus: 1094 documentos (1075 preceptos de 10 normas + 19 extractos de convocatorias), 2431 fragmentos
- Unidad evaluada: documento (artículo o extracto); el ranking de fragmentos se deduplica por documento.
- MRR y nDCG con corte en 10; relevancia binaria.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.464 | 0.524 | 0.601 | 0.637 | 0.619 | 0.561 | 0.566 |
| dense | 0.548 | 0.685 | 0.833 | 0.871 | 0.881 | 0.711 | 0.746 |
| hybrid | 0.435 | 0.601 | 0.649 | 0.774 | 0.690 | 0.599 | 0.627 |

## Diferencias pareadas (bootstrap, IC 95 %)

- hybrid − bm25, mrr: +0.038 [-0.030, +0.113]
- hybrid − bm25, recall@5: +0.048 [+0.000, +0.107]
- hybrid − dense, mrr: -0.113 [-0.230, -0.007]
- hybrid − dense, recall@5: -0.185 [-0.298, -0.083]
- dense − bm25, mrr: +0.150 [+0.015, +0.288]
- dense − bm25, recall@5: +0.232 [+0.119, +0.357]

## Ajuste del peso de BM25 en el híbrido (dev/test)

Peso elegido con las 21 preguntas impares (dev, mrr): 0.1→0.721, 0.2→0.685, 0.3→0.692, 0.5→0.663, 0.7→0.622, 1.0→0.604. Mejor: **hybrid@0.1**.

Resultados en las 21 preguntas pares (test, no vistas al elegir el peso):

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.500 | 0.548 | 0.571 | 0.643 | 0.571 | 0.560 | 0.575 |
| dense | 0.476 | 0.643 | 0.833 | 0.881 | 0.905 | 0.648 | 0.702 |
| hybrid@1.0 | 0.452 | 0.619 | 0.667 | 0.786 | 0.714 | 0.593 | 0.635 |
| hybrid@0.1 | 0.476 | 0.667 | 0.810 | 0.881 | 0.857 | 0.650 | 0.702 |

## Variante con glosario coloquial → jurídico (post hoc, optimista)

El glosario (`text.GLOSARIO`) se escribió *después* de ver los fallos de BM25 en estas mismas preguntas, así que estas cifras sobrestiman lo que daría con preguntas nuevas.

| modo | recall@1 | recall@3 | recall@5 | recall@10 | hit@5 | mrr | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bm25x | 0.512 | 0.655 | 0.714 | 0.780 | 0.762 | 0.658 | 0.675 |
| hybridx@1.0 | 0.565 | 0.702 | 0.756 | 0.833 | 0.786 | 0.724 | 0.739 |
| hybridx@0.1 | 0.500 | 0.696 | 0.845 | 0.883 | 0.881 | 0.680 | 0.733 |

## Por pregunta (MRR)

| id | pregunta | bm25 | dense | hybrid |
|---|---|---|---|---|
| q01 | soy asalariado de 30 años en Madrid, ¿qué ayudas o deducciones puedo pedir para alquiler? | 0.20 | 0.33 | 1.00 |
| q02 | ¿Cuánto me puedo desgravar del alquiler en la Comunidad de Madrid si tengo menos de 40 años? | 0.00 | 1.00 | 0.00 |
| q03 | Tengo un piso alquilado a un inquilino en Madrid, ¿puedo deducir los gastos de reparaciones y el seguro de impago? | 1.00 | 1.00 | 1.00 |
| q04 | deducción en Madrid por sacar al alquiler una casa que tenía vacía | 1.00 | 1.00 | 1.00 |
| q05 | ¿hay alguna deducción en la renta de Madrid por tener un bebé? | 0.00 | 1.00 | 0.12 |
| q06 | en Madrid, ¿puedo desgravar lo que pago de seguridad social de la empleada de hogar que cuida a mi hijo de 2 años? | 1.00 | 1.00 | 1.00 |
| q07 | desgravación por gastos de colegio, uniformes y clases de idiomas de mis hijos en Madrid | 1.00 | 1.00 | 1.00 |
| q08 | tengo 32 años y me doy de alta como autónomo por primera vez en Madrid, ¿tengo alguna deducción? | 1.00 | 0.50 | 1.00 |
| q09 | pedí un préstamo para pagar el máster, ¿puedo deducir los intereses? | 1.00 | 1.00 | 1.00 |
| q10 | trabajo y a la vez estudio un grado con 25 años, ¿me puedo deducir la matrícula? | 1.00 | 1.00 | 1.00 |
| q11 | ¿qué deducciones hay por ser familia numerosa? | 1.00 | 1.00 | 1.00 |
| q12 | cuido en casa a mi madre de 70 años, ¿hay deducción autonómica en Madrid? | 0.14 | 1.00 | 1.00 |
| q13 | me voy a vivir a un pueblo pequeño de Madrid en riesgo de despoblación, ¿qué beneficios fiscales tengo? | 0.25 | 0.50 | 0.33 |
| q14 | deducción por los intereses de la hipoteca para jóvenes en la Comunidad de Madrid | 1.00 | 1.00 | 1.00 |
| q15 | ¿qué es la deducción por maternidad de 1.200 euros y quién puede pedirla? | 1.00 | 0.25 | 0.50 |
| q16 | ¿se puede cobrar por adelantado cada mes la deducción por maternidad? | 1.00 | 0.33 | 0.50 |
| q17 | gano unos 16.000 euros brutos al año como asalariado, ¿tengo alguna deducción por sueldo bajo? | 0.00 | 0.00 | 0.00 |
| q18 | si pongo placas solares para autoconsumo en casa, ¿cuánto me desgravo? | 1.00 | 1.00 | 1.00 |
| q19 | desgravación en la renta por comprarme un coche eléctrico | 0.33 | 1.00 | 0.50 |
| q20 | obras para mejorar la eficiencia energética de la vivienda, ¿qué deducción hay en el IRPF? | 1.00 | 1.00 | 1.00 |
| q21 | ¿cuánto me deduzco en la renta por donar dinero a una ONG? | 0.00 | 1.00 | 0.11 |
| q22 | compré mi casa con hipoteca en 2010, ¿sigo teniendo la deducción por vivienda habitual? | 0.00 | 0.25 | 0.11 |
| q23 | ¿puedo deducir el alquiler en la declaración estatal si mi contrato es de 2013? | 0.00 | 1.00 | 0.12 |
| q24 | requisitos para pedir el ingreso mínimo vital | 0.00 | 0.25 | 0.17 |
| q25 | ¿cuánto dinero se cobra del ingreso mínimo vital? | 0.00 | 0.00 | 0.00 |
| q26 | renta mínima de inserción de la Comunidad de Madrid: ¿quién puede pedirla? | 0.12 | 0.33 | 0.33 |
| q27 | ¿cuántos hijos hacen falta para ser familia numerosa? | 1.00 | 1.00 | 1.00 |
| q28 | ¿qué descuentos tiene una familia numerosa en tasas, transporte o matrículas? | 1.00 | 0.20 | 0.50 |
| q29 | bono alquiler joven: requisitos de edad y de ingresos | 1.00 | 1.00 | 1.00 |
| q30 | ¿durante cuánto tiempo se cobra el bono alquiler joven? | 0.00 | 0.00 | 0.00 |
| q31 | ayudas para jóvenes que se compran una casa en un pueblo pequeño | 1.00 | 1.00 | 1.00 |
| q32 | me van a desahuciar, ¿hay alguna ayuda para pagar un alquiler? | 0.00 | 0.25 | 0.00 |
| q33 | ¿las becas de estudio tributan en el IRPF? | 1.00 | 1.00 | 1.00 |
| q34 | ¿cuánto reduce el IRPF el mínimo por cada hijo? | 0.00 | 0.00 | 0.00 |
| q35 | ayudas públicas para rehabilitar mi piso y hacerlo más accesible | 0.00 | 0.17 | 0.00 |
| q36 | ¿cuánto paga al mes la ayuda estatal al alquiler para jóvenes que se emancipan? | 0.00 | 1.00 | 0.33 |
| q37 | ayudas para jóvenes dramaturgos o autores de teatro menores de 35 años | 0.00 | 1.00 | 0.00 |
| q38 | beca para estudiar un máster en Estados Unidos | 0.50 | 0.50 | 0.50 |
| q39 | ayudas sociales para mujeres deportistas o entrenadoras | 1.00 | 1.00 | 1.00 |
| q40 | premio para periodistas sobre comunicación feminista | 1.00 | 1.00 | 1.00 |
| q41 | becas de formación para recién graduados en el Instituto Geográfico Nacional | 1.00 | 1.00 | 1.00 |
| q42 | ayuda de viaje para doctorandos menores de 30 para un congreso de investigación cardiovascular | 1.00 | 1.00 | 1.00 |
