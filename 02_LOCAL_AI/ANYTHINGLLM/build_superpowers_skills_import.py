from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

SKILLS_ROOT = Path(r"C:\AI_WORKFLOW_V2\11_LAB\superpowers_import\skills")
OUTPUT_DIR = Path(
    r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM\storage\documents\framework-skills-superpowers-2026-07-28"
)
MANIFEST_PATH = Path(
    r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM\framework_skills_superpowers_manifest_2026-07-28.json"
)


def build_doc_payload(source: Path) -> tuple[str, dict]:
    text = source.read_text(encoding="utf-8")
    relative_source = source.relative_to(SKILLS_ROOT.parent).as_posix()
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(source.resolve())))
    published = datetime.fromtimestamp(source.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    word_count = len(text.split())
    token_estimate = max(word_count * 2, len(text) // 4)
    filename = f"{source.stem}-{source.parent.name}-{doc_id}.json"
    payload = {
        "id": doc_id,
        "url": source.resolve().as_uri(),
        "title": f"{source.parent.name}/{source.name}",
        "docAuthor": "Jesse Vincent (obra/superpowers), MIT License",
        "description": f"Superpowers skill library: {relative_source}",
        "docSource": relative_source,
        "chunkSource": "",
        "published": published,
        "wordCount": word_count,
        "token_count_estimate": token_estimate,
        "pageContent": text,
    }
    return filename, payload


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "workspaceSlug": "framework-skills-superpowers",
        "documents": [],
    }
    for md_file in sorted(SKILLS_ROOT.rglob("*.md")):
        filename, payload = build_doc_payload(md_file)
        output_path = OUTPUT_DIR / filename
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["documents"].append(
            {
                "source": str(md_file),
                "relativeDocumentPath": f"framework-skills-superpowers-2026-07-28/{filename}",
                "title": payload["title"],
            }
        )
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(manifest["documents"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
