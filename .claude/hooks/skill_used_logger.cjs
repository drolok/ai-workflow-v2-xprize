"use strict";

const fs = require("fs");
const path = require("path");

function firstText(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (value && typeof value === "object" && typeof value.name === "string" && value.name.trim()) {
      return value.name.trim();
    }
  }
  return null;
}

function failLoudly(error) {
  const message = `${new Date().toISOString()} SKILL_USED no registrado: ${error.stack || error}\n`;
  try {
    fs.appendFileSync(path.join(__dirname, "skill_used_logger_error.log"), message, "utf8");
  } catch (_) {
    // stderr sigue haciendo visible el fallo en Claude Code.
  }
  process.stderr.write(message);
  process.exitCode = 1;
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { raw += chunk; });
process.stdin.on("end", () => {
  try {
    const input = JSON.parse(raw);
    let skillName = null;
    let invocationTrigger = null;

    if (input.hook_event_name === "PreToolUse" && input.tool_name === "Skill") {
      const toolInput = input.tool_input || {};
      skillName = firstText(toolInput.skill, toolInput.skill_name, toolInput.skillName, toolInput.name);
      invocationTrigger = "claude-proactive";
    } else if (
      input.hook_event_name === "UserPromptExpansion" &&
      input.expansion_type === "slash_command"
    ) {
      skillName = firstText(input.command_name);
      invocationTrigger = "user-slash";
    } else {
      return;
    }

    if (!skillName) throw new Error("el hook recibio una invocacion sin nombre de skill");
    if (!firstText(input.session_id)) throw new Error("el hook recibio una invocacion sin session_id");

    const event = {
      actor: "claude",
      payload: {
        hook_event: input.hook_event_name,
        invocation_trigger: invocationTrigger,
        session: input.session_id,
        skill: skillName,
      },
      ts: new Date().toISOString(),
      type: "SKILL_USED",
    };
    if (firstText(input.tool_use_id)) event.payload.tool_use_id = input.tool_use_id;
    if (firstText(input.command_source)) event.payload.command_source = input.command_source;
    if (firstText(input.agent_id)) event.payload.agent_id = input.agent_id;

    const projectRoot = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, "..", "..");
    const ledger = path.join(projectRoot, ".ai", "events", "EVENTS.jsonl");
    fs.mkdirSync(path.dirname(ledger), { recursive: true });
    fs.appendFileSync(ledger, `${JSON.stringify(event)}\n`, "utf8");
  } catch (error) {
    failLoudly(error);
  }
});
