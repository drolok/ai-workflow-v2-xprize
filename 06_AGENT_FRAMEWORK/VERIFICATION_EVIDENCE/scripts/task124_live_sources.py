#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adaptadores deterministas y reutilizables para fuentes de estado vivo.

El módulo no decide si una pregunta debe usar estado vivo o documentación.
Solo consulta fuentes explícitas, siempre en modo de lectura, y devuelve la
evidencia observada. TASK-123 y TASK-124 comparten estos adaptadores para que
una comprobación y una respuesta no puedan divergir por implementación.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


WORKSPACE = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 12
USER_AGENT = "task124-live-sources/1"
DEFAULT_TCHASKY_REPO = Path("<HOME>/<PRIVATE_PROJECT>")
WINDOWS_TCHASKY_REPO = Path(r"\\wsl$\Ubuntu\home\<USER>\<PRIVATE_PROJECT>")
DEFAULT_CANONICAL_HOME = Path("<HOME>")
WINDOWS_CANONICAL_HOME = Path(r"\\wsl$\Ubuntu\home\<USER>")
DEFAULT_POSTGRES_CONTAINER = "lifeos_postgres"
DEFAULT_REDIS_CONTAINER = "lifeos_redis"
DEFAULT_ROUTER_CONTAINER = "anythingllm-router"
WSL_WINDOWS_HOST = "host.docker.internal"


class SourceUnavailable(RuntimeError):
    """La fuente no está disponible o no permite una conclusión honesta."""


@dataclass(frozen=True)
class LiveObservation:
    source: str
    observed: Any
    collected_at: str
    credential: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def observation(
    source: str,
    observed: Any,
    credential: str,
    detail: str = "",
) -> LiveObservation:
    return LiveObservation(source, observed, utc_now(), credential, detail)


def tchasky_repo() -> Path:
    configured = os.environ.get("TASK124_TCHASKY_REPO") or os.environ.get(
        "TASK123_TCHASKY_REPO"
    )
    candidates = [
        Path(configured) if configured else None,
        DEFAULT_TCHASKY_REPO,
        WINDOWS_TCHASKY_REPO,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate
    raise SourceUnavailable(
        "repositorio Tchasky no disponible; defina TASK124_TCHASKY_REPO"
    )


def canonical_home() -> Path:
    configured = os.environ.get("TASK124_CANONICAL_HOME") or os.environ.get(
        "TASK123_CANONICAL_HOME"
    )
    if configured:
        return Path(configured)
    if os.name == "nt":
        return WINDOWS_CANONICAL_HOME
    if DEFAULT_CANONICAL_HOME.exists():
        return DEFAULT_CANONICAL_HOME
    return Path.home()


def run(
    args: Sequence[str], timeout: int = TIMEOUT_SECONDS
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise SourceUnavailable(f"comando no disponible: {args[0]}") from error
    except OSError as error:
        raise SourceUnavailable(
            f"no se pudo ejecutar {args[0]}: {type(error).__name__}"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise SourceUnavailable(
            f"tiempo agotado al ejecutar {args[0]}"
        ) from error


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SourceUnavailable(f"no existe el archivo de credenciales: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def git_current_branch(repo: Path | None = None) -> str:
    target = repo or tchasky_repo()
    result = run(["git", "-C", str(target), "branch", "--show-current"])
    if result.returncode:
        raise SourceUnavailable(f"git no pudo leer la rama en {target}")
    return result.stdout.strip()


def git_last_commit(repo: Path | None = None) -> dict[str, str]:
    target = repo or tchasky_repo()
    result = run(
        ["git", "-C", str(target), "log", "-1", "--format=%H%n%cI%n%s"]
    )
    if result.returncode:
        raise SourceUnavailable(f"git no pudo leer el último commit en {target}")
    lines = result.stdout.splitlines()
    if len(lines) < 3:
        raise SourceUnavailable("git devolvió un último commit incompleto")
    return {"sha": lines[0], "committed_at": lines[1], "subject": "\n".join(lines[2:])}


def _is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return False
    return "microsoft" in release.casefold()


def _is_loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return socket.inet_aton(host) == socket.inet_aton("127.0.0.1")
    except OSError:
        return False


def _tcp_listening_from_windows_host(
    port: int,
    timeout: float,
    container: str = DEFAULT_ROUTER_CONTAINER,
) -> bool:
    """Observa el host Windows desde Docker cuando WSL no ve su loopback."""
    code = (
        "import socket,sys; "
        "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); "
        "s.settimeout(float(sys.argv[3])); "
        "print(1 if s.connect_ex((sys.argv[1],int(sys.argv[2])))==0 else 0); "
        "s.close()"
    )
    result = run(
        [
            "docker",
            "exec",
            container,
            "python3",
            "-c",
            code,
            WSL_WINDOWS_HOST,
            str(int(port)),
            str(float(timeout)),
        ],
        timeout=max(TIMEOUT_SECONDS, int(timeout) + 2),
    )
    observed = result.stdout.strip()
    if result.returncode or observed not in {"0", "1"}:
        raise SourceUnavailable(
            "WSL no puede observar el loopback de Windows y el contenedor "
            f"{container} no pudo consultar {WSL_WINDOWS_HOST}:{port}"
        )
    return observed == "1"


def tcp_listening(host: str, port: int, timeout: float = 1.5) -> bool:
    if _is_wsl() and _is_loopback(host):
        return _tcp_listening_from_windows_host(port, timeout)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        return client.connect_ex((host, int(port))) == 0


def file_mode(path: Path) -> str:
    """Devuelve permisos POSIX incluso al observar un archivo WSL desde Windows."""
    raw = str(path)
    unc_parts = raw.lstrip("\\").split("\\")
    is_wsl_unc = (
        os.name == "nt"
        and len(unc_parts) >= 3
        and unc_parts[0].casefold() in {"wsl$", "wsl.localhost"}
    )
    if not is_wsl_unc:
        return oct(path.stat().st_mode & 0o777)

    distro = unc_parts[1]
    linux_path = "/" + "/".join(unc_parts[2:])
    result = run(["wsl.exe", "-d", distro, "--", "stat", "-c", "%a", "--", linux_path])
    observed = result.stdout.strip()
    if result.returncode or not observed.isdigit():
        raise SourceUnavailable(f"no se pudieron leer permisos POSIX de {linux_path}")
    return f"0o{observed}"


def docker_inspect(container: str) -> dict[str, Any]:
    result = run(["docker", "inspect", container])
    if result.returncode:
        if "No such" in result.stderr:
            return {}
        raise SourceUnavailable("Docker Engine no disponible")
    try:
        return json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError) as error:
        raise SourceUnavailable("respuesta inválida de docker inspect") from error


def docker_running(container: str) -> bool:
    info = docker_inspect(container)
    return bool(info and info.get("State", {}).get("Running"))


def docker_published_ports(container: str) -> list[int]:
    info = docker_inspect(container)
    if not info:
        return []
    ports: list[int] = []
    for bindings in info.get("NetworkSettings", {}).get("Ports", {}).values():
        for binding in bindings or []:
            raw = binding.get("HostPort", "")
            if raw.isdigit():
                ports.append(int(raw))
    return sorted(set(ports))


def ollama_via_router(container: str = DEFAULT_ROUTER_CONTAINER) -> dict[str, Any]:
    code = r'''import json,os,urllib.parse,urllib.request
u=urllib.parse.urlsplit(os.environ["ROUTER_OLLAMA_URL"])
base=f"{u.scheme}://{u.hostname}:{u.port}"
with urllib.request.urlopen(base+"/api/version",timeout=8) as r:
    version=json.load(r)["version"]
with urllib.request.urlopen(base+"/v1/models",timeout=8) as r:
    models=[item["id"] for item in json.load(r).get("data",[])]
print(json.dumps({"port":u.port,"version":version,"models":models}))'''
    result = run(["docker", "exec", container, "python3", "-c", code])
    if result.returncode:
        raise SourceUnavailable(
            "Ollama no es alcanzable desde el contenedor del router"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SourceUnavailable("respuesta inválida al consultar Ollama") from error


def postgres_query(
    sql: str, container: str = DEFAULT_POSTGRES_CONTAINER
) -> list[str]:
    info = docker_inspect(container)
    if not info or not info.get("State", {}).get("Running"):
        raise SourceUnavailable(f"contenedor {container} no está activo")
    environment = {}
    for item in info.get("Config", {}).get("Env", []):
        if "=" in item:
            key, value = item.split("=", 1)
            environment[key] = value
    user = environment.get("POSTGRES_USER", "postgres")
    database = environment.get("POSTGRES_DB", user)
    result = run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-Atqc",
            sql,
        ]
    )
    if result.returncode:
        raise SourceUnavailable("consulta PostgreSQL de solo lectura no disponible")
    return [line for line in result.stdout.splitlines() if line]


def postgres_status() -> dict[str, Any]:
    rows = postgres_query(
        "select current_database(), current_setting('server_version')"
    )
    if not rows:
        raise SourceUnavailable("PostgreSQL no devolvió estado")
    database, _, version = rows[0].partition("|")
    return {"reachable": True, "database": database, "version": version}


def postgres_latest_migration() -> dict[str, Any]:
    rows = postgres_query(
        "select filename, applied_at::text from _manual_sql_migrations "
        "order by applied_at desc, id desc limit 1"
    )
    if not rows:
        return {"filename": None, "applied_at": None}
    filename, _, applied_at = rows[0].partition("|")
    return {"filename": filename, "applied_at": applied_at}


def redis_command(
    command: Sequence[str],
    *,
    container: str = DEFAULT_REDIS_CONTAINER,
    credentials: Path | None = None,
) -> list[str]:
    credentials = credentials or (tchasky_repo() / "apps" / "api" / ".env")
    values = load_dotenv(credentials)
    url = values.get("REDIS_URL")
    if not url:
        raise SourceUnavailable("falta REDIS_URL")
    parsed = urllib.parse.urlsplit(url)
    args = ["docker", "exec"]
    if parsed.password:
        args += ["-e", f"REDISCLI_AUTH={parsed.password}"]
    args += [container, "redis-cli", "--no-auth-warning"]
    if parsed.username:
        args += ["--user", parsed.username]
    args += list(command)
    result = run(args)
    if result.returncode:
        raise SourceUnavailable("Redis no respondió a la consulta de solo lectura")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def redis_ping(
    container: str = DEFAULT_REDIS_CONTAINER,
    credentials: Path | None = None,
) -> bool:
    lines = redis_command(["PING"], container=container, credentials=credentials)
    if not lines:
        raise SourceUnavailable("Redis no devolvió respuesta a PING")
    return lines[-1].casefold() == "pong"


def redis_config(
    key: str,
    container: str = DEFAULT_REDIS_CONTAINER,
    credentials: Path | None = None,
) -> str | None:
    lines = redis_command(
        ["CONFIG", "GET", key], container=container, credentials=credentials
    )
    return lines[-1] if lines else None


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
    request = urllib.request.Request(url, data=data, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise SourceUnavailable(
            f"HTTP {error.code} en {urllib.parse.urlsplit(url).netloc}"
        ) from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SourceUnavailable(
            f"fuente HTTP no disponible: {type(error).__name__}"
        ) from error


def _repo_credential(key: str) -> tuple[str, str]:
    path = tchasky_repo() / ".env"
    value = load_dotenv(path).get(key)
    if not value:
        raise SourceUnavailable(f"falta la credencial {key}")
    return value, f"{key} existente en {path}; valor oculto"


def railway_latest_deployment() -> dict[str, Any]:
    token, credential = _repo_credential("RAILWAY_TOKEN")
    project_id = "bb980d52-a858-4953-b422-93aba12acc5f"
    environment_id = "26e490d9-1c59-4096-bf1e-c260302afa2d"
    service_id = "010a4bfe-937a-43b0-8618-82d128d7c441"
    query = (
        "query($projectId:String!,$environmentId:String!,$serviceId:String!){"
        "deployments(input:{projectId:$projectId,environmentId:$environmentId,"
        "serviceId:$serviceId},first:1){edges{node{id status createdAt meta}}}}"
    )
    payload = _request_json(
        "https://backboard.railway.app/graphql/v2",
        headers={"Project-Access-Token": token},
        payload={
            "query": query,
            "variables": {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": service_id,
            },
        },
    )
    edges = payload.get("data", {}).get("deployments", {}).get("edges", [])
    if not edges:
        errors = [item.get("message") for item in payload.get("errors", [])]
        raise SourceUnavailable(
            "Railway no devolvió un deployment" + (f": {errors}" if errors else "")
        )
    node = edges[0]["node"]
    metadata = node.get("meta") or {}
    return {
        "id": node.get("id"),
        "status": node.get("status"),
        "created_at": node.get("createdAt"),
        "branch": metadata.get("branch"),
        "commit_sha": metadata.get("commitHash") or metadata.get("commitSha"),
        "credential": credential,
    }


def vercel_latest_production() -> dict[str, Any]:
    token, credential = _repo_credential("VERCEL_TOKEN")
    project_id = "prj_q8f85BuPB6TG8x5BdwmLa86ja2Yi"
    query = urllib.parse.urlencode(
        {"projectId": project_id, "limit": 1, "target": "production"}
    )
    payload = _request_json(
        f"https://api.vercel.com/v6/deployments?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    deployments = payload.get("deployments", [])
    if not deployments:
        raise SourceUnavailable("Vercel no devolvió un deployment de producción")
    deployment = deployments[0]

    def iso_from_milliseconds(value: Any) -> str | None:
        if not isinstance(value, (int, float)):
            return None
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()

    metadata = deployment.get("meta") or {}
    return {
        "id": deployment.get("uid"),
        "state": deployment.get("state"),
        "url": deployment.get("url"),
        "created_at": iso_from_milliseconds(deployment.get("createdAt")),
        "ready_at": iso_from_milliseconds(deployment.get("ready")),
        "branch": metadata.get("githubCommitRef"),
        "commit_sha": metadata.get("githubCommitSha"),
        "credential": credential,
    }
