#!/usr/bin/env python3
"""milestones.py -- los hitos HIT0..HITn del diseno (seccion 28).

Un hito NO es una estructura paralela al ledger: es un CORTE sobre el.
`.ai/events/EVENTS.jsonl` sigue siendo el registro crudo de todo lo que pasa;
un hito marca el cierre de un bloque de trabajo, guarda lo que hay que
recordar de el (estado, decisiones, errores, resultados, metricas, patrones)
y se queda con la ventana de eventos que cubre.

La idea que lo hace valer, y que es literal del diseno:

    "no deben entrar todos al contexto. Tus diferentes ventanas pueden
     analizar los ultimos 10 hitos, los ultimos 50, los ultimos 100, para
     descubrir diferentes escalas de patron."

Por eso `ver` imprime una linea por hito y no el JSON entero, y `patrones`
existe: memoria corta, media y larga son la MISMA lista leida con tres
ventanas distintas.

Subcomandos:

  crear --actor A --titulo T [--estado S] [--decision D]... [--error E]...
        [--resultado R]... [--metrica k=v]... [--patron P]... [--commit SHA]...
      Crea el siguiente HIT<n>, calcula la ventana de eventos desde el hito
      anterior y emite MILESTONE al ledger. Append-only: nunca reescribe.

  ver [--ultimos N] [--campo CAMPO] [--id HITn]
      Una linea por hito. Con --campo imprime solo ese campo. Con --id
      vuelca un hito entero en JSON (la unica via que carga todo).

  patrones [--ultimos N]
      Que se repite en la ventana: patrones, errores y actores, ordenados
      por frecuencia. Correr con 10, 50 y 100 da tres escalas distintas.

  autoprueba
      Chequeo propio sobre un almacen temporal. Sin framework de tests.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reality import append_event, now_utc, read_events  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STORE = Path(os.environ.get("AI_MILESTONES", ROOT / ".ai" / "milestones" / "MILESTONES.jsonl"))


def leer() -> list[dict]:
    if not STORE.exists():
        return []
    out = []
    for n, linea in enumerate(STORE.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            out.append(json.loads(linea))
        except json.JSONDecodeError as exc:
            sys.exit(f"{STORE}:{n}: linea corrupta ({exc}) -- investigar, NO reescribir")
    return out


def ventana_de_eventos(desde: str | None) -> dict:
    """Los eventos del ledger posteriores al hito anterior. Esto es lo que
    convierte un hito en un corte y no en un documento suelto."""
    eventos = [e for e in read_events() if desde is None or e.get("ts", "") > desde]
    tipos = collections.Counter(e.get("type") for e in eventos)
    return {
        "desde": desde,
        "n": len(eventos),
        "tipos": dict(sorted(tipos.items())),
        "actores": sorted({e.get("actor") for e in eventos if e.get("actor")}),
    }


def cmd_crear(args) -> int:
    hitos = leer()
    anterior = hitos[-1] if hitos else None
    hito = {
        "id": f"HIT{len(hitos)}",
        "ts": now_utc(),
        "actor": args.actor,
        "titulo": args.titulo,
        "estado": args.estado or "",
        "decisiones": args.decision,
        "errores": args.error,
        "resultados": args.resultado,
        "metricas": dict(m.split("=", 1) for m in args.metrica),
        "patrones": args.patron,
        "commits": args.commit,
        "eventos": ventana_de_eventos(anterior["ts"] if anterior else None),
    }
    STORE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(hito, ensure_ascii=False, sort_keys=True) + "\n")
    if not args.sin_evento:
        append_event("MILESTONE", args.actor, None, {"hito": hito["id"], "titulo": hito["titulo"]})
    print(f"{hito['id']} creado - {hito['eventos']['n']} eventos del ledger en la ventana")
    return 0


def cmd_ver(args) -> int:
    hitos = leer()
    if args.id:
        elegido = [h for h in hitos if h["id"] == args.id]
        if not elegido:
            sys.exit(f"no existe {args.id} (hay {len(hitos)} hitos)")
        print(json.dumps(elegido[0], ensure_ascii=False, indent=1, sort_keys=True))
        return 0
    ventana = hitos[-args.ultimos:] if args.ultimos else hitos
    if not ventana:
        print("no hay hitos todavia")
        return 0
    for h in ventana:
        if args.campo:
            valor = h.get(args.campo)
            for v in (valor if isinstance(valor, list) else [valor]):
                if v:
                    print(f"{h['id']}  {v}")
        else:
            print(f"{h['id']:<6} {h['ts'][:16]}  {h.get('estado','?'):<9} {h['titulo']}")
    if not args.campo:
        print(f"-- {len(ventana)} de {len(hitos)} hitos")
    return 0


def cmd_patrones(args) -> int:
    hitos = leer()
    ventana = hitos[-args.ultimos:] if args.ultimos else hitos
    if not ventana:
        print("no hay hitos todavia")
        return 0
    print(f"ventana: {len(ventana)} hitos de {len(hitos)} ({ventana[0]['id']}..{ventana[-1]['id']})")
    for campo in ("patrones", "errores"):
        cuenta = collections.Counter(v for h in ventana for v in h.get(campo, []))
        repetidos = [(v, n) for v, n in cuenta.most_common() if n > 1]
        print(f"\n{campo} que se repiten ({len(cuenta)} distintos):")
        if not repetidos:
            print("  ninguno se repite todavia -- la ventana es corta o el patron aun no existe")
        for v, n in repetidos:
            print(f"  {n}x  {v}")
    actores = collections.Counter(h.get("actor") for h in ventana)
    print("\nactores:", ", ".join(f"{a} {n}" for a, n in actores.most_common()))
    return 0


def cmd_autoprueba(_args) -> int:
    import tempfile
    global STORE
    with tempfile.TemporaryDirectory() as tmp:
        STORE = Path(tmp) / "M.jsonl"
        args = argparse.Namespace(
            actor="prueba", titulo="uno", estado="verde", decision=[], error=["timeout"],
            resultado=[], metrica=["n=1"], patron=["mismo"], commit=[], sin_evento=True)
        cmd_crear(args)
        args.titulo, args.metrica = "dos", ["n=2"]
        cmd_crear(args)
        hitos = leer()
        assert [h["id"] for h in hitos] == ["HIT0", "HIT1"], "los ids no son correlativos"
        assert hitos[0]["eventos"]["desde"] is None, "el primer hito no puede tener corte anterior"
        assert hitos[1]["eventos"]["desde"] == hitos[0]["ts"], "la ventana no arranca en el hito previo"
        assert hitos[1]["metricas"] == {"n": "2"}, "las metricas no se parsearon"
        cuenta = collections.Counter(v for h in hitos for v in h["patrones"])
        assert cuenta["mismo"] == 2, "el conteo de patrones no acumula entre hitos"
    print("OK autoprueba: ids correlativos, ventana encadenada, metricas, conteo de patrones")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="milestones.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("crear", help="cerrar un bloque de trabajo como HIT<n>")
    c.add_argument("--actor", required=True)
    c.add_argument("--titulo", required=True)
    c.add_argument("--estado", default="")
    for campo in ("decision", "error", "resultado", "metrica", "patron", "commit"):
        c.add_argument(f"--{campo}", action="append", default=[])
    c.add_argument("--sin-evento", action="store_true", help="no emitir MILESTONE al ledger")
    c.set_defaults(fn=cmd_crear)

    v = sub.add_parser("ver", help="una linea por hito, sin cargarlos enteros")
    v.add_argument("--ultimos", type=int, default=10)
    v.add_argument("--campo")
    v.add_argument("--id")
    v.set_defaults(fn=cmd_ver)

    t = sub.add_parser("patrones", help="que se repite en los ultimos N hitos")
    t.add_argument("--ultimos", type=int, default=10)
    t.set_defaults(fn=cmd_patrones)

    sub.add_parser("autoprueba", help="chequeo propio sobre un almacen temporal").set_defaults(fn=cmd_autoprueba)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
