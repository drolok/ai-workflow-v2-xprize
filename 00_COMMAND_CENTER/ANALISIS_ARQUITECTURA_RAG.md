# Analisis: que del estado del arte nos sirve, medido contra nuestro corpus

**Origen.** El fundador entrego el 2026-08-13 un documento extenso sobre como
funciona un sistema RAG moderno —tokens, embeddings, bucles de agente, KV cache,
reranking, orquestacion, grafo, niveles de memoria— y pidio revisarlo: **cuanto de
eso ayuda de verdad, que ya tenemos, y pros y contras**. No implementar.

**Lo que hace util esta revision:** se cruza contra mediciones propias sobre el
corpus real, no contra intuiciones.

---

## 1. Lo que el documento propone y ya esta implementado

| Idea | Estado | Evidencia |
|---|---|---|
| RAG como sistema separado de la LLM | Implementado | AnythingLLM + LanceDB, 3.501 documentos, 37.497 vectores |
| Embeddings y busqueda por similitud | Implementado | `bge-m3`, 1.024 dimensiones |
| **Filtrado por metadatos antes de la similitud** | **Implementado, y es la palanca que mas aporta** | Enrutamiento por `docSource`: **+7,5 de los +11,25 puntos totales** |
| Cadena local + nube por costo | Implementado | NVIDIA 1,7 s, Gemini 1,9 s, local 4,9 s |
| Actualizacion de memoria entre sesiones | **Implementado, y es el activo mas fuerte** | Handoffs, `DECISION_LOG`, ledger de eventos, gotchas |

---

## 2. Lo que el documento recomienda y AQUI RESTA

**Tres de sus recomendaciones centrales se midieron sobre este corpus el 13/08 y
las tres dan negativo:**

| Recomendacion | Medido aqui |
|---|---:|
| Reescritura y expansion de consulta | **-9,5 puntos** |
| Reranker sobre los resultados | **-16,7 puntos** con 150 candidatos |
| Busqueda hibrida BM25 + densa | **-4,8 puntos** |

**El documento no esta equivocado: describe bien el estado del arte general.** Lo
que ocurre es que **este corpus no es el corpus promedio**, y la palanca que gano
por 11 puntos —limitar a un fragmento por documento— casi no aparece en esa
literatura.

**Esa es la funcion del conjunto de referencia:** convierte *"esto suele
funcionar"* en *"esto funciona aqui, o no"*.

---

## 3. Lo que falta y si ayudaria, por relacion valor/costo

### A. Cache de consultas — el mas rentable

**No existe.** Cada pregunta repetida vuelve a pagar recuperacion y generacion.

- **A favor:** una pregunta frecuente pasaria de segundos a milisegundos y de
  miles de tokens a cero. Riesgo casi nulo y reversible.
- **En contra:** **la invalidacion es el trabajo real.** Una cache que devuelve el
  estado de ayer es peor que no tenerla.
- **Cuanto ayuda:** mucho en latencia y costo, **nada en recall**. Mejora la
  experiencia, no la calidad.

### B. Orquestador que elija entre fuentes — la idea estructural grande

**Es lo que mas falta.** Hoy todo va al RAG. Una pregunta como *"¿fallo BullMQ
hoy?"* se busca en documentos escritos hace semanas cuando la respuesta esta en
Sentry.

- **A favor:** resuelve una clase entera de preguntas que **hoy no puede
  contestar bien por mas que suba el recall**. Ningun ajuste de embeddings arregla
  que la verdad este en otro sitio.
- **En contra:** es el componente mas complejo, y **enrutar mal es peor que no
  enrutar**. Ademas aplica la decision del fundador del 13/08: **nada puede quedar
  inalcanzable**.
- **Cuanto ayuda:** potencialmente mas que todo lo hecho hoy, **pero son semanas,
  no horas**.

### C. Metadatos mas ricos que la ruta

Hoy solo se usa `docSource`. El documento propone ademas fecha, estado, proyecto,
rama.

- **A favor:** **extiende exactamente la palanca que ya demostro aportar**, y
  ataca un problema real: hay documentos que se contradicen porque uno es viejo.
  Ordenar por fecha resolveria las consultas de *"lo ultimo sobre X"*.
- **En contra:** hay que generarlos para 3.501 documentos, y **generarlos mal
  envenena el filtrado**.
- **Cuanto ayuda:** es la continuacion natural de lo que gana. **Primero de los
  tres.**

### D. Grafo de conocimiento conectado a la recuperacion

Graphify existe pero **no esta conectado** al camino de consulta.

- **A favor:** contesta lo que el vector no puede. *"¿Que se rompe si toco
  PostGIS?"* no es similitud, es relacion.
- **En contra:** mantenerlo al dia es trabajo permanente, y **un grafo
  desactualizado miente con confianza**.
- **Cuanto ayuda:** poco para las preguntas del conjunto actual; mucho para una
  clase que **ni siquiera se esta midiendo**.

---

## 4. Lo que no es accionable

**KV cache, generacion autoregresiva, prefill, TTFT.** Correctos, y explican por
que la latencia se comporta como se comporta, pero **ocurren dentro del modelo**.
Sirven para entender, no para construir.

---

## 5. La idea mas profunda, y donde estamos parados

> *"El RAG deberia ser la memoria persistente del macrobucle."*

**Es correcto, y ya se esta ganando ahi sin haberlo llamado asi.** El macrobucle
—handoffs, decisiones registradas, gotchas, ledger— **esta mucho mas construido
que el RAG**. Se vio el mismo 13/08: Claude encontro todo lo que necesito leyendo
esos archivos, no consultando vectores.

**La conclusion incomoda:** el RAG puede no ser el cuello de botella del sistema
que se esta construyendo. Es una pieza que funciona al **72,5 %** y a la que se le
dedico un dia entero; el macrobucle funciona mejor y casi no ha recibido tiempo.

**Recomendacion, en orden:**

1. **Metadatos mas ricos** — extiende lo que ya gana.
2. **Cache de consultas** — barato y visible.
3. **Orquestador** — **solo al volver de Tchasky**: se parece mas a un proyecto
   que a una tarea.
