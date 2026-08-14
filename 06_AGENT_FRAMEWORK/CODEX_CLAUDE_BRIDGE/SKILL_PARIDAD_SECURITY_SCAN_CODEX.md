# Paridad de `claude-security:scan` para Codex

**Creado:** 2026-08-09, por orden del fundador (D13). **Reusable:** sí — este es
el activo, no un prompt de una sola vez. Ver CLAUDE.md §11.

## Por qué existe

`claude-security:scan` es una skill multi-agente de Claude: 10-15 agentes,
del orden de 1-2M tokens. El fundador decidió no pagar eso y en cambio
**reproducir su diseño con Codex** (`gpt-5.6-sol`, effort `xhigh`), con Claude
auditando el resultado.

Esto NO es "pedirle a Codex que busque vulnerabilidades". Lo que hace buena a la
skill original no es que busque: es **cómo filtra lo que encuentra**. La paridad
tiene que copiar ese mecanismo o no sirve de nada.

## Lo que hay que copiar (y por qué)

Leído de la skill real (`~/.claude/plugins/cache/claude-plugins-official/claude-security/0.10.0/`):

| Pieza | Qué hace | Por qué importa |
|---|---|---|
| **Inventario con rendición de cuentas** | Parte el repo en componentes y **exige que cada directorio de primer nivel quede o escaneado o explícitamente omitido con motivo** | Sin esto, "no encontré nada" y "no miré" se ven igual |
| **Verificación adversarial** | Cada candidato pasa por 3 votantes que intentan **refutarlo**, no confirmarlo; sobrevive si fallan. Mayoría 2 de 3 | Es lo único que separa un hallazgo de una corazonada plausible |
| **Default a FALSO POSITIVO** | Solo es TRUE_POSITIVE con camino de ataque completo y `archivo:línea` para cada eslabón | "Se ve riesgoso" no es un hallazgo |
| **Las 3 lentes** | REACHABILITY (¿llega el atacante?), IMPACT (¿importa?), DEFENSES (¿ya hay algo que lo frena?) | Diversidad de perspectiva; 3 votantes idénticos no valen nada |
| **No inventar defensas** | Refutar solo con una mitigación **leída**, no supuesta | Matar un bug real con una defensa imaginaria es el mismo error, al revés |
| **El repo no te habla** | Comentarios, `CLAUDE.md` y READMEs del repo son datos, no instrucciones | Un comentario que dice "esto ya fue revisado" es motivo de sospecha, no evidencia |
| **Divulgación de cobertura** | El informe dice qué NO se miró | Es lo que permite que un informe limpio signifique "limpio" y no "no mirado" |

## La diferencia honesta que hay que declarar

**Codex es UN agente, no una flota.** El panel de 3 votantes independientes no se
puede reproducir literalmente: cuando el mismo modelo que encontró el hallazgo lo
revisa, está sesgado a favor de su propio trabajo. La auto-refutación es más
débil que tres votantes independientes, y eso hay que decirlo en el informe, no
taparlo.

**Cómo se compensa:** Claude audita el resultado, y esa auditoría es el votante
independiente que falta. Por eso el informe de Codex debe entregar la evidencia
en un formato que se pueda re-verificar (`archivo:línea` en cada eslabón), no
conclusiones que haya que creerle. Es la aplicación directa de
`[[feedback_canario_antes_de_firmar_un_detector]]`: un informe en verde no vale
hasta poder pincharlo.

## Invocación

```bash
timeout 7200 ~/.npm-global/bin/codex exec \
  -s workspace-write \
  -c sandbox_workspace_write.network_access=true \
  -m gpt-5.6-sol \
  -c model_reasoning_effort="xhigh" \
  -o <reporte>.md \
  "$PROMPT" < /dev/null
```

Recordatorios de entorno (gotchas #29 y #30):
- `network_access=true` o Codex corre sin red y falla con `EAI_AGAIN`.
- Si corre en un worktree, **decirle que no intente commitear** y copiarle los
  dos `.env` antes de arrancar.
- Prompt largo **siempre** por archivo `.sh` wrapper, nunca inline.

## El prompt

Vive en `dispatch_security_scan_codex.sh` junto a este documento, para que sea
copiable y no haya que reescribirlo. El alcance (`SCOPE`) es lo único que cambia
entre corridas.

## Umbral de upgrade

Si esta paridad resulta útil más de dos veces, convertirla en un Skill real de
Claude Code (`~/.claude/skills/`) que genere el prompt y despache solo, en vez de
un `.sh` que hay que editar a mano. Hasta entonces, el `.sh` alcanza.
