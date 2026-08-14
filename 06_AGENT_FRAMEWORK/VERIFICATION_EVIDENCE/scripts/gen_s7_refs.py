"""Genera los insumos crudos de S7: referencias al arbol viejo (C:\\AI_WORKFLOW
sin _V2, o /mnt/c/AI_WORKFLOW) en docs y scripts de V2. El juicio de que rompe
y que no lo ponen las IAs del cluster (TASK-4/TASK-5); esto es solo el dato."""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\AI_WORKFLOW_V2")
OUT = ROOT / "08_REPORTS" / "S7_PREP"
EXCLUDE = {".git", "node_modules", "__pycache__", ".venv", "venv",
           "site-packages", "dist", "build", "09_BACKUPS", "12_ARCHIVE",
           "source_repos", ".playwright-mcp"}
PAT = re.compile(r"(?:C:[\\/]+|/mnt/c/)AI_WORKFLOW(?!_V2)", re.IGNORECASE)
DOC_EXTS = {".md"}
SCRIPT_EXTS = {".ps1", ".psm1", ".py", ".sh"}


def scan():
    docs, scripts = [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE)
        for name in sorted(filenames):
            ext = Path(name).suffix.lower()
            if ext not in DOC_EXTS and ext not in SCRIPT_EXTS:
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith("08_REPORTS/S7_PREP/"):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                print(f"WARN no se pudo leer {rel}: {exc}", file=sys.stderr)
                continue
            # split("\n"), NUNCA splitlines(): splitlines corta ademas en form
            # feed, vertical tab, NEL y U+2028/29, asi que numera distinto que
            # grep, los editores y Get-Content. Un HALLAZGOS.md con dos form
            # feeds ya mandaba a S7 dos lineas mas abajo de la referencia real.
            for lineno, line in enumerate(text.split("\n"), 1):
                if PAT.search(line):
                    entry = f"{rel}:{lineno}: {line.strip()[:220]}"
                    (docs if ext in DOC_EXTS else scripts).append(entry)
    return docs, scripts


def write(path: Path, entries: list, label: str) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = sorted({e.split(":", 1)[0] for e in entries})
    header = [
        f"# Insumo crudo S7 — {label}",
        f"# generado: {now} por gen_s7_refs.py (orquestador, sesion S5)",
        f"# patron: C:\\AI_WORKFLOW o /mnt/c/AI_WORKFLOW SIN sufijo _V2",
        f"# total: {len(entries)} referencias en {len(files)} archivos",
        "",
    ]
    path.write_text("\n".join(header + entries) + "\n", encoding="utf-8", newline="\n")
    print(f"OK {path.name}: {len(entries)} refs en {len(files)} archivos")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    docs, scripts = scan()
    write(OUT / "refs_docs_raw.txt", docs, "referencias en DOCS (.md)")
    write(OUT / "refs_scripts_raw.txt", scripts, "referencias en SCRIPTS (.ps1/.psm1/.py/.sh)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
