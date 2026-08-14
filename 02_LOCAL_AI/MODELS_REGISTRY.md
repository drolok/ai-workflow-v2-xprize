# Models Registry

Ultima actualizacion: 2026-07-19

## Modelos aprobados y validados

| Modelo | Runtime | Uso principal | Tamano nominal | Tamano real en disco | Ruta principal | Estado | Notas |
|---|---|---|---|---|---|---|---|
| `qwen2.5-coder:7b` | Ollama | Chat local, Open WebUI, AnythingLLM, LM Studio | `4.7 GB` | `4683074048` bytes | `<WINDOWS_HOME>\.ollama\models\blobs\sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463` | OK | Validado en Ollama, Open WebUI, AnythingLLM y LM Studio |
| `qwen3.5:9b` | Ollama | Modelo exploratorio para comparacion local | `6.6 GB` | `6594462816` bytes | `<WINDOWS_HOME>\.ollama\models\blobs\sha256-dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c` | No clear role | Entra en el rango razonable para `8 GB VRAM`, pero no fue promovido sobre `qwen2.5-coder:7b` ni para codigo ni para resumen documental en espanol |
| `nomic-embed-text:latest` | Ollama | Embeddings para RAG en AnythingLLM | `274 MB` | `274290656` bytes | `<WINDOWS_HOME>\.ollama\models\blobs\sha256-970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6` | OK | Usado como embedder final en AnythingLLM |

## Reutilizacion en LM Studio

- Archivo visible en:
  - `C:\AI_WORKFLOW\02_LOCAL_AI\LM_STUDIO\qwen2.5-coder-7b.gguf`
- Tipo:
  - `HardLink`
- Conteo de hard links observado:
  - `3`
- Implicacion:
  - LM Studio reutiliza el mismo payload fisico del modelo.
  - No se consumieron otros `4.7 GB` extra para la copia de LM Studio.

## Modelos auxiliares no aprobados como stack principal

| Modelo o cache | Origen | Uso | Tamano observado | Ruta | Estado | Notas |
|---|---|---|---|---|---|---|
| `all-MiniLM-L6-v2` y cache asociado | Open WebUI | Cache interno de embeddings del contenedor | `930896841` bytes en cache | `C:\AI_WORKFLOW\02_LOCAL_AI\OPEN_WEBUI\data\cache\embedding\models` | OK | Descargado automaticamente por Open WebUI al primer arranque |

## Resumen de peso descargado para la fase

- Descarga aprobada de modelos Ollama:
  - `qwen2.5-coder:7b` -> `4683074048` bytes
  - `nomic-embed-text:latest` -> `274290656` bytes
- Total principal descargado para modelos aprobados:
  - `4957364704` bytes

## Imagenes Docker usadas

- `ghcr.io/open-webui/open-webui:main` -> `7.01GB`
- `mintplexlabs/anythingllm:latest` -> `4.78GB`

Estas imagenes no sustituyen a los modelos anteriores; son la huella de las aplicaciones contenedorizadas de la fase.

## Comparacion exploratoria - 2026-07-19

Prompt usado en ambos modelos:

```text
In TypeScript, why does Array(3).map(() => 1) not behave like many people expect, and what is one correct fix? Answer in 3 bullets and one code block.
```

Resultado real:

| Modelo | Tiempo pared observado | `eval_count` | Lectura subjetiva |
|---|---:|---:|---|
| `qwen2.5-coder:7b` | `5.34s` | `134` | Mas rapido, mas conciso, y dio una correccion util con `Array.from({ length: 3 }, () => 1)` |
| `qwen3.5:9b` | `59.25s` | `257` | Mucho mas lento y mas alucinatorio en esta prueba; aun menciono `Array.from`, pero mezclo explicaciones incorrectas sobre `Array(3)` |

Lectura final del laboratorio:

- `qwen3.5:9b` si corre localmente y entra en el presupuesto de disco/VRAM de este equipo.
- En esta prueba puntual de codigo, `qwen2.5-coder:7b` fue mejor opcion practica.
- Decision derivada: mantener `qwen2.5-coder:7b` como modelo local principal para tareas tecnicas y dejar `qwen3.5:9b` como modelo exploratorio, no como reemplazo todavia.

## Comparacion real de resumen en espanol - 2026-07-19

Documento usado:

- `C:\AI_WORKFLOW\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA\01_ANALISIS_Y_ARQUITECTURA\proyectos_privados\DOCTRINA_CONFLUENCIA_TCHASKY_2026-06-19.md`

Artefacto:

- `C:\AI_WORKFLOW\08_REPORTS\LOCAL_AI\qwen_spanish_summary_compare_2026-07-19.json`

Resultado real:

| Modelo | Tiempo pared observado | `eval_count` | Lectura subjetiva |
|---|---:|---:|---|
| `qwen2.5-coder:7b` | `23.285s` | `800` | Resumen completo en espanol, aceptablemente obediente al formato pedido |
| `qwen3.5:9b` | `89.671s` | `2046` | Mucho mas lento; corto por `length` y derivo hacia propuestas no pedidas |

Lectura final del laboratorio:

- `qwen3.5:9b` no gano un rol claro como modelo de analisis documental en espanol dentro de este hardware.
- `qwen2.5-coder:7b` sigue siendo el mejor compromiso practico para el stack local actual.
