"""Indice de referencias del entorno V2: que archivo referencia que ruta.

Escanea los .md y los scripts (.ps1/.psm1/.py/.sh/.bat/.cmd) del framework y
extrae:
  - rutas absolutas C:\\AI_WORKFLOW_V2\\... (abs_v2) y C:\\AI_WORKFLOW_V2\\...
    (abs_orig -- deuda de aislamiento)
  - rutas relativas con prefijo de carpeta top-level real (rel)
  - links markdown [texto](ruta) relativos (mdlink)

Emite (JSON generado, spec seccion 0: con _meta completo, sin truncado):
  08_REPORTS/REFERENCE_INDEX/reference_index.json  -- el grafo crudo
  08_REPORTS/REFERENCE_INDEX/blast_radius.json     -- radio de explosion por
    carpeta top-level: cuantas referencias ENTRANTES se romperian al moverla

Determinismo: orden total (sort_keys + listas ordenadas), timestamps solo en
_meta. Dos corridas deben dar diff vacio salvo _meta.generated_at.

Decisiones documentadas:
  - Los [[wikilinks]] de Obsidian NO se indexan: 01_OBSIDIAN esta fuera de
    limites para la reorganizacion, sus links internos no son radio de
    explosion de las carpetas que si se mueven.
  - Exclusiones de directorios identicas al harness (dependencias
    reinstalables y 09_BACKUPS).
"""
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = r"C:\AI_WORKFLOW_V2"
OUT_DIR = os.path.join(ROOT, "08_REPORTS", "REFERENCE_INDEX")
EXCLUDE_DIRS = {"node_modules", "__pycache__", ".venv", "venv", ".git",
                "site-packages", "dist", "build", "09_BACKUPS", "12_ARCHIVE"}
DOC_EXTS = {".md"}
SCRIPT_EXTS = {".ps1", ".psm1", ".py", ".sh", ".bat", ".cmd"}

RE_ABS = re.compile(r"[Cc]:[\\/][A-Za-z0-9_\\/.\-]+")
RE_MDLINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")


def top_level_names():
    names = []
    for name in sorted(os.listdir(ROOT)):
        full = os.path.join(ROOT, name)
        if os.path.isdir(full) and name not in EXCLUDE_DIRS and name != "<PRIVATE_PROJECT>":
            names.append(name)
    return names


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS
                             and not os.path.islink(os.path.join(dirpath, d)))
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            if ext in DOC_EXTS or ext in SCRIPT_EXTS:
                yield os.path.join(dirpath, fn), ext


def norm_rel(path):
    return os.path.normpath(path).replace("/", "\\")


def classify_and_resolve(raw, src_dir, top_names):
    """Devuelve (kind, resolved_rel_or_abs, exists) o None si no es una ruta
    de este repo."""
    p = raw.strip().rstrip(".,;:)\"'`")
    if not p or "*" in p or "<" in p or ">" in p or "..." in p or "$" in p or "%" in p:
        return None
    low = p.lower().replace("/", "\\")
    if low.startswith("c:\\ai_workflow_v2\\"):
        rel = norm_rel(p[len("c:\\ai_workflow_v2\\"):])
        return ("abs_v2", rel, os.path.exists(os.path.join(ROOT, rel)))
    if low.startswith("c:\\ai_workflow\\"):
        return ("abs_orig", norm_rel(p), True)  # el original sigue vivo
    if low.startswith("c:\\"):
        return None  # otras rutas del sistema, no de este repo
    first = re.split(r"[\\/]", p, maxsplit=1)[0]
    if first in top_names or first in (".claude", ".ai"):
        rel = norm_rel(p)
        return ("rel", rel, os.path.exists(os.path.join(ROOT, rel)))
    return None


def resolve_mdlink(raw, src_dir, top_names):
    p = raw.strip()
    if (not p or p.startswith("#") or "://" in p or p.startswith("mailto:")
            or "*" in p or "<" in p or "$" in p or "%" in p):
        return None
    p = p.split("#", 1)[0]
    if not p:
        return None
    cand = os.path.normpath(os.path.join(src_dir, p))
    if cand.lower().startswith(ROOT.lower() + os.sep):
        rel = cand[len(ROOT) + 1:]
        return ("mdlink", norm_rel(rel), os.path.exists(cand))
    return classify_and_resolve(p, src_dir, top_names)


def main():
    top_names = top_level_names()
    index = {}
    n_docs = n_scripts = 0
    for full, ext in walk_files():
        rel_src = norm_rel(full[len(ROOT) + 1:])
        if ext in DOC_EXTS:
            n_docs += 1
        else:
            n_scripts += 1
        refs = {}
        try:
            with io.open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as e:
            index[rel_src] = {"error": str(e), "refs": []}
            continue
        src_dir = os.path.dirname(full)
        for m in RE_ABS.finditer(text):
            r = classify_and_resolve(m.group(0), src_dir, top_names)
            if r:
                refs[(r[0], r[1])] = r[2]
        if ext in DOC_EXTS:
            for m in RE_MDLINK.finditer(text):
                r = resolve_mdlink(m.group(1), src_dir, top_names)
                if r:
                    refs[(r[0], r[1])] = r[2]
        for m in re.finditer(
                r"(?<![\w\\/])((?:%s|\.claude|\.ai)[\\/][A-Za-z0-9_\\/.\-]+[A-Za-z0-9_\-])"
                % "|".join(re.escape(t) for t in top_names), text):
            r = classify_and_resolve(m.group(1), src_dir, top_names)
            if r:
                refs.setdefault((r[0], r[1]), r[2])
        if refs:
            index[rel_src] = [
                {"kind": k, "target": t, "exists": refs[(k, t)]}
                for (k, t) in sorted(refs)
            ]

    # --- radio de explosion por carpeta top-level ---------------------------
    blast = {}
    for src, refs in sorted(index.items()):
        if isinstance(refs, dict):
            continue
        for r in refs:
            if r["kind"] == "abs_orig":
                folder = "(C:\\AI_WORKFLOW_V2 original)"
            else:
                folder = r["target"].split("\\", 1)[0]
            b = blast.setdefault(folder, {"inbound_refs": 0, "sources": set()})
            b["inbound_refs"] += 1
            b["sources"].add(src)
    blast_out = {
        f: {"inbound_refs": v["inbound_refs"],
            "distinct_source_files": len(v["sources"]),
            "sources_sample": sorted(v["sources"])[:20]}
        for f, v in sorted(blast.items())
    }

    with io.open(__file__, "rb") as fh:
        gen_hash = hashlib.sha256(fh.read()).hexdigest()[:16]
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "06_AGENT_FRAMEWORK\\HARNESS\\build_reference_index.py",
        "generator_hash": gen_hash,
        "freshness": "derived",
        "docs_scanned": n_docs,
        "scripts_scanned": n_scripts,
        "files_with_refs": len(index),
        "truncated": False,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with io.open(os.path.join(OUT_DIR, "reference_index.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump({"_meta": meta, "index": index}, fh, ensure_ascii=False,
                  sort_keys=True, indent=1)
    with io.open(os.path.join(OUT_DIR, "blast_radius.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump({"_meta": meta, "blast_radius": blast_out}, fh,
                  ensure_ascii=False, sort_keys=True, indent=1)
    print("docs=%d scripts=%d files_with_refs=%d" % (n_docs, n_scripts, len(index)))
    for f, v in sorted(blast_out.items(), key=lambda kv: -kv[1]["inbound_refs"]):
        print("%-38s inbound=%-6d fuentes=%d" % (f, v["inbound_refs"], v["distinct_source_files"]))


if __name__ == "__main__":
    sys.exit(main())
