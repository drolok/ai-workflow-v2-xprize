# Agent Framework

## Objetivo

Este directorio define como colaboran los agentes del framework `AI_WORKFLOW` sin obligar a releer todo el historial en cada relevo. La meta de Fase 6 es dejar un contrato estable de contexto, handoff y prompts reutilizables para futuras fases.

## Alcance de esta fase

- Definir roles y limites de cada agente o IA.
- Estandarizar el formato de `context packs`, `handoffs` y prompts de trabajo.
- Reutilizar los scripts ya validados en Fase 5 para generar artefactos reales.
- Mantener todo aislado dentro de `C:\AI_WORKFLOW`.

## Fuera de alcance

- No se toman decisiones de producto sobre `TCHASKY` en esta fase.
- No se modifica el stack local de IA de Fase 3.
- No se reescriben scripts de Fase 5.

## Estructura

- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\AGENT_TEMPLATES` contiene las plantillas base.
- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CONTEXT_PACKS` guarda paquetes de contexto autocontenidos.
- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\HANDOFFS` guarda relevos entre agentes.
- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\AGENT_REPORTS` guarda evidencia, notas de validacion y reportes auxiliares.
- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX` queda reservado para materiales especificos del rol de Codex.
- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CLAUDE_CODE` queda reservado para materiales especificos del rol de Claude Code.

## Formato compartido

Todo artefacto generado en esta fase debe ser autocontenido. Eso significa que el siguiente agente debe poder actuar solo con el archivo recibido y las rutas explicitas que ese archivo enumera.

Un `context pack` valido debe incluir como minimo:

- objetivo actual
- restricciones aprobadas
- decisiones ya tomadas
- resumen del repositorio o espacio de trabajo relevante
- archivos clave
- siguiente paso recomendado

Un `handoff` valido debe incluir como minimo:

- estado actual verificado
- lo que ya se hizo
- artefactos exactos a revisar
- riesgos abiertos o preguntas pendientes
- siguiente accion sugerida

## Flujo recomendado

1. El agente que prepara el trabajo crea o actualiza un `context pack`.
2. El agente orquestador emite un `task prompt` para el ejecutor.
3. El agente ejecutor implementa o valida el cambio sin expandir el scope.
4. Un agente revisor o auditor ejecuta la revision critica.
5. Si el trabajo cambia de manos, se genera un `handoff` autocontenido.
6. Si el trabajo se pausa, se deja un `daily snapshot` corto.

## Scripts reutilizados de Fase 5

- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\generate_context_pack.py`
- `C:\AI_WORKFLOW\03_AUTOMATION\SCRIPTS\agent_handoff_template.py`

Estos scripts siguen siendo la via oficial para generar artefactos de prueba en esta fase. Las plantillas nuevas se disenan para ser compatibles con sus placeholders actuales.

## Regla operativa central

Si un agente necesita releer todo el historial para continuar, el artefacto entregado no esta suficientemente bien hecho. La calidad del framework se mide por la claridad del contexto transferido, no por la cantidad de texto acumulado.
