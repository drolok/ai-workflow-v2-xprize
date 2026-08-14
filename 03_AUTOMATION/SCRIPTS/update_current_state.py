from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
from pathlib import Path


AUTO_START = "<!-- AUTO_STATE_START -->"
AUTO_END = "<!-- AUTO_STATE_END -->"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_latest_json(path: Path, fallback_name: str) -> Path:
    candidate = path / fallback_name
    if candidate.exists():
        return candidate
    matches = sorted(path.glob("*.json"))
    if not matches:
        raise FileNotFoundError(f"No JSON files found in {path}")
    return matches[-1]


def render_block(health: dict, ports: dict) -> str:
    checks = health.get("checks", [])
    port_rows = ports.get("ports", [])
    ok_count = sum(1 for check in checks if check.get("Status") == "OK")
    warn_count = sum(1 for check in checks if check.get("Status") == "WARN")
    fail_count = sum(1 for check in checks if check.get("Status") == "FAIL")

    active_ports = [
        row for row in port_rows
        if row.get("State") == "LISTEN"
    ]

    check_lines = "\n".join(
        f"- `{check.get('Name')}` -> {check.get('Status')}: {check.get('Detail')}"
        for check in checks
    ) or "- [none]"

    port_lines = "\n".join(
        f"- `{row.get('Port')}` -> {row.get('Process')} (PID {row.get('Pid')})"
        for row in active_ports
    ) or "- [none]"

    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return "\n".join(
        [
            AUTO_START,
            "## Automation Snapshot",
            "",
            f"- Generated at: {generated_at}",
            f"- Latest health report: `{health.get('report_path', '-')}`",
            f"- Latest port scan: `{ports.get('report_path', '-')}`",
            f"- Health summary: OK={ok_count}, WARN={warn_count}, FAIL={fail_count}",
            "",
            "### Latest Scripted Checks",
            "",
            check_lines,
            "",
            "### Active Ports From Latest Scan",
            "",
            port_lines,
            "",
            "### Safety",
            "",
            "- This managed block is appended or replaced without deleting manual sections.",
            "- Backups are written before CURRENT_STATE.md is overwritten.",
            AUTO_END,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely update CURRENT_STATE.md from generated health and port reports.")
    parser.add_argument(
        "--current-state",
        default=r"C:\AI_WORKFLOW_V2\00_COMMAND_CENTER\CURRENT_STATE.md",
        help="Path to CURRENT_STATE.md",
    )
    parser.add_argument(
        "--health-dir",
        default=r"C:\AI_WORKFLOW_V2\08_REPORTS\HEALTH_CHECKS",
        help="Directory containing health check JSON outputs.",
    )
    parser.add_argument(
        "--ports-dir",
        default=r"C:\AI_WORKFLOW_V2\08_REPORTS\PORT_SCANS",
        help="Directory containing port scan JSON outputs.",
    )
    args = parser.parse_args()

    current_state_path = Path(args.current_state).resolve()
    health_json_path = find_latest_json(Path(args.health_dir).resolve(), "latest_health_check.json")
    ports_json_path = find_latest_json(Path(args.ports_dir).resolve(), "latest_port_scan.json")

    original = current_state_path.read_text(encoding="utf-8")
    health = load_json(health_json_path)
    ports = load_json(ports_json_path)
    block = render_block(health, ports)

    pattern = re.compile(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END), re.S)
    if pattern.search(original):
        updated = pattern.sub(lambda _: block, original)
    else:
        suffix = "" if original.endswith("\n") else "\n"
        updated = original + suffix + "\n" + block + "\n"

    diff_text = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(current_state_path),
            tofile=str(current_state_path) + " (updated)",
        )
    )

    backup_path = current_state_path.with_name(
        f"{current_state_path.stem}.backup_{dt.datetime.now():%Y%m%d_%H%M%S}{current_state_path.suffix}"
    )
    backup_path.write_text(original, encoding="utf-8")
    current_state_path.write_text(updated, encoding="utf-8")

    print("Diff:")
    print(diff_text if diff_text else "[no changes]")
    print(f"Backup: {backup_path}")
    print(f"Updated: {current_state_path}")
    print(f"Health JSON: {health_json_path}")
    print(f"Ports JSON: {ports_json_path}")


if __name__ == "__main__":
    main()
