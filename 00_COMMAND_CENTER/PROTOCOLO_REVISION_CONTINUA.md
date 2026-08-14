# Protocolo de revisión continua de herramientas

Una certificación de hoy no es permanente. Las herramientas se
actualizan, mejoran, o cambian de rol — algo marcado `No aprobado` hoy
puede merecer un rol real en unos meses, y algo `OK` hoy puede quedar
obsoleto. Este protocolo define cuándo y cómo se re-testea, para que eso
quede trackeado en vez de perderse.

## Dónde vive la prueba constante

`11_LAB\` sigue siendo el sandbox fuera del flujo principal — nada se
prueba directo contra producción ni contra el repo real de Tchasky. Cada
subcarpeta de herramienta ya sigue el patrón `CERTIFICATION_RESULTS.md`
con barra de aprobación fijada antes de probar. Eso no cambia.

## Qué se agrega: campo de "Próxima revisión" por herramienta

Cada fila de `TOOL_REGISTRY.md` con estado `Partial`, `Blocked`, o `No
aprobado` (no las `OK` estables como Git/Docker/Python, esas no
necesitan reintento periódico) debe tener una fecha de próxima revisión,
calculada así:

- **`Blocked` por causa externa** (rate limit, falta de permiso, cuenta):
  revisar cuando la causa externa se resuelva (no hay fecha fija, es un
  disparador de evento, ej. "cuando el fundador confirme la key").
- **`Partial` por no llegar al umbral** (ej. RAG bajo 7/10, Kimi/OpenCode
  sin superficie operable): revisar en **60 días** o antes si sale una
  versión mayor nueva del proyecto — lo que ocurra primero.
- **Marketing vs. medición real que no coincidió** (ej. Ponytail):
  revisar en **90 días** — cambios de comportamiento suelen tardar más
  en aparecer.
- **`Blocked` técnico sin causa externa** (ej. Bash dofork, PostgresAI
  viejo): revisar cuando el fundador decida retomarlo, sin fecha
  automática — ya se agotaron los métodos remotos razonables.

## Cómo se re-testea (no se repite la certificación entera)

1. Confirmar primero si la versión cambió desde la última certificación
   (changelog/release notes reales, no asumir).
2. Si no cambió nada relevante, no vale la pena re-correr toda la
   prueba — anotar "sin cambios, no reevaluado" y correr la próxima
   revisión más adelante.
3. Si cambió, re-correr la misma barra de aprobación original (no
   inventar una nueva more permisiva para que pase) y actualizar el
   veredicto con fecha nueva.

## Qué se guarda

- El propio `TOOL_REGISTRY.md` queda como fuente de verdad del estado
  actual + próxima revisión.
- El historial de revisiones anteriores (qué cambió entre una y otra)
  va en `08_REPORTS\TECH_RADAR\` con fecha en el nombre de archivo, sin
  sobrescribir el reporte anterior — así se puede ver la evolución real
  de una herramienta en el tiempo, no solo el último estado.
