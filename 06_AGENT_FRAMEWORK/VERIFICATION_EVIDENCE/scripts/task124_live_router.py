#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enruta preguntas conservadoramente entre estado vivo y RAG.

La ruta LIVE solo se activa cuando coinciden una señal de actualidad y una
intención soportada por un adaptador determinista. Cualquier duda, pregunta
histórica, decisión o pregunta de arquitectura conserva la ruta RAG.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import task124_live_sources as sources


ROUTE_LIVE = "LIVE"
ROUTE_RAG = "RAG"


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", plain))


DOCUMENTARY_SIGNALS = {
    "arquitectura",
    "decision",
    "decidio",
    "documentado",
    "diseno",
    "disenada",
    "historia",
    "historico",
    "historicos",
    "motivo",
    "motivos",
    "por que",
    "que ocurrio",
}
LIVE_SIGNALS = {
    "activo",
    "activa",
    "actual",
    "ahora",
    "disponible",
    "desplegado",
    "desplegada",
    "estado actual",
    "fallo",
    "hoy",
    "ultimo",
    "ultima",
    "responde",
    "escuchando",
    "vigente",
}


INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("local_health", ("servicios locales", "estado local", "fallo algo")),
    ("git_branch", ("rama",)),
    ("git_commit", ("commit",)),
    ("api_port", ("api local", "puerto 3001")),
    ("web_port", ("web local", "puerto 5173")),
    ("postgres", ("postgres", "postgresql", "migracion")),
    ("redis", ("redis", "expulsion", "eviction")),
    ("ollama", ("ollama",)),
    ("vercel", ("vercel",)),
    ("railway", ("railway",)),
)


@dataclass(frozen=True)
class RoutingDecision:
    route: str
    intent: str | None
    matched_live_signals: tuple[str, ...]
    matched_documentary_signals: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["matched_live_signals"] = list(self.matched_live_signals)
        result["matched_documentary_signals"] = list(
            self.matched_documentary_signals
        )
        return result


def _phrase_present(normalized: str, phrase: str) -> bool:
    return f" {phrase} " in f" {normalized} "


def classify_question(question: str) -> RoutingDecision:
    normalized = normalize(question)
    documentary = tuple(
        sorted(signal for signal in DOCUMENTARY_SIGNALS if _phrase_present(normalized, signal))
    )
    live = tuple(
        sorted(signal for signal in LIVE_SIGNALS if _phrase_present(normalized, signal))
    )
    intent = next(
        (
            name
            for name, terms in INTENT_RULES
            if any(_phrase_present(normalized, term) for term in terms)
        ),
        None,
    )
    if documentary:
        return RoutingDecision(
            ROUTE_RAG,
            None,
            live,
            documentary,
            "La pregunta pide historia, decisión o arquitectura; prevalece RAG.",
        )
    if not live:
        return RoutingDecision(
            ROUTE_RAG,
            None,
            (),
            (),
            "No hay una señal inequívoca de estado actual; ante la duda se usa RAG.",
        )
    if intent is None:
        return RoutingDecision(
            ROUTE_RAG,
            None,
            live,
            (),
            "Hay actualidad, pero no existe un adaptador vivo soportado; se usa RAG.",
        )
    return RoutingDecision(
        ROUTE_LIVE,
        intent,
        live,
        (),
        "Coinciden una señal de actualidad y una fuente viva soportada.",
    )


def _source(
    name: str,
    observed: Any,
    credential: str,
    detail: str,
) -> dict[str, Any]:
    return sources.observation(name, observed, credential, detail).as_dict()


def _local_health() -> tuple[str, list[dict[str, Any]]]:
    api = sources.tcp_listening("127.0.0.1", 3001)
    web = sources.tcp_listening("127.0.0.1", 5173)
    postgres = sources.postgres_status()
    redis = sources.redis_ping()
    observed = {
        "api_3001_listening": api,
        "web_5173_listening": web,
        "postgres_reachable": postgres["reachable"],
        "redis_ping": redis,
    }
    anomalies = [name for name, ok in observed.items() if not ok]
    if anomalies:
        answer = (
            "La sonda puntual no reconstruye todo el día, pero detecta una anomalía "
            f"actual: {', '.join(anomalies)}."
        )
    else:
        answer = (
            "La sonda puntual no reconstruye todo el día y no detecta anomalías "
            "actuales en API, web, PostgreSQL ni Redis."
        )
    evidence = [
        _source(
            "socket TCP local",
            {"127.0.0.1:3001": api, "127.0.0.1:5173": web},
            "sin credencial; conexión TCP local",
            "Sondeo puntual de listeners, no historial de incidentes.",
        ),
        _source(
            "PostgreSQL local",
            postgres,
            "usuario y base leídos del entorno del contenedor; valores ocultos",
            "SELECT current_database(), current_setting('server_version')",
        ),
        _source(
            "Redis local",
            {"ping": redis},
            "REDIS_URL existente en apps/api/.env; valor oculto",
            "redis-cli PING dentro del contenedor",
        ),
    ]
    return answer, evidence


def _git_branch() -> tuple[str, list[dict[str, Any]]]:
    branch = sources.git_current_branch()
    return (
        f"La rama local actual de Tchasky es {branch}.",
        [
            _source(
                "Git local",
                {"branch": branch},
                "sin credencial; repositorio local",
                "git branch --show-current",
            )
        ],
    )


def _git_commit() -> tuple[str, list[dict[str, Any]]]:
    commit = sources.git_last_commit()
    return (
        f"El último commit local es {commit['sha'][:12]}: {commit['subject']}.",
        [
            _source(
                "Git local",
                commit,
                "sin credencial; repositorio local",
                "git log -1",
            )
        ],
    )


def _port(label: str, port: int) -> tuple[str, list[dict[str, Any]]]:
    listening = sources.tcp_listening("127.0.0.1", port)
    state = "está escuchando" if listening else "no está escuchando"
    return (
        f"{label} {state} en 127.0.0.1:{port}.",
        [
            _source(
                "socket TCP local",
                {"host": "127.0.0.1", "port": port, "listening": listening},
                "sin credencial; conexión TCP local",
                "connect_ex con tiempo límite de 1,5 segundos",
            )
        ],
    )


def _postgres() -> tuple[str, list[dict[str, Any]]]:
    status = sources.postgres_status()
    migration = sources.postgres_latest_migration()
    answer = (
        f"PostgreSQL responde en la base {status['database']} con versión "
        f"{status['version']}; la última migración registrada es "
        f"{migration['filename']} ({migration['applied_at']})."
    )
    return (
        answer,
        [
            _source(
                "PostgreSQL local",
                {"status": status, "latest_migration": migration},
                "usuario y base leídos del entorno del contenedor; valores ocultos",
                "Consultas SELECT de solo lectura dentro de lifeos_postgres.",
            )
        ],
    )


def _redis() -> tuple[str, list[dict[str, Any]]]:
    ping = sources.redis_ping()
    policy = sources.redis_config("maxmemory-policy")
    return (
        f"Redis responde {'PONG' if ping else 'sin PONG'} y su política actual es {policy}.",
        [
            _source(
                "Redis local",
                {"ping": ping, "maxmemory-policy": policy},
                "REDIS_URL existente en apps/api/.env; valor oculto",
                "redis-cli PING y CONFIG GET dentro de lifeos_redis.",
            )
        ],
    )


def _ollama() -> tuple[str, list[dict[str, Any]]]:
    state = sources.ollama_via_router()
    return (
        f"Ollama reporta la versión {state['version']} por el puerto {state['port']}.",
        [
            _source(
                "API de Ollama vía anythingllm-router",
                state,
                "sin credencial; URL leída del entorno del contenedor",
                "GET /api/version y GET /v1/models desde el contenedor del router.",
            )
        ],
    )


def _vercel() -> tuple[str, list[dict[str, Any]]]:
    deployment = sources.vercel_latest_production()
    credential = deployment.pop("credential")
    return (
        f"El último deployment de producción en Vercel está {deployment['state']} "
        f"y usa {deployment['id']} ({deployment['url']}).",
        [
            _source(
                "Vercel REST API",
                deployment,
                credential,
                "GET /v6/deployments para el proyecto tchasky-web y target production.",
            )
        ],
    )


def _railway() -> tuple[str, list[dict[str, Any]]]:
    deployment = sources.railway_latest_deployment()
    credential = deployment.pop("credential")
    return (
        f"El último deployment de producción en Railway está "
        f"{deployment['status']} y usa {deployment['id']}.",
        [
            _source(
                "Railway GraphQL API",
                deployment,
                credential,
                "Consulta deployments(first: 1) del servicio y entorno de producción.",
            )
        ],
    )


LIVE_HANDLERS: dict[str, Callable[[], tuple[str, list[dict[str, Any]]]]] = {
    "local_health": _local_health,
    "git_branch": _git_branch,
    "git_commit": _git_commit,
    "api_port": lambda: _port("La API local", 3001),
    "web_port": lambda: _port("La web local", 5173),
    "postgres": _postgres,
    "redis": _redis,
    "ollama": _ollama,
    "vercel": _vercel,
    "railway": _railway,
}


def answer_question(question: str) -> dict[str, Any]:
    decision = classify_question(question)
    result: dict[str, Any] = {
        "schema": "task124-answer-v1",
        "question": question,
        "routing": decision.as_dict(),
        "answered_at": sources.utc_now(),
    }
    if decision.route == ROUTE_RAG:
        result.update(
            {
                "status": "HANDOFF",
                "answer": "La pregunta debe continuar por el RAG documental vigente.",
                "sources": [],
            }
        )
        return result
    try:
        answer, evidence = LIVE_HANDLERS[decision.intent or ""]()
    except sources.SourceUnavailable as error:
        result.update(
            {
                "status": "SOURCE_UNAVAILABLE",
                "answer": f"La fuente viva no está disponible: {error}",
                "sources": [],
            }
        )
        return result
    result.update({"status": "ANSWERED", "answer": answer, "sources": evidence})
    return result


def render_text(result: dict[str, Any]) -> str:
    lines = [
        result["answer"],
        f"Ruta: {result['routing']['route']}",
        f"Marca de respuesta: {result['answered_at']}",
    ]
    for item in result.get("sources", []):
        lines.append(
            f"Fuente: {item['source']} | consultada: {item['collected_at']} | "
            f"credencial: {item['credential']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enruta una pregunta a fuentes vivas o al RAG"
    )
    parser.add_argument("question")
    parser.add_argument("--classify-only", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.classify_only:
        payload: dict[str, Any] = classify_question(args.question).as_dict()
    else:
        payload = answer_question(args.question)
    encoded = (
        render_text(payload)
        if args.format == "text" and not args.classify_only
        else json.dumps(payload, ensure_ascii=False, indent=2)
    )
    print(encoded)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if payload.get("status") != "SOURCE_UNAVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
