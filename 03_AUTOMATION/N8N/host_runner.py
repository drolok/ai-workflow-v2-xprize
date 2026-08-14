from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


AI_WORKFLOW_ROOT = Path(r"C:\AI_WORKFLOW")
HOST = os.environ.get("AIW_N8N_RUNNER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AIW_N8N_RUNNER_PORT", "8765"))
RUNNER_TOKEN = os.environ.get("AIW_N8N_RUNNER_TOKEN", "").strip()
RUNNER_DIR = AI_WORKFLOW_ROOT / "03_AUTOMATION" / "N8N"
REPORT_ROOT = AI_WORKFLOW_ROOT / "08_REPORTS" / "N8N"
TEST_REPORT_DIR = REPORT_ROOT / "TEST_RUNS"
ALERT_REPORT_DIR = REPORT_ROOT / "ALERTS"
RUNNER_LOG = RUNNER_DIR / "host_runner.log"
HEALTH_SCRIPT = AI_WORKFLOW_ROOT / "03_AUTOMATION" / "SCRIPTS" / "health_check.ps1"
PORT_SCAN_SCRIPT = AI_WORKFLOW_ROOT / "03_AUTOMATION" / "SCRIPTS" / "scan_ports.ps1"
BANK_SYNC_SCRIPT = AI_WORKFLOW_ROOT / "03_AUTOMATION" / "SCRIPTS" / "sync_banco_counts.py"
TCHASKY_WSL_ROOT = "<HOME>/<PRIVATE_PROJECT>"
TCHASKY_API_HEALTH_URL = "http://localhost:3001/health"


def log_line(message: str) -> None:
    RUNNER_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with RUNNER_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def is_authorized(handler: BaseHTTPRequestHandler) -> bool:
    return handler.headers.get("X-Runner-Token", "") == RUNNER_TOKEN


def run_command(command: list[str], timeout: int, cwd: str | None = None) -> dict[str, Any]:
    started = datetime.now()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round((datetime.now() - started).total_seconds(), 2),
            "command": command,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "duration_seconds": round((datetime.now() - started).total_seconds(), 2),
            "command": command,
            "timed_out": True,
        }


def latest_file(directory: Path, pattern: str) -> str | None:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(matches[0]) if matches else None


def run_health_check(update_canonical: bool = False) -> dict[str, Any]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(HEALTH_SCRIPT),
    ]
    if update_canonical:
        command.append("-UpdateCanonical")
    result = run_command(command, timeout=180)
    report_dir = AI_WORKFLOW_ROOT / "08_REPORTS" / "HEALTH_CHECKS"
    result["report_path"] = latest_file(report_dir, "health_check_*.md")
    result["json_path"] = latest_file(report_dir, "health_check_*.json")
    return result


def run_port_scan(additional_ports: list[int] | None = None) -> dict[str, Any]:
    additional_ports = additional_ports or [5678, PORT]
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PORT_SCAN_SCRIPT),
        "-AdditionalPorts",
    ] + [str(port) for port in additional_ports]
    result = run_command(command, timeout=180)
    report_dir = AI_WORKFLOW_ROOT / "08_REPORTS" / "PORT_SCANS"
    result["report_path"] = latest_file(report_dir, "port_scan_*.md")
    result["json_path"] = latest_file(report_dir, "port_scan_*.json")
    return result


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_test_suite() -> dict[str, Any]:
    stamp = now_stamp()
    TEST_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = TEST_REPORT_DIR / f"test_run_{stamp}.md"
    json_path = TEST_REPORT_DIR / f"test_run_{stamp}.json"
    command = [
        "wsl.exe",
        "bash",
        "-lc",
        f"cd {TCHASKY_WSL_ROOT} && pnpm -C apps/api test",
    ]
    result = run_command(command, timeout=900)
    summary = "PASS" if result["ok"] else "FAIL"
    markdown = "\n".join(
        [
            "# n8n Test Runner",
            "",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"- Status: {summary}",
            f"- Duration seconds: {result['duration_seconds']}",
            f"- Command: `{' '.join(command)}`",
            "",
            "## Stdout",
            "",
            "```text",
            result["stdout"].strip(),
            "```",
            "",
            "## Stderr",
            "",
            "```text",
            result["stderr"].strip(),
            "```",
            "",
        ]
    )
    write_markdown(report_path, markdown)
    json_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    result["status"] = summary.lower()
    result["report_path"] = str(report_path)
    result["json_path"] = str(json_path)
    return result


def run_banco_sync() -> dict[str, Any]:
    command = [
        "python",
        str(BANK_SYNC_SCRIPT),
    ]
    result = run_command(command, timeout=180)
    report_dir = AI_WORKFLOW_ROOT / "08_REPORTS" / "N8N" / "BANCO_SYNC"
    result["report_path"] = latest_file(report_dir, "banco_sync_*.json")
    result["latest_report"] = latest_file(report_dir, "latest_banco_sync.json")
    return result


def tcp_check(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return {"ok": True, "detail": "connected"}
    except OSError as exc:
        return {"ok": False, "detail": str(exc)}
    finally:
        sock.close()


def http_check(url: str, timeout: int = 8) -> dict[str, Any]:
    ps_script = (
        "$ProgressPreference='SilentlyContinue'; "
        f"try {{ $r = Invoke-WebRequest -Uri '{url}' -UseBasicParsing -TimeoutSec {timeout}; "
        "[Console]::Out.WriteLine($r.StatusCode) } "
        "catch { "
        "if ($_.Exception.Response) { [Console]::Out.WriteLine([int]$_.Exception.Response.StatusCode) } "
        "else { [Console]::Out.WriteLine('ERROR: ' + $_.Exception.Message) }; "
        "exit 1 }"
    )
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
    ]
    result = run_command(command, timeout=timeout + 10)
    if result["ok"]:
        return {"ok": True, "detail": result["stdout"].strip()}
    return {"ok": False, "detail": (result["stdout"] + result["stderr"]).strip()}


def monitor_tchasky() -> dict[str, Any]:
    stamp = now_stamp()
    ALERT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    checks = {
        "postgres": tcp_check("127.0.0.1", 5432),
        "redis": tcp_check("127.0.0.1", 6379),
        "api": http_check(TCHASKY_API_HEALTH_URL),
    }
    failing = [name for name, check in checks.items() if not check["ok"]]
    status = "ok" if not failing else "alert"
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "failing": failing,
        "checks": checks,
    }
    if failing:
        report_path = ALERT_REPORT_DIR / f"alert_{stamp}.md"
        latest_path = ALERT_REPORT_DIR / "latest_alert.md"
        markdown = "\n".join(
            [
                "# Tchasky Stack Alert",
                "",
                f"Generated at: {payload['generated_at']}",
                "",
                f"- Status: {status.upper()}",
                f"- Failing services: {', '.join(failing)}",
                "",
                "## Checks",
                "",
                *[f"- **{name}**: {'OK' if item['ok'] else 'DOWN'} - {item['detail']}" for name, item in checks.items()],
                "",
            ]
        )
        write_markdown(report_path, markdown)
        write_markdown(latest_path, markdown)
        payload["alert_path"] = str(report_path)
    return payload


def enqueue_bridge_task(body: dict[str, Any]) -> dict[str, Any]:
    script = AI_WORKFLOW_ROOT / "06_AGENT_FRAMEWORK" / "CODEX_CLAUDE_BRIDGE" / "bridge_queue.py"
    cmd = [
        "python",
        str(script),
        "enqueue",
        "--from-agent", body.get("fromAgent", "n8n_event_watcher"),
        "--to-agent", body.get("toAgent", "claude"),
        "--kind", body.get("kind", "event_notification"),
        "--title", body.get("title", "n8n Event Triggered"),
    ]
    if "bodyText" in body:
        cmd.extend(["--body-text", body["bodyText"]])
    elif "bodyFile" in body:
        cmd.extend(["--body-file", body["bodyFile"]])
    else:
        cmd.extend(["--body-text", "Automatic notification from n8n event runner."])

    for attachment in body.get("attachments", []):
        cmd.extend(["--attachment", attachment])
    for constraint in body.get("constraints", []):
        cmd.extend(["--constraint", constraint])

    return run_command(cmd, timeout=30)


class RunnerHandler(BaseHTTPRequestHandler):
    server_version = "AIWorkflowN8NHostRunner/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        log_line(fmt % args)

    def do_GET(self) -> None:
        if not is_authorized(self):
            json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "n8n-host-runner",
                    "port": PORT,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return
        if parsed.path == "/monitor/tchasky":
            payload = monitor_tchasky()
            json_response(self, HTTPStatus.OK, payload)
            return
        json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if not is_authorized(self):
            json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return
        parsed = urlparse(self.path)
        body = read_json_body(self)
        if parsed.path == "/run/health-check":
            payload = run_health_check(update_canonical=bool(body.get("updateCanonical", False)))
            json_response(self, HTTPStatus.OK, payload)
            return
        if parsed.path == "/run/scan-ports":
            raw_ports = body.get("additionalPorts") or [5678, PORT]
            ports = [int(port) for port in raw_ports]
            payload = run_port_scan(additional_ports=ports)
            json_response(self, HTTPStatus.OK, payload)
            return
        if parsed.path == "/run/test-runner":
            payload = run_test_suite()
            status = HTTPStatus.OK if payload["ok"] else HTTPStatus.INTERNAL_SERVER_ERROR
            json_response(self, status, payload)
            return
        if parsed.path == "/run/sync-banco-counts":
            payload = run_banco_sync()
            status = HTTPStatus.OK if payload["ok"] else HTTPStatus.INTERNAL_SERVER_ERROR
            json_response(self, status, payload)
            return
        if parsed.path == "/run/enqueue-task":
            payload = enqueue_bridge_task(body)
            status = HTTPStatus.OK if payload["ok"] else HTTPStatus.INTERNAL_SERVER_ERROR
            json_response(self, status, payload)
            return
        if parsed.path == "/monitor/tchasky":
            payload = monitor_tchasky()
            json_response(self, HTTPStatus.OK, payload)
            return
        json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})



def main() -> int:
    if not RUNNER_TOKEN:
        sys.stderr.write("AIW_N8N_RUNNER_TOKEN is required to start host_runner.py\n")
        return 1
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_line(f"Starting host runner on {HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), RunnerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log_line("Stopping host runner")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
