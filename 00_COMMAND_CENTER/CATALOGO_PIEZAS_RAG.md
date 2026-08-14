# Catalogo de piezas del RAG — lo probado, lo descartado y lo que falta probar

**Que es esto y por que existe.** El fundador lo pidio asi: *"las soluciones estan
dispersas pero estan, y cuando tengamos todas podemos aplicarlas justo a lo que
necesitamos."* Cada pieza que se investiga o se mide entra aqui **con su numero**,
para que ninguna sesion vuelva a probar lo ya descartado ni pierda lo ya ganado.

**Se actualiza en el momento en que se mide una pieza, no al final.**

---

## Frescura

| Campo | Valor |
|---|---|
| `source` | Mediciones propias sobre las 42 preguntas de `rag_golden_set.json` |
| `timestamp` | Consultar `git log -1 --format=%ci -- 00_COMMAND_CENTER/CATALOGO_PIEZAS_RAG.md` |
| `confidence` | Alta en lo medido; las estimaciones estan marcadas como tales |
| `re-medir` | `python 02_LOCAL_AI/ANYTHINGLLM/eval_rag.py` desde Windows |

---

## 1. PIEZAS APLICADAS Y MEDIDAS

| Pieza | Efecto | Estado |
|---|---:|---|
| **Fragmento 1.200/200** (era 8.192/20) | **+11,1 pp** | Aplicada |
| **Consolidar 10 espacios en 1** | -16,6 pp en lo viejo, **pero abre 6/6 preguntas antes imposibles** | Aplicada por decision del fundador |
| **Quitar 38 documentos-maquina** | 0 pp directo, **habilita las demas**. Libero 55,1 % del indice | Aplicada |
| **Diversidad por documento N=1** | **+21,5 pp** (57,1 -> 78,6) | **Medida. Falta conectarla al camino real** |
| Deduplicar 3 documentos exactos | ~0 pp | Aplicada |
| Umbral 0,45 (era 0,25) | 0 pp de recall, **+2 abstenciones** | Aplicada |

**Estado hoy: recall@5 57,1 % en el camino real, 78,6 % con la capa aplicada.**

---

## 2. PIEZAS DESCARTADAS CON NUMERO — no reintentar

| Pieza | Efecto medido | Por que fallo aqui |
|---|---:|---|
| **Busqueda hibrida BM25 + RRF** | **-4,8 pp** | El corpus es mayormente prosa en espanol; el lexico aporta poco y mete ruido |
| **Expansion de consulta** | **-9,5 pp** | Las variantes diluyen la consulta original en la fusion |
| **HyDE** | **-19,0 pp** y 8 errores | La respuesta hipotetica se aleja del vocabulario real |
| **Reordenamiento de AnythingLLM** | -14 pp, 9,4x mas lento | **Solo ve 50 fragmentos**: el 0,06 % del indice |
| **Umbral 0,50 o mas** | -2,4 pp | Gana una abstencion, pierde un acierto |
| **Partir documentos grandes** | 0 pp | AnythingLLM refragmenta por su cuenta |
| **Sacar los `lote_*`** | +2,8 pp aparente, **negativo en consultas personales** | Es corpus personal, no ruido |
| **Diversidad N=2 o N=3** | 73,8 % contra 78,6 % de N=1 | Dos fragmentos del mismo documento ya desplazan |

---

## 3. PIEZAS IDENTIFICADAS Y SIN PROBAR — la cola de trabajo

| Pieza | Por que podria servir | Costo estimado |
|---|---|---|
| **CRAG acotado** — un evaluador que juzga la recuperacion antes de responder | **Es la unica que ataca el problema abierto:** el buscador nunca dice "no se" (2 de 4 preguntas sin respuesta reciben relevancia inventada) | Una llamada LLM por consulta |
| **Multi-vector por documento** | Version **estructural** de lo que resolvimos por post-proceso: el documento se puntua como unidad | Reindexar; alto |
| **Contextual retrieval selectivo** (10 % del indice) | -35 % de fallos segun Anthropic, medido sobre otro corpus | **USD 48** por lotes, o ~11 h en local |
| **Fragmentacion por tipo documental** | Un ADR, una conversacion y un manifiesto no se deberian cortar igual | Reembeber; +7,1 a +11,9 pp estimado |
| **Recuperacion padre-hijo** (hidratar) | Mejora la respuesta sin cambiar el recall | Bajo |
| **Ampliar el conjunto de 42 preguntas** | Con 42, una vale 2,4 pp. **Dos veces hoy una muestra chica dio la respuesta contraria** | Trabajo manual |

---

## 3.b HIPOTESIS PROPIAS PROBADAS Y REFUTADAS

**Cruce de idiomas — REFUTADA el 2026-08-13.** El corpus es **82,7 % ingles** y
las preguntas son en espanol, asi que parecia una causa evidente. **Medido,
partiendo el recall por idioma del documento esperado:**

| Grupo | Preguntas | Base | Con diversidad N=1 |
|---|---:|---:|---:|
| Documento esperado en espanol | 35 | 51,4 % | 74,3 % |
| Documento esperado en ingles | 7 | **85,7 %** | **100,0 %** |

**Los documentos en ingles se recuperan MEJOR.** `bge-m3` maneja el cruce sin
problema, que era exactamente el motivo por el que se eligio sobre
`nomic-embed-text`.

**Lo que si sugiere, y encaja con todo lo demas:** los que fallan son los
documentos **en espanol del propio fundador**, donde hay muchos hablando de lo
mismo —decisiones de Tchasky, handoffs, auditorias— compitiendo entre si. **Es
competencia entre documentos parecidos, no falta de senal.**

**Salvedad honesta:** solo hay 7 preguntas con documento esperado en ingles, asi
que una vale 14 puntos en ese grupo. La direccion es clara; la magnitud no.

---

## 4. LO QUE ESTA LITERATURA RECOMIENDA Y AQUI NO SIRVE

**Las tres primeras recomendaciones de cualquier articulo de RAG de 2026 —hibrida,
reordenamiento y HyDE— miden negativo en este corpus.** Lo que gano por 21 puntos
—diversidad por documento— casi no aparece en esa literatura.

**Y hay evidencia de que lo inverso tambien pasa:** una medicion publicada
encontro que MMR, primo cercano de nuestra diversidad, **cuesta 11,2 puntos de
recall** en su corpus. **La tecnica no es buena ni mala: depende del corpus.**

**La leccion operativa, que ya costo dos correcciones el 13/08:** buscar en la web
sirve para saber **que existe**; solo medir sobre el corpus propio decide **que se
aplica**.

---

## 4.b LA PREGUNTA DE FONDO — ¿hace falta un RAG?

**Encontrado el 2026-08-13 mirando el problema en globo, por pedido del fundador.**

**La industria de agentes de codigo ya se movio en la direccion contraria a la
que estamos afinando:**

- **Anthropic quito la busqueda vectorial de Claude Code en mayo de 2025** y la
  reemplazo por `grep`. Boris Cherny, su creador: *"supero a todo lo demas. Por
  mucho."*
- **Cursor, Windsurf, Cline, Devin y Sourcegraph Amp** hicieron lo mismo.
- Estudio sobre **116 preguntas de LongMemEval**: el agente con sistema de
  archivos gano al RAG en correccion (**8,4 contra 6,4**) y relevancia (**9,6
  contra 8**).

**Y hay una observacion propia, de la sesion del 13/08:** Claude encontro todo lo
que necesito del vault **con `grep` y leyendo rutas**, mientras el RAG media
78,6 %. Nadie lo estaba comparando porque nadie lo habia planteado como
alternativa.

**El matiz medido, que impide dar esto por cerrado:** escalar es mas facil con
RAG, y **una busqueda vectorial afinada llevo una tarea de 68 % a 100 %** en el
trabajo de Qdrant. **A un `grep` no se lo puede afinar.**

**Lo que sigue, y es una medicion, no una opinion:** TASK-118 compara tres brazos
sobre las mismas preguntas —RAG actual, `ripgrep` puro y agente con herramientas—
y reporta **en que preguntas gana cada uno**. Si el lexico gana en nombres y
siglas y el vectorial en lo conceptual, **la respuesta no es elegir: es darle los
dos al agente**.

---

## 5. EL METODO QUE HAY QUE REPETIR

1. **Una pieza por medicion.** Si se mueven dos y sube, no se sabe cual fue.
2. **Simular antes de aplicar.** Filtrar en la consulta prueba el efecto sin tocar
   el indice.
3. **Respaldo verificado y script de restauracion** antes de cualquier cambio que
   toque el indice.
4. **Con 42 preguntas, una vale 2,4 pp.** Menos que eso es ruido, no mejora.
5. **Un numero de arnes no es una mejora del sistema.** Solo cuenta cuando se
   verifica por el camino real que usa el fundador.
