#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
BASE_DIR = Path(__file__).resolve().parent
QUEUE_DIR = BASE_DIR.parent / "queue"
INDEX_FILE = BASE_DIR / "index.html"
FOLDERS = {
    "requests": "Pendientes",
    "in_progress": "En progreso",
    "responses": "Respondidas",
    "archive": "Archivo",
}
LOOKUP_PRIORITY = {
    "requests": 40,
    "in_progress": 30,
    "archive": 20,
    "responses": 10,
}
PRIMARY_TEXT_KEYS = (
    "body_markdown",
    "response_markdown",
    "summary",
    "body",
    "message",
    "content",
    "text",
)


def preview_text(text: str, limit: int = 300) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def infer_kind(payload: dict[str, Any], file_path: Path) -> str:
    kind = payload.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()

    schema = str(payload.get("schema") or "")
    if schema.endswith(".response.v1") or file_path.name.endswith("_response.json"):
        return "response"
    if schema.endswith(".task.v1") or file_path.name.endswith("_request.json"):
        return "task"
    return "unknown"


def infer_status(payload: dict[str, Any], folder_name: str) -> str:
    status = payload.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()

    if folder_name == "requests":
        return "pending"
    if folder_name == "in_progress":
        return "in_progress"
    return "completed"


def extract_primary_text(payload: dict[str, Any]) -> tuple[str, str]:
    for key in PRIMARY_TEXT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return key, value.strip()
    return "", ""


def parse_queue_file(file_path: Path, folder_name: str) -> dict[str, Any]:
    stat = file_path.stat()
    item: dict[str, Any] = {
        "file_name": file_path.name,
        "file_path": str(file_path),
        "folder": folder_name,
        "mtime": iso_from_timestamp(stat.st_mtime),
        "mtime_epoch": stat.st_mtime,
    }

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        item.update(
            {
                "task_id": file_path.stem,
                "kind": "invalid_json",
                "from_agent": "",
                "to_agent": "",
                "title": file_path.stem,
                "status": "blocked",
                "summary": "",
                "primary_text_key": "",
                "text_preview": "",
                "text_full": "",
                "schema": "",
                "created_at": "",
                "parse_error": str(exc),
                "_lookup_priority": LOOKUP_PRIORITY.get(folder_name, 0),
                "_is_request_like": False,
            }
        )
        return item

    primary_text_key, primary_text = extract_primary_text(payload)
    schema = str(payload.get("schema") or "")
    item.update(
        {
            "task_id": str(payload.get("task_id") or file_path.stem),
            "kind": infer_kind(payload, file_path),
            "from_agent": str(payload.get("from_agent") or ""),
            "to_agent": str(payload.get("to_agent") or ""),
            "title": str(payload.get("title") or ""),
            "status": infer_status(payload, folder_name),
            "summary": str(payload.get("summary") or ""),
            "primary_text_key": primary_text_key,
            "text_preview": preview_text(primary_text),
            "text_full": primary_text,
            "schema": schema,
            "created_at": str(payload.get("created_at") or ""),
            "source_request": str(payload.get("source_request") or ""),
            "parse_error": "",
            "_lookup_priority": LOOKUP_PRIORITY.get(folder_name, 0),
            "_is_request_like": schema.endswith(".task.v1") or file_path.name.endswith("_request.json"),
        }
    )
    return item


def build_queue_state() -> dict[str, Any]:
    sections: dict[str, list[dict[str, Any]]] = {}
    request_lookup: dict[str, dict[str, Any]] = {}

    for folder_name in FOLDERS:
        folder_path = QUEUE_DIR / folder_name
        items: list[dict[str, Any]] = []

        if folder_path.exists():
            files = sorted(folder_path.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
            for file_path in files:
                item = parse_queue_file(file_path, folder_name)
                items.append(item)

                if item.get("_is_request_like") and item.get("task_id"):
                    current = request_lookup.get(item["task_id"])
                    if current is None or item["_lookup_priority"] > current["_lookup_priority"]:
                        request_lookup[item["task_id"]] = item

        sections[folder_name] = items

    for items in sections.values():
        for item in items:
            task_id = item.get("task_id")
            source = request_lookup.get(task_id or "")

            if source:
                if not item.get("title"):
                    item["title"] = source.get("title") or ""
                if item.get("kind") in {"response", "unknown"} and source.get("kind"):
                    item["kind"] = source["kind"]

            if not item.get("title"):
                item["title"] = item.get("summary") or item.get("text_preview") or item.get("file_name", "")

            item.pop("_lookup_priority", None)
            item.pop("_is_request_like", None)

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "queue_root": str(QUEUE_DIR),
        "counts": {folder_name: len(items) for folder_name, items in sections.items()},
        "sections": sections,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "CodexClaudeBridgeDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_index()
            return
        if parsed.path == "/api/queue":
            self.serve_queue_api()
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def serve_index(self) -> None:
        try:
            content = INDEX_FILE.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "index.html not found")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_queue_api(self) -> None:
        try:
            payload = build_queue_state()
        except Exception as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": str(exc),
                    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                },
            )
            return

        self.send_json(HTTPStatus.OK, payload)

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local dashboard for the Codex-Claude bridge queue.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind. Default: {DEFAULT_PORT}")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    url = f"http://localhost:{args.port}/"
    print(f"Serving Codex-Claude bridge dashboard from {BASE_DIR}")
    print(f"Queue root: {QUEUE_DIR}")
    print(f"Open: {url}")
    print("Stop with Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
