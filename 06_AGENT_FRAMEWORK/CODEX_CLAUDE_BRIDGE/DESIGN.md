# Codex-Claude Bridge Design

## Goal

Remove the founder from routine copy-paste between Codex and Claude Code for operational work:

- code review requests
- evidence audits
- test launches
- n8n / workflow review
- doc sync and state confirmation

Do **not** use the bridge to decide product, business, pricing, scope, legal, or other founder-owned questions.

## Reality Check: What Exists On This Machine

### Codex side

- A real Codex CLI is callable from shell:
  - `<WINDOWS_HOME>\AppData\Local\OpenAI\Codex\bin\5dee10576ec7a5b8\codex.exe`
- Verified commands:
  - `codex --help`
  - `codex mcp --help`
  - `codex mcp-server --help`
  - `codex remote-control --help`
- Conclusion: Codex exposes a usable external surface.

### Claude side

- Claude is installed as a Windows app package:
  - `C:\Program Files\WindowsApps\Claude_1.22209.3.0_x64__pzs8sxrjxfjjc`
- The package contains:
  - `app\claude.exe`
  - `app\resources\cowork-svc.exe`
  - a registered custom protocol: `claude:`
- Internal strings mention `/mcp` and `claude remote-control`, which suggests the app has native concepts for those features.
- But from this shell, direct invocations such as:
  - `claude.exe --help`
  - `claude.exe remote-control --help`
  - `claude.exe mcp --help`
  returned only a Node deprecation warning and no usable CLI surface.

Conclusion: Claude has an app and likely internal bridge features, but from **outside** the app there is no stable, documented, shell-usable automation surface that can be trusted today.

### A2A / MCP libraries

- In the reusable Python lab venv:
  - `a2a=True`
  - `mcp=False`
- So A2A SDK is present.
- Generic Python MCP tooling is not present in that venv.

## Options Evaluated

### Option A - Native Codex CLI to native Claude CLI

Status: rejected for today.

Why:

- Codex CLI is real and callable.
- Claude app is present, but its shell entry surface is not usable from this PowerShell session.
- No reliable `claude` command is available in PATH.
- No documented request/response CLI contract was recoverable from the installed app.

### Option B - MCP bridge

Status: promising in theory, rejected for today.

Why:

- Codex can run as an MCP server via `codex mcp-server`.
- Claude app clearly knows about MCP internally.
- But this still depends on a Claude-side setup surface we cannot drive or validate from here.
- For a bridge that must work **today**, this is too dependent on undocumented app behavior.

### Option C - A2A bridge

Status: viable future path, rejected for today.

Why:

- `a2a` is installed.
- A2A would be cleaner than file polling once both sides expose callable worker processes.
- But today there is still no shell-usable Claude worker surface to bind to A2A cleanly.
- It would add more moving parts than necessary before the basic transport problem is solved.

### Option D - Shared filesystem queue

Status: chosen.

Why:

- Both agents already share the same disk.
- No resident daemon is required.
- Fully auditable via JSON + JSONL logs.
- Crash-safe enough for routine work: a task stays in `requests` or `in_progress`, never disappears silently.
- Works even if one agent is temporarily offline.
- Does not depend on hidden app protocols or unstable reverse engineering.

## Chosen Design

The bridge is a shared queue on disk:

- Root:
  - `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\queue`
- Folders:
  - `requests`
  - `in_progress`
  - `responses`
  - `archive`
  - `logs`

Main script:

- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py`

Optional wrapper for Codex-side enqueue:

- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\enqueue_task.ps1`

Audit log:

- `C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\queue\logs\bridge_log.jsonl`

## What Goes Through The Bridge

Allowed routine traffic:

1. Review a set of findings and return a technical verdict.
2. Verify a claim against repo / docs / database evidence.
3. Run or re-check a known test command and summarize result.
4. Compare documentation against code and flag discrepancies.
5. Produce a bounded handoff or audit packet.

Must still escalate to the founder:

1. Product or business decisions.
2. Pricing, take rate, district selection, lending policy, or scope changes.
3. Legal / fintech / KYC tradeoffs.
4. Any case where two technically valid options exist but the choice changes product behavior.
5. Any protected-file change that already requires explicit authorization by project rule.

Rule of thumb:

- Routine execution and verification can flow through the bridge.
- Decision-making authority does not.

## Failure And Recovery

### If the consumer crashes mid-task

- The task file remains in `in_progress`.
- The markdown packet remains on disk.
- Recovery: resume or reissue a response from the same `task_id`.

### If the bridge fails before claim

- The task is still in `requests`.
- Recovery: claim it again later; nothing was lost.

### If a task needs founder input mid-stream

- The consumer must respond with status `needs_founder`.
- It must not silently choose between business options.

### If the queue gets stale

- Run `bridge_queue.py status`.
- Inspect `bridge_log.jsonl`.
- Re-enqueue only if the old task is clearly abandoned and documented.

## Exact Commands

### Codex side: enqueue a task for Claude

```powershell
C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\enqueue_task.ps1 `
  -Title "Review Agentic Radar findings for n8n" `
  -BodyFile "C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\tasks\TASK_AGENTIC_RADAR_N8N_REVIEW_2026-07-20.md" `
  -Kind "review"
```

### Claude side: claim the next task

```powershell
<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe `
  C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py `
  claim --agent claude --once
```

This prints the claimed `task_id`, the JSON file path, and the generated markdown packet path in `in_progress`.

### Claude side: respond after doing the work

```powershell
<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe `
  C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py `
  respond --agent claude --task-id <TASK_ID> --status completed `
  --response-file <ABSOLUTE_PATH_TO_RESPONSE_MD> `
  --summary "Completed review with evidence"
```

Supported statuses:

- `completed`
- `blocked`
- `needs_founder`
- `rejected`

## Important Limitation Right Now

This bridge removes manual copy-paste of task **content**, but it does **not** yet create a fully autonomous Claude daemon.

Why not:

- Claude is installed as an app, but there is no shell-verified external CLI/API surface we can call from Codex today.
- So the best reliable mode right now is:
  - Codex writes the task packet to disk.
  - Claude Code, once bootstrapped in its own session, claims and answers tasks from the queue itself.

That still removes the founder from acting as a messenger of prompts and results. It does **not** eliminate the need for a one-time Claude session bootstrap.

## Recommended Next Step

Use the file queue immediately for routine audits and reviews.

If, later, the Claude-side `remote-control` or `/mcp` surface becomes externally scriptable and verifiable, revisit:

1. Codex `mcp-server`
2. Claude `/mcp`
3. A2A as a cleaner active-active bridge

For today, the file queue is the only option that is both honest and operational.
