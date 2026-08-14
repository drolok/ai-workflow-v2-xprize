from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path

from docling.document_converter import DocumentConverter


def convert_file(input_path: Path, output_dir: Path) -> Path:
    converter = DocumentConverter()
    result = converter.convert(str(input_path))
    markdown_body = result.document.export_to_markdown()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.md"

    header = [
        f"# Extracted Markdown: {input_path.name}",
        "",
        f"- Source file: `{input_path}`",
        f"- Extracted with: `Docling {version('docling')}`",
        "",
        "## Content",
        "",
    ]

    output_path.write_text("\n".join(header) + markdown_body, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert documents to Markdown with Docling.")
    parser.add_argument("inputs", nargs="+", help="One or more input files to convert.")
    parser.add_argument("--output-dir", required=True, help="Directory where Markdown files will be written.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    for raw_input in args.inputs:
        path = Path(raw_input)
        if not path.exists():
            raise FileNotFoundError(f"Input not found: {path}")
        output = convert_file(path, output_dir)
        print(output)


if __name__ == "__main__":
    main()
