from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path


AI_ROOT = Path(r"C:\AI_WORKFLOW")
PHASE4_ROOT = AI_ROOT / "04_DOCUMENT_PROCESSING"
DOCLING_PYTHON = PHASE4_ROOT / ".venv" / "Scripts" / "python.exe"
DOCLING_SCRIPT = PHASE4_ROOT / "DOCLING" / "convert_with_docling.py"
OCR_SCRIPT = PHASE4_ROOT / "OCR" / "ocr_with_tesseract.ps1"
WHISPER_SCRIPT = PHASE4_ROOT / "WHISPER" / "transcribe_with_whisper.ps1"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

DOC_SUFFIXES = {".pdf", ".docx", ".pptx"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".ogg", ".flac"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 4 document ingestion pipeline in a non-destructive way.")
    parser.add_argument(
        "--source-dir",
        default=str(PHASE4_ROOT / "00_Inbox"),
        help="Directory containing synthetic input files.",
    )
    parser.add_argument(
        "--run-label",
        default=f"phase5_{dt.datetime.now():%Y%m%d_%H%M%S}",
        help="Label used to isolate outputs.",
    )
    parser.add_argument(
        "--glob",
        default="*",
        help="Only process files matching this glob inside the source directory.",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Glob pattern to exclude from the selected inputs. Can be used multiple times.",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    selected_inputs = sorted(
        path for path in source_dir.glob(args.glob)
        if path.is_file()
    )
    if args.exclude_glob:
        excluded = set()
        for pattern in args.exclude_glob:
            excluded.update(path.resolve() for path in source_dir.glob(pattern) if path.is_file())
        selected_inputs = [path for path in selected_inputs if path.resolve() not in excluded]

    markdown_dir = PHASE4_ROOT / "Markdown_Output" / f"ingest_{args.run_label}"
    processed_dir = PHASE4_ROOT / "Processed" / f"ingest_{args.run_label}"
    staging_dir = processed_dir / "staging"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str]] = []

    doc_inputs = sorted(path for path in selected_inputs if path.suffix.lower() in DOC_SUFFIXES)
    if doc_inputs:
        command = [str(DOCLING_PYTHON), str(DOCLING_SCRIPT), *[str(path) for path in doc_inputs], "--output-dir", str(markdown_dir)]
        result = run_command(command)
        manifest.append(
            {
                "stage": "docling",
                "status": "OK" if result.returncode == 0 else "FAIL",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )

    for source_path in sorted(path for path in selected_inputs if path.suffix.lower() in AUDIO_SUFFIXES):
        staged = staging_dir / f"{source_path.stem}__{args.run_label}{source_path.suffix}"
        shutil.copy2(source_path, staged)
        output_md = markdown_dir / f"{staged.stem}.md"
        command = [
            str(POWERSHELL),
            "-NoProfile",
            "-File",
            str(WHISPER_SCRIPT),
            "-AudioPath",
            str(staged),
            "-OutputMarkdownPath",
            str(output_md),
        ]
        result = run_command(command)
        raw_txt = PHASE4_ROOT / "Processed" / f"{staged.stem}_whisper.txt"
        if raw_txt.exists():
            shutil.move(str(raw_txt), processed_dir / raw_txt.name)
        manifest.append(
            {
                "stage": "whisper",
                "source": str(source_path),
                "staged_source": str(staged),
                "output_markdown": str(output_md),
                "status": "OK" if result.returncode == 0 else "FAIL",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )

    for source_path in sorted(path for path in selected_inputs if path.suffix.lower() in IMAGE_SUFFIXES):
        staged = staging_dir / f"{source_path.stem}__{args.run_label}{source_path.suffix}"
        shutil.copy2(source_path, staged)
        output_md = markdown_dir / f"{staged.stem}.md"
        command = [
            str(POWERSHELL),
            "-NoProfile",
            "-File",
            str(OCR_SCRIPT),
            "-ImagePath",
            str(staged),
            "-OutputMarkdownPath",
            str(output_md),
        ]
        result = run_command(command)
        raw_txt = PHASE4_ROOT / "Processed" / f"{staged.stem}_ocr.txt"
        if raw_txt.exists():
            shutil.move(str(raw_txt), processed_dir / raw_txt.name)
        manifest.append(
            {
                "stage": "ocr",
                "source": str(source_path),
                "staged_source": str(staged),
                "output_markdown": str(output_md),
                "status": "OK" if result.returncode == 0 else "FAIL",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )

    manifest_path = processed_dir / "manifest.json"
    manifest_md_path = processed_dir / "manifest.md"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Document Ingest Run",
        "",
        f"- Source dir: `{source_dir}`",
        f"- Run label: `{args.run_label}`",
        f"- Markdown dir: `{markdown_dir}`",
        f"- Processed dir: `{processed_dir}`",
        "",
        "## Steps",
        "",
    ]
    for row in manifest:
        lines.extend(
            [
                f"- `{row.get('stage', '-')}` -> {row.get('status', '-')}",
                f"  stdout: `{row.get('stdout', '')[:180]}`",
                f"  stderr: `{row.get('stderr', '')[:180]}`",
            ]
        )

    manifest_md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Source dir: {source_dir}")
    print(f"Run label: {args.run_label}")
    print(f"Markdown dir: {markdown_dir}")
    print(f"Processed dir: {processed_dir}")
    print(f"Manifest JSON: {manifest_path}")
    print(f"Manifest MD: {manifest_md_path}")
    for row in manifest:
        print(f"{row.get('stage')}: {row.get('status')}")


if __name__ == "__main__":
    main()
