# XPRIZE "Build with Gemini" — evidencia de la integración

**Fecha:** 2026-08-11
**Deadline de la convocatoria:** 2026-08-17
**Rama:** `feature/xprize-gemini-triage` (worktree `<HOME>/wt-xprize-gemini`)
**Base:** `cf46008` de `feature/mobile-foundation`

---

## Qué exige la convocatoria y cómo se cumple

> Al menos **una llamada real a Gemini** si el producto tiene funcionalidad LLM.

Tchasky ya tenía funcionalidad LLM en producción: el asistente de soporte
*Chasqui* (`apps/api/src/services/supportService.ts`), que usa Anthropic. **Ese
asistente no se tocó** — es producto desplegado que funciona. Lo que se agregó es
una funcionalidad nueva que sí usa Gemini.

---

## La llamada real, ejecutada y con salida cruda

```
$ ./apps/api/node_modules/.bin/tsx scripts/xprize-gemini-probe.ts

Estado HTTP: 200
Latencia: 3307 ms
Respuesta:
{"choices":[{"finish_reason":"stop","index":0,
  "message":{"content":"{\"ok\":true,\"mensaje\":\"Gemini respondió\"}",
  "role":"assistant"}}],
 "created":1786444706,
 "id":"n_t6av6QMdqeqtsPwK2ciQc",
 "model":"gemini-3.5-flash",
 "object":"chat.completion",
 "usage":{"completion_tokens":11,"prompt_tokens":19,"total_tokens":353}}
```

- **Modelo:** `gemini-3.5-flash`
- **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
- **Latencia medida:** 3.307 ms
- **Script reproducible:** `scripts/xprize-gemini-probe.ts`

Nota técnica: `gemini-2.0-flash` está dado de baja y devuelve `404 — no longer
available`. Cualquier intento de reproducir esto con ese modelo falla.

---

## Qué se construyó: triage de disputas asistido por IA

No es un chatbot más. Es una **decisión operacional auditable**: cuando se abre
una disputa entre un cliente y un profesional, un administrador puede pedir una
sugerencia de resolución que Gemini produce a partir del contexto del caso.

### La regla de producto que define el diseño

**La IA nunca resuelve una disputa ni mueve dinero.** Produce una sugerencia no
vinculante que un administrador humano lee y evalúa. Todo movimiento de fondos
sigue pasando por el flujo humano existente (`resolveDispute()`), sin cambios.

Esto es deliberado y no es una limitación técnica: en una plataforma que maneja
pagos reales entre personas, una IA que resuelve disputas sola es un riesgo que
no se justifica por la comodidad que ahorra.

### Qué hace auditable a la sugerencia

Cada triage inserta una fila en la tabla `dispute_ai_triage` que guarda:

| Campo | Para qué |
|---|---|
| `prompt_sent` | el prompt **literal** que se envió |
| `raw_response` | la respuesta **cruda** del proveedor, sin parsear |
| `model`, `provider` | qué modelo exacto opinó (`gemini-3.5-flash`, `google`) |
| `suggested_outcome` | `refund_client` / `pay_pro` / `split` / `needs_more_evidence` / `inconclusive` |
| `suggested_client_refund`, `suggested_pro_payment` | los montos sugeridos |
| `rationale`, `confidence` | el porqué, y qué tan seguro dice estar |
| `latency_ms` | cuánto tardó |
| `error` | si la llamada falló, el motivo |
| `created_at` | cuándo |

**La tabla es append-only, y no por convención:** un trigger
`BEFORE UPDATE OR DELETE` lanza excepción. Re-correr el triage sobre la misma
disputa **inserta una fila nueva**, nunca sobrescribe. El historial de lo que la
IA opinó a lo largo del tiempo es parte de la auditoría.

**Una fila con error también es auditoría:** prueba que se intentó y por qué no
salió. Sin la clave configurada, el servicio no explota — registra
`error='GEMINI_API_KEY no configurada'` y devuelve `inconclusive`.

### Privacidad

El prompt manda **solo** el motivo de la disputa, su descripción, la cantidad de
evidencias adjuntas y el monto de la task. **No se agrega ninguna PII**: ni
nombres, ni teléfonos, ni correos, ni documentos de identidad.

### Salvaguardas

- Los montos sugeridos se recortan contra el monto real de la task; la IA no
  puede sugerir devolver más de lo que existe.
- Timeout de 30 s con `AbortController`, sin reintentos automáticos.
- Salida validada con Zod. Si el JSON no valida, el resultado es `inconclusive`
  y **la respuesta cruda se guarda igual**.
- El endpoint exige rol de administrador.

---

## Archivos

| Archivo | Qué es |
|---|---|
| `apps/api/src/db/migrations/0070_xprize_gemini_dispute_triage.sql` | tabla append-only con su trigger |
| `apps/api/src/services/disputeTriageService.ts` | el servicio y la llamada a Gemini |
| `apps/api/src/routes/admin.ts` | `POST` y `GET /api/v1/admin/disputes/{id}/ai-triage` |
| `apps/api/src/config/env.ts` | `GEMINI_API_KEY` (opcional, degrada sin ella) |
| `apps/api/src/openapi/registry.ts` + `openapi.json` | el contrato publicado |
| `apps/api/src/__tests__/xprizeGeminiDisputeTriage.test.ts` | los seis casos |
| `scripts/xprize-gemini-probe.ts` | la llamada real, reproducible |

## Cobertura de pruebas

1. Sin clave configurada: no explota, registra auditoría con error.
2. Respuesta válida: guarda los campos parseados.
3. JSON inválido: `inconclusive` y respuesta cruda guardada igual.
4. Montos por encima del monto de la task: se recortan.
5. El endpoint exige rol de administrador (403 para un usuario normal).
6. Append-only: dos triages sobre la misma disputa dejan dos filas.

---

## Cómo se hizo, y quién revisó a quién

**Implementación:** Codex CLI 0.147.0, en un worktree aislado, con acceso de
escritura acotado a ese directorio.
**Revisión:** una sesión de Claude Code distinta del autor, siguiendo el
protocolo de dos llaves del framework (el revisor nunca es el mismo que el
propietario del cambio).

La revisión encontró y corrigió dos defectos reales que el autor no vio:
`openapi.json` no se había regenerado tras registrar los endpoints nuevos, y el
conteo congelado de operaciones del contrato había quedado viejo. Ese segundo
número se actualizó **solo después de verificar** que las operaciones nuevas
traen contrato completo, porque subirlo sin eso habría invalidado el test que
existe justamente para impedir operaciones sin contrato.

La llamada real a Gemini y el gate completo de tests los ejecutó el revisor: el
sandbox del implementador no tiene DNS ni acceso al socket de Docker, y lo
reportó explícitamente en vez de afirmar que había verificado.
