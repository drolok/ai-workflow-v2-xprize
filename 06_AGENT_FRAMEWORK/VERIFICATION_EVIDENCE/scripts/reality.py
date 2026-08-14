#!/usr/bin/env python3
"""reality.py -- la shared reality de S3 (Fase 1 del spec de contratos v1).

Un solo binario, stdlib puro (Python 3.13 de Windows), subcomandos:

  event TYPE --actor A [--task T] [--payload JSON]
      Append al ledger .ai/events/EVENTS.jsonl (contrato 2.2). ts/type/actor
      obligatorios. El ledger NUNCA se reescribe: solo append.
  task-create --id N --title .. --owner .. --reviewer .. --risk .. [..]
      Crea .ai/tasks/TASK-<n>.yaml (contrato 2.1). HACE CUMPLIR:
      owner != reviewer; riesgo HIGH exige criterio de canario. Emite
      TASK_CREATED al ledger.
  task-status TASK-N NUEVO_STATUS --actor A
      Cambia status del task y emite TASK_STATUS {from,to} al ledger.
  task-validate [ARCHIVO..]
      Valida tasks escritos a mano (la via de escape del create). Exit 2 si
      alguno viola el contrato.
  lease RUTA
      Quien tiene el lease de un archivo (locked_files de tasks activos).
  handoff-validate ARCHIVO
      Contrato 2.3: what_i_verified / what_i_did_not_verify obligatorias.
  agents
      Genera .ai/state/agents.json (contrato 2.4) desde el heartbeat del hook
      y los tasks activos. freshness=live: SIEMPRE estampa generated_at nuevo
      (preservar el timestamp de un artefacto "live" seria mentir).
  derive
      Reconcilia primero el ciclo de vida desde evidencia durable del disco y
      genera .ai/generated/CURRENT_STATE.json DERIVADO de ledger + tasks.
      La reconciliacion es idempotente: nunca duplica un hecho ya registrado.
      Nunca se escribe a mano. Determinista byte a byte: preserva
      generated_at si items/inputs/generator no cambiaron (patron de
      build_registries.py). NO embebe datos "live" (heartbeats): los apunta
      (state_ref), porque el hook late en cada comando de shell y romperia
      el diff vacio de dos corridas.
  merge-gate TASK-N
      Permite el merge solo si el ultimo REVIEW_VERDICT del task es APROBADO.
  reports-check
      Exige contenido minimo en el reporte crudo de cada task cerrado cuyo
      owner es codex; la deuda historica se explicita, no se inventa ni oculta.
  read RUTA --max-age-hours H
      El lector que aplica la regla 0 del spec: un artefacto sin _meta
      fresco SE TRATA COMO AUSENTE (exit 3), no como verdadero.
  selftest
      Chequeos puros del parser/emisor YAML y de las reglas. Exit != 0 si
      algo se rompe.

YAML: no hay PyYAML en este entorno (stdlib puro, decision de S2). Este
archivo trae un emisor y un parser de un SUBCONJUNTO estricto -- claves
`k: v`, bloques anidados de 2 espacios, listas `- item` / `- k: v`, inline
`[a, b]` y `{k: v}` -- y ante cualquier cosa fuera del subconjunto FALLA
RUIDOSO con archivo y linea, nunca parsea en silencio algo distinto de lo
que el autor escribio. El spec (seccion 1) exige exactamente esto si se usa
YAML sin dependencia.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / ".ai" / "events" / "EVENTS.jsonl"
TASKS = ROOT / ".ai" / "tasks"
REPORTS = ROOT / ".ai" / "reports"
HANDOFFS = ROOT / ".ai" / "handoffs"
STATE = ROOT / ".ai" / "state" / "agents.json"
CURRENT = ROOT / ".ai" / "generated" / "CURRENT_STATE.json"
HEARTBEAT = ROOT / "08_REPORTS" / "WATCHDOG" / "heartbeat.txt"
LIFECYCLE_CONFIG = ROOT / ".ai" / "lifecycle" / "CONFIG.json"
LIFECYCLE_RECONSTRUCTION = ROOT / ".ai" / "lifecycle" / "TASK-101_RECONSTRUCTION.json"
LEDGER_WARN_AFTER_HOURS = 12.0

RISKS = ("LOW", "MEDIUM", "HIGH")
STATUSES = ("proposed", "accepted", "implementing", "review", "fixing", "done", "blocked")
# Un lease se libera recien en done: un task blocked sigue siendo dueno de
# sus archivos (nadie mas deberia tocarlos mientras se destraba).
LEASE_RELEASED = ("done",)
ALIVE_WINDOW_MIN = 10  # el hook late en cada comando de shell; 10 min es holgado


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def die(msg: str, code: int = 2) -> None:
    print(f"RECHAZADO: {msg}", file=sys.stderr)
    raise SystemExit(code)


# ---------------------------------------------------------------- YAML subset


class YamlSubsetError(Exception):
    pass


def _scalar(raw: str, where: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [] if not inner else [_scalar(p, where) for p in inner.split(",")]
    if raw.startswith("{") and raw.endswith("}"):
        inner = raw[1:-1].strip()
        out = {}
        for part in ([] if not inner else inner.split(",")):
            if ":" not in part:
                raise YamlSubsetError(f"{where}: entrada de mapa inline sin ':': {part!r}")
            k, v = part.split(":", 1)
            out[k.strip()] = _scalar(v, where)
        return out
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    if raw in (">", "|") or raw.startswith((">", "|")) and len(raw) <= 2:
        raise YamlSubsetError(f"{where}: bloques multilinea '>'/'|' fuera del subconjunto -- usar una sola linea")
    if raw.startswith(("&", "*", "?")):
        raise YamlSubsetError(f"{where}: anclas/referencias YAML fuera del subconjunto: {raw!r}")
    return raw


def parse_yaml_subset(text: str, source: str = "<yaml>") -> dict:
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlSubsetError(f"{source}:{n}: tab en la indentacion -- solo espacios")
        lines.append((n, raw))
    obj, nxt = _parse_block(lines, 0, 0, source)
    if nxt != len(lines):
        n, raw = lines[nxt]
        raise YamlSubsetError(f"{source}:{n}: linea fuera de estructura: {raw!r}")
    if not isinstance(obj, dict):
        raise YamlSubsetError(f"{source}: el documento raiz debe ser un mapa")
    return obj


def _indent_of(raw: str) -> int:
    return len(raw) - len(raw.lstrip(" "))


def _parse_block(lines, i, indent, source):
    first = lines[i][1].lstrip()
    if first.startswith("- "):
        return _parse_list(lines, i, indent, source)
    return _parse_map(lines, i, indent, source)


def _parse_map(lines, i, indent, source):
    out = {}
    while i < len(lines):
        n, raw = lines[i]
        ind = _indent_of(raw)
        if ind < indent:
            break
        if ind != indent:
            raise YamlSubsetError(f"{source}:{n}: indentacion {ind} inesperada (se esperaba {indent})")
        body = raw.strip()
        if body.startswith("- "):
            break
        if ":" not in body:
            raise YamlSubsetError(f"{source}:{n}: se esperaba 'clave: valor', vino: {body!r}")
        key, _, rest = body.partition(":")
        key = key.strip()
        if key in out:
            raise YamlSubsetError(f"{source}:{n}: clave duplicada: {key!r}")
        rest = rest.strip()
        if rest:
            out[key] = _scalar(rest, f"{source}:{n}")
            i += 1
        else:
            i += 1
            if i >= len(lines) or _indent_of(lines[i][1]) <= indent:
                raise YamlSubsetError(f"{source}:{n}: '{key}:' sin bloque anidado (para vacio usar [] o {{}})")
            out[key], i = _parse_block(lines, i, _indent_of(lines[i][1]), source)
    return out, i


def _parse_list(lines, i, indent, source):
    out = []
    while i < len(lines):
        n, raw = lines[i]
        ind = _indent_of(raw)
        if ind < indent:
            break
        body = raw.strip()
        if ind != indent or not body.startswith("- "):
            break
        item = body[2:].strip()
        if ":" in item and not (item.startswith(("[", "{", "'", '"'))):
            # '- clave: valor' -> item mapa; continuaciones con indent+2
            key, _, rest = item.partition(":")
            entry = {key.strip(): _scalar(rest, f"{source}:{n}")}
            i += 1
            while i < len(lines) and _indent_of(lines[i][1]) == indent + 2 \
                    and not lines[i][1].strip().startswith("- "):
                n2, raw2 = lines[i]
                body2 = raw2.strip()
                if ":" not in body2:
                    raise YamlSubsetError(f"{source}:{n2}: continuacion de item sin ':': {body2!r}")
                k2, _, r2 = body2.partition(":")
                k2 = k2.strip()
                if k2 in entry:
                    raise YamlSubsetError(f"{source}:{n2}: clave duplicada en item: {k2!r}")
                if not r2.strip():
                    raise YamlSubsetError(f"{source}:{n2}: bloque anidado dentro de item de lista fuera del subconjunto")
                entry[k2] = _scalar(r2, f"{source}:{n2}")
                i += 1
            out.append(entry)
        else:
            out.append(_scalar(item, f"{source}:{n}"))
            i += 1
    return out, i


def _emit_scalar(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_emit_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_emit_scalar(v)}" for k, v in value.items()) + "}"
    text = str(value)
    if text == "" or text != text.strip() or text.startswith(("[", "{", "'", '"', "&", "*", "?", "-", ">", "|", "#")) \
            or ": " in text or text.endswith(":"):
        return '"' + text.replace('"', "'") + '"'
    return text


def emit_yaml(data: dict, indent: int = 0) -> str:
    pad = " " * indent
    out = []
    for key, value in data.items():
        if isinstance(value, dict) and value:
            out.append(f"{pad}{key}:")
            out.append(emit_yaml(value, indent + 2))
        elif isinstance(value, list) and value and any(isinstance(v, (dict, list)) or ": " in str(v) for v in value):
            out.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    keys = list(item.keys())
                    out.append(f"{pad}  - {keys[0]}: {_emit_scalar(item[keys[0]])}")
                    for k in keys[1:]:
                        out.append(f"{pad}    {k}: {_emit_scalar(item[k])}")
                else:
                    out.append(f"{pad}  - {_emit_scalar(item)}")
        else:
            out.append(f"{pad}{key}: {_emit_scalar(value)}")
    return "\n".join(out) + ("\n" if indent == 0 else "")


def load_yaml_file(path: Path) -> dict:
    try:
        return parse_yaml_subset(path.read_text(encoding="utf-8"), str(path))
    except YamlSubsetError as exc:
        die(f"YAML fuera del subconjunto soportado -- {exc}")
    except OSError as exc:
        die(f"no se pudo leer {path}: {exc}")


# ------------------------------------------------------------------- eventos


def append_event(etype: str, actor: str, task: str | None, payload, ts: str | None = None) -> dict:
    if not etype or not etype.strip():
        die("type vacio -- ts/type/actor son obligatorios (contrato 2.2)")
    if not actor or not actor.strip():
        die("actor vacio -- ts/type/actor son obligatorios (contrato 2.2)")
    stamp = ts or now_utc()
    try:
        parsed_stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed_stamp.tzinfo is None:
            raise ValueError("timestamp sin zona horaria")
    except ValueError as exc:
        die(f"timestamp de evento invalido {stamp!r}: {exc}")
    event = {"ts": stamp, "type": etype.strip(), "actor": actor.strip()}
    if task:
        event["task"] = task
    if payload is not None:
        event["payload"] = payload
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with io.open(EVENTS, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return event


def read_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    out = []
    for n, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            die(f"{EVENTS}:{n}: linea corrupta en el ledger ({exc}) -- investigar, NO reescribir")
    return out


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_from_epoch_ns(epoch_ns: int) -> str:
    seconds, nanos = divmod(epoch_ns, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{nanos:09d}Z" if nanos else base + "Z"


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp sin zona horaria")
    return parsed.astimezone(timezone.utc)


def load_json_file(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"no se pudo leer {path}: {exc}")
    if not isinstance(value, dict):
        die(f"{path}: se esperaba un objeto JSON en la raiz")
    return value


_GUARD_RECORD = re.compile(
    r"(?m)^(?P<ts>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) BYPASS[^\n]*:"
)
_CODEX_DISPATCH = re.compile(
    r"cat\s+['\"]?[^\s'\"|]*TASK-(?P<id>\d+)_owner\.md['\"]?\s*\|\s*[^\n]*?\bcodex\s+exec\b"
)


def guard_dispatch_records(path: Path) -> list[dict]:
    """Extrae despachos reales del log escrito antes de ejecutar el comando."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    starts = list(_GUARD_RECORD.finditer(text))
    records = []
    for idx, match in enumerate(starts):
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(text)
        block = text[match.start():end]
        line = text.count("\n", 0, match.start()) + 1
        for command_match in _CODEX_DISPATCH.finditer(block):
            command = command_match.group(0).strip()
            records.append({
                "task": f"TASK-{command_match.group('id')}",
                "ts": match.group("ts"),
                "line": line,
                "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
            })
    return records


def lifecycle_fact_exists(events: list[dict], candidate: dict) -> bool:
    task = candidate.get("task")
    etype = candidate.get("type")
    candidate_evidence = candidate.get("payload", {}).get("evidencia", {})
    candidate_key = (
        candidate_evidence.get("command_sha256")
        or candidate_evidence.get("sha256")
        or candidate_evidence.get("commit")
    )
    for event in events:
        if event.get("task") != task or event.get("type") != etype:
            continue
        if etype == "TASK_STATUS" and event.get("payload", {}).get("to") == candidate.get("payload", {}).get("to"):
            return True
        event_evidence = event.get("payload", {}).get("evidencia", {})
        event_key = (
            event_evidence.get("command_sha256")
            or event_evidence.get("sha256")
            or event_evidence.get("commit")
        )
        if candidate_key and event_key == candidate_key:
            return True
        if event.get("ts") == candidate.get("ts"):
            return True
    return False


def verify_reconstructed_candidate(candidate: dict, dispatches: list[dict]) -> None:
    evidence = candidate.get("payload", {}).get("evidencia")
    if not isinstance(evidence, dict):
        die(f"{candidate.get('task')} {candidate.get('type')}: evidencia reconstruida ausente")
    kind = evidence.get("tipo")
    if kind == "dispatch_log":
        expected = (candidate.get("task"), candidate.get("ts"))
        if not any((item["task"], item["ts"]) == expected for item in dispatches):
            die(f"{candidate.get('task')}: el despacho {candidate.get('ts')} no aparece en el log del backstop")
        handoff = ROOT / str(evidence.get("handoff"))
        if not handoff.is_file() or sha256_file(handoff) != evidence.get("handoff_sha256"):
            die(f"{candidate.get('task')}: el contrato no coincide con el SHA-256 reconstruido")
        return
    if kind in ("report_file", "completed_stream"):
        source = ROOT / str(evidence.get("path"))
        if not source.is_file() or sha256_file(source) != evidence.get("sha256"):
            die(f"{candidate.get('task')}: la entrega no coincide con el SHA-256 reconstruido")
        actual_ts = utc_from_epoch_ns(source.stat().st_mtime_ns)
        if actual_ts != candidate.get("ts"):
            die(f"{candidate.get('task')}: mtime reconstruido {candidate.get('ts')} != mtime real {actual_ts}")
        if kind == "completed_stream":
            marker = re.compile(rf"\bCompletad[oa]\s+{re.escape(str(candidate.get('task')))}\b", re.IGNORECASE)
            if not marker.search(source.read_text(encoding="utf-8", errors="replace")):
                die(f"{candidate.get('task')}: el stream no contiene una respuesta final completada")
        return
    if kind == "git_commit":
        commit = str(evidence.get("commit", ""))
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "show", "-s", "--format=%H%x09%cI%x09%s", commit],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if proc.returncode != 0:
            die(f"{candidate.get('task')}: commit reconstruido ilegible {commit}: {proc.stderr.strip()}")
        actual_hash, actual_ts, actual_subject = proc.stdout.rstrip("\n").split("\t", 2)
        expected = (commit, evidence.get("committed_at"), evidence.get("subject"))
        if (actual_hash, actual_ts, actual_subject) != expected:
            die(f"{candidate.get('task')}: la evidencia del commit reconstruido ya no coincide con Git")
        if parse_utc(actual_ts) != parse_utc(str(candidate.get("ts"))):
            die(f"{candidate.get('task')}: timestamp del cierre no coincide con el commit")
        return
    die(f"{candidate.get('task')} {candidate.get('type')}: tipo de evidencia desconocido {kind!r}")


def reconstructed_lifecycle_candidates(dispatches: list[dict], events: list[dict]) -> list[dict]:
    if not LIFECYCLE_RECONSTRUCTION.exists():
        return []
    data = load_json_file(LIFECYCLE_RECONSTRUCTION)
    candidates = data.get("events")
    if not isinstance(candidates, list):
        die(f"{LIFECYCLE_RECONSTRUCTION}: 'events' debe ser una lista")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            die(f"{LIFECYCLE_RECONSTRUCTION}: cada evento debe ser un objeto")
        if candidate.get("payload", {}).get("origen") != "reconstruido":
            die(f"{candidate.get('task')}: todo backfill debe declarar origen=reconstruido")
        # La evidencia se verifica antes del primer append. Una vez que el
        # hecho esta en el ledger, su hash ya es historico: una edicion futura
        # del informe no debe inutilizar `derive` ni reescribir el pasado.
        if not lifecycle_fact_exists(events, candidate):
            verify_reconstructed_candidate(candidate, dispatches)
    return candidates


def git_commits_since(started_at: datetime) -> list[dict]:
    since = started_at.isoformat().replace("+00:00", "Z")
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--all", "--reverse", f"--since={since}", "--format=%H"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        die(f"no se pudo derivar cierres desde Git: {proc.stderr.strip()}")
    commits = []
    for commit in [line.strip() for line in proc.stdout.splitlines() if line.strip()]:
        meta = subprocess.run(
            ["git", "-C", str(ROOT), "show", "-s", "--format=%H%x00%cI%x00%B", commit],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        files = subprocess.run(
            ["git", "-C", str(ROOT), "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if meta.returncode != 0 or files.returncode != 0:
            die(f"no se pudo inspeccionar el commit {commit} durante lifecycle-reconcile")
        actual_hash, committed_at, body = meta.stdout.rstrip("\n").split("\x00", 2)
        commits.append({
            "commit": actual_hash,
            "ts": committed_at,
            "body": body.strip(),
            "subject": body.strip().splitlines()[0] if body.strip() else "",
            "files": {line.strip() for line in files.stdout.splitlines() if line.strip()},
        })
    return commits


def paths_named_in_delivery(source: Path) -> set[str]:
    if not source.is_file():
        return set()
    text = source.read_text(encoding="utf-8", errors="replace")
    absolute = re.findall(r"/mnt/c/AI_WORKFLOW_V2/([^\s):\]]+)", text)
    markdown = re.findall(r"\]\((?!https?://)([^\s):\]]+)", text)
    out = set()
    for raw in absolute + markdown:
        clean = raw.split("#", 1)[0].lstrip("./")
        if clean:
            out.add(clean)
    return out


def automatic_lifecycle_candidates(dispatches: list[dict], events: list[dict]) -> list[dict]:
    """Deriva hechos nuevos; la fuente existe aunque nadie recuerde emitir."""
    if not LIFECYCLE_CONFIG.exists():
        return []
    config = load_json_file(LIFECYCLE_CONFIG)
    min_task = int(config.get("automatic_task_min", 0))
    started_at = parse_utc(str(config.get("started_at")))
    closure_window = timedelta(minutes=float(config.get("closure_window_minutes", 10)))
    guard_rel = str(config.get("dispatch_log"))
    candidates = []
    selected_dispatches = []
    responses = {}
    for item in dispatches:
        task_number = int(item["task"].split("-", 1)[1])
        if task_number < min_task or parse_utc(item["ts"]) < started_at:
            continue
        selected_dispatches.append(item)
        handoff = ROOT / ".ai" / "handoffs" / f"{item['task']}_owner.md"
        candidates.append({
            "ts": item["ts"], "type": "DISPATCH", "actor": "claude", "task": item["task"],
            "payload": {
                "origen": "automatico",
                "evidencia": {
                    "tipo": "dispatch_log", "path": guard_rel, "line": item["line"],
                    "command_sha256": item["command_sha256"],
                    "handoff": str(handoff.relative_to(ROOT)) if handoff.exists() else None,
                    "handoff_sha256": sha256_file(handoff) if handoff.is_file() else None,
                },
            },
        })

    for item in selected_dispatches:
        task = item["task"]
        report = ROOT / ".ai" / "reports" / f"{task}.raw.md"
        stream = ROOT / ".ai" / f"task{task.split('-', 1)[1]}_stream.log"
        source = report if report.is_file() and report.stat().st_size else None
        evidence_type = "report_file"
        if source is None and stream.is_file() and stream.stat().st_size:
            marker = re.compile(rf"\bCompletad[oa]\s+{re.escape(task)}\b", re.IGNORECASE)
            if marker.search(stream.read_text(encoding="utf-8", errors="replace")):
                source = stream
                evidence_type = "completed_stream"
        if source is None:
            continue
        response = {
            "ts": utc_from_epoch_ns(source.stat().st_mtime_ns),
            "type": "RESPONSE", "actor": "codex", "task": task,
            "payload": {
                "origen": "automatico", "ok": True,
                "evidencia": {
                    "tipo": evidence_type, "path": str(source.relative_to(ROOT)),
                    "sha256": sha256_file(source), "timestamp_source": "mtime_ns",
                },
            },
        }
        candidates.append(response)
        responses[task] = {"event": response, "source": source}

    already_done = {
        event.get("task") for event in events
        if event.get("type") == "TASK_STATUS" and event.get("payload", {}).get("to") == "done"
    }
    used_commits = {
        event.get("payload", {}).get("evidencia", {}).get("commit") for event in events
        if event.get("type") == "TASK_STATUS"
    }
    unresolved = {task for task in responses if task not in already_done}
    for commit in git_commits_since(started_at):
        if commit["commit"] in used_commits:
            continue
        committed_at = parse_utc(commit["ts"])
        eligible = []
        for task in unresolved:
            responded_at = parse_utc(responses[task]["event"]["ts"])
            if responded_at <= committed_at <= responded_at + closure_window:
                eligible.append(task)
        if not eligible:
            continue
        explicit = [task for task in eligible if re.search(rf"\b{re.escape(task)}\b", commit["body"], re.IGNORECASE)]
        overlaps = [
            task for task in eligible
            if paths_named_in_delivery(responses[task]["source"]) & commit["files"]
        ]
        chosen = None
        rule = None
        if len(explicit) == 1:
            chosen, rule = explicit[0], "task_id_en_commit"
        elif len(overlaps) == 1:
            chosen, rule = overlaps[0], "archivo_entregado_en_commit"
        elif len(eligible) == 1:
            chosen, rule = eligible[0], "unica_entrega_pendiente_en_ventana"
        if chosen is None:
            print(
                "WARN lifecycle-reconcile: commit " + commit["commit"][:12]
                + " ambiguo para " + ", ".join(sorted(eligible)) + "; no se invento TASK_STATUS",
                file=sys.stderr,
            )
            continue
        candidates.append({
            "ts": commit["ts"], "type": "TASK_STATUS", "actor": "claude", "task": chosen,
            "payload": {
                "from": "review", "to": "done", "owner": "codex", "reviewer": "claude",
                "two_key": True, "origen": "automatico",
                "evidencia": {
                    "tipo": "git_commit", "commit": commit["commit"],
                    "committed_at": commit["ts"], "subject": commit["subject"],
                    "regla_asociacion": rule, "ventana_minutos": closure_window.total_seconds() / 60,
                },
            },
        })
        unresolved.remove(chosen)
        used_commits.add(commit["commit"])
    return candidates


def reconcile_lifecycle(events: list[dict]) -> int:
    guard_path = ROOT / ".claude" / "hooks" / "danger_full_access_bypass_log.txt"
    dispatches = guard_dispatch_records(guard_path)
    candidates = reconstructed_lifecycle_candidates(dispatches, events)
    candidates += automatic_lifecycle_candidates(dispatches, events)
    candidates.sort(key=lambda item: parse_utc(str(item.get("ts"))))
    appended = 0
    for candidate in candidates:
        if lifecycle_fact_exists(events, candidate):
            continue
        event = append_event(
            str(candidate.get("type", "")), str(candidate.get("actor", "")),
            candidate.get("task"), candidate.get("payload"), str(candidate.get("ts", "")),
        )
        events.append(event)
        appended += 1
    if appended:
        print(f"OK lifecycle-reconcile: {appended} hecho(s) derivados de evidencia durable")
    else:
        print("OK lifecycle-reconcile: 0 hechos nuevos (idempotente)")
    return appended


def ledger_health(events: list[dict], checked_at: datetime | None = None) -> dict:
    """Mide si el ledger sigue vivo; no altera ni rellena eventos."""
    checked = checked_at or datetime.now(timezone.utc)
    checked = checked.astimezone(timezone.utc)
    checked_text = checked.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    base = {
        "checked_at": checked_text,
        "warn_after_hours": LEDGER_WARN_AFTER_HOURS,
    }
    if not events:
        return {
            **base,
            "status": "WARN",
            "last_event_ts": None,
            "last_event_age_hours": None,
            "reason": "ledger vacio",
        }

    last_ts = events[-1].get("ts")
    try:
        last_at = datetime.fromisoformat(str(last_ts).replace("Z", "+00:00"))
        if last_at.tzinfo is None:
            raise ValueError("timestamp sin zona horaria")
        last_at = last_at.astimezone(timezone.utc)
    except ValueError as exc:
        return {
            **base,
            "status": "WARN",
            "last_event_ts": last_ts,
            "last_event_age_hours": None,
            "reason": f"timestamp final invalido: {exc}",
        }

    age_hours = (checked - last_at).total_seconds() / 3600
    if age_hours < 0:
        return {
            **base,
            "status": "WARN",
            "last_event_ts": last_ts,
            "last_event_age_hours": round(age_hours, 2),
            "reason": "ultimo evento fechado en el futuro",
        }
    status = "WARN" if age_hours > LEDGER_WARN_AFTER_HOURS else "OK"
    reason = (
        f"sin eventos por mas de {LEDGER_WARN_AFTER_HOURS:g} horas"
        if status == "WARN" else "ledger dentro del umbral"
    )
    return {
        **base,
        "status": status,
        "last_event_ts": last_ts,
        "last_event_age_hours": round(age_hours, 2),
        "reason": reason,
    }


# --------------------------------------------------------------------- tasks


def validate_task(data: dict, filename: str) -> list[str]:
    errors = []
    for field in ("id", "title", "owner", "reviewer", "created_by", "created_at", "risk", "status"):
        if not str(data.get(field, "")).strip():
            errors.append(f"falta el campo obligatorio '{field}'")
    tid = str(data.get("id", ""))
    if tid and not (tid.startswith("TASK-") and tid[5:].isdigit()):
        errors.append(f"id invalido: {tid!r} (se espera TASK-<n>)")
    if tid and filename and Path(filename).name != f"{tid}.yaml":
        errors.append(f"el archivo {Path(filename).name!r} no coincide con id {tid!r}")
    owner = str(data.get("owner", "")).strip().lower()
    reviewer = str(data.get("reviewer", "")).strip().lower()
    if owner and reviewer and owner == reviewer:
        errors.append(f"owner == reviewer ({owner!r}) -- Two-Key violado, NUNCA el mismo (contrato 2.1)")
    risk = str(data.get("risk", "")).strip()
    if risk and risk not in RISKS:
        errors.append(f"risk invalido: {risk!r} (validos: {', '.join(RISKS)})")
    status = str(data.get("status", "")).strip()
    if status and status not in STATUSES:
        errors.append(f"status invalido: {status!r} (validos: {', '.join(STATUSES)})")
    acceptance = data.get("acceptance", [])
    if not isinstance(acceptance, list):
        errors.append("acceptance debe ser una lista")
        acceptance = []
    if risk == "HIGH":
        blob = json.dumps(acceptance, ensure_ascii=False).lower()
        if "canario" not in blob:
            errors.append("risk HIGH sin criterio de canario en acceptance -- obligatorio (contrato 2.1)")
    locked = data.get("locked_files", [])
    if not isinstance(locked, list):
        errors.append("locked_files debe ser una lista")
    return errors


def active_tasks() -> list[tuple[Path, dict]]:
    out = []
    if TASKS.is_dir():
        for path in sorted(TASKS.glob("TASK-*.yaml")):
            out.append((path, load_yaml_file(path)))
    return out


def cmd_task_create(args) -> int:
    tid = f"TASK-{args.id}"
    data = {
        "id": tid,
        "title": args.title,
        "objective": args.objective or args.title,
        "owner": args.owner,
        "reviewer": args.reviewer,
        "created_by": args.created_by or args.owner,
        "created_at": now_utc(),
        "scope": {"allowed": args.allowed or [], "forbidden": args.forbidden or []},
        "locked_files": args.lock or [],
        "acceptance": [json.loads(a) for a in (args.acceptance or [])],
        "risk": args.risk,
        "required_validation": args.required_validation.split(",") if args.required_validation else ["reviewer"],
        "status": "proposed",
    }
    path = TASKS / f"{tid}.yaml"
    errors = validate_task(data, str(path))
    if errors:
        die(f"{tid}: " + "; ".join(errors))
    if path.exists():
        die(f"{path} ya existe -- los tasks no se pisan")
    text = emit_yaml(data)
    reparsed = parse_yaml_subset(text, str(path))
    if reparsed != {k: v for k, v in data.items()}:
        die(f"{tid}: el emisor YAML no round-tripea -- bug del emisor, no se escribe nada")
    TASKS.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    append_event("TASK_CREATED", data["created_by"], tid, task_event_payload(
        data, {"risk": data["risk"], "owner": data["owner"], "reviewer": data["reviewer"]}))
    print(f"OK {path.relative_to(ROOT)} creado (owner={data['owner']} reviewer={data['reviewer']} risk={data['risk']})")
    return do_derive()


def cmd_task_status(args) -> int:
    path = TASKS / f"{args.task}.yaml"
    if not path.exists():
        die(f"{path} no existe")
    data = load_yaml_file(path)
    if args.status not in STATUSES:
        die(f"status invalido: {args.status!r} (validos: {', '.join(STATUSES)})")
    previous = data.get("status")

    # Regla 3 del protocolo two-key: EL DONE LO FIRMA EL REVIEWER.
    #
    # Estaba escrita en PROTOCOLO_TWO_KEY.md y no la hacia cumplir nadie. El
    # agujero lo encontro el rojo del registro retroactivo de TASK-10 el
    # 2026-08-11: `task-status TASK-10 done --actor codex` -- el owner firmando
    # su propio done -- devolvia OK.
    #
    # Que owner != reviewer se validara en `task-create` no alcanza: eso separa
    # los roles al abrir el task, pero si despues el owner puede firmar el
    # cierre, el dos-llaves se vuelve una convencion y no una garantia. La regla
    # tiene que estar en el unico lugar donde el ciclo se cierra.
    if args.status == "done":
        reviewer = (data.get("reviewer") or "").strip()
        actor = (args.actor or "").strip()
        if reviewer and actor != reviewer:
            quien = "el OWNER" if actor == (data.get("owner") or "").strip() else "un tercero"
            die(f"{args.task}: el done lo firma el reviewer ({reviewer!r}), "
                f"y lo esta intentando {quien} ({actor!r}). "
                f"Regla 3 del protocolo two-key: el que implementa no firma su propio done.")

    data["status"] = args.status
    errors = validate_task(data, str(path))
    if errors:
        die(f"{args.task}: " + "; ".join(errors))
    path.write_text(emit_yaml(data), encoding="utf-8", newline="\n")
    append_event("TASK_STATUS", args.actor, args.task,
                 task_event_payload(data, {"from": previous, "to": args.status}))
    print(f"OK {args.task}: {previous} -> {args.status}")
    return do_derive()


def cmd_task_validate(args) -> int:
    paths = [Path(p) for p in args.files] if args.files else [p for p, _ in active_tasks()]
    if not paths:
        print("OK 0 tasks (no hay nada que validar)")
        return 0
    failed = 0
    for path in paths:
        errors = validate_task(load_yaml_file(path), str(path))
        if errors:
            failed += 1
            for err in errors:
                print(f"RECHAZADO {path.name}: {err}", file=sys.stderr)
        else:
            print(f"OK {path.name}")
    return 2 if failed else 0


def cmd_lease(args) -> int:
    holders = []
    for path, data in active_tasks():
        if str(data.get("status", "")) in LEASE_RELEASED:
            continue
        locked = data.get("locked_files", [])
        if isinstance(locked, list) and args.path in [str(x) for x in locked]:
            holders.append({"task": data.get("id"), "owner": data.get("owner"),
                            "since": data.get("created_at"), "status": data.get("status")})
    if holders:
        print(json.dumps({"path": args.path, "leased": True, "holders": holders},
                         ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps({"path": args.path, "leased": False}, ensure_ascii=False, sort_keys=True))
    return 0


# ------------------------------------------------------------------ handoffs


def cmd_handoff_validate(args) -> int:
    path = Path(args.file)
    data = load_yaml_file(path)
    errors = []
    for field in ("id", "from", "to", "created_at", "next_action"):
        if field not in data or (isinstance(data[field], str) and not data[field].strip()):
            errors.append(f"falta el campo obligatorio '{field}'")
    for section in ("what_i_verified", "what_i_did_not_verify"):
        value = data.get(section)
        if not isinstance(value, list):
            errors.append(f"falta la seccion obligatoria '{section}' (lista; [] solo si es literalmente vacia)")
            continue
        required = ("claim", "evidence") if section == "what_i_verified" else ("claim", "why")
        for idx, item in enumerate(value):
            if not isinstance(item, dict) or any(not str(item.get(k, "")).strip() for k in required):
                errors.append(f"{section}[{idx}]: cada item lleva {' y '.join(required)}")
    if "what_i_verified" in data and isinstance(data.get("what_i_verified"), list) and not data["what_i_verified"]:
        errors.append("what_i_verified vacio: un handoff que no verifico NADA no es un handoff, es una nota")
    if errors:
        die(f"{path.name}: " + "; ".join(errors))
    print(f"OK {path.name} cumple el contrato 2.3")
    return 0


# ---------------------------------------------------------- agents / derive


def generator_hash() -> str:
    with io.open(__file__, "rb") as fh:
        return sha256_bytes(fh.read())


def is_synthetic_marker(value) -> bool:
    return value is True or value == "true"


def task_event_payload(task: dict, payload: dict) -> dict:
    out = dict(payload)
    if is_synthetic_marker(task.get("synthetic")):
        out["synthetic"] = True
    return out


def is_real_event(event: dict) -> bool:
    payload = event.get("payload")
    return event.get("type") != "CANARY" and not (
        isinstance(payload, dict) and is_synthetic_marker(payload.get("synthetic"))
    )


def is_s6_done_task(task: dict) -> bool:
    return task.get("status") == "done" and not is_synthetic_marker(task.get("synthetic"))


def cmd_agents(_args) -> int:
    agents: dict[str, dict] = {}
    heartbeat = None
    if HEARTBEAT.exists():
        heartbeat = HEARTBEAT.read_text(encoding="utf-8").strip() or None
    alive = False
    if heartbeat:
        try:
            beat = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
            alive = (datetime.now(timezone.utc) - beat).total_seconds() < ALIVE_WINDOW_MIN * 60
        except ValueError:
            heartbeat = None
    agents["claude"] = {"heartbeat": heartbeat, "alive": alive,
                        "heartbeat_source": str(HEARTBEAT.relative_to(ROOT))}
    for _path, data in active_tasks():
        status = str(data.get("status", ""))
        if status in LEASE_RELEASED:
            continue
        for role_field, role in (("owner", "implementer"), ("reviewer", "reviewer")):
            name = str(data.get(role_field, "")).strip().lower()
            if not name:
                continue
            entry = agents.setdefault(name, {"heartbeat": None, "alive": False, "heartbeat_source": None})
            entry.setdefault("tasks", []).append({"task": data.get("id"), "role": role, "status": status})
    payload = {
        "_meta": {
            "generated_at": now_utc(),  # live: preservar el timestamp seria mentir
            "generator": ".ai/bin/reality.py agents",
            "generator_hash": generator_hash(),
            "freshness": "live",
            "item_count": len(agents),
        },
        "agents": agents,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(canonical(payload), encoding="utf-8", newline="\n")
    print(f"OK {STATE.relative_to(ROOT)}: {len(agents)} agente(s), heartbeat {'vivo' if alive else 'MUERTO/ausente'}")
    return 0


def do_derive() -> int:
    events = read_events()
    reconcile_lifecycle(events)
    by_type: dict[str, int] = {}
    actors: set[str] = set()
    per_task_events: dict[str, list[dict]] = {}
    for ev in events:
        by_type[ev.get("type", "?")] = by_type.get(ev.get("type", "?"), 0) + 1
        actors.add(ev.get("actor", "?"))
        if ev.get("task"):
            per_task_events.setdefault(ev["task"], []).append(ev)

    tasks_out, invalid, inconsistencies = [], [], []
    tasks_done = 0
    tasks_synthetic = 0
    task_files = active_tasks()
    for path, data in task_files:
        errors = validate_task(data, str(path))
        if errors:
            invalid.append({"file": str(path.relative_to(ROOT)), "errors": errors})
            continue
        tid = str(data.get("id"))
        tev = per_task_events.get(tid, [])
        last = tev[-1] if tev else None
        status_events = [e for e in tev if e.get("type") == "TASK_STATUS"]
        if status_events and status_events[-1].get("payload", {}).get("to") != data.get("status"):
            inconsistencies.append({
                "task": tid,
                "file_status": data.get("status"),
                "last_event_status": status_events[-1].get("payload", {}).get("to"),
                "detalle": "el YAML y el ledger no cuentan la misma historia -- investigar antes de confiar en cualquiera",
            })
        tasks_out.append({
            "id": tid, "title": data.get("title"), "owner": data.get("owner"),
            "reviewer": data.get("reviewer"), "risk": data.get("risk"),
            "status": data.get("status"), "events": len(tev),
            "checkpoints": sum(1 for e in tev if e.get("type") == "CHECKPOINT"),
            "last_event": {"ts": last["ts"], "type": last["type"]} if last else None,
        })
        if data.get("status") == "done" and is_synthetic_marker(data.get("synthetic")):
            tasks_synthetic += 1
        elif is_s6_done_task(data):
            tasks_done += 1

    events_synthetic = sum(
        1 for event in events
        if isinstance(event.get("payload"), dict)
        and is_synthetic_marker(event["payload"].get("synthetic"))
    )
    real_events = [event for event in events if is_real_event(event)]
    health = ledger_health(events)
    state = {
        "events": {
            "count": len(events), "count_real": len(real_events), "by_type": by_type,
            "actors": sorted(actors),
            "first_ts": events[0]["ts"] if events else None,
            "last_ts": events[-1]["ts"] if events else None,
            "health": health,
        },
        "tasks": tasks_out,
        "open_tasks": [t["id"] for t in tasks_out if t["status"] not in ("done",)],
        "invalid_tasks": invalid,
        "inconsistencies": inconsistencies,
        "s6_gate": {
            "events_real": len(real_events), "events_umbral": 200,
            "events_synthetic": events_synthetic,
            "tasks_done": tasks_done, "tasks_umbral": 10,
            "tasks_synthetic": tasks_synthetic,
            "abierto": len(real_events) >= 200 and tasks_done >= 10,
        },
        "agents_ref": ".ai/state/agents.json",
    }

    input_parts = [EVENTS.read_bytes() if EVENTS.exists() else b""]
    input_parts += [p.read_bytes() for p, _ in task_files]
    inputs_hash = sha256_bytes(b"\x00".join(input_parts))
    items_hash = sha256_bytes(canonical(state).encode())
    ghash = generator_hash()
    prev = {}
    if CURRENT.exists():
        try:
            prev = json.loads(CURRENT.read_text(encoding="utf-8")).get("_meta", {})
        except (OSError, json.JSONDecodeError):
            prev = {}
    unchanged = (prev.get("items_hash") == items_hash and prev.get("inputs_hash") == inputs_hash
                 and prev.get("generator_hash") == ghash)
    payload = {
        "_meta": {
            "generated_at": prev.get("generated_at") if unchanged else now_utc(),
            "generator": ".ai/bin/reality.py derive",
            "generator_hash": ghash,
            "inputs_hash": inputs_hash,
            "items_hash": items_hash,
            "item_count": len(tasks_out),
            "freshness": "derived",
        },
        "state": state,
    }
    CURRENT.parent.mkdir(parents=True, exist_ok=True)
    CURRENT.write_text(canonical(payload), encoding="utf-8", newline="\n")
    print(f"OK {CURRENT.relative_to(ROOT)}: {len(events)} eventos, {len(tasks_out)} tasks, "
          f"{len(invalid)} invalidos, {len(inconsistencies)} inconsistencias"
          + (" [sin cambios: generated_at preservado]" if unchanged else ""))
    age = health["last_event_age_hours"]
    age_text = "desconocida" if age is None else f"{age:.2f} h"
    print(f"LEDGER {health['status']}: ultimo={health['last_event_ts']}, "
          f"antiguedad={age_text}, WARN si supera {LEDGER_WARN_AFTER_HOURS:g} h "
          f"({health['reason']})")
    return 0


def cmd_derive(_args) -> int:
    return do_derive()


def merge_gate_decision(events: list[dict], task_id: str) -> tuple[bool, str]:
    task_events = [event for event in events if event.get("task") == task_id]
    if not task_events:
        return False, f"{task_id} no existe en el ledger"
    verdicts = [event for event in task_events if event.get("type") == "REVIEW_VERDICT"]
    if not verdicts:
        return False, f"{task_id} no tiene REVIEW_VERDICT"
    verdict = verdicts[-1].get("payload", {}).get("verdict")
    if verdict != "APROBADO":
        return False, f"{task_id}: ultimo REVIEW_VERDICT es {verdict!r}, se requiere 'APROBADO'"
    return True, f"{task_id}: ultimo REVIEW_VERDICT es APROBADO"


def cmd_merge_gate(args) -> int:
    allowed, reason = merge_gate_decision(read_events(), args.task)
    if not allowed:
        die(reason)
    print(f"OK {reason}")
    return 0


# ------------------------------------------------------------ raw reports


# El reporte crudo valido mas corto observado tiene 208 bytes. Un umbral de 200
# conserva ese informe conciso, pero rechaza archivos de un byte y placeholders.
# Se mide texto util (sin espacios exteriores), no solo el tamano del archivo.
MIN_REPORT_CONTENT_BYTES = 200

# Tasks cerrados antes de que el despacho guardara el reporte crudo con -o.
# Su salida se perdio y no es recuperable: fabricarla seria peor que no tenerla.
# No agregar nada aqui sin esa misma justificacion: la lista existe para que el
# chequeo detecte omisiones NUEVAS, no para volverlo verde.
SIN_REPORTE_HISTORICO = {"TASK-10", "TASK-11", "TASK-13"}


def report_candidates(task_id: str, reports_dir: Path, ai_dir: Path) -> list[Path]:
    """Encuentra solo nombres de informe conocidos y revisiones numericas."""
    match = re.fullmatch(r"TASK-(\d+)", task_id)
    if not match:
        return []

    escaped_id = re.escape(task_id)
    report_name = re.compile(
        rf"{escaped_id}(?:\.raw|_r[0-9]+\.raw|\.codex(?:\.r[0-9]+)?)\.md"
    )
    historical_name = re.compile(rf"task{match.group(1)}_r[0-9]+_out\.md")
    candidates = [
        path for path in reports_dir.glob(f"{task_id}*.md")
        if report_name.fullmatch(path.name)
    ]
    candidates.extend(
        path for path in ai_dir.glob(f"task{match.group(1)}_r*_out.md")
        if historical_name.fullmatch(path.name)
    )
    return sorted(set(candidates))


def report_has_minimum_content(path: Path) -> bool:
    """Acepta un informe solo si es texto UTF-8 con contenido util suficiente."""
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False
    return len(content.strip().encode("utf-8")) >= MIN_REPORT_CONTENT_BYTES


def missing_codex_reports(
    tasks: list[tuple[Path, dict]],
    reports_dir: Path = REPORTS,
    ai_dir: Path = ROOT / ".ai",
) -> list[str]:
    """Devuelve los tasks done de Codex sin contenido de informe suficiente."""
    missing = []
    for _path, data in tasks:
        if data.get("status") != "done" or str(data.get("owner", "")).strip().lower() != "codex":
            continue
        task_id = str(data.get("id", "")).strip()
        if task_id in SIN_REPORTE_HISTORICO:
            continue
        reports = report_candidates(task_id, reports_dir, ai_dir)
        if not any(report_has_minimum_content(path) for path in reports):
            missing.append(task_id)
    return missing


def cmd_reports_check(_args) -> int:
    missing = missing_codex_reports(active_tasks())
    if missing:
        die("reportes crudos de Codex ausentes para task(s) cerrado(s): " + ", ".join(missing))
    historical_debt = ", ".join(sorted(SIN_REPORTE_HISTORICO))
    print(
        "OK reports-check: no hay omisiones fuera de la deuda historica explicita "
        f"({historical_debt}); umbral={MIN_REPORT_CONTENT_BYTES} bytes de texto util"
    )
    return 0


def cmd_read(args) -> int:
    path = Path(args.path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"AUSENTE {args.path}: el archivo no existe")
        return 3
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"AUSENTE {args.path}: ilegible ({exc})")
        return 3
    meta = data.get("_meta") or {}
    stamp = meta.get("generated_at")
    if not stamp:
        print(f"AUSENTE {args.path}: sin _meta.generated_at -- un artefacto sin _meta fresco se trata como ausente (regla 0)")
        return 3
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds() / 3600
    except ValueError:
        print(f"AUSENTE {args.path}: generated_at invalido: {stamp!r}")
        return 3
    if age_h > args.max_age_hours:
        print(f"AUSENTE {args.path}: _meta viejo ({age_h:.1f}h > {args.max_age_hours}h) -- se trata como ausente, no como verdadero")
        return 3
    print(f"OK {args.path}: fresco ({age_h:.2f}h <= {args.max_age_hours}h, freshness={meta.get('freshness')})")
    return 0


# ------------------------------------------------------------------ selftest


def cmd_selftest(_args) -> int:
    task = {
        "id": "TASK-9999", "title": "t", "objective": "o", "owner": "a", "reviewer": "b",
        "created_by": "a", "created_at": "2026-08-10T00:00:00Z",
        "scope": {"allowed": [".ai/**"], "forbidden": [".claude/**"]},
        "locked_files": [".ai/bin/reality.py"],
        "acceptance": [{"id": "A1", "criterio": "canario en rojo", "verificacion": "quitar guard, ver fallo"}],
        "risk": "HIGH", "required_validation": ["reviewer"], "status": "proposed",
    }
    assert parse_yaml_subset(emit_yaml(task), "<roundtrip>") == task, "round-trip YAML fallo"
    assert validate_task(task, "TASK-9999.yaml") == [], "task valido rechazado"
    bad = dict(task, reviewer="a")
    assert any("Two-Key" in e for e in validate_task(bad, "TASK-9999.yaml")), "owner==reviewer no detectado"
    bad = dict(task, acceptance=[{"id": "A1", "criterio": "sin nada", "verificacion": "x"}])
    assert any("canario" in e for e in validate_task(bad, "TASK-9999.yaml")), "HIGH sin canario no detectado"
    bad = dict(task, status="volando")
    assert any("status invalido" in e for e in validate_task(bad, "TASK-9999.yaml")), "status invalido no detectado"
    approved = [{"task": "TASK-9", "type": "REVIEW_VERDICT", "payload": {"verdict": "APROBADO"}}]
    rejected = [{"task": "TASK-9", "type": "REVIEW_VERDICT", "payload": {"verdict": "RECHAZADO"}}]
    no_verdict = [{"task": "TASK-9", "type": "TASK_STATUS", "payload": {"to": "review"}}]
    assert merge_gate_decision(approved, "TASK-9")[0], "merge-gate rechazo APROBADO"
    assert not merge_gate_decision(rejected, "TASK-9")[0], "merge-gate acepto RECHAZADO"
    assert not merge_gate_decision(no_verdict, "TASK-9")[0], "merge-gate acepto task sin veredicto"
    with TemporaryDirectory() as tmp:
        ai_dir = Path(tmp) / ".ai"
        reports_dir = ai_dir / "reports"
        reports_dir.mkdir(parents=True)

        def done_task(task_id: str, owner: str = "codex") -> tuple[Path, dict]:
            return Path(f"{task_id}.yaml"), dict(task, id=task_id, status="done", owner=owner)

        def check_reports(*task_ids: str) -> list[str]:
            return missing_codex_reports(
                [done_task(task_id) for task_id in task_ids], reports_dir, ai_dir
            )

        enough = "x" * MIN_REPORT_CONTENT_BYTES
        assert check_reports("TASK-9001") == ["TASK-9001"], \
            "reports-check no detecto reporte faltante"
        assert missing_codex_reports([done_task("TASK-9001", "claude")], reports_dir, ai_dir) == [], \
            "reports-check exigio reporte de Codex a owner claude"

        (reports_dir / "TASK-9002.raw.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9002") == [], "reports-check rechazo el nombre raw exacto"
        (reports_dir / "TASK-9003.raw.md").write_text("", encoding="utf-8")
        assert check_reports("TASK-9003") == ["TASK-9003"], "reports-check acepto archivo vacio"
        (reports_dir / "TASK-9004.raw.md").write_text("x", encoding="utf-8")
        assert check_reports("TASK-9004") == ["TASK-9004"], "reports-check acepto un byte"
        (reports_dir / "TASK-9005.raw.md").write_text(" " * (MIN_REPORT_CONTENT_BYTES + 1), encoding="utf-8")
        assert check_reports("TASK-9005") == ["TASK-9005"], "reports-check conto espacios como contenido"
        (reports_dir / "TASK-9013.raw.md").write_text("x" * (MIN_REPORT_CONTENT_BYTES - 1), encoding="utf-8")
        assert check_reports("TASK-9013") == ["TASK-9013"], "reports-check acepto menos del umbral"

        (reports_dir / "TASK-9006_rbasura.raw.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9006") == ["TASK-9006"], "reports-check acepto revision no numerica"
        (reports_dir / "TASK-9007_r2.raw.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9007") == [], "reports-check rechazo revision numerica"
        (reports_dir / "TASK-9009_r2.raw.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9008") == ["TASK-9008"], \
            "reports-check confundio la revision de otra tarea"

        (reports_dir / "TASK-9010.codexNO_ES_REPORTE.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9010") == ["TASK-9010"], "reports-check acepto nombre codex enganoso"
        (reports_dir / "TASK-9011.codex.r2.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9011") == [], "reports-check rechazo nombre codex historico"

        for task_number in (2, 3, 7):
            (ai_dir / f"task{task_number}_r1_out.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-2", "TASK-3", "TASK-7") == [], \
            "reports-check no reconocio informes historicos taskN_rN_out.md"
        (ai_dir / "task9012_rbasura_out.md").write_text(enough, encoding="utf-8")
        assert check_reports("TASK-9012") == ["TASK-9012"], \
            "reports-check acepto revision historica no numerica"
    synthetic_event = {"type": "CHECKPOINT", "payload": {"synthetic": True}}
    normal_event = {"type": "CHECKPOINT", "payload": {}}
    synthetic_task = dict(task, status="done", synthetic="true")
    normal_done_task = dict(task, status="done")
    assert is_synthetic_marker(True) and is_synthetic_marker("true"), "marca synthetic truthy no detectada"
    assert not is_synthetic_marker(False), "marca synthetic false detectada"
    assert not is_real_event(synthetic_event), "evento synthetic conto como real"
    assert is_real_event(normal_event), "evento normal no conto como real"
    assert not is_s6_done_task(synthetic_task), "task synthetic done conto para S6"
    assert is_s6_done_task(normal_done_task), "task normal done no conto para S6"
    assert task_event_payload(synthetic_task, {"from": "review", "to": "done"}) == {
        "from": "review", "to": "done", "synthetic": True,
    }, "evento de task synthetic sin marca"
    assert task_event_payload(normal_done_task, {"from": "review", "to": "done"}) == {
        "from": "review", "to": "done",
    }, "evento de task normal ensuciado con synthetic"
    health_now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    fresh_health = ledger_health([{"ts": "2026-08-13T01:00:00Z"}], health_now)
    stale_health = ledger_health([{"ts": "2026-08-12T23:00:00Z"}], health_now)
    assert fresh_health["status"] == "OK" and fresh_health["last_event_age_hours"] == 11.0, \
        "salud del ledger marco WARN antes del umbral"
    assert stale_health["status"] == "WARN" and stale_health["last_event_age_hours"] == 13.0, \
        "salud del ledger no detecto 13 horas sin eventos"
    assert ledger_health([], health_now)["status"] == "WARN", "ledger vacio no marco WARN"
    dispatch_match = _CODEX_DISPATCH.search(
        "cat /mnt/c/proyecto/.ai/handoffs/TASK-123_owner.md | /opt/bin/codex exec -o salida -"
    )
    assert dispatch_match and dispatch_match.group("id") == "123", "no se reconocio un despacho codex real"
    done_candidate = {"task": "TASK-123", "type": "TASK_STATUS", "payload": {"to": "done"}}
    assert lifecycle_fact_exists([done_candidate], done_candidate), "la deduplicacion no reconocio TASK_STATUS done"
    assert not lifecycle_fact_exists([], done_candidate), "la deduplicacion invento un hecho existente"
    first_dispatch = {
        "task": "TASK-123", "type": "DISPATCH", "ts": "2026-08-13T07:00:00Z",
        "payload": {"evidencia": {"command_sha256": "a"}},
    }
    retry_dispatch = {
        "task": "TASK-123", "type": "DISPATCH", "ts": "2026-08-13T07:01:00Z",
        "payload": {"evidencia": {"command_sha256": "b"}},
    }
    assert not lifecycle_fact_exists([first_dispatch], retry_dispatch), "un retry real se confundio con duplicado"
    assert parse_utc("2026-08-13T02:00:00-05:00") == parse_utc("2026-08-13T07:00:00Z"), \
        "normalizacion de timestamps con zona horaria incorrecta"
    for text in ("clave:\n", "a: >\n  multi\n", "k: &ancla v\n", "\tx: 1\n", "a: 1\na: 2\n"):
        try:
            parse_yaml_subset(text, "<malo>")
        except YamlSubsetError:
            pass
        else:
            raise AssertionError(f"el parser acepto en silencio: {text!r}")
    inline = parse_yaml_subset('a: [1, 2]\nb: {x: y}\nc: "z: con dos puntos"\nvacio: []\n', "<inline>")
    assert inline == {"a": ["1", "2"], "b": {"x": "y"}, "c": "z: con dos puntos", "vacio": []}, f"inline parse: {inline}"
    print("OK selftest: round-trip, reglas two-key/canario/status/merge-gate/reports-check/S6, "
          "salud del ledger, reconciliacion idempotente y rechazos ruidosos del parser")
    return 0


# ---------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(prog="reality.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("event", help="append al ledger")
    p.add_argument("type")
    p.add_argument("--actor", required=True)
    p.add_argument("--task")
    p.add_argument("--payload", help="JSON")
    p.set_defaults(fn=lambda a: (
        print(json.dumps(append_event(a.type, a.actor, a.task,
                                      json.loads(a.payload) if a.payload else None),
                         ensure_ascii=False, sort_keys=True)) or 0))

    p = sub.add_parser("task-create", help="crear un task (contrato 2.1, reglas HECHAS CUMPLIR)")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--objective")
    p.add_argument("--owner", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--created-by", dest="created_by")
    p.add_argument("--risk", required=True, choices=RISKS)
    p.add_argument("--allowed", action="append")
    p.add_argument("--forbidden", action="append")
    p.add_argument("--lock", action="append")
    p.add_argument("--acceptance", action="append", help='JSON: {"id","criterio","verificacion"}')
    p.add_argument("--required-validation", dest="required_validation")
    p.set_defaults(fn=cmd_task_create)

    p = sub.add_parser("task-status", help="cambiar status y registrar el evento")
    p.add_argument("task")
    p.add_argument("status")
    p.add_argument("--actor", required=True)
    p.set_defaults(fn=cmd_task_status)

    p = sub.add_parser("task-validate", help="validar tasks escritos a mano")
    p.add_argument("files", nargs="*")
    p.set_defaults(fn=cmd_task_validate)

    p = sub.add_parser("lease", help="quien tiene el lease de un archivo")
    p.add_argument("path")
    p.set_defaults(fn=cmd_lease)

    p = sub.add_parser("handoff-validate", help="validar un handoff (contrato 2.3)")
    p.add_argument("file")
    p.set_defaults(fn=cmd_handoff_validate)

    p = sub.add_parser("agents", help="generar .ai/state/agents.json (contrato 2.4)")
    p.set_defaults(fn=cmd_agents)

    p = sub.add_parser("derive", help="derivar CURRENT_STATE.json del ledger (nunca a mano)")
    p.set_defaults(fn=cmd_derive)

    p = sub.add_parser("merge-gate", help="permitir merge solo con ultimo REVIEW_VERDICT APROBADO")
    p.add_argument("task")
    p.set_defaults(fn=cmd_merge_gate)

    p = sub.add_parser("reports-check", help="exigir reportes crudos para tasks cerrados de Codex")
    p.set_defaults(fn=cmd_reports_check)

    p = sub.add_parser("read", help="lector que aplica la regla 0 (sin _meta fresco = ausente)")
    p.add_argument("path")
    p.add_argument("--max-age-hours", type=float, default=24.0)
    p.set_defaults(fn=cmd_read)

    p = sub.add_parser("selftest", help="chequeos puros del parser/emisor y las reglas")
    p.set_defaults(fn=cmd_selftest)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
