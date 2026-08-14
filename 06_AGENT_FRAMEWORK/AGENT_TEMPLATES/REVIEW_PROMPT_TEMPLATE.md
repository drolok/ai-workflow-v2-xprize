# Review Prompt Template

Review the completed work as an auditor. Prioritize real findings over summaries.

## Review Goal

[State what change, report or implementation must be reviewed.]

## Evidence To Inspect

- Context pack: [absolute path]
- Handoff or report: [absolute path]
- Files changed: [absolute paths]
- Test outputs or screenshots: [absolute paths]

## Review Rules

- Findings come first, ordered by severity.
- Use exact file references when pointing out issues.
- Prefer bugs, regressions, missing validations and documentation gaps.
- If something cannot be verified, say so explicitly.
- If no findings exist, state that clearly and mention any residual risks.

## Expected Output

- Findings
- Open questions or assumptions
- Short approval or rejection decision
