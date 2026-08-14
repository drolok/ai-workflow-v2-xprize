#!/usr/bin/env python3
"""Generadores del Control Plane -- reescritura de S2 (2026-08-10).

Emite los 6 registries a .ai/generated/*.json + INVENTORY_MANIFEST.json.

Reglas que gobiernan este archivo (SPEC_CONTRATOS_V1 seccion 0 + decisiones
del fundador):
  - SIN TRUNCADO. No hay MAX_* ni timeouts de descubrimiento. Si un dia hay
    que cortar algo, el corte va declarado en el manifest Y avisado por
    stdout -- nunca escondido. (Los generadores anteriores murieron por
    MAX_SCRIPTS=10, MAX_PLUGINS=5 y un rg con timeout de 3s.)
  - Presupuesto de tiempo DECLARADO: TIME_BUDGET_SECONDS. Si se supera, el
    manifest lo marca y stdout lo grita, pero NO se trunca.
  - Todo artefacto lleva _meta: generated_at, generator, generator_hash,
    inputs_hash, items_hash, item_count, freshness, truncated.
  - Determinismo byte a byte: si items_hash + inputs_hash + generator_hash
    no cambiaron respecto del archivo anterior, se PRESERVA su generated_at
    -- dos corridas sin cambios producen archivos identicos, incluido el
    timestamp. "Salvo timestamps" ya no hace falta como excusa.
  - JSON para lo generado (decision 8). sort_keys + indent=1 + \n.
  - stdlib puro. Corre con el python de Windows (3.13).

Fuentes por registry (heredadas de la auditoria de los generadores viejos,
que tenian las fuentes bien y los topes mal):
  SCRIPTS  : arbol de V2, extensiones de script, exclusiones = las del harness.
  SKILLS   : ~/.claude/skills (SKILL.md recursivo + *.md sueltos) + skills/*/
             SKILL.md de TODOS los snapshots de plugins cacheados.
  PLUGINS  : TODOS los snapshots nombre/revision de la cache de plugins.
  AGENTS   : .claude/agents de V2 + ~/.claude/agents (el generador viejo no
             lo miraba: por eso AGENTS=0) + agents/*.md de TODOS los plugins.
  MCP      : settings.json de V2 y del usuario + configs de TODOS los plugins.
  SERVICES : evidencia documental (patron por servicio) sobre TODOS los .md
             de 00_COMMAND_CENTER y 06_AGENT_FRAMEWORK + .env.example + los
             dos settings.json.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".ai" / "generated"
USER_CLAUDE = Path.home() / ".claude"
PLUGIN_CACHE = USER_CLAUDE / "plugins" / "cache" / "claude-plugins-official"
LOCAL_SKILLS = USER_CLAUDE / "skills"

TIME_BUDGET_SECONDS = 600  # presupuesto declarado; superarlo se reporta, no se trunca

EXCLUDE_DIRS = {"node_modules", "__pycache__", ".venv", "venv", ".git",
                "site-packages", "dist", "build", "09_BACKUPS", "12_ARCHIVE",
                "source_repos"}
SCRIPT_EXTS = {".ps1": "powershell", ".psm1": "powershell", ".py": "python",
               ".sh": "shell", ".bat": "batch", ".cmd": "batch"}
SERVICE_PATTERNS = {
    "railway": r"\brailway\b", "vercel": r"\bvercel\b", "sentry": r"\bsentry\b",
    "expo": r"\bexpo\b", "posthog": r"\bposthog\b", "github": r"\bgithub\b",
    "postgres": r"\b(postgres|postgresql)\b", "redis": r"\bredis\b",
    "culqi": r"\bculqi\b", "mercado-pago": r"\b(mercado[ _-]?pago|mercadopago)\b",
    "docker": r"\bdocker\b", "anythingllm": r"\banything\s?llm\b",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    p = path.resolve()
    for base, prefix in ((ROOT, ""), (USER_CLAUDE, "~/.claude/")):
        try:
            return prefix + p.relative_to(base).as_posix()
        except ValueError:
            continue
    return p.as_posix()


def stable_id(*parts: str) -> str:
    value = "-".join(str(p) for p in parts if p)
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-.")


def read_lines(path: Path, limit: int) -> list[str]:
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return [fh.readline() for _ in range(limit)]


def frontmatter(path: Path) -> dict:
    lines = read_lines(path, 80)
    if not lines or lines[0].strip() != "---":
        return {}
    result = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$", line)
        if m:
            result[m.group(1)] = m.group(2).strip("\"'")
    return result


def first_comment(path: Path) -> str:
    ext = path.suffix.lower()
    for line in read_lines(path, 40):
        s = line.strip()
        if not s:
            continue
        if ext == ".py" and (s.startswith('"""') or s.startswith("'''")):
            return s.strip("'\" ")
        if ext in (".ps1", ".psm1", ".sh") and s.startswith("#") and not s.startswith("#!"):
            return s.lstrip("# ").strip()
        if ext in (".bat", ".cmd") and (s.lower().startswith("rem ") or s.startswith("::")):
            return s[3:].strip() if s.startswith("::") else s[4:].strip()
    return ""


def walk_v2_scripts():
    stack = [ROOT]
    while stack:
        d = stack.pop()
        try:
            for entry in sorted(os.scandir(d), key=lambda e: e.name.lower()):
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in EXCLUDE_DIRS:
                        stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    if os.path.splitext(entry.name)[1].lower() in SCRIPT_EXTS:
                        yield Path(entry.path)
        except OSError:
            continue


def plugin_roots() -> list[tuple[str, str, Path]]:
    """TODOS los snapshots nombre/revision. Sin max_items: ese parametro fue
    exactamente el tope que dejo PLUGINS en 5 de 274."""
    if not PLUGIN_CACHE.is_dir():
        return []
    result = []
    for plugin_dir in sorted((p for p in PLUGIN_CACHE.iterdir() if p.is_dir()),
                             key=lambda p: p.name.lower()):
        for revision in sorted((p for p in plugin_dir.iterdir() if p.is_dir()),
                               key=lambda p: p.name.lower()):
            result.append((plugin_dir.name, revision.name, revision))
    return result


# --- scanners ---------------------------------------------------------------

def scan_scripts():
    items, inputs = [], []
    for path in sorted(walk_v2_scripts(), key=lambda p: p.as_posix().lower()):
        inputs.append(path)
        items.append({
            "id": stable_id(rel(path)),
            "path": rel(path),
            "language": SCRIPT_EXTS[path.suffix.lower()],
            "size_bytes": path.stat().st_size,
            "content_hash": sha256_file(path),
            "description": first_comment(path),
            "source": "filesystem",
        })
    return items, inputs


def scan_skills():
    candidates = []
    if LOCAL_SKILLS.is_dir():
        for cur, dirs, files in os.walk(LOCAL_SKILLS):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
            for name in sorted(files):
                if name == "SKILL.md":
                    candidates.append((Path(cur) / name, "local", ""))
        for p in sorted(LOCAL_SKILLS.glob("*.md")):
            if p.is_file() and p.name != "SKILL.md":
                candidates.append((p, "local", ""))
    for plugin, revision, root in plugin_roots():
        skills_dir = root / "skills"
        if skills_dir.is_dir():
            for p in sorted(skills_dir.glob("*/SKILL.md"), key=lambda p: p.as_posix().lower()):
                candidates.append((p, plugin, revision))
    items, inputs = [], []
    for path, plugin, revision in candidates:
        meta = frontmatter(path)
        name = str(meta.get("name") or (path.parent.name if path.name == "SKILL.md" else path.stem))
        inputs.append(path)
        items.append({
            "id": stable_id(plugin, revision, name),
            "name": name,
            "plugin": plugin,
            "path": rel(path),
            "description": str(meta.get("description", "")),
            "content_hash": sha256_file(path),
            "source": "plugin_skill" if plugin != "local" else "local_skill",
        })
    return items, inputs


def scan_plugins():
    items, inputs = [], []
    for name, revision, root in plugin_roots():
        manifest = {}
        manifest_path = None
        for cand in (root / ".claude-plugin" / "plugin.json",
                     root / ".claude-plugin" / "manifest.json"):
            if cand.is_file():
                try:
                    manifest = json.loads(cand.read_text(encoding="utf-8"))
                    manifest_path = cand
                    break
                except (OSError, json.JSONDecodeError):
                    continue
        if manifest_path:
            inputs.append(manifest_path)
        structure = {c: (root / c).is_dir() for c in ("skills", "agents", "commands", "hooks")}
        content = json.dumps([manifest, structure], sort_keys=True)
        items.append({
            "id": stable_id(name, revision),
            "name": str(manifest.get("name") or name),
            "revision": revision,
            "version": str(manifest.get("version") or ""),
            "description": str(manifest.get("description") or ""),
            "path": rel(root),
            "has_skills": structure["skills"],
            "has_agents": structure["agents"],
            "has_commands": structure["commands"],
            "has_hooks": structure["hooks"],
            "content_hash": sha256_bytes(content.encode()),
            "source": "plugin_manifest" if manifest else "plugin_structure",
        })
    return items, inputs


def scan_agents():
    paths = []
    for base, source in ((ROOT / ".claude" / "agents", "project_agent"),
                         (USER_CLAUDE / "agents", "user_agent")):
        if base.is_dir():
            paths.extend((p, "local", source) for p in sorted(base.rglob("*.md")))
    for plugin, revision, root in plugin_roots():
        agents_dir = root / "agents"
        if agents_dir.is_dir():
            paths.extend((p, plugin, "plugin_agent")
                         for p in sorted(agents_dir.glob("*.md"), key=lambda p: p.as_posix().lower()))
    items, inputs = [], []
    for path, plugin, source in paths:
        meta = frontmatter(path)
        name = str(meta.get("name") or path.stem)
        tools = meta.get("tools", meta.get("allowed-tools", ""))
        inputs.append(path)
        items.append({
            "id": stable_id(plugin, source, name),
            "name": name,
            "plugin": plugin,
            "path": rel(path),
            "description": str(meta.get("description", ""))[:300],
            "tools": str(tools),
            "content_hash": sha256_file(path),
            "source": source,
        })
    return items, inputs


def scan_mcp():
    paths = [ROOT / ".claude" / "settings.json", USER_CLAUDE / "settings.json"]
    for _, _, root in plugin_roots():
        for cand in (root / ".mcp.json", root / "mcp.json",
                     root / ".claude-plugin" / "plugin.json",
                     root / ".claude-plugin" / "manifest.json"):
            if cand.is_file():
                paths.append(cand)
    items, inputs = [], []
    for path in sorted(set(paths), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        servers = {}
        if isinstance(data, dict):
            for key in ("mcpServers", "mcp_servers"):
                if isinstance(data.get(key), dict):
                    servers = data[key]
        if not servers:
            continue
        inputs.append(path)
        try:
            plugin = path.resolve().relative_to(PLUGIN_CACHE.resolve()).parts[0]
        except ValueError:
            plugin = "local"
        for name, config in sorted(servers.items()):
            config = config if isinstance(config, dict) else {}
            transport = ("stdio" if any(k in config for k in ("command", "args"))
                         else "http" if any(k in config for k in ("url", "endpoint"))
                         else "no_verificado")
            items.append({
                "id": stable_id(plugin, str(name)),
                "name": str(name),
                "plugin": plugin,
                "path": rel(path),
                "transport": transport,
                "requires_auth": any(k in config for k in ("env", "headers", "token", "apiKey", "api_key")),
                "content_hash": sha256_bytes(json.dumps(config, sort_keys=True).encode()),
                "source": "plugin_mcp_config" if plugin != "local" else "settings_mcp",
            })
    return items, inputs


def scan_services():
    paths = []
    for base in (ROOT / "00_COMMAND_CENTER", ROOT / "06_AGENT_FRAMEWORK"):
        for cur, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
            for name in sorted(files):
                if name.endswith(".md"):
                    paths.append(Path(cur) / name)
    for cur, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        if ".env.example" in files:
            paths.append(Path(cur) / ".env.example")
    paths += [ROOT / ".claude" / "settings.json", USER_CLAUDE / "settings.json"]
    evidence = {name: [] for name in SERVICE_PATTERNS}
    scanned = []
    for path in sorted(set(paths), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned.append(path)
        for name, pattern in SERVICE_PATTERNS.items():
            if re.search(pattern, text, flags=re.I):
                evidence[name].append(path)
    items = []
    for name, hits in evidence.items():
        if not hits:
            continue
        unique = sorted(set(hits), key=lambda p: p.as_posix().lower())
        items.append({
            "id": stable_id(name),
            "name": name,
            "evidence_count": len(unique),
            "evidence_sample": [rel(p) for p in unique[:10]],
            "content_hash": sha256_bytes("\n".join(rel(p) for p in unique).encode()),
            "source": "documented_evidence",
        })
    return items, scanned


# --- emision -----------------------------------------------------------------

REGISTRIES = {
    "SCRIPTS": scan_scripts, "SKILLS": scan_skills, "PLUGINS": scan_plugins,
    "AGENTS": scan_agents, "MCP": scan_mcp, "SERVICES": scan_services,
}


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)


def previous_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("_meta", {})
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    started = time.monotonic()
    with io.open(__file__, "rb") as fh:
        generator_hash = sha256_bytes(fh.read())
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_registries = {}
    counts = {}
    for name, scanner in REGISTRIES.items():
        t0 = time.monotonic()
        items, inputs = scanner()
        items = sorted(items, key=lambda i: (i["id"], i.get("path", "")))
        items_hash = sha256_bytes(canonical(items).encode())
        inputs_hash = sha256_bytes("\n".join(sorted(rel(p) for p in set(inputs))).encode())
        out_path = OUT / f"{name}.json"
        prev = previous_meta(out_path)
        unchanged = (prev.get("items_hash") == items_hash
                     and prev.get("inputs_hash") == inputs_hash
                     and prev.get("generator_hash") == generator_hash)
        meta = {
            "registry": name,
            "generated_at": prev.get("generated_at") if unchanged else now,
            "generator": ".ai/bin/build_registries.py",
            "generator_hash": generator_hash,
            "inputs_hash": inputs_hash,
            "items_hash": items_hash,
            "item_count": len(items),
            "freshness": "derived",
            "truncated": False,
        }
        write_if_changed(out_path, canonical({"_meta": meta, "items": items}))
        manifest_registries[name] = {k: meta[k] for k in
                                     ("generated_at", "generator_hash", "inputs_hash",
                                      "items_hash", "item_count", "truncated")}
        counts[name] = len(items)
        print("%-8s %5d items en %5.1fs" % (name, len(items), time.monotonic() - t0), flush=True)

    elapsed = time.monotonic() - started
    manifest_path = OUT / "INVENTORY_MANIFEST.json"
    prev_manifest = {}
    if manifest_path.exists():
        try:
            prev_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    manifest = {
        "_meta": {
            "generated_at": (prev_manifest.get("_meta", {}).get("generated_at")
                             if prev_manifest.get("registries") == manifest_registries else now),
            "generator": ".ai/bin/build_registries.py",
            "generator_hash": generator_hash,
            "freshness": "derived",
            "time_budget_seconds": TIME_BUDGET_SECONDS,
            "budget_exceeded": elapsed > TIME_BUDGET_SECONDS,
        },
        "registries": manifest_registries,
        "schema_version": 2,
    }
    write_if_changed(manifest_path, canonical(manifest))
    print("TOTAL %.1fs (presupuesto %ds)%s" % (
        elapsed, TIME_BUDGET_SECONDS,
        "  *** PRESUPUESTO SUPERADO -- NO se trunco nada, optimizar ***" if elapsed > TIME_BUDGET_SECONDS else ""))
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
