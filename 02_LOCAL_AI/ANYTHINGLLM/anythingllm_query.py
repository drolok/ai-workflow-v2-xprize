from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:3101"
DEFAULT_TOKEN = "APC1XGT-QX7MYMT-G76R786-E01F1FD"
DEFAULT_CONTAINER = "anythingllm-localai"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query an AnythingLLM workspace via SSE.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--transport",
        choices=("docker", "http"),
        default="docker",
        help="Use docker exec into the AnythingLLM container by default because host HTTP is flaky on this machine.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def extract_text(parts: Any) -> str:
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in parts
        )
    return str(parts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    if args.transport != "docker":
        raise SystemExit("Host HTTP transport is intentionally disabled here; use --transport docker.")

    js = f"""
const http = require('http');
const requestBody = JSON.stringify({{
  message: {json.dumps(args.message, ensure_ascii=False)},
  attachments: []
}});
const events = [];
let finalText = '';
let buffer = '';
const sourceMap = new Map();
const req = http.request({{
  hostname: '127.0.0.1',
  port: 3001,
  path: {json.dumps(f"/api/workspace/{args.workspace}/stream-chat")},
  method: 'POST',
  headers: {{
    Authorization: {json.dumps(f"Bearer {args.token}")},
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    'Content-Length': Buffer.byteLength(requestBody)
  }}
}}, (res) => {{
  res.setEncoding('utf8');
  res.on('data', (chunk) => {{
    buffer += chunk;
    const lines = buffer.split(/\\r?\\n/);
    buffer = lines.pop();
    for (const rawLine of lines) {{
      const line = rawLine.trim();
      if (!line.startsWith('data:')) continue;
      const eventText = line.slice(5).trim();
      if (!eventText) continue;
      try {{
        const event = JSON.parse(eventText);
        events.push(event);
        if (Array.isArray(event.sources)) {{
          for (const source of event.sources) {{
            const key = JSON.stringify(source);
            if (!sourceMap.has(key)) sourceMap.set(key, source);
          }}
        }}
        if (event.type === 'textResponseChunk' || event.type === 'textResponse') {{
          const raw = event.textResponse;
          finalText = Array.isArray(raw)
            ? raw.map((part) => typeof part === 'object' && part !== null ? (part.text || '') : String(part)).join('')
            : finalText + String(raw || '');
        }}
      }} catch (err) {{
        console.error('EVENT_PARSE_ERROR', err.message, eventText.slice(0, 200));
        process.exit(1);
      }}
    }}
  }});
  res.on('end', () => {{
    console.log(JSON.stringify({{
      status: res.statusCode,
      eventsSeen: events.map((event) => event.type),
      lastEvent: events.length ? events[events.length - 1] : null,
      finalText,
      uniqueSources: Array.from(sourceMap.values())
    }}));
  }});
}});
req.on('error', (err) => {{
  console.error(err.message);
  process.exit(1);
}});
req.write(requestBody);
req.end();
"""
    completed = subprocess.run(
        ["docker", "exec", "-i", args.container, "node", "-"],
        input=js,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.timeout + 15,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip())
    parsed = json.loads(completed.stdout)
    events_seen = parsed.get("eventsSeen", [])
    final_text = parsed.get("finalText", "")

    result = {
        "workspace": args.workspace,
        "message": args.message,
        "finalText": final_text,
        "eventsSeen": events_seen,
        "lastEvent": parsed.get("lastEvent"),
        "uniqueSources": parsed.get("uniqueSources", []),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
