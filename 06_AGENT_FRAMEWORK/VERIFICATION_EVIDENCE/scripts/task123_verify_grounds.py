#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica ``grounds_to`` deterministas en documentos operativos.

TASK-123 separa deteccion de reparacion: este programa solo lee fuentes y
escribe, de forma atomica, su propio informe en ``.ai/state``. No usa IA, no
actualiza documentos y no ejecuta comandos arbitrarios declarados en YAML.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import task124_live_sources as live


WORKSPACE = live.WORKSPACE
DEFAULT_OUTPUT = WORKSPACE / ".ai" / "state" / "task123_ground_truth.json"
SCAN_ROOTS = (
    WORKSPACE / "00_COMMAND_CENTER",
    WORKSPACE / "01_OBSIDIAN" / "BIS_BRAIN" / "03_Tchasky",
)
STATUSES = ("VERDADERO", "FALSO", "NO COMPROBABLE")
USER_AGENT = "task123-ground-verifier/1"
TIMEOUT_SECONDS = live.TIMEOUT_SECONDS
_HTTP_CACHE: dict[str, Any] = {}
_OLLAMA_CACHE: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class CheckResult:
    status: str
    observed: Any
    evidence: str


NotCheckable = live.SourceUnavailable


def _scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("[") and value.endswith("]"):
        return json.loads(value.replace("'", '"'))
    return value


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    """Lee el mismo subconjunto YAML que TASK-122."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"Frontmatter sin cierre: {path}")
    raw = normalized[4:end]
    body = normalized[end + 5 :]
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line_number, line in enumerate(raw.splitlines(), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if current_list is None:
                raise ValueError(f"Lista YAML sin campo en {path}:{line_number}")
            data[current_list].append(_scalar(line[4:]))
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", line)
        if not match:
            raise ValueError(f"YAML no soportado en {path}:{line_number}: {line}")
        key, raw_value = match.groups()
        if raw_value in {None, ""}:
            data[key] = []
            current_list = key
        else:
            data[key] = _scalar(raw_value)
            current_list = None
    return data, body


def _tchasky_repo() -> Path:
    return live.tchasky_repo()


def _resolve_path(raw: str) -> Path:
    replacements = {
        "{workspace}": str(WORKSPACE),
        "{tchasky_repo}": str(_tchasky_repo()),
        "{home}": str(live.canonical_home()),
    }
    expanded = raw
    for token, value in replacements.items():
        expanded = expanded.replace(token, value)
    path = Path(expanded).expanduser()
    return path if path.is_absolute() else WORKSPACE / path


def _run(args: list[str], timeout: int = TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    return live.run(args, timeout=timeout)


def _load_dotenv(path: Path) -> dict[str, str]:
    return live.load_dotenv(path)


def _request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    cache_key = json.dumps(
        {"url": url, "headers": request_headers, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
    )
    if cache_key in _HTTP_CACHE:
        return _HTTP_CACHE[cache_key]
    request = urllib.request.Request(url, data=data, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            result = json.load(response)
            _HTTP_CACHE[cache_key] = result
            return result
    except urllib.error.HTTPError as error:
        raise NotCheckable(f"HTTP {error.code} en {urllib.parse.urlsplit(url).netloc}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise NotCheckable(f"fuente HTTP no disponible: {type(error).__name__}") from error


def _truth(ok: bool, observed: Any, evidence: str) -> CheckResult:
    return CheckResult("VERDADERO" if ok else "FALSO", observed, evidence)


def check_path_exists(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    kind = anchor.get("kind", "any")
    exists = path.is_file() if kind == "file" else path.is_dir() if kind == "dir" else path.exists()
    return _truth(exists, exists, f"ruta {kind}: {path}")


def check_paths_exist(anchor: dict[str, Any]) -> CheckResult:
    paths = [_resolve_path(item) for item in anchor["paths"]]
    missing = [str(path) for path in paths if not path.exists()]
    return _truth(not missing, {"total": len(paths), "missing": missing}, "existencia de rutas")


def check_file_contains(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    if not path.is_file():
        raise NotCheckable(f"archivo no disponible: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    expected = str(anchor["expected"])
    if anchor.get("normalize_hex"):
        text = re.sub(r"[^0-9a-f]", "", text.casefold())
        expected = re.sub(r"[^0-9a-f]", "", expected.casefold())
    found = expected in text
    return _truth(found, found, f"contenido literal en {path}")


def _json_at(value: Any, pointer: list[Any]) -> Any:
    current = value
    for part in pointer:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def check_json_value(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    if not path.is_file():
        raise NotCheckable(f"JSON no disponible: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        observed = _json_at(data, anchor["pointer"])
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
        return CheckResult("FALSO", None, f"ruta JSON ausente o invalida en {path}: {type(error).__name__}")
    return _truth(observed == anchor["expected"], observed, f"valor JSON en {path}")


def check_dotenv_keys(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    values = _load_dotenv(path)
    missing = [key for key in anchor["keys"] if not values.get(key)]
    return _truth(not missing, {"configured": len(anchor["keys"]) - len(missing), "missing": missing}, f"nombres de variables en {path}; valores ocultos")


def check_dotenv_keys_absent(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    values = _load_dotenv(path)
    present = [key for key in anchor["keys"] if values.get(key)]
    return _truth(not present, {"present": present}, f"ausencia de variables en {path}; valores ocultos")


def check_file_mode(anchor: dict[str, Any]) -> CheckResult:
    path = _resolve_path(anchor["path"])
    if not path.exists():
        return CheckResult("FALSO", "ausente", f"permisos de {path}")
    observed = live.file_mode(path)
    return _truth(observed == anchor["expected"], observed, f"permisos de {path}")


def check_git_current_branch(anchor: dict[str, Any]) -> CheckResult:
    repo = _resolve_path(anchor["repo"])
    result = _run(["git", "-C", str(repo), "branch", "--show-current"])
    if result.returncode:
        raise NotCheckable(f"git no pudo leer la rama en {repo}")
    observed = result.stdout.strip()
    return _truth(observed == anchor["expected"], observed, f"git branch --show-current en {repo}")


def check_git_ref_exists(anchor: dict[str, Any]) -> CheckResult:
    repo = _resolve_path(anchor["repo"])
    ref = anchor["ref"]
    result = _run(["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref])
    if result.returncode not in {0, 1}:
        raise NotCheckable(f"git no pudo consultar {ref}")
    return _truth(result.returncode == 0, result.returncode == 0, f"git show-ref {ref}")


def check_git_refs_equal(anchor: dict[str, Any]) -> CheckResult:
    repo = _resolve_path(anchor["repo"])
    refs = list(anchor["refs"])
    result = _run(["git", "-C", str(repo), "rev-parse", *refs])
    if result.returncode:
        raise NotCheckable(f"git no pudo resolver {', '.join(refs)}")
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    expected_prefix = anchor.get("expected_prefix")
    ok = len(values) == len(refs) and len(set(values)) == 1
    if expected_prefix:
        ok = ok and values[0].startswith(expected_prefix)
    observed = {ref: value[:12] for ref, value in zip(refs, values)}
    return _truth(ok, observed, f"git rev-parse de {', '.join(refs)}")


def check_git_commit_exists(anchor: dict[str, Any]) -> CheckResult:
    repo = _resolve_path(anchor["repo"])
    commit = anchor["commit"]
    result = _run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"])
    if result.returncode not in {0, 1, 128}:
        raise NotCheckable(f"git no pudo consultar el commit {commit}")
    return _truth(result.returncode == 0, result.returncode == 0, f"git cat-file {commit}")


def check_tcp_port(anchor: dict[str, Any]) -> CheckResult:
    host = anchor.get("host", "127.0.0.1")
    port = int(anchor["port"])
    listening = live.tcp_listening(host, port)
    expected = bool(anchor.get("listening", True))
    return _truth(listening == expected, listening, f"conexion TCP {host}:{port}")


def _docker_inspect(container: str) -> dict[str, Any]:
    return live.docker_inspect(container)


def check_docker_running(anchor: dict[str, Any]) -> CheckResult:
    info = _docker_inspect(anchor["container"])
    running = bool(info and info.get("State", {}).get("Running"))
    return _truth(running, running, f"estado Docker de {anchor['container']}")


def check_docker_published_port(anchor: dict[str, Any]) -> CheckResult:
    info = _docker_inspect(anchor["container"])
    if not info:
        return CheckResult("FALSO", "contenedor ausente", f"puerto Docker de {anchor['container']}")
    bindings = info.get("NetworkSettings", {}).get("Ports", {})
    observed: list[int] = []
    for values in bindings.values():
        for value in values or []:
            if value.get("HostPort", "").isdigit():
                observed.append(int(value["HostPort"]))
    expected = int(anchor["port"])
    return _truth(expected in observed, sorted(set(observed)), f"puertos publicados por {anchor['container']}")


def _ollama_via_router(container: str) -> dict[str, Any]:
    if container in _OLLAMA_CACHE:
        return _OLLAMA_CACHE[container]
    observed = live.ollama_via_router(container)
    _OLLAMA_CACHE[container] = observed
    return observed


def check_ollama_via_router(anchor: dict[str, Any]) -> CheckResult:
    observed = _ollama_via_router(anchor.get("container", "anythingllm-router"))
    field = anchor["field"]
    expected = anchor["expected"]
    if field == "model":
        value = expected in observed["models"]
        return _truth(value, value, "GET /v1/models via contenedor del router")
    value = observed[field]
    return _truth(value == expected, value, f"Ollama {field} via contenedor del router")


def check_http_json(anchor: dict[str, Any]) -> CheckResult:
    data = _request_json(anchor["url"])
    observed = _json_at(data, anchor["pointer"])
    return _truth(observed == anchor["expected"], observed, f"GET {urllib.parse.urlsplit(anchor['url']).netloc}")


def check_doh_record(anchor: dict[str, Any]) -> CheckResult:
    query = urllib.parse.urlencode({"name": anchor["name"], "type": anchor["record_type"]})
    data = _request_json(f"https://dns.google/resolve?{query}")
    answers = [str(item.get("data", "")).rstrip(".") for item in data.get("Answer", [])]
    expected = str(anchor["expected"]).rstrip(".")
    normalized = [item.casefold() for item in answers]
    return _truth(expected.casefold() in normalized, answers, f"DNS {anchor['record_type']} de {anchor['name']}")


def _provider_credential(path: str, key: str) -> tuple[str, str]:
    credential_path = _resolve_path(path)
    if credential_path.is_file():
        value = _load_dotenv(credential_path).get(key)
        if not value:
            raise NotCheckable(f"falta la credencial {key} en {credential_path}")
        return value, f"{key} existente en {credential_path}; valor oculto"
    if key in {"RAILWAY_TOKEN", "VERCEL_TOKEN"}:
        return live._repo_credential(key)
    _load_dotenv(credential_path)
    raise AssertionError("load_dotenv debio rechazar una ruta inexistente")


def check_railway_project(anchor: dict[str, Any]) -> CheckResult:
    token, credential = _provider_credential(anchor["credentials"], "RAILWAY_TOKEN")
    query = "query($id:String!){project(id:$id){id name services{edges{node{id name}}} environments{edges{node{id name}}}}}"
    data = _request_json(
        "https://backboard.railway.app/graphql/v2",
        headers={"Project-Access-Token": token},
        payload={"query": query, "variables": {"id": anchor["project_id"]}},
    )
    project = data.get("data", {}).get("project")
    if not project:
        return CheckResult(
            "FALSO", None, f"Railway no devolvio el proyecto; {credential}"
        )
    observed = {"project_id": project.get("id"), "project_name": project.get("name")}
    if anchor.get("service_id"):
        observed["service_ids"] = [edge["node"]["id"] for edge in project["services"]["edges"]]
    if anchor.get("environment_id"):
        observed["environment_ids"] = [edge["node"]["id"] for edge in project["environments"]["edges"]]
    ok = observed["project_id"] == anchor["project_id"]
    if anchor.get("project_name"):
        ok = ok and observed["project_name"] == anchor["project_name"]
    if anchor.get("service_id"):
        ok = ok and anchor["service_id"] in observed["service_ids"]
    if anchor.get("environment_id"):
        ok = ok and anchor["environment_id"] in observed["environment_ids"]
    return _truth(ok, observed, f"Railway GraphQL; {credential}")


def check_railway_deployment_meta(anchor: dict[str, Any]) -> CheckResult:
    token, credential = _provider_credential(anchor["credentials"], "RAILWAY_TOKEN")
    query = "query($projectId:String!,$environmentId:String!,$serviceId:String!){deployments(input:{projectId:$projectId,environmentId:$environmentId,serviceId:$serviceId},first:1){edges{node{id status meta}}}}"
    variables = {
        "projectId": anchor["project_id"],
        "environmentId": anchor["environment_id"],
        "serviceId": anchor["service_id"],
    }
    data = _request_json(
        "https://backboard.railway.app/graphql/v2",
        headers={"Project-Access-Token": token},
        payload={"query": query, "variables": variables},
    )
    edges = data.get("data", {}).get("deployments", {}).get("edges", [])
    if not edges:
        raise NotCheckable(
            f"Railway no devolvio un deployment de produccion; {credential}"
        )
    node = edges[0]["node"]
    try:
        observed = _json_at(node, anchor["pointer"])
    except (KeyError, IndexError, TypeError):
        if anchor.get("missing_is_not_checkable"):
            raise NotCheckable(
                f"el deployment {node.get('id')} no expone "
                f"{'.'.join(map(str, anchor['pointer']))}; {credential}"
            )
        return CheckResult(
            "FALSO",
            None,
            f"campo ausente en deployment Railway {node.get('id')}; {credential}",
        )
    return _truth(
        observed == anchor["expected"],
        observed,
        f"metadatos del deployment Railway {node.get('id')} "
        f"({node.get('status')}); {credential}",
    )


def _vercel_request(anchor: dict[str, Any], suffix: str) -> tuple[Any, str]:
    token, credential = _provider_credential(anchor["credentials"], "VERCEL_TOKEN")
    data = _request_json(
        f"https://api.vercel.com{suffix}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return data, credential


def check_vercel_project(anchor: dict[str, Any]) -> CheckResult:
    data, credential = _vercel_request(
        anchor, f"/v9/projects/{anchor['project_id']}"
    )
    observed = {"id": data.get("id"), "name": data.get("name")}
    ok = observed == {"id": anchor["project_id"], "name": anchor["project_name"]}
    return _truth(ok, observed, f"Vercel REST; {credential}")


def check_vercel_env(anchor: dict[str, Any]) -> CheckResult:
    data, credential = _vercel_request(
        anchor, f"/v10/projects/{anchor['project_id']}/env"
    )
    matches = [item for item in data.get("envs", []) if item.get("key") == anchor["key"]]
    wanted_targets = set(anchor.get("targets", []))
    matching = [
        item
        for item in matches
        if "expected" not in anchor or item.get("value") == anchor["expected"]
    ]
    matching_targets = {target for item in matching for target in item.get("target", [])}
    ok = bool(matching) and wanted_targets.issubset(matching_targets)
    observed = {
        "entries": len(matches),
        "targets": sorted({target for item in matches for target in item.get("target", [])}),
        "matching_targets": sorted(matching_targets),
        "value_matches": bool(matching),
    }
    return _truth(
        ok,
        observed,
        f"variable {anchor['key']} en Vercel; {credential}; "
        "valores sensibles ocultos",
    )


def check_expo_token_active(anchor: dict[str, Any]) -> CheckResult:
    token, _credential = _provider_credential(anchor["credentials"], "EXPO_TOKEN")
    data = _request_json(
        "https://api.expo.dev/graphql",
        headers={"Authorization": f"Bearer {token}"},
        payload={"query": "query { meActor { id __typename } }"},
    )
    actor = data.get("data", {}).get("meActor")
    return _truth(bool(actor and actor.get("id")), {"active": bool(actor), "type": actor.get("__typename") if actor else None}, "Expo GraphQL; token activo, valor oculto")


def check_cloudinary_credentials(anchor: dict[str, Any]) -> CheckResult:
    values = _load_dotenv(_resolve_path(anchor["credentials"]))
    required = ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    if any(not values.get(key) for key in required):
        raise NotCheckable("faltan credenciales de Cloudinary")
    basic = base64.b64encode(f"{values['CLOUDINARY_API_KEY']}:{values['CLOUDINARY_API_SECRET']}".encode()).decode()
    data = _request_json(
        f"https://api.cloudinary.com/v1_1/{values['CLOUDINARY_CLOUD_NAME']}/ping",
        headers={"Authorization": f"Basic {basic}"},
    )
    observed = data.get("status")
    return _truth(observed == "ok", observed, "Cloudinary /ping; credenciales activas, valores ocultos")


def check_bearer_api_active(anchor: dict[str, Any]) -> CheckResult:
    token, _credential = _provider_credential(
        anchor["credentials"], anchor["credential_key"]
    )
    data = _request_json(anchor["url"], headers={"Authorization": f"Bearer {token}"})
    pointer = anchor.get("pointer")
    observed = _json_at(data, pointer) if pointer else bool(data)
    expected = anchor.get("expected", True)
    return _truth(observed == expected, observed, f"API {urllib.parse.urlsplit(anchor['url']).netloc}; credencial activa, valor oculto")


def _postgres_query(sql: str, container: str) -> list[str]:
    return live.postgres_query(sql, container)


def check_postgres_rows(anchor: dict[str, Any]) -> CheckResult:
    rows = _postgres_query(anchor["query"], anchor.get("container", "lifeos_postgres"))
    expected = [str(item) for item in anchor["expected_rows"]]
    return _truth(rows == expected, rows, f"consulta PostgreSQL de solo lectura en {anchor.get('container', 'lifeos_postgres')}")


def check_redis_config(anchor: dict[str, Any]) -> CheckResult:
    observed = live.redis_config(
        anchor["key"],
        container=anchor.get("container", "lifeos_redis"),
        credentials=_resolve_path(anchor["credentials"]),
    )
    return _truth(observed == anchor["expected"], observed, f"Redis CONFIG GET {anchor['key']}; credencial oculta")


def check_apk_certificate_sha1(anchor: dict[str, Any]) -> CheckResult:
    apk_env = anchor.get("apk_env", "TASK123_PLAY_APK")
    apk_raw = os.environ.get(apk_env)
    if not apk_raw:
        raise NotCheckable(f"defina {apk_env} con el APK extraido del telefono")
    apk = Path(apk_raw).expanduser()
    if not apk.is_file():
        raise NotCheckable(f"APK no disponible en {apk}")
    apksigner = os.environ.get("TASK123_APKSIGNER", "<HOME>/Android/Sdk/build-tools/36.0.0/apksigner")
    result = _run([apksigner, "verify", "--print-certs", str(apk)], timeout=30)
    if result.returncode:
        raise NotCheckable("apksigner no pudo medir el APK")
    match = re.search(r"Signer #1 certificate SHA-1 digest:\s*([0-9a-f:]+)", result.stdout, re.I)
    if not match:
        raise NotCheckable("apksigner no devolvio SHA-1")
    observed = match.group(1).upper()
    expected = str(anchor["expected"]).upper()
    return _truth(observed == expected, observed, "apksigner sobre APK indicado por TASK123_PLAY_APK")


CHECKS: dict[str, Callable[[dict[str, Any]], CheckResult]] = {
    "path_exists": check_path_exists,
    "paths_exist": check_paths_exist,
    "file_contains": check_file_contains,
    "json_value": check_json_value,
    "dotenv_keys": check_dotenv_keys,
    "dotenv_keys_absent": check_dotenv_keys_absent,
    "file_mode": check_file_mode,
    "git_current_branch": check_git_current_branch,
    "git_ref_exists": check_git_ref_exists,
    "git_refs_equal": check_git_refs_equal,
    "git_commit_exists": check_git_commit_exists,
    "tcp_port": check_tcp_port,
    "docker_running": check_docker_running,
    "docker_published_port": check_docker_published_port,
    "ollama_via_router": check_ollama_via_router,
    "http_json": check_http_json,
    "doh_record": check_doh_record,
    "railway_project": check_railway_project,
    "railway_deployment_meta": check_railway_deployment_meta,
    "vercel_project": check_vercel_project,
    "vercel_env": check_vercel_env,
    "expo_token_active": check_expo_token_active,
    "cloudinary_credentials": check_cloudinary_credentials,
    "bearer_api_active": check_bearer_api_active,
    "postgres_rows": check_postgres_rows,
    "redis_config": check_redis_config,
    "apk_certificate_sha1": check_apk_certificate_sha1,
}


def discover_documents(selected: list[str] | None = None) -> list[tuple[Path, dict[str, Any]]]:
    selected_paths = {_resolve_path(item).resolve() for item in selected or []}
    documents: list[tuple[Path, dict[str, Any]]] = []
    candidates = sorted(selected_paths) if selected_paths else [
        path for root in SCAN_ROOTS for path in sorted(root.rglob("*.md"))
    ]
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        header_end = text.find("\n---\n", 4) if text.startswith("---\n") else -1
        if header_end < 0 or not re.search(
            r'(?mi)^type:\s*["\']?operational["\']?\s*$', text[4:header_end]
        ):
            continue
        metadata, _ = parse_frontmatter(text, path)
        if metadata.get("type") == "operational":
            documents.append((path, metadata))
    if selected_paths:
        found = {path.resolve() for path, _ in documents}
        missing = selected_paths - found
        if missing:
            raise ValueError("No son documentos operativos: " + ", ".join(map(str, sorted(missing))))
    return documents


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return str(path)


def _parse_anchor(raw: Any, path: Path) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise ValueError(f"grounds_to debe contener JSON entre comillas en {path}")
    try:
        anchor = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"grounds_to invalido en {path}: {error}") from error
    required = {"id", "claim", "check"}
    missing = required - set(anchor)
    if missing:
        raise ValueError(f"Faltan {sorted(missing)} en grounds_to de {path}")
    if anchor["check"] not in CHECKS:
        raise ValueError(f"Check no permitido {anchor['check']} en {path}")
    return anchor


def verify(selected: list[str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    documents = discover_documents(selected)
    results: list[dict[str, Any]] = []
    ids: set[str] = set()
    documents_with_grounds = 0
    for path, metadata in documents:
        raw_anchors = metadata.get("grounds_to", [])
        if not isinstance(raw_anchors, list):
            raise ValueError(f"grounds_to debe ser lista en {path}")
        if raw_anchors:
            documents_with_grounds += 1
        for raw in raw_anchors:
            anchor = _parse_anchor(raw, path)
            if anchor["id"] in ids:
                raise ValueError(f"ID de ancla duplicado: {anchor['id']}")
            ids.add(anchor["id"])
            try:
                checked = CHECKS[anchor["check"]](anchor)
            except NotCheckable as error:
                checked = CheckResult("NO COMPROBABLE", None, str(error))
            except Exception as error:  # un fallo del adaptador nunca se convierte en verde
                checked = CheckResult("NO COMPROBABLE", None, f"error del verificador: {type(error).__name__}: {error}")
            results.append(
                {
                    "id": anchor["id"],
                    "document": _display_path(path),
                    "claim": anchor["claim"],
                    "check": anchor["check"],
                    "status": checked.status,
                    "observed": checked.observed,
                    "evidence": checked.evidence,
                }
            )
    counts = {status: sum(item["status"] == status for item in results) for status in STATUSES}
    per_document = []
    for path, _ in documents:
        relative = _display_path(path)
        subset = [item for item in results if item["document"] == relative]
        per_document.append(
            {
                "document": relative,
                "claims": len(subset),
                **{status: sum(item["status"] == status for item in subset) for status in STATUSES},
            }
        )
    return {
        "schema": "task123-ground-truth-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "documents_scanned": len(documents),
        "documents_with_grounds": documents_with_grounds,
        "summary": {"claims": len(results), **counts},
        "per_document": per_document,
        "results": results,
    }


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(encoded)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica grounds_to sin IA ni reparacion")
    parser.add_argument("command", nargs="?", default="verify", choices=["verify"])
    parser.add_argument("--document", action="append", help="Limita la comprobacion a un documento")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Informe JSON de estado")
    parser.add_argument("--no-write", action="store_true", help="No escribe el informe; util para pruebas")
    parser.add_argument("--strict", action="store_true", help="Devuelve codigo 1 si hay alguna afirmacion falsa")
    args = parser.parse_args()
    try:
        payload = verify(args.document)
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if not args.no_write:
        _write_atomic(_resolve_path(args.output), payload)
    summary = payload["summary"]
    print(
        f"TASK-123: {summary['VERDADERO']} VERDADERO, "
        f"{summary['FALSO']} FALSO, {summary['NO COMPROBABLE']} NO COMPROBABLE "
        f"({summary['claims']} afirmaciones, {payload['documents_scanned']} documentos, "
        f"{payload['duration_ms']:.1f} ms)"
    )
    for item in payload["results"]:
        print(f"{item['status']}: {item['id']} — {item['claim']}")
    return 1 if args.strict and summary["FALSO"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
