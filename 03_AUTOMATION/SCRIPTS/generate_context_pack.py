from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def render_list(items: list[str]) -> str:
    if not items:
        return "- [none]"
    return "\n".join(f"- {item}" for item in items)


def summarize_project(root: Path) -> dict:
    files = [path for path in root.rglob("*") if path.is_file()]
    folders = [path for path in root.rglob("*") if path.is_dir()]
    markdown_files = [path for path in files if path.suffix.lower() == ".md"]
    top_level = sorted(entry.name + ("/" if entry.is_dir() else "") for entry in root.iterdir())
    key_files = [
        "PROJECT_BRIEF.md",
        "CURRENT_STATE.md",
        "TASK_BOARD.md",
        "DECISION_LOG.md",
        "AGENT_HANDOFF.md",
    ]
    present_key_files = [name for name in key_files if (root / name).exists()]

    return {
        "project_root": str(root),
        "total_files": str(len(files)),
        "total_dirs": str(len(folders)),
        "markdown_files": str(len(markdown_files)),
        "top_level_entries": render_list([f"`{name}`" for name in top_level]),
        "key_files": render_list([f"`{name}`" for name in present_key_files]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a context pack from a template and project data.")
    parser.add_argument("--project-root", required=True, help="Project root to inspect.")
    parser.add_argument("--template", required=True, help="Markdown template path.")
    parser.add_argument("--data-json", help="Optional JSON file with additional data.")
    parser.add_argument("--output", help="Optional output markdown path.")
    parser.add_argument("--project-name", help="Project name override.")
    parser.add_argument("--notes", default="Generated for automation testing only.", help="Free-form notes.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    template_path = Path(args.template).resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"Project root not found: {project_root}")
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    data: dict[str, str] = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": args.project_name or project_root.name,
        "notes": args.notes,
    }
    data.update(summarize_project(project_root))

    if args.data_json:
        json_path = Path(args.data_json).resolve()
        extra = json.loads(json_path.read_text(encoding="utf-8"))
        data.update({key: str(value) for key, value in extra.items()})

    rendered = template
    for key, value in data.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    output_path = (
        Path(args.output).resolve()
        if args.output
        else project_root
        / "CONTEXT_PACKS"
        / f"CP_01_AUTOGEN_{dt.datetime.now():%Y%m%d_%H%M%S}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    print(f"Project root: {project_root}")
    print(f"Template: {template_path}")
    print(f"Output: {output_path}")
    print(f"Project name: {data['project_name']}")
    print(f"Markdown files counted: {data['markdown_files']}")


if __name__ == "__main__":
    main()

