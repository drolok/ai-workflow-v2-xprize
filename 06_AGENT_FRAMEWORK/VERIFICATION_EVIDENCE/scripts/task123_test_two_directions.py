#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba reversible del contrato de TASK-123 en las dos direcciones."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))
import task123_verify_grounds as verifier  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    result = subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode:
        raise RuntimeError(f"Fallo {' '.join(args)}: {result.stderr.strip()}")


def write_fixture(path: Path, repo: Path, expected_branch: str) -> None:
    anchor = {
        "id": "task123_test.branch",
        "claim": f"La rama actual es {expected_branch}",
        "check": "git_current_branch",
        "repo": str(repo),
        "expected": expected_branch,
    }
    encoded = json.dumps(json.dumps(anchor, ensure_ascii=False), ensure_ascii=False)
    path.write_text(
        "\n".join(
            [
                "---",
                'type: "operational"',
                'key: "task123_test"',
                'namespace: "task123.test"',
                'verified: "2026-08-14"',
                "stale_after: null",
                "sources:",
                '  - "repositorio Git aislado de prueba"',
                "grounds_to:",
                f"  - {encoded}",
                "---",
                "# Documento de prueba TASK-123",
                "",
            ]
        ),
        encoding="utf-8",
    )


def status(path: Path) -> str:
    payload = verifier.verify([str(path)])
    results = payload["results"]
    if len(results) != 1:
        raise RuntimeError(f"Se esperaba una afirmación, se obtuvieron {len(results)}")
    return results[0]["status"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba TASK-123 en ambas direcciones")
    parser.add_argument(
        "--output",
        default=str(WORKSPACE / ".ai" / "state" / "task123_two_direction_test.json"),
    )
    args = parser.parse_args()
    started = time.perf_counter()
    evidence: dict[str, object] = {
        "schema": "task123-two-direction-test-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_direction": {},
        "document_direction": {},
    }
    with tempfile.TemporaryDirectory(prefix="task123_ground_test_") as raw_tmp:
        root = Path(raw_tmp)
        repo = root / "repo"
        repo.mkdir()
        run("git", "init", "-b", "main", cwd=repo)
        run("git", "config", "user.name", "TASK-123 Test", cwd=repo)
        run("git", "config", "user.email", "task123-test@example.invalid", cwd=repo)
        (repo / "evidence.txt").write_text("base\n", encoding="utf-8")
        run("git", "add", "evidence.txt", cwd=repo)
        run("git", "commit", "-m", "base", cwd=repo)
        document = root / "task123_test_document.md"

        # Dirección 1: el documento no cambia; cambia Git al crear/cambiar de rama.
        write_fixture(document, repo, "main")
        before = status(document)
        run("git", "switch", "-c", "task123-system-drift", cwd=repo)
        after_system_change = status(document)
        run("git", "switch", "main", cwd=repo)
        system_passed = before == "VERDADERO" and after_system_change == "FALSO"
        evidence["system_direction"] = {
            "change": "git switch -c task123-system-drift en repositorio temporal aislado",
            "document_modified_between_checks": False,
            "before": before,
            "after": after_system_change,
            "passed": system_passed,
        }

        # Dirección 2: el sistema queda en main; se falsea solo la afirmación.
        write_fixture(document, repo, "rama-documentada-incorrecta")
        after_document_change = status(document)
        document_passed = after_document_change == "FALSO"
        evidence["document_direction"] = {
            "change": "expected de grounds_to alterado a rama-documentada-incorrecta",
            "system_branch": "main",
            "after": after_document_change,
            "passed": document_passed,
        }

    evidence["passed"] = bool(system_passed and document_passed)
    evidence["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "TASK-123 dos direcciones: "
        f"sistema={'APRUEBA' if system_passed else 'FALLA'}, "
        f"documento={'APRUEBA' if document_passed else 'FALLA'} "
        f"({evidence['duration_ms']:.1f} ms)"
    )
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
