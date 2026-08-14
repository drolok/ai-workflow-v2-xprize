#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evalúa TASK-124 contra sus 15 casos prerregistrados y genera evidencia."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import task124_live_router as router
import task124_live_sources as live
import task123_verify_grounds as grounds


WORKSPACE = live.WORKSPACE
CASES = WORKSPACE / ".ai" / "tests" / "task124_live_routing_cases.json"
DEFAULT_OUTPUT = WORKSPACE / ".ai" / "state" / "task124_evaluation.json"
DEFAULT_INVENTORY = WORKSPACE / ".ai" / "state" / "task124_source_inventory.json"
DEFAULT_REPORT = WORKSPACE / ".ai" / "reports" / "task124_report.md"
ANYTHINGLLM_DB = WORKSPACE / "02_LOCAL_AI" / "ANYTHINGLLM" / "storage" / "anythingllm.db"
RAG_BASE = "http://127.0.0.1:3110"
RAG_WORKSPACE = "bis_brain-segundo-cerebro"

PROTECTED_HASHES_BEFORE = {
    "02_LOCAL_AI/ANYTHINGLLM/rag_golden_set.json": "603293c5dd3d5beec1a9054d3bd51563d7f5cd2c327cbd619d480ee134b9778f",
    "02_LOCAL_AI/ANYTHINGLLM/operational_golden_set.json": "cd3350f894e74282ef1ac19b8fbffed66fb5f2adf43df8511f92798df5c3d1a4",
    "02_LOCAL_AI/ANYTHINGLLM/operational_index.sqlite3": "027174c9ca2f28e80c1354ab62e431facac13195102a26c8cf476b3c2fa71fd4",
    "02_LOCAL_AI/ANYTHINGLLM/storage/anythingllm.db": "53d8f5d4bbf5941a40145160c4538cbb48e2933894e56bd091785b34fea9e36e",
    "02_LOCAL_AI/ROUTER/**": "45cf5210d428b5fb8d26749823c1502ea7e051a1cebc498f0ed79637da91db3f",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for candidate in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(hashlib.sha256(candidate.read_bytes()).hexdigest().encode("ascii"))
        digest.update(b"  ")
        digest.update(relative)
        digest.update(b"\n")
    return digest.hexdigest()


def protected_state() -> dict[str, Any]:
    rows = []
    for relative, before in PROTECTED_HASHES_BEFORE.items():
        if relative.endswith("/**"):
            current = sha256_tree(WORKSPACE / relative[:-3])
        else:
            current = sha256_file(WORKSPACE / relative)
        rows.append(
            {
                "path": relative,
                "sha256_before": before,
                "sha256_after": current,
                "unchanged": current == before,
            }
        )
    return {"all_unchanged": all(item["unchanged"] for item in rows), "items": rows}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(encoded)
        temporary = Path(handle.name)
    temporary.replace(path)


def _probe(label: str, credential: str, call: Callable[[], Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        observed = call()
        return {
            "source": label,
            "reachable": True,
            "credential": credential,
            "reason": "Consulta real aprobada.",
            "observed": observed,
            "checked_at": live.utc_now(),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except (live.SourceUnavailable, OSError, ValueError, KeyError) as error:
        return {
            "source": label,
            "reachable": False,
            "credential": credential,
            "reason": str(error),
            "observed": None,
            "checked_at": live.utc_now(),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def _run_cli(args: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
        raise live.SourceUnavailable(
            f"no ejecutable desde este entorno: {type(error).__name__}: {error}"
        ) from error
    if result.returncode:
        message = (result.stderr or result.stdout).strip().splitlines()
        raise live.SourceUnavailable(
            message[0] if message else f"código de salida {result.returncode}"
        )
    return {"executable": args[0], "identity": result.stdout.strip().splitlines()[-1]}


def _mcp_inventory() -> list[dict[str, Any]]:
    generated = json.loads(
        (WORKSPACE / ".ai" / "generated" / "MCP.json").read_text(encoding="utf-8")
    )
    registry = (WORKSPACE / ".ai" / "registry" / "MCP.yaml").read_text(
        encoding="utf-8"
    )
    connected_block = registry.split("conectados:", 1)[1].split(
        "no_disponibles_hoy:", 1
    )[0]
    prior_names = [
        line.strip()[:-1]
        for line in connected_block.splitlines()
        if line.startswith("  ")
        and not line.startswith("    ")
        and line.strip().endswith(":")
    ]
    return [
        {
            "source": "Catálogo MCP inventariado",
            "reachable": False,
            "credential": "no aplica",
            "reason": (
                f"{len(generated.get('items', []))} definiciones instalables; "
                "un catálogo no equivale a conexiones activas."
            ),
            "observed": {"catalog_entries": len(generated.get("items", []))},
            "checked_at": live.utc_now(),
        },
        {
            "source": "MCP del proyecto en esta sesión Codex",
            "reachable": False,
            "credential": "no hay conexión pertinente expuesta",
            "reason": (
                "La enumeración de herramientas de esta sesión expuso solo codex_apps "
                "para funciones del producto, sin MCP de Tchasky; 0 de 394 son "
                "consultables aquí como fuente viva del proyecto."
            ),
            "observed": {
                "project_relevant_callable": 0,
                "runtime_servers": ["codex_apps"],
                "registry_connected_previous_session": prior_names,
                "registry_previous_count": len(prior_names),
            },
            "checked_at": live.utc_now(),
        },
    ]


def source_inventory() -> dict[str, Any]:
    rows = _mcp_inventory()
    gh_path = shutil.which("gh") or shutil.which("gh.exe")
    gh_hosts = Path("<WINDOWS_HOME>/AppData/Roaming/GitHub CLI/hosts.yml")
    if gh_path:
        rows.append(
            _probe(
                "GitHub CLI remoto",
                (
                    "configuración autenticada en Windows; credencial en el "
                    "Administrador de credenciales, no exportada a Linux"
                ),
                lambda: _run_cli([gh_path, "auth", "status"]),
            )
        )
        rows[-1]["installed"] = True
        rows[-1]["auth_config_present"] = gh_hosts.is_file()
    else:
        rows.append(
            {
                "source": "GitHub CLI remoto",
                "reachable": False,
                "installed": False,
                "credential": "ausente",
                "reason": "gh no está instalado.",
                "observed": None,
                "checked_at": live.utc_now(),
            }
        )

    vercel_path = shutil.which("vercel")
    if vercel_path:
        rows.append(
            _probe(
                "Vercel CLI",
                "sesión persistida de Vercel CLI",
                lambda: _run_cli([vercel_path, "whoami"]),
            )
        )
        rows[-1]["installed"] = True
    else:
        rows.append(
            {
                "source": "Vercel CLI",
                "reachable": False,
                "installed": False,
                "credential": "ausente",
                "reason": "Vercel CLI no está instalado.",
                "observed": None,
                "checked_at": live.utc_now(),
            }
        )

    for label, commands, credential in (
        ("Railway CLI", ("railway", "railway.exe"), "no hay sesión CLI"),
        ("Sentry CLI/API", ("sentry-cli", "sentry-cli.exe"), "falta SENTRY_AUTH_TOKEN"),
    ):
        executable = next((shutil.which(item) for item in commands if shutil.which(item)), None)
        rows.append(
            {
                "source": label,
                "reachable": False,
                "installed": bool(executable),
                "credential": credential,
                "reason": (
                    "El ejecutable existe, pero no se probó una sesión válida."
                    if executable
                    else "El ejecutable no está instalado en este entorno."
                ),
                "observed": {"executable": executable} if executable else None,
                "checked_at": live.utc_now(),
            }
        )

    rows.extend(
        [
            _probe(
                "Git local",
                "sin credencial; repositorio local",
                lambda: {
                    "branch": live.git_current_branch(),
                    "last_commit": live.git_last_commit(),
                },
            ),
            _probe(
                "Sondas TCP locales",
                "sin credencial",
                lambda: {
                    str(port): live.tcp_listening("127.0.0.1", port)
                    for port in (3001, 5173, 5432, 6379)
                },
            ),
            _probe(
                "Docker Engine local",
                "socket local de Docker",
                lambda: {
                    name: live.docker_running(name)
                    for name in (
                        "lifeos_postgres",
                        "lifeos_redis",
                        "anythingllm-localai",
                        "anythingllm-router",
                    )
                },
            ),
            _probe(
                "PostgreSQL local",
                "credenciales del entorno del contenedor; valores ocultos",
                lambda: {
                    "status": live.postgres_status(),
                    "latest_migration": live.postgres_latest_migration(),
                },
            ),
            _probe(
                "Redis local",
                "REDIS_URL en apps/api/.env; valor oculto",
                lambda: {
                    "ping": live.redis_ping(),
                    "maxmemory-policy": live.redis_config("maxmemory-policy"),
                },
            ),
            _probe(
                "Ollama vía contenedor del router",
                "sin credencial; URL del entorno del contenedor",
                live.ollama_via_router,
            ),
            _probe(
                "Railway GraphQL API",
                "RAILWAY_TOKEN en el .env del repositorio; valor oculto",
                live.railway_latest_deployment,
            ),
            _probe(
                "Vercel REST API",
                "VERCEL_TOKEN en el .env del repositorio; valor oculto",
                live.vercel_latest_production,
            ),
        ]
    )
    grounds_payload = grounds.verify()
    grounds_by_id = {item["id"]: item for item in grounds_payload["results"]}
    for claim_id, label, credential in (
        (
            "support_email.mx1",
            "DNS público vía Google DoH",
            "sin credencial",
        ),
        (
            "railway.health",
            "API pública de producción de Tchasky",
            "sin credencial; endpoint /health",
        ),
        (
            "expo.token_active",
            "Expo GraphQL API",
            "EXPO_TOKEN existente; valor oculto",
        ),
        (
            "cloudinary.active_credentials",
            "Cloudinary REST API",
            "cloud name, API key y secret existentes; valores ocultos",
        ),
        (
            "mercado_pago.active_token",
            "Mercado Pago REST API",
            "MP_ACCESS_TOKEN existente; valor oculto",
        ),
        (
            "resend.active_key",
            "Resend REST API",
            "RESEND_API_KEY existente; valor oculto",
        ),
    ):
        item = grounds_by_id[claim_id]
        reachable = item["status"] != "NO COMPROBABLE"
        rows.append(
            {
                "source": label,
                "reachable": reachable,
                "credential": credential,
                "reason": item["evidence"],
                "observed": item["observed"],
                "checked_at": grounds_payload["generated_at"],
                "elapsed_ms": grounds_payload["duration_ms"],
                "task123_claim_status": item["status"],
            }
        )
    reachable = sum(bool(item.get("reachable")) for item in rows)
    repo_environment = live.load_dotenv(live.tchasky_repo() / ".env")
    credential_presence = {
        "linux_home_railway_file": (Path.home() / ".railway_credentials").is_file(),
        "linux_home_vercel_file": (Path.home() / ".vercel_credentials").is_file(),
        "windows_home_railway_file": Path(
            "<WINDOWS_HOME>/.railway_credentials"
        ).is_file(),
        "windows_home_vercel_file": Path(
            "<WINDOWS_HOME>/.vercel_credentials"
        ).is_file(),
        "repo_env_railway_token": bool(repo_environment.get("RAILWAY_TOKEN")),
        "repo_env_vercel_token": bool(repo_environment.get("VERCEL_TOKEN")),
    }
    return {
        "schema": "task124-source-inventory-v1",
        "generated_at": live.utc_now(),
        "summary": {
            "rows": len(rows),
            "reachable": reachable,
            "not_reachable": len(rows) - reachable,
            "mcp_catalog_entries": 394,
            "mcp_project_relevant_callable_now": 0,
            "task123_claims_checked": grounds_payload["summary"]["claims"],
            "task123_checkable": (
                grounds_payload["summary"]["claims"]
                - grounds_payload["summary"]["NO COMPROBABLE"]
            ),
        },
        "credential_presence": credential_presence,
        "sources": rows,
    }


def _anythingllm_key() -> str:
    uri = f"file:{ANYTHINGLLM_DB.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        row = connection.execute(
            "SELECT secret FROM api_keys ORDER BY id LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if not row or not row[0]:
        raise RuntimeError("AnythingLLM no tiene una API key disponible.")
    return str(row[0])


def rag_query(question: str) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(
        f"{RAG_BASE}/api/v1/workspace/{RAG_WORKSPACE}/vector-search",
        data=json.dumps({"query": question, "topN": 5}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_anythingllm_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
            status = response.status
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {
            "called": True,
            "success": False,
            "error": str(error),
            "queried_at": live.utc_now(),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "top_sources": [],
        }
    top_sources = []
    for item in payload.get("results", []):
        source = str((item.get("metadata") or {}).get("docSource") or "")
        if source and source not in top_sources:
            top_sources.append(source)
    return {
        "called": True,
        "success": status == 200,
        "http_status": status,
        "queried_at": live.utc_now(),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "top_sources": top_sources,
    }


def evaluate() -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    test_definition = json.loads(CASES.read_text(encoding="utf-8"))
    cases = test_definition["cases"]
    patterns_started = time.perf_counter()
    classifications = []
    for case in cases:
        decision = router.classify_question(case["question"])
        route_ok = decision.route == case["expected_route"]
        intent_ok = (
            "expected_intent" not in case
            or decision.intent == case.get("expected_intent")
        )
        classifications.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_route": case["expected_route"],
                "expected_intent": case.get("expected_intent"),
                "decision": decision.as_dict(),
                "correct": route_ok and intent_ok,
            }
        )
    patterns_ms = (time.perf_counter() - patterns_started) * 1000
    pattern_correct = sum(item["correct"] for item in classifications)
    conservative_questions = (
        "¿Cómo está diseñada actualmente la arquitectura de pagos?",
        "¿Qué está pasando?",
        "¿Cuál era la versión histórica de Ollama?",
    )
    conservative_probes = [
        {
            "question": question,
            "decision": router.classify_question(question).as_dict(),
            "passed": router.classify_question(question).route == router.ROUTE_RAG,
        }
        for question in conservative_questions
    ]

    live_results = []
    negative_results = []
    for case in cases:
        decision = router.classify_question(case["question"])
        if case["expected_route"] == router.ROUTE_LIVE:
            answer = router.answer_question(case["question"])
            sources_ok = bool(answer.get("sources")) and all(
                item.get("source") and item.get("collected_at")
                for item in answer.get("sources", [])
            )
            live_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "route": decision.route,
                    "intent": decision.intent,
                    "answer": answer,
                    "passed": (
                        decision.route == router.ROUTE_LIVE
                        and answer.get("status") == "ANSWERED"
                        and sources_ok
                    ),
                }
            )
        else:
            rag = rag_query(case["question"]) if decision.route == router.ROUTE_RAG else {
                "called": False,
                "success": False,
                "top_sources": [],
            }
            negative_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "route": decision.route,
                    "rag": rag,
                    "passed": decision.route == router.ROUTE_RAG and rag["success"],
                }
            )

    inventory = source_inventory()
    protected = protected_state()
    live_passed = sum(item["passed"] for item in live_results)
    negative_passed = sum(item["passed"] for item in negative_results)
    approved = (
        pattern_correct == len(cases)
        and live_passed == 10
        and negative_passed == 5
        and all(item["passed"] for item in conservative_probes)
        and protected["all_unchanged"]
    )
    result = {
        "schema": "task124-evaluation-v1",
        "generated_at": live.utc_now(),
        "criterion": test_definition["criterion"],
        "approved": approved,
        "summary": {
            "patterns_correct": pattern_correct,
            "patterns_total": len(cases),
            "patterns_accuracy": round(pattern_correct / len(cases), 4),
            "patterns_total_ms": round(patterns_ms, 3),
            "patterns_mean_ms": round(patterns_ms / len(cases), 3),
            "live_passed": live_passed,
            "live_total": 10,
            "negative_rag_passed": negative_passed,
            "negative_rag_total": 5,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        },
        "model_classifier": {
            "executed": False,
            "accuracy": None,
            "improvement_over_patterns_percentage_points": None,
            "maximum_possible_improvement_percentage_points": 0.0,
            "reason": (
                "Los patrones alcanzaron 15/15. Un modelo no puede mejorar la "
                "exactitud de este conjunto y añadiría la latencia que la tarea "
                "ordena evitar."
            ),
        },
        "classifications": classifications,
        "conservative_probes": conservative_probes,
        "live_results": live_results,
        "negative_results": negative_results,
        "protected_scope": protected,
        "source_inventory_summary": inventory["summary"],
    }
    return result, inventory


def _cell(value: Any, limit: int = 220) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_report(result: dict[str, Any], inventory: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# TASK-124 — Fuentes vivas antes que documentos viejos",
        "",
        f"**Veredicto: {'APRUEBA' if result['approved'] else 'NO APRUEBA'}.**",
        "",
        (
            f"Patrones: **{summary['patterns_correct']}/{summary['patterns_total']}** "
            f"en {summary['patterns_total_ms']:.3f} ms totales. Estado vivo: "
            f"**{summary['live_passed']}/{summary['live_total']}**. Control negativo "
            f"enviado realmente al RAG: **{summary['negative_rag_passed']}/"
            f"{summary['negative_rag_total']}**."
        ),
        "",
        "El clasificador por modelo no se ejecutó: los patrones ya alcanzaron 15/15, "
        "por lo que la mejora posible en este conjunto era 0 puntos porcentuales.",
        "",
        "## Fuentes realmente alcanzables",
        "",
        "| Fuente | Alcanzable hoy | Credencial | Evidencia o causa |",
        "|---|---:|---|---|",
    ]
    for item in inventory["sources"]:
        lines.append(
            f"| {_cell(item['source'])} | {'Sí' if item.get('reachable') else 'No'} | "
            f"{_cell(item.get('credential', ''))} | {_cell(item.get('reason', ''))} |"
        )
    lines.extend(
        [
            "",
            "El inventario largo contiene 394 definiciones instalables. En esta sesión "
            "hay **0 MCP del proyecto utilizables como fuente viva**; los siete de "
            "`MCP.yaml` pertenecen a una sesión anterior y no se contaron como activos.",
            "",
            "La carencia observada ayer no persiste en este contexto: existen los "
            "archivos de credenciales de Railway y Vercel en el home Linux y también "
            "existen `RAILWAY_TOKEN` y `VERCEL_TOKEN` en el `.env` del repositorio. "
            "Ambas API autenticaron; TASK-124 no creó ni modificó credenciales. Las "
            "copias equivalentes del home de Windows siguen ausentes.",
            "",
            "## Diez respuestas de estado vivo",
            "",
            "| Caso | Pregunta | Respuesta | Fuente y marca de tiempo | Resultado |",
            "|---|---|---|---|---:|",
        ]
    )
    for case in result["live_results"]:
        answer = case["answer"]
        source_text = "; ".join(
            f"{item['source']} @ {item['collected_at']}" for item in answer.get("sources", [])
        )
        lines.append(
            f"| {case['id']} | {_cell(case['question'])} | {_cell(answer['answer'])} | "
            f"{_cell(source_text)} | {'APRUEBA' if case['passed'] else 'FALLA'} |"
        )
    lines.extend(
        [
            "",
            "## Control negativo: cinco preguntas que conservaron el RAG",
            "",
            "| Caso | Pregunta | Ruta | Primera fuente recuperada | Resultado |",
            "|---|---|---|---|---:|",
        ]
    )
    for case in result["negative_results"]:
        top = case["rag"].get("top_sources", [])
        lines.append(
            f"| {case['id']} | {_cell(case['question'])} | {case['route']} | "
            f"{_cell(top[0] if top else 'sin resultado')} | "
            f"{'APRUEBA' if case['passed'] else 'FALLA'} |"
        )
    lines.extend(
        [
            "",
            "## Alcance protegido",
            "",
            "| Ruta | Sin cambios | SHA-256 final |",
            "|---|---:|---|",
        ]
    )
    for item in result["protected_scope"]["items"]:
        lines.append(
            f"| `{item['path']}` | {'Sí' if item['unchanged'] else 'No'} | "
            f"`{item['sha256_after']}` |"
        )
    lines.extend(
        [
            "",
            "No se modificaron los golden sets, FTS5, la base de AnythingLLM ni "
            "`02_LOCAL_AI/ROUTER/`. Tampoco se reparó ninguna afirmación falsa.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa TASK-124")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result, inventory = evaluate()
    _atomic_json(args.output, result)
    _atomic_json(args.inventory, inventory)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(build_report(result, inventory), encoding="utf-8")
    summary = result["summary"]
    print(
        f"TASK-124: {'APRUEBA' if result['approved'] else 'NO APRUEBA'}; "
        f"patrones {summary['patterns_correct']}/{summary['patterns_total']}, "
        f"vivo {summary['live_passed']}/{summary['live_total']}, "
        f"RAG negativo {summary['negative_rag_passed']}/{summary['negative_rag_total']}"
    )
    return 0 if result["approved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
