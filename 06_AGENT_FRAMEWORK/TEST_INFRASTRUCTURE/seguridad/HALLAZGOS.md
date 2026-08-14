# Registro Histórico de Hallazgos de Ciberseguridad — Tchasky

Este documento centraliza todos los hallazgos de seguridad detectados mediante escaneos SAST (Semgrep), análisis de vulnerabilidades en dependencias (pnpm audit CVEs) y revisiones manuales de arquitectura.

## Tabla de Hallazgos

| ID | Severidad | Descripción | Archivo / Línea | Fecha Detectado | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **VULN-001** | **HIGH** | Google Sign-In Mobile Flujo Implícito sin PKCE | apps/mobile/src/services/auth.ts | 2026-07-30 | **RESUELTO** | Corregido con flujo Authorization Code + PKCE (S256), state y nonce validados. |
| **VULN-002** | **HIGH** | Vulnerabilidad de DoS en brace-expansion (CVE-2026-14257) | package.json (transitivo) | 2026-07-31 | **RESUELTO** | Corregido con override brace-expansion: 2.1.2 en root package.json (Commit b117b76). |
| **VULN-003** | **HIGH** | Path Traversal en PostCSS sourceMappingURL (GHSA-r28c-9q8g-f849) | package.json (devDependency) | 2026-07-31 | **RESUELTO** | Corregido con override postcss: >=8.5.18 en root package.json (Commit b117b76). |
| **VULN-004** | **MEDIUM** | Inyección/Escape HTML casero con replaceAll en Notificaciones | apps/api/src/services/notificationService.ts:28-31 | 2026-07-31 | **REGRESIÓN EN MOBILE** | Resuelto en master (commit 839e7eb), pero reaparece en eature/mobile-foundation por falta de rebase con master. |
| **VULN-005** | **MEDIUM** | Desencriptación AES-GCM sin verificación de Tag Length explícito | apps/api/src/services/taskItemSerialService.ts:43-47 | 2026-07-31 | **REGRESIÓN EN MOBILE** | Resuelto en master (commit 839e7eb), pero reaparece en eature/mobile-foundation por falta de rebase con master. |
| **VULN-006** | **LOW** | Hook de Protección de Comandos (critical_action_guard) sin cobertura contra comandos en WSL/Bash | C:\AI_WORKFLOW\.Codex\hooks\critical_action_guard.ps1 | 2026-07-30 | **ABIERTO** | Cobertura parcial en comandos de PowerShell; no intercepta directamente llamadas puras de Bash dentro de WSL. |
| **VULN-007** | **LOW** | 49 Vulnerabilidades (7 Low, 34 Mod, 7 High, 1 Crit) en Dependencias de Monorepo | pnpm-lock.yaml | 2026-07-31 | **ABIERTO** | Detectado por pnpm audit en escaneo del 2026-08-02. Afecta principalmente a paquetes dev/frontend (posthog-js, dompurify). |
