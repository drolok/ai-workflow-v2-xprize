from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def render_list(value: object) -> str:
    if isinstance(value, list):
        if not value:
            return "- [none]"
        return "\n".join(f"- {item}" for item in value)
    if value is None:
        return "- [none]"
    return f"- {value}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an agent handoff markdown file from a template.")
    parser.add_argument("--template", required=True, help="Path to the template markdown file.")
    parser.add_argument("--data-json", help="Optional JSON file with template values.")
    parser.add_argument("--output", help="Optional output markdown path.")
    parser.add_argument("--project-name", default="AI_WORKFLOW_V2_TEST", help="Project name.")
    parser.add_argument("--objective", default="Prepare a safe handoff for the next agent.", help="Current objective.")
    parser.add_argument("--status", default="Ready for handoff.", help="Short status line.")
    args = parser.parse_args()

    template_path = Path(args.template).resolve()
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    data: dict[str, str] = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": args.project_name,
        "objective": args.objective,
        "status": args.status,
        "next_steps": "- Confirm scope\n- Continue with the next approved phase",
        "artifacts": "- [pending]",
        "open_questions": "- [none]",
    }

    if args.data_json:
        extra = json.loads(Path(args.data_json).resolve().read_text(encoding="utf-8"))
        for key, value in extra.items():
            data[key] = render_list(value) if key in {"next_steps", "artifacts", "open_questions"} else str(value)

    template = template_path.read_text(encoding="utf-8")
    rendered = template
    for key, value in data.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    output_path = (
        Path(args.output).resolve()
        if args.output
        else Path(r"C:\AI_WORKFLOW_V2\08_REPORTS\AGENT_HANDOFFS")
        / f"agent_handoff_{dt.datetime.now():%Y%m%d_%H%M%S}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    print(f"Template: {template_path}")
    print(f"Output: {output_path}")
    print(f"Project name: {data['project_name']}")
    print(f"Objective: {data['objective']}")


if __name__ == "__main__":
    main()

