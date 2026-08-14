import json
import math
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


SOURCE_ROOT = Path(r"C:\AI_WORKFLOW_V2\07_PROJECTS\TCHASKY\_DOCUMENTACION_CONSOLIDADA")
DOCS_FOLDER_NAME = "tchasky-consolidated-2026-07-19"
OUTPUT_ROOT = Path(r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM\storage\documents") / DOCS_FOLDER_NAME
MANIFEST_PATH = Path(r"C:\AI_WORKFLOW_V2\02_LOCAL_AI\ANYTHINGLLM") / "tchasky_corpus_import_manifest_2026-07-19.json"
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | {".docx"}


def load_existing_doc_sources() -> set[str]:
    existing = set()
    if not OUTPUT_ROOT.exists():
        return existing

    for path in OUTPUT_ROOT.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        doc_source = data.get("docSource")
        if doc_source:
            existing.add(doc_source)
    return existing


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_docx_text(path: Path) -> str:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)

    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        runs = []
        for node in paragraph.findall(".//w:t", namespace):
            if node.text:
                runs.append(node.text)
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def read_source_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return read_text_file(path)
    if suffix == ".docx":
        return read_docx_text(path)
    raise ValueError(f"Unsupported file type: {path}")


def build_record(path: Path, relative_source: str) -> tuple[str, dict]:
    content = read_source_text(path)
    word_count = len(content.split())
    token_estimate = max(1, math.ceil(len(content) / 4))
    doc_id = str(uuid.uuid4())
    filename = f"{path.name}-{doc_id}.json"

    record = {
        "id": doc_id,
        "url": f"file:///ai_workflow/tchasky_consolidated/{relative_source.replace('\\', '/')}",
        "title": path.name,
        "docAuthor": "Unknown",
        "description": f"Imported from consolidated Tchasky corpus: {relative_source}",
        "docSource": relative_source,
        "chunkSource": "",
        "published": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "wordCount": word_count,
        "pageContent": content,
        "token_count_estimate": token_estimate,
    }
    return filename, record


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    existing_sources = load_existing_doc_sources()

    generated = []
    skipped = []
    for source_path in sorted(SOURCE_ROOT.rglob("*")):
        if not source_path.is_file():
            continue
        if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        relative_source = source_path.relative_to(SOURCE_ROOT).as_posix()
        if relative_source in existing_sources:
            skipped.append(relative_source)
            continue

        filename, record = build_record(source_path, relative_source)
        output_path = OUTPUT_ROOT / filename
        output_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated.append(f"{DOCS_FOLDER_NAME}/{filename}")

    manifest = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "sourceRoot": str(SOURCE_ROOT),
        "outputFolder": str(OUTPUT_ROOT),
        "folderName": DOCS_FOLDER_NAME,
        "generatedCount": len(generated),
        "skippedExistingCount": len(skipped),
        "generatedDocpaths": generated,
        "skippedExistingDocSources": skipped,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
