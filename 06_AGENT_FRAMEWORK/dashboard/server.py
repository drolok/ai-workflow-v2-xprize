#!/usr/bin/env python3
"""Dashboard local, sin dependencias, para la telemetria WorkEvent."""
from __future__ import annotations

import argparse
import json
import math
import mimetypes
import queue
import socket
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = Path(__file__).resolve().parent
EVENT_TYPES = {"tool_evaluation", "decision", "experiment", "verification", "blocker", "incident", "outcome"}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def clean(text: object, limit: int = 240) -> str:
    """No persiste prompts ni stdout: solo mensajes de telemetria acotados."""
    value = " ".join(str(text or "").split())
    return value[:limit] + ("…" if len(value) > limit else "")


class Store:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.seen: set[str] = set()
        self.clients: list[queue.Queue[str]] = []
        self.lock = threading.Lock()

    def add(self, event: dict) -> None:
        if event["event_id"] in self.seen:
            return
        with self.lock:
            if event["event_id"] in self.seen:
                return
            self.seen.add(event["event_id"])
            self.events.append(event)
            self.events.sort(key=lambda e: e["occurred_at"], reverse=True)
            # SSE siempre usa el mismo contrato que /api/events. Antes enviaba
            # solo {event, analytics}; el cliente espera events y abortaba el render.
            payload = json.dumps({"events": self.events[:300], "analytics": analytics(self.events)}, ensure_ascii=False)
            for client in self.clients[:]:
                try: client.put_nowait(payload)
                except queue.Full: self.clients.remove(client)

    def snapshot(self) -> dict:
        with self.lock:
            return {"events": self.events[:300], "analytics": analytics(self.events)}


def percentile(values: list[float], p: float) -> float | None:
    if not values: return None
    values = sorted(values); index = math.ceil(p * len(values)) - 1
    return round(values[max(0, index)], 2)


def analytics(events: list[dict]) -> dict:
    today = datetime.now().date().isoformat()
    tokens = sum((e["metrics"].get("tokens_read_estimate") or 0) for e in events if e["occurred_at"].startswith(today))
    per_model: dict[str, list[float]] = defaultdict(list)
    success: dict[str, list[bool]] = defaultdict(list)
    hourly: Counter[str] = Counter()
    for e in events:
        elapsed = e["metrics"].get("elapsed_minutes")
        if elapsed is not None: per_model[e.get("model", "unknown")].append(float(elapsed) * 60)
        success[e["event_type"]].append(e["outcome"] == "success")
        hourly[e["occurred_at"][:13] + ":00"] += 1
    return {"tokens_today": tokens, "latency_by_model": [{"model": k, "avg_seconds": round(sum(v)/len(v), 2), "p95_seconds": percentile(v, .95)} for k,v in per_model.items()], "success_by_type": [{"type": k, "rate": round(100 * sum(v)/len(v), 1), "count": len(v)} for k,v in success.items()], "events_by_hour": [{"hour": k, "count": v} for k,v in sorted(hourly.items())]}


def event(event_type: str, artifact: Path, message: str, occurred_at: str | None = None, *, outcome: str = "success", elapsed: float | None = None, model: str = "codex", tokens: int | None = None, evidence_kind: str = "command_result") -> dict:
    stable = f"{artifact.resolve()}:{occurred_at or now()}:{event_type}:{message}"
    return {"event_id": "WE-" + uuid.uuid5(uuid.NAMESPACE_URL, stable).hex[:16], "occurred_at": occurred_at or now(), "project": "ai_workflow", "task_id": artifact.stem, "event_type": event_type if event_type in EVENT_TYPES else "outcome", "scope": {"domains": ["agent_framework"], "capabilities": ["observability"], "technologies": ["python", "sse"]}, "intent": "telemetría local de invocación", "action": clean(message), "artifact_refs": [str(artifact.relative_to(ROOT)) if artifact.is_relative_to(ROOT) else str(artifact)], "evidence": [{"kind": evidence_kind, "ref": str(artifact), "excerpt_or_metric": clean(message), "observed_at": occurred_at or now()}], "outcome": outcome, "metrics": {"elapsed_minutes": elapsed, "cost_usd": None, "tokens_read_estimate": tokens, "ram_min_gb": None, "tests_passed": None}, "constraints": ["sin prompt ni stdout crudo"], "supersedes": [], "captured_by": "codex", "review_status": "auto_captured", "model": model}


def parse_react(path: Path, line: str) -> dict | None:
    try: raw = json.loads(line)
    except json.JSONDecodeError:
        return event("outcome", path, "Evento no parseable: JSON inválido.", outcome="failed")
    if not isinstance(raw, dict):
        return event("outcome", path, "Evento no parseable: se esperaba un objeto JSON.", outcome="failed")
    # Los logs .react.jsonl también pueden recibir WorkEvent directamente.
    # Normalizamos campos opcionales para que un evento válido nunca desaparezca.
    if any(key in raw for key in ("event_type", "summary", "captured_by", "status")):
        summary = clean(raw.get("summary") or raw.get("action") or "Evento sin resumen.")
        occurred_at = str(raw.get("occurred_at") or now())
        event_type = str(raw.get("event_type") or "outcome")
        normalized = event(event_type, path, summary, occurred_at,
                           outcome=str(raw.get("status") or raw.get("outcome") or "success"),
                           model=str(raw.get("model") or raw.get("captured_by") or "unknown"),
                           evidence_kind="work_event")
        normalized["event_id"] = str(raw.get("event_id") or normalized["event_id"])
        normalized["captured_by"] = raw.get("captured_by") or normalized["captured_by"]
        return normalized
    step = str(raw.get("step", "")); data = raw.get("data") or {}; msg = clean(raw.get("message"))
    mapping = {"ScopeGuard": "verification", "QualityGate": "verification", "SecurityGuard": "verification", "RagLifecycle": "tool_evaluation", "Thought": "decision", "Action": "tool_evaluation", "Observation": "verification"}
    outcome = "failed" if "FAILED" in msg or "REJECTED" in msg else ("blocked" if "insuficiente" in msg.lower() else "success")
    return event(mapping.get(step, "outcome"), path, f"{step}: {msg}", raw.get("timestamp"), outcome=outcome, model=str(data.get("agent", "codex")), evidence_kind="command_result")


class Watcher(threading.Thread):
    def __init__(self, store: Store, extra_root: Path | None = None) -> None:
        super().__init__(daemon=True); self.store = store; self.offsets: dict[Path, int] = {}; self.outputs: dict[Path, float] = {}
        self.roots = [ROOT / "06_AGENT_FRAMEWORK" / "rag-invocations", ROOT / "06_AGENT_FRAMEWORK" / "CODEX_CLAUDE_BRIDGE" / "queue" / "logs", ROOT / "06_AGENT_FRAMEWORK" / "CODEX_CLAUDE_BRIDGE" / "tasks" / "outputs"]
        if extra_root: self.roots.append(extra_root)

    def run(self) -> None:
        while True:
            for root in self.roots:
                if not root.exists(): continue
                for path in root.rglob("*.jsonl"):
                    self.read_jsonl(path)
                for path in root.rglob("*.output"):
                    self.read_output(path)
                if root.name == "rag-invocations":
                    for path in root.glob("*.md"):
                        self.read_output(path)
                for path in root.glob("*.md") if root.name == "outputs" else []:
                    if path.name.lower() != "readme.md": self.read_output(path)
            time.sleep(0.75)

    def read_jsonl(self, path: Path) -> None:
        offset = self.offsets.get(path, 0)
        try:
            with path.open("r", encoding="utf-8-sig", errors="replace") as f:
                f.seek(offset)
                for line in f:
                    if path.name.endswith(".react.jsonl"):
                        parsed = parse_react(path, line)
                        if parsed: self.store.add(parsed)
                self.offsets[path] = f.tell()
        except OSError: pass

    def read_output(self, path: Path) -> None:
        try: stamp = path.stat().st_mtime
        except OSError: return
        if self.outputs.get(path) == stamp: return
        self.outputs[path] = stamp
        try: text = path.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError: text = ""
        import re
        match = re.search(r"tokens used\s*\n\s*([\d.,]+)", text, re.I)
        tokens = int(match.group(1).replace(".", "").replace(",", "")) if match else None
        self.store.add(event("outcome", path, "Salida final de codex exec detectada.", datetime.fromtimestamp(stamp, timezone.utc).astimezone().isoformat(timespec="seconds"), outcome="success", model="codex", tokens=tokens, evidence_kind="command_result"))


STORE = Store()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_: object) -> None: pass
    def send_json(self, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode(); self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/events": return self.send_json(STORE.snapshot())
        if route == "/events":
            q: queue.Queue[str] = queue.Queue(maxsize=50)
            with STORE.lock: STORE.clients.append(q)
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "keep-alive"); self.end_headers()
            try:
                try:
                    self.wfile.write(b"data: " + json.dumps(STORE.snapshot(), ensure_ascii=False).encode() + b"\n\n"); self.wfile.flush()
                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError, OSError):
                    print("[dashboard] cliente SSE desconectado", flush=True)
                    self.close_connection = True
                    return
                while True:
                    try: data = q.get(timeout=15)
                    except queue.Empty: data = "{}"
                    try:
                        self.wfile.write(b"data: " + data.encode() + b"\n\n"); self.wfile.flush()
                    except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError, OSError):
                        print("[dashboard] cliente SSE desconectado", flush=True)
                        self.close_connection = True
                        return
            finally:
                with STORE.lock:
                    if q in STORE.clients: STORE.clients.remove(q)
            return
        if route in ("/", "/index.html"):
            data = (DASHBOARD / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        self.send_error(404)


def free_port(preferred: int) -> int:
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", preferred)) != 0: return preferred
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=8765); parser.add_argument("--event-root", type=Path); args = parser.parse_args()
    port = free_port(args.port); Watcher(STORE, args.event_root).start(); print(f"Dashboard local: http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
