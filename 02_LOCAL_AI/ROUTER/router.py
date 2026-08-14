#!/usr/bin/env python3
"""OpenAI-compatible failover router for AnythingLLM answer generation.

It deliberately logs only provider, duration and outcome: never prompts,
responses, headers or credentials.
"""
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.getenv("ROUTER_PORT", "8080"))
# Los remotos se cortan pronto para reservar el presupuesto de la petición RAG
# para Ollama, el respaldo inmediato. La medición RAG local fue 52 s; 120 s deja
# 68 s de margen ante variación de carga sin convertir un fallo remoto en espera.
REMOTE_TIMEOUT_SECONDS = float(os.getenv("ROUTER_REMOTE_TIMEOUT_SECONDS", os.getenv("ROUTER_TIMEOUT_SECONDS", "8")))
LOCAL_TIMEOUT_SECONDS = float(os.getenv("ROUTER_LOCAL_TIMEOUT_SECONDS", "120"))
NVIDIA_PROBE_INTERVAL_SECONDS = int(os.getenv("ROUTER_NVIDIA_PROBE_INTERVAL_SECONDS", "300"))
LOG_PATH = os.getenv("ROUTER_LOG_PATH", "/tmp/notes-router.jsonl")
NVIDIA_HEALTH = {"checked_at": 0.0, "available": False, "reason": "not_checked"}


def default_ollama_chat_url():
    """Construye la URL de Ollama accesible desde Docker mediante OLLAMA_HOST."""
    host = os.getenv("OLLAMA_HOST", "host.docker.internal:11434").strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host + "/v1/chat/completions"


def key_from_file(variable):
    """Read either KEY=value or a bare key, without reporting its value."""
    path = os.getenv(variable, "")
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as source:
            value = source.read().strip()
    except OSError:
        return ""
    if "=" in value:
        value = value.split("=", 1)[1].strip().strip("\"'")
    return value


def log_event(**event):
    event["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG_PATH, "a", encoding="utf-8") as target:
        target.write(json.dumps(event, separators=(",", ":")) + "\n")


def normalize_openai_response(payload):
    """Make reasoning-only OpenAI dialect responses consumable by AnythingLLM.

    Ollama may put a useful answer in a reasoning extension while leaving
    ``message.content`` empty. The public OpenAI-compatible response still
    needs content, so promote that text without judging its quality.
    """
    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return payload
    for field in ("reasoning", "reasoning_content", "analysis"):
        fallback = message.get(field)
        if isinstance(fallback, str) and fallback.strip():
            message["content"] = fallback
            return payload
    return None


def is_valid_openai_response(payload):
    return normalize_openai_response(payload) is not None


def post_json(url, body, headers, timeout_seconds):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
        return None, str(error)
    if status < 200 or status >= 300 or not normalize_openai_response(payload):
        return None, "invalid_or_empty_openai_response"
    return payload, None


class Provider:
    def __init__(self, name, enabled, request_fn):
        self.name = name
        self.enabled = enabled
        self.request_fn = request_fn

    def complete(self, request_body):
        started = time.monotonic()
        if not self.enabled():
            return None, "sin_clave_configurada", round((time.monotonic() - started) * 1000)
        payload, error = self.request_fn(request_body)
        return payload, error, round((time.monotonic() - started) * 1000)


def openai_provider(name, url, model, key_variable=None, timeout_seconds=REMOTE_TIMEOUT_SECONDS):
    def enabled():
        return key_variable is None or bool(key_from_file(key_variable))

    def request_fn(incoming):
        body = {key: value for key, value in incoming.items() if key not in {"stream", "model"}}
        body.update({"model": model, "stream": False})
        headers = {"Content-Type": "application/json"}
        if key_variable:
            headers["Authorization"] = "Bearer " + key_from_file(key_variable)
        return post_json(url, body, headers, timeout_seconds)
    return Provider(name, enabled, request_fn)


def anthropic_provider():
    def enabled():
        return bool(key_from_file("ROUTER_ANTHROPIC_KEY_FILE"))

    def request_fn(incoming):
        messages = incoming.get("messages", [])
        system = "\n".join(item.get("content", "") for item in messages if item.get("role") == "system")
        body = {
            "model": os.getenv("ROUTER_ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            "max_tokens": incoming.get("max_tokens", 1024),
            "messages": [item for item in messages if item.get("role") != "system"],
        }
        if system:
            body["system"] = system
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-api-key": key_from_file("ROUTER_ANTHROPIC_KEY_FILE"), "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REMOTE_TIMEOUT_SECONDS) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = result["content"][0]["text"]
            payload = {"id": result.get("id", "anthropic-router"), "object": "chat.completion", "created": int(time.time()), "model": result.get("model", body["model"]), "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": result.get("stop_reason", "stop")}]} 
            return (payload, None) if is_valid_openai_response(payload) else (None, "invalid_or_empty_openai_response")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as error:
            return None, str(error)
    return Provider("claude", enabled, request_fn)


def providers():
    nvidia = openai_provider("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", os.getenv("ROUTER_NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"), "ROUTER_NVIDIA_KEY_FILE")
    original_enabled = nvidia.enabled

    def nvidia_enabled():
        now = time.monotonic()
        if not original_enabled():
            NVIDIA_HEALTH.update(checked_at=now, available=False, reason="sin_clave_configurada")
            return False
        if now - NVIDIA_HEALTH["checked_at"] >= NVIDIA_PROBE_INTERVAL_SECONDS:
            probe = {"messages": [{"role": "user", "content": "Responde exactamente: ROUTER_NVIDIA_OK"}]}
            payload, error = nvidia.request_fn(probe)
            NVIDIA_HEALTH.update(checked_at=now, available=bool(payload), reason=error or "ok")
            log_event(provider="nvidia", elapsed_ms=0, outcome="probe_success" if payload else "probe_failure", reason=error)
        return NVIDIA_HEALTH["available"]

    nvidia.enabled = nvidia_enabled
    return [
        # TEMPORAL — pedido explicito del fundador el 2026-08-13 14:03: NVIDIA
        # primero porque necesita velocidad ahora. Medido: NVIDIA 1,7 s, Gemini
        # 1,9 s, local 4,9 s.
        #
        # VUELVE A SU LUGAR CUANDO EL FUNDADOR LO REVOQUE. Para revertir, mover
        # `nvidia` al final de esta lista y reconstruir. El orden original ponia
        # lo local antes que lo remoto a proposito: privacidad (la consulta no
        # sale de la maquina) y cupo (NVIDIA y Gemini tienen limite diario).
        nvidia,
        openai_provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", os.getenv("ROUTER_GEMINI_MODEL", "gemini-3.5-flash"), "ROUTER_GEMINI_KEY_FILE"),
        # Gemini tiene un cupo diario bajo: el modelo local es el respaldo final.
        openai_provider("local", os.getenv("ROUTER_OLLAMA_URL", default_ollama_chat_url()), os.getenv("ROUTER_OLLAMA_MODEL", "qwen2.5:3b-instruct"), timeout_seconds=LOCAL_TIMEOUT_SECONDS),
    ]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path == "/healthz":
            self.respond(200, {"status": "ok", "providers": [provider.name for provider in providers()]})
        else:
            self.respond(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.respond(404, {"error": "not_found"})
        try:
            incoming = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self.respond(400, {"error": "invalid_json"})
        for provider in providers():
            payload, error, elapsed_ms = provider.complete(incoming)
            log_event(provider=provider.name, elapsed_ms=elapsed_ms, outcome="success" if payload else "failure", reason=error)
            if payload:
                if incoming.get("stream") is True:
                    return self.respond_stream(payload)
                return self.respond(200, payload)
        self.respond(503, {"error": {"message": "all providers failed", "type": "router_unavailable"}})

    def respond(self, status, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def respond_stream(self, payload):
        """Translate a completed fallback response into OpenAI-compatible SSE."""
        choice = payload["choices"][0]
        chunk = {
            "id": payload.get("id", "router-stream"),
            "object": "chat.completion.chunk",
            "created": payload.get("created", int(time.time())),
            "model": payload.get("model", "router/auto"),
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": choice["message"]["content"]}, "finish_reason": choice.get("finish_reason", "stop")}],
        }
        body = ("data: " + json.dumps(chunk) + "\n\n" + "data: [DONE]\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
