#!/usr/bin/env python3
"""Genera un handoff orientado a auditoría, sin ejecutar ni modificar proyectos."""
from __future__ import annotations
import argparse, hashlib, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\AI_WORKFLOW")
EXCLUDE = {"tchasky", ".git", "node_modules", "__pycache__"}

def recent_files(hours: int) -> list[Path]:
    cutoff = datetime.now().timestamp() - hours * 3600
    found = []
    # os.walk tolera mejor enlaces/venvs incompletos que Path.rglob en Windows.
    for base, dirs, names in os.walk(ROOT, onerror=lambda _err: None):
        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE]
        for name in names:
            item = Path(base, name)
            try:
                if item.stat().st_mtime >= cutoff: found.append(item)
            except OSError: pass
    return sorted(found, key=lambda p:p.stat().st_mtime, reverse=True)[:80]

def excerpt(path: Path, date: str) -> str:
    if not path.exists(): return "No disponible."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    selected = [f"{n}: {line}" for n,line in enumerate(lines,1) if date in line][:12]
    return "\n".join(selected) if selected else "No se encontró una entrada fechada; verificar el archivo completo."

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", required=True); ap.add_argument("--hours", type=int, default=24); ap.add_argument("--audit-question", default="¿Las afirmaciones de este handoff están respaldadas por los artefactos citados?"); args=ap.parse_args()
    now=datetime.now(timezone.utc); date=now.date().isoformat(); changed=recent_files(args.hours)
    rows="\n".join(f"- `{p.relative_to(ROOT).as_posix()}` — {p.stat().st_size} bytes — UTC {datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}" for p in changed) or "- Ninguno detectado en la ventana; verificar el reloj y el alcance."
    decisions=excerpt(ROOT / "00_COMMAND_CENTER" / "DECISION_LOG.md", date)
    current_state=excerpt(ROOT / "00_COMMAND_CENTER" / "CURRENT_STATE.md", date)
    body=f"""# Handoff para auditoría de respaldo

Generado UTC: {now.isoformat()}  
Generador: `06_AGENT_FRAMEWORK/BACKUP_AUDITOR/generate_handoff.py`  
Alcance permitido: `C:\\AI_WORKFLOW`, excluyendo `07_PROJECTS/Tchasky`. No autoriza escritura, red ni shell libre.

## Pregunta de auditoría

{args.audit_question}

## Afirmaciones a verificar

- El generador sólo inventaría esta lista si lo hiciera explícitamente un operador; las afirmaciones de trabajo deben añadirse con evidencia primaria.
- Los archivos recientes enumerados abajo existían cuando se generó el handoff; su contenido y estado Git no quedan probados por esta lista.

## Evidencia primaria disponible

- Decisiones de hoy: `00_COMMAND_CENTER/DECISION_LOG.md`.
- Estado operativo: `00_COMMAND_CENTER/CURRENT_STATE.md`.
- Gateway: `06_AGENT_FRAMEWORK/BACKUP_AUDITOR/tools_gateway.py`.
- Use `read_file`, `grep`, `git_status`, `git_diff`, `docker_ps` o `certification_files` del gateway. No confíe en esta sección sin consultarlos.

### Extracto de decisiones (índice, no prueba)

{decisions}

### Tareas/estado reportados hoy (índice, no prueba)

{current_state}

## Archivos modificados recientemente (ventana: {args.hours} h)

{rows}

## Ledger de decisiones

| Afirmación | Estado | Evidencia que debe consultarse | Qué invalidaría la afirmación |
|---|---|---|---|
| No se autorizan APIs/suscripciones pagas sin aprobación | PENDIENTE_DE_VERIFICAR | `00_COMMAND_CENTER/DECISION_LOG.md` | Una entrada posterior que permita el gasto |
| El auditor no toca Tchasky | PENDIENTE_DE_VERIFICAR | Código del gateway + rutas solicitadas | Cualquier operación que acepte una ruta Tchasky |

## Huecos conocidos y siguientes verificaciones

- Este generador no ejecuta tests ni deduce tareas completadas: exige evidencia explícita.
- Git puede no aplicar si `C:\\AI_WORKFLOW` no es un repositorio válido; ejecutar `git_status` y registrar su resultado.
- Verificar hashes de los artefactos críticos mediante `certification_files` antes de emitir un dictamen.
"""
    digest=hashlib.sha256(body.encode()).hexdigest(); body += f"\n## Integridad\n\nSHA-256 del cuerpo anterior: `{digest}`\n"
    output=Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(body,encoding="utf-8")
    print(output)
if __name__ == "__main__": main()
