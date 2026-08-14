from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"
REQUESTS = QUEUE / "requests"
IN_PROGRESS = QUEUE / "in_progress"
RESPONSES = QUEUE / "responses"
ARCHIVE = QUEUE / "archive"
LOGS = QUEUE / "logs"
LOG_FILE = LOGS / "bridge_log.jsonl"
LEDGER = ROOT.parents[1] / ".ai" / "events" / "EVENTS.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def elapsed_seconds(started_at: str | None, ended_at: str | None) -> int | None:
    """Duracion entre dos marcas persistidas del mismo ciclo de tarea."""
    if not started_at or not ended_at:
        return None
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
        if started.tzinfo is None or ended.tzinfo is None:
            return None
        seconds = int((ended.astimezone(timezone.utc) - started.astimezone(timezone.utc)).total_seconds())
        return seconds if seconds >= 0 else None
    except ValueError:
        return None


def ensure_dirs() -> None:
    for path in (REQUESTS, IN_PROGRESS, RESPONSES, ARCHIVE, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def log_event(event: str, **fields: object) -> None:
    ensure_dirs()
    entry = {"timestamp": now_iso(), "event": event}
    entry.update(fields)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ledger_event(etype: str, actor: str, payload: dict, task: str | None = None) -> None:
    """Adaptador al ledger de shared reality (.ai/events/EVENTS.jsonl).

    Mismo contrato 2.2 que reality.py (ts/type/actor + payload), sin importar
    reality.py para no acoplar el puente al arbol de .ai/bin. Si el ledger no
    es escribible, el puente sigue funcionando y deja constancia en su log
    propio: el puente nunca se cae por el ledger.
    """
    event = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "type": etype,
        "actor": actor,
        "payload": payload,
    }
    if task:
        event["task"] = task
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        log_event("ledger_write_failed", error=str(exc), intended=event)


def task_markdown(task: dict) -> str:
    attachments = task.get("attachments") or []
    constraints = task.get("constraints") or []

    lines = [
        f"# {task['title']}",
        "",
        f"- task_id: `{task['task_id']}`",
        f"- from: `{task['from_agent']}`",
        f"- to: `{task['to_agent']}`",
        f"- kind: `{task['kind']}`",
        f"- created_at: `{task['created_at']}`",
        "",
        "## Body",
        "",
        task["body_markdown"].rstrip(),
        "",
    ]

    if constraints:
        lines.extend(["## Constraints", ""])
        lines.extend(f"- {item}" for item in constraints)
        lines.append("")

    if attachments:
        lines.extend(["## Attachments", ""])
        lines.extend(f"- `{item}`" for item in attachments)
        lines.append("")

    lines.extend(
        [
            "## Response Contract",
            "",
            "- Provide evidence when relevant.",
            "- If founder input is needed, do not decide it yourself.",
            "- Return status `needs_founder` instead.",
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def request_files_for(agent: str) -> list[Path]:
    candidates: list[Path] = []
    for path in REQUESTS.glob("*.json"):
        payload = read_json(path)
        if payload.get("to_agent") in {agent, "any"}:
            candidates.append(path)
    return sorted(candidates, key=lambda item: (item.stat().st_mtime, item.name))


def search_task(task_id: str) -> tuple[str, Path] | None:
    locations = {
        "requests": REQUESTS / f"{task_id}.json",
        "in_progress": IN_PROGRESS / f"{task_id}.json",
        "responses": RESPONSES / f"{task_id}.json",
        "archive_request": ARCHIVE / f"{task_id}_request.json",
        "archive_response": ARCHIVE / f"{task_id}_response.json",
    }
    for label, path in locations.items():
        if path.exists():
            return label, path
    return None


def cmd_init(_: argparse.Namespace) -> int:
    ensure_dirs()
    print(str(QUEUE))
    return 0


def cmd_enqueue(args: argparse.Namespace) -> int:
    ensure_dirs()
    body = args.body_text or ""
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    if not body.strip():
        raise SystemExit("Task body is empty. Use --body-file or --body-text.")

    task_id = args.task_id or f"{datetime.now().strftime('%Y-%m-%d')}_{uuid4().hex[:8]}"
    request_path = REQUESTS / f"{task_id}.json"
    if request_path.exists():
        raise SystemExit(f"Task already exists: {request_path}")

    attachments = [str(Path(item).resolve()) for item in (args.attachment or [])]
    constraints = list(args.constraint or [])

    payload = {
        "schema": "ai_workflow.bridge.task.v1",
        "task_id": task_id,
        "created_at": now_iso(),
        "from_agent": args.from_agent,
        "to_agent": args.to_agent,
        "kind": args.kind,
        "title": args.title,
        "body_markdown": body,
        "attachments": attachments,
        "constraints": constraints,
        "requires_founder_decision": False,
        "status": "pending",
    }
    if args.synthetic:
        payload["synthetic"] = True
    write_json(request_path, payload)
    log_event(
        "enqueued",
        task_id=task_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        request_path=str(request_path),
    )
    dispatch_payload = {
        "rol_emisor": "bridge",
        "bridge_task_id": task_id,
        "from_agent": args.from_agent,
        "kind": args.kind,
        "title": args.title,
    }
    if args.synthetic:
        dispatch_payload["synthetic"] = True
    ledger_event("DISPATCH", args.to_agent, dispatch_payload,
                 task=getattr(args, "ledger_task", None))
    print(str(request_path))
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    ensure_dirs()
    candidates = request_files_for(args.agent)
    if not candidates:
        print("NO_TASK")
        return 0

    request_path = candidates[0]
    payload = read_json(request_path)
    task_id = payload["task_id"]
    claimed_path = IN_PROGRESS / f"{task_id}.json"
    markdown_path = IN_PROGRESS / f"{task_id}.md"

    payload["status"] = "in_progress"
    payload["claimed_at"] = now_iso()
    payload["claimed_by"] = args.agent

    shutil.move(str(request_path), str(claimed_path))
    write_json(claimed_path, payload)
    markdown_path.write_text(task_markdown(payload), encoding="utf-8")

    log_event(
        "claimed",
        task_id=task_id,
        by_agent=args.agent,
        claimed_path=str(claimed_path),
        packet_path=str(markdown_path),
    )

    print(f"task_id={task_id}")
    print(f"json={claimed_path}")
    print(f"packet={markdown_path}")
    return 0


def cmd_respond(args: argparse.Namespace) -> int:
    ensure_dirs()
    in_progress_path = IN_PROGRESS / f"{args.task_id}.json"
    packet_path = IN_PROGRESS / f"{args.task_id}.md"
    if not in_progress_path.exists():
        raise SystemExit(f"Task not found in progress: {in_progress_path}")

    response_body = Path(args.response_file).read_text(encoding="utf-8")
    task = read_json(in_progress_path)
    response_path = RESPONSES / f"{args.task_id}.json"

    responded_at = now_iso()
    response = {
        "schema": "ai_workflow.bridge.response.v1",
        "task_id": args.task_id,
        "created_at": responded_at,
        "from_agent": args.agent,
        "to_agent": task["from_agent"],
        "status": args.status,
        "summary": args.summary,
        "response_markdown": response_body,
        "source_request": str(in_progress_path),
    }

    write_json(response_path, response)
    shutil.copy2(in_progress_path, ARCHIVE / f"{args.task_id}_request.json")
    shutil.copy2(response_path, ARCHIVE / f"{args.task_id}_response.json")
    if packet_path.exists():
        shutil.move(str(packet_path), str(ARCHIVE / f"{args.task_id}_packet.md"))
    in_progress_path.unlink()

    log_event(
        "responded",
        task_id=args.task_id,
        by_agent=args.agent,
        status=args.status,
        response_path=str(response_path),
    )

    # La duracion de trabajo empieza al reclamar la tarea, no al encolarla.
    # Medir desde created_at mezclaba espera en cola con ejecucion: una tarea
    # abandonada cuatro dias parecia una ejecucion de cuatro dias.
    duracion_s = elapsed_seconds(task.get("claimed_at"), responded_at)
    espera_cola_s = elapsed_seconds(task.get("created_at"), task.get("claimed_at"))
    response_payload = {
        "rol_emisor": "bridge",
        "bridge_task_id": args.task_id,
        "ok": args.status == "completed",
        "status": args.status,
        "duracion_s": duracion_s,
        "espera_cola_s": espera_cola_s,
        "duracion_base": "claimed_at_a_response" if duracion_s is not None else "sin_claimed_at_valido",
        "response_path": str(response_path),
    }
    if task.get("synthetic") or args.synthetic:
        response_payload["synthetic"] = True
    ledger_event("RESPONSE", args.agent, response_payload,
                 task=getattr(args, "ledger_task", None))

    print(str(response_path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ensure_dirs()
    if args.task_id:
        found = search_task(args.task_id)
        if not found:
            print("NOT_FOUND")
            return 1
        label, path = found
        print(f"state={label}")
        print(f"path={path}")
        return 0

    summary = {
        "requests": len(list(REQUESTS.glob("*.json"))),
        "in_progress": len(list(IN_PROGRESS.glob("*.json"))),
        "responses": len(list(RESPONSES.glob("*.json"))),
        "archive_requests": len(list(ARCHIVE.glob("*_request.json"))),
        "archive_responses": len(list(ARCHIVE.glob("*_response.json"))),
    }
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auditable file-based bridge between Codex and Claude.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create queue folders if missing.")
    init_parser.set_defaults(func=cmd_init)

    enqueue_parser = subparsers.add_parser("enqueue", help="Enqueue a new task.")
    enqueue_parser.add_argument("--from-agent", required=True)
    enqueue_parser.add_argument("--to-agent", required=True)
    enqueue_parser.add_argument("--kind", required=True)
    enqueue_parser.add_argument("--title", required=True)
    enqueue_parser.add_argument("--task-id")
    enqueue_parser.add_argument("--body-file")
    enqueue_parser.add_argument("--body-text")
    enqueue_parser.add_argument("--attachment", action="append")
    enqueue_parser.add_argument("--constraint", action="append")
    enqueue_parser.add_argument("--synthetic", action="store_true",
                                help="Marca de prueba de infraestructura: el evento del ledger NO cuenta para el gate de S6.")
    enqueue_parser.add_argument("--ledger-task", dest="ledger_task",
                                help="TASK-N del task system al que se vincula el evento del ledger.")
    enqueue_parser.set_defaults(func=cmd_enqueue)

    claim_parser = subparsers.add_parser("claim", help="Claim the next task for an agent.")
    claim_parser.add_argument("--agent", required=True)
    claim_parser.add_argument("--once", action="store_true", help="Compatibility flag for explicit single-claim use.")
    claim_parser.set_defaults(func=cmd_claim)

    respond_parser = subparsers.add_parser("respond", help="Submit a response for a claimed task.")
    respond_parser.add_argument("--agent", required=True)
    respond_parser.add_argument("--task-id", required=True)
    respond_parser.add_argument(
        "--status",
        required=True,
        choices=["completed", "blocked", "needs_founder", "rejected"],
    )
    respond_parser.add_argument("--response-file", required=True)
    respond_parser.add_argument("--summary", required=True)
    respond_parser.add_argument("--synthetic", action="store_true",
                                help="Marca de prueba de infraestructura: el evento del ledger NO cuenta para el gate de S6.")
    respond_parser.add_argument("--ledger-task", dest="ledger_task",
                                help="TASK-N del task system al que se vincula el evento del ledger.")
    respond_parser.set_defaults(func=cmd_respond)

    status_parser = subparsers.add_parser("status", help="Inspect queue status.")
    status_parser.add_argument("--task-id")
    status_parser.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
