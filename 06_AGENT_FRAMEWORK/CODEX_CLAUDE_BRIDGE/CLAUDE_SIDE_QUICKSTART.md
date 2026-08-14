# Claude Side Quickstart

## One-time Session Behavior

In the Claude Code session, use the bridge as a self-serve inbox.

Do not wait for the founder to paste prompts manually if a queue task already exists.

## Claim Next Task

```powershell
<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe `
  C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py `
  claim --agent claude --once
```

This prints:

- `task_id`
- claimed JSON path
- generated markdown packet path

Read the markdown packet from `queue\in_progress\`.

## After Finishing The Work

Save your response as a markdown file, then submit it:

```powershell
<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe `
  C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py `
  respond --agent claude --task-id <TASK_ID> --status completed `
  --response-file <ABSOLUTE_PATH_TO_RESPONSE_MD> `
  --summary "Completed with evidence"
```

If you need the founder to decide something:

```powershell
<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe `
  C:\AI_WORKFLOW\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py `
  respond --agent claude --task-id <TASK_ID> --status needs_founder `
  --response-file <ABSOLUTE_PATH_TO_RESPONSE_MD> `
  --summary "Founder decision required"
```

## Non-negotiable Rules

1. Do not take business decisions through the bridge.
2. If the task touches protected files or changes product behavior, escalate explicitly.
3. Keep evidence in the response markdown.
4. Do not delete queue history; the log is the audit trail.
