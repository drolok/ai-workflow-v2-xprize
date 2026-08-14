# PROTOCOLO DE CAPTURA DE CONOCIMIENTO — qué se guarda, de qué tipo, y dónde

**Encargado por el fundador el 2026-08-13.** Con sus palabras: que todo lo que se
logre en una sesión —los cambios, los errores encontrados y más— **se guarde
organizado por tipo**, porque *"hay diferencia entre un bug, un gotcha, los SHA
que son como llaves, y el cómo se interactúa con cada app del stack"*. Y que
**entre cada handoff se recuerde siempre que hay que hacerlo.**

**La regla que lo hace obligatorio vive en `CLAUDE.md`, sección 18**, no aquí.
Este archivo es el detalle; `CLAUDE.md` es lo que el harness carga solo en cada
sesión. Se separaron a propósito: el 13/08 se midió que una instrucción que vive
solo dentro de los handoffs se pierde en cuanto una sesión no la copia.

---

## LA REGLA DE ORO

**Guardar por guardar no sirve.** Un archivo donde cae todo mezclado es un
archivo que nadie consulta, y entonces el conocimiento se perdió igual, solo que
más lentamente.

**Antes de escribir algo, se decide de qué tipo es.** Si no encaja en ningún
tipo de la tabla, casi siempre es porque **no es conocimiento durable** — es
ruido de sesión y no va a ningún lado.

---

## LA TABLA — de qué tipo es y dónde vive

| Tipo | Qué es exactamente | Dónde vive | Qué es obligatorio escribir |
|---|---|---|---|
| **Bug de producto** | Un defecto en Tchasky que ven o sufren los usuarios | El mensaje del commit que lo cierra + `BLOCKERS.md` si queda abierto | Síntoma observable, causa raíz, y **cómo se detectaría de nuevo** |
| **Gotcha técnico** | Una trampa del entorno (Windows/WSL/pnpm/quoting/herramientas) que **ya se repitió** o costó tiempo diagnosticar | `06_AGENT_FRAMEWORK/GOTCHAS_TECNICOS_CRITICOS.md`, **numerado** | El síntoma engañoso, por qué engaña, y la receta que sí funciona |
| **Llave / SHA** | Un identificador que hay que poder recuperar: SHA desplegado, número de migración, huella de firma, ID de cliente OAuth, número de ticket | `01_OBSIDIAN/BIS_BRAIN/03_Tchasky/LLAVES_Y_SHAS.md` | Qué identifica, dónde se usa, y **cómo se verifica que sigue vigente** |
| **Interacción con una app del stack** | Cómo se despliega, autentica, mide o depura contra Vercel, Railway, EAS/Expo, adb, GitHub, Culqi, Mercado Pago, AnythingLLM | `01_OBSIDIAN/BIS_BRAIN/03_Tchasky/DEPLOY_INFRAESTRUCTURA/<APP>/README.md` | El comando exacto verificado, sus requisitos previos, y qué salida significa éxito |
| **Incidente resuelto** | Algo que **estuvo roto de verdad** y se arregló: caída, autenticación rota, despliegue que servía código viejo | `01_OBSIDIAN/BIS_BRAIN/03_Tchasky/OPS/INCIDENTES.md` | Desde cuándo estuvo roto, causa raíz **confirmada**, qué lo arregló, y la señal temprana que lo habría delatado |
| **Decisión** | Una elección entre alternativas reales, tomada por el fundador o delegada | `00_COMMAND_CENTER/DECISION_LOG.md` | Qué se eligió, **qué se descartó y por qué**, y el disparador que la reabriría |
| **Bloqueo** | Algo que impide avanzar y no depende de nosotros, o espera decisión | `00_COMMAND_CENTER/BLOCKERS.md` | De quién depende, desde cuándo, y qué lo desbloquearía |
| **Rendimiento de una IA** | Un dato medido y reproducible sobre un ejecutor: tiempo, tasa de éxito real, costo, quirk de entorno | `06_AGENT_FRAMEWORK/CODEX_CLAUDE_BRIDGE/AI_PERFORMANCE_LEDGER.md` | El número medido, no la impresión |
| **Estado del proyecto** | Dónde está el producto hoy | `00_COMMAND_CENTER/CURRENT_STATE.md` | Lo que cambió, con evidencia |
| **Herramienta** | Qué está instalado y cómo se invoca | `00_COMMAND_CENTER/TOOL_REGISTRY.md` | Nombre, versión, comando real |

---

## CÓMO DISTINGUIR LOS TIPOS QUE SE CONFUNDEN

Esta sección existe porque el fundador señaló exactamente esto: que un bug y un
gotcha no son lo mismo, y que meterlos en el mismo lugar destruye la utilidad de
los dos.

**Bug contra gotcha.** El bug lo sufre **el usuario de Tchasky**; el gotcha lo
sufre **quien trabaja en el proyecto**. Un botón ilegible en modo oscuro es un
bug. Que `wsl -- bash -c` devuelva siempre `$?` igual a 0 es un gotcha. Si el
usuario final jamás lo va a notar, no es un bug.

**Gotcha contra incidente.** El gotcha es una **propiedad estable del entorno**:
siempre estuvo ahí y va a volver a morder. El incidente es un **evento con
fecha**: algo funcionaba, se rompió, se arregló. La autenticación de Google que
se rompió el 7 de agosto es un incidente; que `keytool` mienta al leer la firma
de un APK es un gotcha.

**Incidente contra bug.** Si estuvo roto **en producción** y hubo que
diagnosticar por qué, es incidente. Si es un defecto que se encuentra y se
arregla dentro de la misma tarea, alcanza con el mensaje del commit.

**Llave contra estado.** La llave es **un identificador que hay que recuperar
después**: el SHA que está desplegado, la huella que Google tiene registrada. El
estado es la narración de dónde está el proyecto. Un SHA suelto dentro de un
párrafo de estado **no se puede buscar**; por eso las llaves tienen su propio
archivo.

**Interacción con una app contra gotcha.** La interacción es **el camino feliz
verificado**: así se despliega, así se autentica. El gotcha es **la trampa** de
ese camino. Van juntos pero separados: el README del área lleva el procedimiento,
y el gotcha numerado lleva la advertencia.

---

## EL RITUAL — cuándo se hace

**No es un paso al final de la sesión.** Se hace **dentro de la misma tarea donde
se descubre la cosa**, por el mismo motivo que las secciones 11 y 13 de
`CLAUDE.md`: lo que se deja "para después" compite con el contexto que se está
por resumir, y pierde.

**Además, antes de escribir cualquier handoff nuevo**, se recorre la tabla y se
responde, tipo por tipo: *¿esta sesión produjo algo de este tipo que todavía no
esté escrito en su hogar?* Lo que aparezca se escribe **antes** de dar el handoff
por terminado.

**Criterio para no inflar los archivos:** entra lo que **le costaría tiempo real
redescubrir a la sesión siguiente**. No entra lo que se deduce leyendo el código
en dos minutos, ni lo que ya está en el historial de git.

---

## LOS HITOS — la otra mitad, y no reemplaza a la tabla

Esta tabla contesta **"¿de qué tipo es esto y dónde vive?"**. No contesta
**"¿qué pasó en el último bloque de trabajo, y qué se viene repitiendo?"**. Eso
es lo que el §28 del diseño llama un hito, y vive aparte:

```
python .ai/bin/milestones.py crear --actor <quien> --titulo "..." --estado cerrado \
  --resultado "..." --error "..." --decision "..." --metrica recall_at_5=0.583 \
  --patron "..." --commit <sha>
```

**Un hito es un corte sobre `.ai/events/EVENTS.jsonl`, no una estructura
paralela:** se queda con la ventana de eventos desde el hito anterior, y emite
un evento `MILESTONE` al mismo ledger. Se crea **al cerrar un bloque de
trabajo**, que es un momento distinto del de esta tabla —la tabla se aplica en
el instante del descubrimiento, el hito al cerrar.

**Cómo se leen sin cargarlos todos al contexto**, que es la razón de ser del
formato:

| Para qué | Comando |
|---|---|
| Memoria corta — qué pasó recién | `milestones.py ver --ultimos 10` |
| Memoria media / larga | `--ultimos 50` · `--ultimos 100` |
| Sólo un campo de la ventana | `ver --ultimos 50 --campo errores` |
| **Escalas de patrón** — qué se repite | `milestones.py patrones --ultimos 10` y de nuevo con 50 y 100 |
| Un hito entero, y es la única vía cara | `ver --id HIT7` |

**Lo que ya reveló con cuatro hitos**, y es el motivo de que el campo `--patron`
exista: *"la causa raíz estaba fuera del componente sospechado"* apareció dos
veces en una sola madrugada —el puerto que tenía el IDE y el chequeo de salud
que miraba el proceso en vez del puerto—. Un patrón así no se ve mirando un
incidente; se ve mirando la ventana.

**Se etiqueta con criterio:** un `--patron` sirve si puede repetirse en otro
trabajo distinto. Si describe solamente lo que pasó esta vez, eso va en
`--error` o en `--resultado`, no en `--patron`.

---

## EL RAG — el estado real, medido el 2026-08-13

**La fuente de verdad son los archivos markdown del vault, no el RAG.** Se
escribe primero en el archivo que corresponde; el RAG es un indice **encima** de
eso, no un reemplazo. Esto no cambia aunque el RAG funcione perfecto: un indice
se puede reconstruir, un conocimiento que nunca se escribio no.

**Y el RAG funciona.** Medido contra la base de AnythingLLM, no leido de un
documento:

| Espacio de trabajo | Documentos embebidos |
|---|---:|
| Cybersecurity Skills Reference | 2578 |
| **BIS_BRAIN (segundo cerebro)** | **410** |
| Tchasky Pc Audit | 155 |
| Tchasky Growth E Intel | 79 |
| Tchasky Handoffs Y Estado | 70 |
| Tchasky Decisiones Y Pagos | 67 |
| Framework Skills Superpowers | 38 |
| Tchasky Arquitectura Y Codigo | 31 |
| Tchasky Estado Vivo | 3 |

Total **3431** documentos, con vectores reales en LanceDB (23 MB solo para el
segundo cerebro). El contenedor `anythingllm-router` estaba arriba al medir.

**La unica limitacion real:** el indice refleja la **ultima ingesta**. Lo que se
escribe hoy no es buscable por el RAG hasta reingerir. Por eso el ritual de este
protocolo es escribir en el archivo correcto — eso funciona siempre, con o sin
ingesta al dia.

**Como se midio, para poder repetirlo:**

```python
import sqlite3, shutil
shutil.copy("C:/AI_WORKFLOW_V2/02_LOCAL_AI/ANYTHINGLLM/storage/anythingllm.db", dst)
sqlite3.connect(dst).execute(
    "SELECT w.name, COUNT(wd.id) FROM workspaces w "
    "LEFT JOIN workspace_documents wd ON wd.workspaceId = w.id GROUP BY w.id")
```

Se copia la base antes de consultarla para no tocar la que usa el contenedor.

---

## USO Y ACTUALIZACION DEL RAG — instruccion del fundador, va en cada handoff

**Regla que fijo el fundador el 13/08:** los archivos y el RAG son **ambos**
fuente de verdad, pero con jerarquia clara, porque no fallan igual.

- **El archivo manda.** Si el RAG y el archivo se contradicen, gana el archivo:
  el indice refleja la ultima ingesta, el archivo refleja hoy.
- **El RAG sirve para encontrar, no para citar.** Se usa para descubrir *donde*
  esta algo cuando no se sabe en que documento vive. Una vez encontrado, **se
  abre el archivo y se lee de ahi** antes de afirmar nada. Esto ademas protege
  del envejecimiento: si el fragmento recuperado es viejo, el archivo lo delata.
- **Escribir siempre va primero al archivo**, nunca al RAG. El RAG no se edita.

**Antes de confiar en una respuesta del RAG, verificar los tres eslabones** —y
en orden inverso, porque el ultimo es el que se cae en silencio (gotcha 60):

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:11434/api/tags   # embebedor
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3110/api/ping    # AnythingLLM
```

Los dos deben dar `200`. Si el embebedor no responde, **la consulta no falla: se
cuelga**, y es facil concluir que el RAG esta roto cuando los datos estan bien.

**Cuando reingerir:** cuando se haya escrito conocimiento nuevo que valga la pena
buscar despues — tipicamente al cerrar una sesion con hallazgos. **No en cada
edicion menor**: la ingesta cuesta y un indice unos dias viejo sigue siendo util
mientras el archivo mande.

**Que anotar en el handoff, siempre:** la fecha de la ultima ingesta y si quedo
algo escrito despues de esa fecha. Asi la sesion siguiente sabe **cuanto puede
confiar** en lo que el RAG le devuelva, en vez de asumir que esta al dia.

---

## CUANTO CONFIAR EN EL RAG — medido, no supuesto

**Primera medicion: 2026-08-13.** Antes de esto nadie sabia si el RAG encontraba
lo que se le pedia; solo se sabia que respondia.

| Metrica | Resultado |
|---|---|
| **recall@1** | 50,0 % |
| **recall@3** | 58,3 % |
| **recall@5** | **58,3 %** |
| **MRR** | 0,528 |

**Como se lee:** en **4 de cada 10 preguntas el documento correcto no aparece
nunca**, ni siquiera en el quinto puesto. Cuando aparece, suele salir primero
(por eso recall@1 y recall@5 casi coinciden): el problema **no es el ranking, es
que no lo recupera**.

**Como se mide, y se puede repetir en un minuto:**

```bash
python 02_LOCAL_AI/ANYTHINGLLM/eval_rag.py
```

El conjunto de referencia esta en `rag_golden_set.json`: 12 preguntas con su
documento esperado. **Regla al agregar preguntas:** se pregunta como preguntaria
una persona, **nunca repitiendo las palabras del titulo**. Una pregunta que copia
el titulo mide coincidencia de texto, no comprension, e infla el resultado.

### La causa del 58 %, diagnosticada

**El indice esta contaminado por tamaño.** El documento mas grande tiene
**184.304 tokens** contra una **mediana de 1.188**: es 155 veces la mediana. Los
tres mayores (`01 - cryoandex`, `05 - MODELADO DE LA DOPA`, `03 - qmstart`) suman
casi medio millon de tokens.

Un documento enorme se parte en cientos de fragmentos, ocupa muchisimo espacio
vectorial, **matchea vagamente con casi cualquier consulta** y desplaza al
documento pequeño y preciso que si contesta la pregunta. Se vio en el resultado:
`lote_005` y `lote_027` ganaron dos preguntas cada uno **sin ser la respuesta**.

Ademas **57 de 414 documentos son `lote_*`**, restos de una importacion por
tandas.

**El arreglo, en orden de rendimiento por esfuerzo:**

1. **Partir los documentos gigantes.** Ya existe `split_oversized_doc.py`, o sea
   que alguien topo con esto antes. Es donde esta la mayor ganancia.
2. **Revisar los 57 `lote_*`**: si son concatenaciones de notas sueltas, se
   reindexan como notas individuales.
3. **Volver a correr `eval_rag.py`** y comparar contra el 58,3 %. Sin volver a
   medir, cualquier "mejora" es una creencia.

**Umbral para complicar mas:** medir la calidad de la *redaccion* de la respuesta
(fidelidad, relevancia) exige un juez LLM y con el modelo local sale caro y
ruidoso. Se justifica **solo si el RAG pasa a responderle a un usuario final**,
no mientras sirva para que una sesion encuentre en que archivo esta algo.

---

## LO QUE NO SE GUARDA

- Lo que ya está en el historial de git (qué archivo cambió, en qué commit).
- La estructura del código: se lee del código.
- Detalles que solo importan dentro de la conversación de hoy.
- Datos personales del fundador en cualquier archivo que pueda salir a GitHub.
  **Ver `CLAUDE.md` sección 16** — esto ya falló una vez.
