#!/usr/bin/env python3
"""Gateway de auditoría: API deliberadamente pequeña y de sólo lectura.

Uso CLI: python tools_gateway.py --request '{"operation":"read_file","path":"..."}'
Uso MCP: python tools_gateway.py --mcp
"""
from __future__ import annotations

import argparse, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\AI_WORKFLOW").resolve()
MAX_OUTPUT = 24_000
BLOCKED_PARTS = {"tchasky"}

class GatewayError(ValueError): pass

def _path(value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise GatewayError("path must be a non-empty string")
    candidate = Path(value)
    resolved = (ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try: resolved.relative_to(ROOT)
    except ValueError: raise GatewayError("path escapes C:\\AI_WORKFLOW")
    if any(part.lower() in BLOCKED_PARTS for part in resolved.parts):
        raise GatewayError("Tchasky is outside the backup-auditor scope")
    return resolved

def _clip(value: str) -> str:
    return value[:MAX_OUTPUT] + ("\n[truncated]" if len(value) > MAX_OUTPUT else "")

def read_file(path: str, start_line: int = 1, end_line: int = 400) -> dict:
    target = _path(path)
    if not target.is_file(): raise GatewayError("not a regular file")
    if start_line < 1 or end_line < start_line or end_line - start_line > 2000:
        raise GatewayError("invalid line range")
    try: lines = target.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError: raise GatewayError("binary/non-UTF-8 files are not readable")
    body = "\n".join(f"{n}: {line}" for n, line in enumerate(lines[start_line-1:end_line], start_line))
    return {"path": str(target.relative_to(ROOT)), "start_line": start_line, "end_line": min(end_line, len(lines)), "content": _clip(body)}

def grep(pattern: str, path: str = ".") -> dict:
    if not isinstance(pattern, str) or not pattern or len(pattern) > 300: raise GatewayError("invalid pattern")
    target = _path(path)
    if not target.exists(): raise GatewayError("path does not exist")
    rg = shutil.which("rg")
    if rg:
        done = subprocess.run([rg, "--line-number", "--no-heading", "--max-count", "100", "--", pattern, str(target)], text=True, capture_output=True, timeout=15)
        output = done.stdout
    else:
        try: rx = re.compile(pattern)
        except re.error as exc: raise GatewayError(f"invalid regex: {exc}")
        files = [target] if target.is_file() else (p for p in target.rglob("*") if p.is_file())
        hits = []
        for item in files:
            if len(hits) >= 100: break
            try:
                for number, line in enumerate(item.read_text(encoding="utf-8").splitlines(), 1):
                    if rx.search(line): hits.append(f"{item.relative_to(ROOT)}:{number}:{line}")
                    if len(hits) >= 100: break
            except (UnicodeDecodeError, OSError): pass
        output = "\n".join(hits)
    return {"path": str(target.relative_to(ROOT)), "pattern": pattern, "matches": _clip(output)}

def _repo(path: str = ".") -> Path:
    target = _path(path)
    probe = target if target.is_dir() else target.parent
    result = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"], text=True, capture_output=True, timeout=10)
    if result.returncode: raise GatewayError("no local Git repository at requested path")
    return _path(result.stdout.strip())

def git_status(path: str = ".") -> dict:
    repo = _repo(path)
    result = subprocess.run(["git", "-C", str(repo), "status", "--short"], text=True, capture_output=True, timeout=15)
    return {"repo": str(repo.relative_to(ROOT)), "status": _clip(result.stdout), "exit_code": result.returncode}

def git_diff(path: str = ".") -> dict:
    repo = _repo(path)
    result = subprocess.run(["git", "-C", str(repo), "diff", "--no-ext-diff", "--"], text=True, capture_output=True, timeout=15)
    return {"repo": str(repo.relative_to(ROOT)), "diff": _clip(result.stdout), "exit_code": result.returncode}

def docker_ps() -> dict:
    result = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Image}} {{.Status}}"], text=True, capture_output=True, timeout=15)
    return {"exit_code": result.returncode, "containers": _clip(result.stdout), "stderr": _clip(result.stderr)}

def certification_files(paths: list[str]) -> dict:
    if not isinstance(paths, list) or len(paths) > 20: raise GatewayError("paths must be a list of <=20 paths")
    result = []
    for value in paths:
        item = _path(value)
        result.append({"path": str(item.relative_to(ROOT)), "exists": item.is_file(), "bytes": item.stat().st_size if item.is_file() else None,
                       "sha256": hashlib.sha256(item.read_bytes()).hexdigest() if item.is_file() else None})
    return {"files": result}

OPS = {"read_file": read_file, "grep": grep, "git_status": git_status, "git_diff": git_diff, "docker_ps": docker_ps, "certification_files": certification_files}

def dispatch(request: dict) -> dict:
    if not isinstance(request, dict): raise GatewayError("request must be an object")
    operation = request.get("operation")
    if operation not in OPS: raise GatewayError(f"operation rejected: {operation!r}")
    args = {k: v for k, v in request.items() if k != "operation"}
    try: payload = OPS[operation](**args)
    except TypeError: raise GatewayError("invalid arguments for operation")
    return {"ok": True, "operation": operation, "timestamp_utc": datetime.now(timezone.utc).isoformat(), "result": payload}

def reply(obj: dict) -> None: sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n"); sys.stdout.flush()
def mcp() -> None:
    tools = [{"name": name, "description": f"Read-only backup-auditor operation: {name}", "inputSchema": {"type":"object"}} for name in OPS]
    for raw in sys.stdin:
        try:
            msg = json.loads(raw); method = msg.get("method"); ident = msg.get("id")
            if method == "initialize": response = {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"backup-readonly-gateway","version":"1.0"}}
            elif method == "tools/list": response = {"tools": tools}
            elif method == "tools/call":
                request = dict(msg.get("params", {}).get("arguments", {})); request["operation"] = msg.get("params", {}).get("name")
                response = {"content":[{"type":"text","text":json.dumps(dispatch(request), ensure_ascii=False)}]}
            else: continue
            if ident is not None: reply({"jsonrpc":"2.0","id":ident,"result":response})
        except Exception as exc:
            if 'ident' in locals() and ident is not None: reply({"jsonrpc":"2.0","id":ident,"error":{"code":-32000,"message":str(exc)}})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--request"); parser.add_argument("--mcp", action="store_true"); args = parser.parse_args()
    if args.mcp: mcp()
    else:
        try: reply(dispatch(json.loads(args.request if args.request else sys.stdin.read())))
        except Exception as exc: reply({"ok":False, "error":str(exc)}); sys.exit(2)
