# Infraestructura de Auditoria y Escaneo de Ciberseguridad -- Tchasky

Este directorio contiene las herramientas, configuraciones y guias de ejecucion para realizar la auditoria continua de ciberseguridad sobre el repositorio monorepo de Tchasky.

## Estructura de Archivos

- README.md: Este runbook de uso y comandos de ejecucion.
- HALLAZGOS.md: Registro historico consolidado de vulnerabilidades (SAST, DAST, CVEs) y su estado de mitigacion.

---

## Runbook de Ejecucion de Escaneos

### 1. Escaneo SAST (Analisis Estatico de Codigo Fuente con Semgrep)

El analisis estatico detecta patrones inseguros, sanitizacion casera de inputs y llamadas criptograficas vulnerables.

`ash
# Asegurar PATH en WSL
export PATH=<WINDOWS_HOME>/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Ejecutar scan automatico sobre aplicaciones
cd /ruta/a/tchasky
semgrep --config auto apps/api/src apps/web/src apps/mobile/src
`

### 2. Analisis de Vulnerabilidades en Dependencias (pnpm Audit)

Verifica CVEs conocidas en el arbol de dependencias de Node.js.

`ash
cd /ruta/a/tchasky
pnpm audit --json > audit_results.json
`

### 3. Verificacion Manual de Autenticacion y Secretos

1. Revision de Secretos Hardcodeados:
   grep -rn 'sk_live' apps/
   *Nota:* Redactar todos los valores de claves antes de documentar cualquier hallazgo.

2. Revision de Guards de Autenticacion y Rate Limiting:
   - Confirmar que todo endpoint en apps/api/src/routes/admin.ts incluya el middleware de rol de admin.
   - Confirmar que endpoints sensibles (pago, KYC, auth) tengan sus limitadores asignados en apps/api/src/middleware/rateLimiter.ts.

---

## Integracion con Hawkscan (Claude Code Plugin)

La herramienta Hawkscan esta configurada en el entorno de Claude Code para ejecutar escaneos DAST automatizados tras cambios mayores de arquitectura. Antigravity/Codex audita y registra los resultados resultantes en HALLAZGOS.md.
