from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from task111_ingest_filter import filtrar_docpaths


DEFAULT_BASE_URL = "http://127.0.0.1:3101"
DEFAULT_TOKEN = "APC1XGT-QX7MYMT-G76R786-E01F1FD"
DEFAULT_CONTAINER = "anythingllm-localai"
DEFAULT_MANIFEST = Path(
    r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM\partitions\partition_manifest_2026-07-19.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync AnythingLLM partition workspaces against a local manifest."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--workspace",
        action="append",
        dest="workspaces",
        help="Optional workspace slug to sync. Repeat for multiple.",
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--transport",
        choices=("docker", "http"),
        default="docker",
        help="Use docker exec into the AnythingLLM container by default because host HTTP is flaky on this machine.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def docker_api_request(
    container: str,
    token: str,
    path: str,
    *,
    method: str,
    payload: dict[str, Any] | None,
    timeout: int,
) -> dict[str, Any]:
    js = f"""
const http = require('http');
const payload = {json.dumps(payload, ensure_ascii=False)};
const body = payload ? JSON.stringify(payload) : null;
const req = http.request({{
  hostname: '127.0.0.1',
  port: 3001,
  path: {json.dumps(path)},
  method: {json.dumps(method)},
  headers: {{
    Authorization: {json.dumps(f"Bearer {token}")},
    Accept: 'application/json',
    ...(body ? {{ 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }} : {{}})
  }}
}}, (res) => {{
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {{
    console.log(JSON.stringify({{ status: res.statusCode, body: data }}));
  }});
}});
req.on('error', (err) => {{
  console.error(err.message);
  process.exit(1);
}});
if (body) req.write(body);
req.end();
"""
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "node", "-"],
        input=js,
        text=True,
        capture_output=True,
        timeout=timeout + 15,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"docker request {method} {path} failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    parsed = json.loads(completed.stdout)
    if int(parsed.get("status", 500)) >= 400:
        raise RuntimeError(f"{method} {path} failed with {parsed['status']}: {parsed.get('body', '')}")
    body_text = parsed.get("body", "")
    return json.loads(body_text) if body_text else {}


def api_request(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
    transport: str = "docker",
    container: str = DEFAULT_CONTAINER,
) -> dict[str, Any]:
    if transport == "docker":
        return docker_api_request(
            container,
            token,
            path,
            method=method,
            payload=payload,
            timeout=timeout,
        )
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(base_url.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc}") from exc


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def ensure_workspace(
    base_url: str,
    token: str,
    slug: str,
    name: str,
    timeout: int,
    transport: str,
    container: str,
) -> dict[str, Any]:
    workspaces = api_request(
        base_url,
        token,
        "/api/workspaces",
        timeout=timeout,
        transport=transport,
        container=container,
    )
    for workspace in workspaces.get("workspaces", []):
        if workspace.get("slug") == slug:
            return workspace
    created = api_request(
        base_url,
        token,
        "/api/workspace/new",
        method="POST",
        payload={"name": name},
        timeout=timeout,
        transport=transport,
        container=container,
    )
    return created.get("workspace") or {}


def get_workspace_documents(
    base_url: str,
    token: str,
    slug: str,
    timeout: int,
    transport: str,
    container: str,
) -> tuple[dict[str, Any], set[str]]:
    detail = api_request(
        base_url,
        token,
        f"/api/workspace/{slug}",
        timeout=timeout,
        transport=transport,
        container=container,
    )
    documents = {
        doc.get("docpath")
        for doc in detail.get("workspace", {}).get("documents", [])
        if doc.get("docpath")
    }
    return detail, documents


def sync_workspace(
    *,
    base_url: str,
    token: str,
    slug: str,
    name: str,
    adds: list[str],
    batch_size: int,
    sleep_seconds: float,
    timeout: int,
    dry_run: bool,
    transport: str,
    container: str,
) -> dict[str, Any]:
    ensure_workspace(base_url, token, slug, name, timeout, transport, container)
    before_detail, existing = get_workspace_documents(
        base_url, token, slug, timeout, transport, container
    )
    missing = [doc for doc in adds if doc not in existing]
    payload: dict[str, Any] = {
        "workspace": slug,
        "beforeCount": len(existing),
        "targetCount": len(adds),
        "missingBefore": len(missing),
        "batchesApplied": 0,
        "appliedDocuments": 0,
        "message": None,
    }

    if dry_run or not missing:
        payload["afterCount"] = len(existing)
        payload["missingAfter"] = len(missing)
        payload["workspaceName"] = before_detail.get("workspace", {}).get("name", name)
        return payload

    for batch in chunked(missing, batch_size):
        result = api_request(
            base_url,
            token,
            f"/api/workspace/{slug}/update-embeddings",
            method="POST",
            payload={"adds": batch, "deletes": []},
            timeout=timeout,
            transport=transport,
            container=container,
        )
        payload["message"] = result.get("message")
        payload["batchesApplied"] += 1
        payload["appliedDocuments"] += len(batch)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    after_detail, after_docs = get_workspace_documents(
        base_url, token, slug, timeout, transport, container
    )
    missing_after = [doc for doc in adds if doc not in after_docs]
    payload["afterCount"] = len(after_docs)
    payload["missingAfter"] = len(missing_after)
    payload["workspaceName"] = after_detail.get("workspace", {}).get("name", name)
    return payload


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    target_slugs = set(args.workspaces or manifest["workspaces"].keys())
    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "manifest": str(args.manifest),
        "dryRun": args.dry_run,
        "workspaces": {},
    }

    for slug, config in manifest["workspaces"].items():
        if slug not in target_slugs:
            continue
        filtered_adds, blocked_adds = filtrar_docpaths(config["adds"])
        report["workspaces"][slug] = sync_workspace(
            base_url=args.base_url,
            token=args.token,
            slug=slug,
            name=config["workspaceName"],
            adds=filtered_adds,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep_seconds,
            timeout=args.timeout,
            dry_run=args.dry_run,
            transport=args.transport,
            container=args.container,
        )
        report["workspaces"][slug]["task111IngestFilter"] = {
            "rule": "coincidencia exacta de docSource revisado como ARTEFACTO",
            "blockedCount": len(blocked_adds),
            "blocked": blocked_adds,
        }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
