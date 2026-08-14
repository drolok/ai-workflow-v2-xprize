# AI Workflow V2 — XPRIZE Review Snapshot

This repository is a sanitized, history-free snapshot of the working machinery
used to coordinate AI-assisted development around Tchasky. It is organized for
technical review: command-center documentation, agent orchestration, automation,
document ingestion, local RAG components, and the Tchasky review/deployment
surface are included.

Personal vaults, session memory, credentials, installed dependencies, downloaded
models, databases, generated queues, raw conversations, handoffs, backups, and
other operational artifacts are intentionally absent.

## Start here

1. Read [`00_COMMAND_CENTER/AI_WORKFLOW_MOC.md`](00_COMMAND_CENTER/AI_WORKFLOW_MOC.md)
   for the map of the system.
2. Read [`06_AGENT_FRAMEWORK/AGENT_FRAMEWORK.md`](06_AGENT_FRAMEWORK/AGENT_FRAMEWORK.md)
   and [`06_AGENT_FRAMEWORK/AGENT_ROLES.md`](06_AGENT_FRAMEWORK/AGENT_ROLES.md)
   for the orchestration model and role boundaries.
3. Read [`06_AGENT_FRAMEWORK/CODEX_CLAUDE_BRIDGE/DESIGN.md`](06_AGENT_FRAMEWORK/CODEX_CLAUDE_BRIDGE/DESIGN.md)
   for the agent-to-agent execution bridge.
4. Review [`03_AUTOMATION/AUTOMATION_SETUP.md`](03_AUTOMATION/AUTOMATION_SETUP.md)
   and [`04_DOCUMENT_PROCESSING/DOCUMENT_PIPELINE.md`](04_DOCUMENT_PROCESSING/DOCUMENT_PIPELINE.md)
   for automation and ingestion.
5. Review [`02_LOCAL_AI/LOCAL_AI_SETUP.md`](02_LOCAL_AI/LOCAL_AI_SETUP.md),
   [`02_LOCAL_AI/ANYTHINGLLM/RAG_GOLDEN_SET_README.md`](02_LOCAL_AI/ANYTHINGLLM/RAG_GOLDEN_SET_README.md),
   and [`06_AGENT_FRAMEWORK/GRAPHIFY/README.md`](06_AGENT_FRAMEWORK/GRAPHIFY/README.md)
   for the local retrieval architecture.
6. Open [`07_PROJECTS/TCHASKY/XPRIZE_GEMINI_EVIDENCIA_2026-08-11.md`](07_PROJECTS/TCHASKY/XPRIZE_GEMINI_EVIDENCIA_2026-08-11.md)
   and the adjacent container/deployment files for the Tchasky-facing review
   surface.

## Running the machinery

The framework spans PowerShell, Bash, Python, JavaScript, Docker, and n8n. Begin
with [`05_DEV_ENVIRONMENT/DEV_SETUP.md`](05_DEV_ENVIRONMENT/DEV_SETUP.md), then
follow the setup document for the subsystem under review. Services and external
providers require credentials supplied through the reviewer's own environment;
no credentials or local environment files are included here.

This snapshot is documentation-and-source oriented. It does not bundle models,
databases, binaries, dependency directories, production state, or deploy a live
system by itself.
