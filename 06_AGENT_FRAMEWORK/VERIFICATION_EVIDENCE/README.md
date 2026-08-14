# Scripts y evidencia de verificación

Esta carpeta reúne los scripts operativos de `.ai/bin` y las mediciones finales
que demuestran las tres fases del plan de memoria operativa y el comportamiento
del RAG. Son copias de revisión: las rutas de perfil se sustituyeron por
`<HOME>`, `<WINDOWS_HOME>` y `<PRIVATE_PROJECT>`; configure esos marcadores antes
de intentar ejecutar una copia fuera de su entorno original.

## Scripts

| Archivo | Función |
|---|---|
| `scripts/build_registries.py` | Reconstruye los registros derivados del control plane. |
| `scripts/gen_s7_refs.py` | Localiza referencias al árbol anterior para su revisión. |
| `scripts/milestones.py` | Crea y consulta hitos sobre el ledger de eventos. |
| `scripts/reality.py` | Mantiene la realidad compartida: eventos, tareas, handoffs, estado y gates. |
| `scripts/registry_check.py` | Valida el contrato mínimo de los registros YAML. |
| `scripts/task123_verify_grounds.py` | Contrasta afirmaciones documentadas con fuentes deterministas. |
| `scripts/task123_test_two_directions.py` | Prueba que cambios del sistema y del documento se detecten por separado. |
| `scripts/task124_live_sources.py` | Consulta fuentes vivas mediante adaptadores de solo lectura. |
| `scripts/task124_live_router.py` | Enruta preguntas entre fuentes vivas y RAG. |
| `scripts/task124_evaluate.py` | Evalúa el enrutador y sus controles prerregistrados. |

## Mediciones

- `measurements/rag/task118_analysis.json`: comparación agregada del RAG con
  búsqueda léxica y agente local; evita el volcado crudo por pregunta.
- `measurements/rag/task120_real_route_results.json`: aceptación de la puerta de
  abstención sobre la ruta real.
- `measurements/phase-1/task122_measurement.json`: FTS5 obtiene 20/20 frente a
  16/20 del RAG en el conjunto operativo.
- `measurements/phase-2/task123_ground_truth.json`: estado canónico de 88
  afirmaciones (`86 VERDADERO`, `0 FALSO`, `2 NO COMPROBABLE`).
- `measurements/phase-2/task123_two_direction_test.json`: aceptación reversible
  en las direcciones sistema y documento.
- `measurements/phase-2/task126_final_wsl.json` y
  `task126_final_windows.json`: resultado final equivalente en ambos entornos.
- `measurements/phase-3/task124_evaluation.json`: 15/15 clasificaciones, 10/10
  respuestas vivas y 5/5 controles documentales enviados al RAG.

Los inventarios, corridas parciales, controles negativos aislados, logs y
resultados crudos permanecen fuera de este árbol.
