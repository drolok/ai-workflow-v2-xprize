#!/usr/bin/env python3
"""registry_check.py -- valida .ai/registry/*.yaml.

El registro solo sirve si alguien puede ELEGIR con el. Esto hace cumplir el
minimo que hace posible esa eleccion, y falla con exit 2 si no se cumple:

  - parsea con el mismo subconjunto de YAML que usa reality.py (sin pyyaml)
  - _meta con registro y actualizado
  - MODELS: cada modelo con id, estado, verificado, y al menos un usar_para
  - CAPABILITIES: cada capacidad con estado y resuelve_con

ponytail: sin framework de tests. Se corre solo y se lee su salida.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reality import parse_yaml_subset  # noqa: E402

REGISTRY = Path(__file__).resolve().parents[1] / "registry"

EXIGIDO = {
    "MODELS": ("modelos", ("id", "estado", "verificado", "usar_para")),
    "CAPABILITIES": ("capacidades", ("estado", "resuelve_con")),
    "AGENTS": ("agentes", ("id", "rol", "estado", "verificado")),
}


def check(path: Path) -> list:
    errores = []
    data = parse_yaml_subset(path.read_text(encoding="utf-8"), path.name)
    meta = data.get("_meta") or {}
    for clave in ("registro", "actualizado"):
        if not meta.get(clave):
            errores.append(f"{path.name}: _meta sin {clave}")
    nombre = meta.get("registro", "")
    if nombre not in EXIGIDO:
        return errores  # registro sin contrato propio todavia
    seccion, campos = EXIGIDO[nombre]
    entradas = data.get(seccion)
    if not isinstance(entradas, dict) or not entradas:
        errores.append(f"{path.name}: falta la seccion {seccion} o esta vacia")
        return errores
    for eid, entrada in entradas.items():
        if not isinstance(entrada, dict):
            errores.append(f"{path.name}: {eid} no es un mapa")
            continue
        faltan = [c for c in campos if not entrada.get(c)]
        if faltan:
            errores.append(f"{path.name}: {eid} sin {', '.join(faltan)}")
    return errores


def main() -> int:
    archivos = sorted(REGISTRY.glob("*.yaml"))
    if not archivos:
        print("registry_check: no hay registros en .ai/registry/")
        return 2
    todos = []
    for path in archivos:
        errores = check(path)
        todos += errores
        entradas = sum(
            len(v) for v in parse_yaml_subset(path.read_text(encoding="utf-8"), path.name).values()
            if isinstance(v, (dict, list))
        )
        print(f"{'FALLA' if errores else 'OK   '} {path.name} ({entradas} entradas)")
    for e in todos:
        print("  -", e)
    return 2 if todos else 0


if __name__ == "__main__":
    raise SystemExit(main())
