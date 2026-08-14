from __future__ import annotations

import argparse
import json
import math
import uuid
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
SOURCE_DIR = RAIZ / "storage" / "documents" / "bis-brain-2026-08-11"
OUTPUT_DIR = RAIZ / "storage" / "documents" / "bis-brain-2026-08-11-split"

# TASK-94 identifico cuatro documentos por encima de este umbral. El bloque
# resultante queda por debajo de EMBEDDING_MODEL_MAX_CHUNK_LENGTH=8192.
MIN_TOKENS = 50_000
CHUNK_CHARS = 20_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parte los documentos gigantes del corpus BIS_BRAIN V2."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula el plan sin crear los JSON de salida.",
    )
    return parser.parse_args()


def split_payload(source: Path, original: dict) -> tuple[list[dict], list[str]]:
    text = original["pageContent"]
    parts = [text[i : i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]
    payloads: list[dict] = []
    filenames: list[str] = []

    for idx, part in enumerate(parts, start=1):
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source.as_posix()}#part={idx}"))
        filename = f"{source.stem}-part{idx:03d}-{doc_id}.json"
        payload = {
            "id": doc_id,
            "url": original["url"],
            "title": f"{original['title']} (parte {idx}/{len(parts)})",
            "docAuthor": original["docAuthor"],
            "description": (
                f"{original['description']} — dividido por tamaño "
                f"(parte {idx}/{len(parts)})"
            ),
            "docSource": original["docSource"],
            "chunkSource": "",
            "published": original["published"],
            "wordCount": len(part.split()),
            "token_count_estimate": max(1, math.ceil(len(part) / 4)),
            "pageContent": part,
        }
        payloads.append(payload)
        filenames.append(filename)

    return payloads, filenames


def main() -> int:
    args = parse_args()
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"No existe el corpus de origen: {SOURCE_DIR}")

    selected: list[tuple[Path, dict]] = []
    for source in sorted(SOURCE_DIR.glob("*.json")):
        original = json.loads(source.read_text(encoding="utf-8"))
        if int(original.get("token_count_estimate") or 0) > MIN_TOKENS:
            selected.append((source, original))

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    adds: list[str] = []
    deletes: list[str] = []
    documents: list[dict] = []
    fragment_tokens: list[int] = []

    for source, original in selected:
        payloads, filenames = split_payload(source, original)
        for payload, filename in zip(payloads, filenames):
            if not args.dry_run:
                (OUTPUT_DIR / filename).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            adds.append(f"{OUTPUT_DIR.name}/{filename}")
            fragment_tokens.append(payload["token_count_estimate"])

        deletes.append(f"{SOURCE_DIR.name}/{source.name}")
        documents.append(
            {
                "title": original.get("title"),
                "source": f"{SOURCE_DIR.name}/{source.name}",
                "tokens_before": int(original.get("token_count_estimate") or 0),
                "fragments": len(payloads),
            }
        )

    result = {
        "dry_run": args.dry_run,
        "threshold_tokens": MIN_TOKENS,
        "chunk_chars": CHUNK_CHARS,
        "documents_split": len(documents),
        "fragments_created": len(adds),
        "fragment_tokens_max": max(fragment_tokens, default=0),
        "documents": documents,
        "adds": adds,
        "deletes": deletes,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
