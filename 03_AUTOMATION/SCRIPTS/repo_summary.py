from __future__ import annotations

import argparse
import datetime as dt
from collections import Counter
from pathlib import Path


DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def should_skip(path: Path, excludes: set[str]) -> bool:
    return any(part in excludes for part in path.parts)


def tree_preview(root: Path, max_depth: int, excludes: set[str]) -> list[str]:
    lines: list[str] = []

    def walk(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        children = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for child in children:
            if should_skip(child.relative_to(root), excludes):
                continue
            prefix = "  " * depth + "- "
            lines.append(f"{prefix}{child.name}{'/' if child.is_dir() else ''}")
            if child.is_dir():
                walk(child, depth + 1)

    walk(root, 0)
    return lines


def summarize_repo(root: Path, excludes: set[str]) -> dict:
    total_files = 0
    total_dirs = 0
    total_size = 0
    extension_counts: Counter[str] = Counter()
    largest_files: list[tuple[int, Path]] = []

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if should_skip(relative, excludes):
            continue
        if path.is_dir():
            total_dirs += 1
            continue
        if path.is_file():
            total_files += 1
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            total_size += size
            extension_counts[path.suffix.lower() or "[no extension]"] += 1
            largest_files.append((size, relative))

    largest_files.sort(reverse=True)
    top_level = sorted(
        [
            entry.name + ("/" if entry.is_dir() else "")
            for entry in root.iterdir()
            if not should_skip(Path(entry.name), excludes)
        ]
    )

    return {
        "root": root,
        "total_files": total_files,
        "total_dirs": total_dirs,
        "total_size": total_size,
        "extension_counts": extension_counts,
        "largest_files": largest_files[:10],
        "top_level": top_level,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a read-only repository summary.")
    parser.add_argument("repo", help="Path to the repository or project root to summarize.")
    parser.add_argument("--output", help="Optional output markdown path.")
    parser.add_argument("--max-depth", type=int, default=2, help="Depth for tree preview.")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")

    excludes = set(DEFAULT_EXCLUDES)
    summary = summarize_repo(root, excludes)
    preview = tree_preview(root, args.max_depth, excludes)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output_path = (
        Path(args.output).resolve()
        if args.output
        else Path(r"C:\AI_WORKFLOW_V2\08_REPORTS\REPO_SUMMARIES")
        / f"repo_summary_{root.name}_{dt.datetime.now():%Y%m%d_%H%M%S}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    extension_lines = [
        f"- `{ext}`: {count}"
        for ext, count in summary["extension_counts"].most_common(12)
    ]
    largest_lines = [
        f"- `{path}` -> {human_size(size)}"
        for size, path in summary["largest_files"]
    ]
    top_level_lines = [f"- `{entry}`" for entry in summary["top_level"]]
    preview_lines = preview[:120] if preview else ["- [empty]"]

    markdown = "\n".join(
        [
            "# Repository Summary",
            "",
            f"Generated at: {generated_at}",
            "",
            "## Scope",
            "",
            f"- Root: `{root}`",
            f"- Total files: {summary['total_files']}",
            f"- Total directories: {summary['total_dirs']}",
            f"- Total size: {human_size(summary['total_size'])}",
            "",
            "## Top Level",
            "",
            *(top_level_lines or ["- [none]"]),
            "",
            "## Common Extensions",
            "",
            *(extension_lines or ["- [none]"]),
            "",
            "## Largest Files",
            "",
            *(largest_lines or ["- [none]"]),
            "",
            "## Tree Preview",
            "",
            *preview_lines,
            "",
            "## Notes",
            "",
            "- This summary is read-only.",
            f"- Excluded folders: {', '.join(sorted(excludes))}",
        ]
    )

    output_path.write_text(markdown, encoding="utf-8")

    print(f"Root: {root}")
    print(f"Files: {summary['total_files']}")
    print(f"Directories: {summary['total_dirs']}")
    print(f"Total size: {human_size(summary['total_size'])}")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()

