# Conjunto de referencia RAG — frescura y reproducción

**Última medición:** 2026-08-13 18:20:02 (America/Lima, UTC-05:00)  
**Conjunto medido:** `rag_golden_set.json`, versión `46-preguntas-v2-task104`  
**Tamaño:** 46 consultas: 42 con documento esperado y 4 sin respuesta  
**Espacio:** `bis_brain-segundo-cerebro`  
**Instantánea del espacio al medir:** 3.539 filas en `workspace_documents`, 3.380
`docSource` distintos y 83.597 vectores; las 42 rutas esperadas estaban presentes  
**Fragmentado:** 1.200 caracteres, 200 caracteres de solapamiento  
**Resultado del control:** recall@1 38,1 % (16/42), recall@3 52,4 % (22/42),
recall@5 57,1 % (24/42), MRR 0,452, abstención 50,0 % (2/4) y exactitud@5
56,5 % (26/46)  
**Resultado completo:** `backups/TASK-104_20260813_132429/EVAL_FINAL_46.txt` y
`TASK-104_RESULT_2026-08-13.md`

## Comando exacto de reproducción

El evaluador está preparado para ejecutarse en Windows:

```bat
cd /d C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM
python eval_rag.py
```

En la medición indicada arriba se ejecutó el mismo archivo desde WSL porque la
sesión no tenía interoperabilidad con ejecutables PE:

```bash
cd /mnt/c/AI_WORKFLOW_V2/02_LOCAL_AI/ANYTHINGLLM
python3 eval_rag.py
```

Antes de medir se verificó con un control positivo que
`http://127.0.0.1:3110/api/ping` respondiera y que una consulta conocida
recuperara en primer lugar
`03_Tchasky/docs/adr/0010-mobile-framework.md`. La consulta al índice ocurre a
través de la misma API de AnythingLLM en ambos comandos. En TASK-104 se amplió
el alcance a un único espacio con 3.539 documentos. Se conservaron `bge-m3`, el
fragmentado 1.200/200, el umbral 0,45, el modo `default` y `topN = 4`.

## Regla de actualización

Toda modificación de preguntas, corpus, embeddings o recuperación invalida la
fecha anterior. Después de cualquiera de esos cambios se debe volver a ejecutar
el comando, actualizar la fecha y guardar la tabla completa. Un resultado sin
fecha y sin versión del conjunto no se considera vigente.
