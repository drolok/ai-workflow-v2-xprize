# AI Workflow MOC

Ultima actualizacion: 2026-07-18

## Objetivo

Centralizar el estado tecnico, las decisiones y los reportes del framework `C:\AI_WORKFLOW`.

## Command Center

- [CURRENT_STATE.md](./CURRENT_STATE.md)
- [DECISION_LOG.md](./DECISION_LOG.md)
- [INSTALLATION_LOG.md](./INSTALLATION_LOG.md)
- [TOOL_REGISTRY.md](./TOOL_REGISTRY.md)
- [SYSTEM_HEALTH.md](./SYSTEM_HEALTH.md)
- [NEXT_ACTIONS.md](./NEXT_ACTIONS.md)
- [BLOCKERS.md](./BLOCKERS.md)

## Reportes

- [PREFLIGHT_CHECK.md](../08_REPORTS/HEALTH_CHECKS/PREFLIGHT_CHECK.md)
- [PHASE_1_DEV_BASE.md](../08_REPORTS/INSTALL_REPORTS/PHASE_1_DEV_BASE.md)
- [PHASE_2_OBSIDIAN.md](../08_REPORTS/INSTALL_REPORTS/PHASE_2_OBSIDIAN.md)
- [PHASE_2_AUDITIDEAS_OBSIDIAN_TEST.md](../08_REPORTS/INSTALL_REPORTS/PHASE_2_AUDITIDEAS_OBSIDIAN_TEST.md)
- [PHASE_3_LOCAL_AI.md](../08_REPORTS/INSTALL_REPORTS/PHASE_3_LOCAL_AI.md)

## Entorno base

- [DEV_SETUP.md](../05_DEV_ENVIRONMENT/DEV_SETUP.md)

## IA local

- [LOCAL_AI_SETUP.md](../02_LOCAL_AI/LOCAL_AI_SETUP.md)
- [MODELS_REGISTRY.md](../02_LOCAL_AI/MODELS_REGISTRY.md)

## Obsidian

- [OBSIDIAN_SETUP.md](../01_OBSIDIAN/OBSIDIAN_SETUP.md)
- [TCHASKY_MOC.md](../01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky/TCHASKY_MOC.md)
- [AUDITIDEAS_MOC.md](../01_OBSIDIAN/VAULT_AUDITIDEAS_TEST/03_Maps/AUDITIDEAS_MOC.md)

## Estado resumido

- Fase actual: Fase 3 - IA local completada.
- El vault base del framework ya existe y esta separado de `TCHASKY`.
- El vault de prueba `VAULT_AUDITIDEAS_TEST` ya existe y esta separado del vault principal.
- No hay bloqueos tecnicos activos en el entorno base, la capa documental ni el stack local de IA.
- Riesgos activos: `GitHub CLI` y `PowerShell 7` siguen diferidos; Open WebUI necesita ajuste fino para no reanadir `nomic-embed-text:latest` como modelo de chat secundario.
- Hallazgo importante: la CPU detectada es `Intel Core i9-10900F`, no un i9 de 11th gen.

## Siguiente fase recomendada

- Iniciar Fase 4 - document processing usando un lote sintetico pequeno antes de procesar documentos reales.
