# Infraestructura de carga/concurrencia — Tchasky

Frente 1 del [[PLAN_INFRAESTRUCTURA_AUTOMATIZACION_FRENTES_2026-07-31]].
Construido y verificado 2026-07-31.

## Cómo re-correr (no reconstruir desde cero)

Requisitos:
- Stack local Docker levantado (`lifeos_postgres`, `lifeos_redis` — sanos).
- Servidor API local corriendo: `pnpm --dir apps/api dev` (puerto 3001).
- k6 instalado en WSL: `~/.local/bin/k6` (v0.52.0, instalado 2026-07-31).
- 20 usuarios de prueba pre-verificados (KYC nivel 2 approved,
  pilot_account_mode beta_full) — si no existen, hay que recrearlos vía
  el flujo real de registro antes de correr los scripts (no insertar
  filas de DB directamente).

Correr cada escenario:

```bash
cd /ruta/a/este/repo/06_AGENT_FRAMEWORK/TEST_INFRASTRUCTURE/carga
~/.local/bin/k6 run k6_scenario1_task_creation.js   # 100 VUs, creación de tasks
~/.local/bin/k6 run k6_scenario2_race_condition.js  # 50 VUs, race condition de aceptación de oferta
~/.local/bin/k6 run k6_scenario3_mixed_traffic.js   # 150 VUs, tráfico mixto
~/.local/bin/k6 run k6_scenario4_payment_escrow.js  # 30-50 VUs, pago/escrow bajo concurrencia
~/.local/bin/k6 run k6_scenario5_soak_test.js       # 25 VUs, carga sostenida (soak test 14 min)
~/.local/bin/k6 run k6_scenario6_new_user_registration.js # 40 VUs, registro de usuarios nuevos
```

**NUNCA correr contra producción** — solo contra localhost:3001.

## Resultados históricos

Ver `01_OBSIDIAN/VAULT_TEMPLATE/03_Tchasky/PRUEBAS_CARGA_CONCURRENCIA_2026-07-31.md`
para la primera corrida completa con output real de k6.

Al agregar una corrida nueva, crear un archivo nuevo
`PRUEBAS_CARGA_CONCURRENCIA_<fecha>.md` en el mismo directorio de
Obsidian, para poder comparar entre corridas (regresiones de latencia,
etc.) — no sobreescribir el histórico.

## Escenario más crítico

`k6_scenario2_race_condition.js` — 50 requests simultáneos intentando
aceptar la MISMA oferta. Debe dar SIEMPRE exactamente 1 ganador (200 OK)
y el resto rechazado con 409 Conflict (métrica `winners_200` debe ser
exactamente 1). Si alguna vez da más de 1 ganador, es un bug crítico de
concurrencia en la máquina de estados — tratar como P0.

## Umbral de upgrade

Si el número de escenarios crece más allá de ~10-15, o hace falta
trackear tendencias de latencia a lo largo del tiempo de forma más
sistemática que archivos markdown sueltos, evaluar pasar a un dashboard
real (k6 Cloud, o exportar resultados a un formato indexable).
