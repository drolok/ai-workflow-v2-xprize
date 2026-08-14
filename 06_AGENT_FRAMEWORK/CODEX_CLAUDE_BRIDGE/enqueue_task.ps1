param(
    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string]$BodyFile,

    [string]$Kind = "review",

    [string[]]$Attachments = @(),

    [string[]]$Constraints = @()
)

$ErrorActionPreference = "Stop"

$Python = "<WINDOWS_HOME>\AppData\Local\Programs\Python\Python313\python.exe"
$Script = "C:\AI_WORKFLOW_V2\06_AGENT_FRAMEWORK\CODEX_CLAUDE_BRIDGE\bridge_queue.py"

$args = @(
    $Script,
    "enqueue",
    "--from-agent", "codex",
    "--to-agent", "claude",
    "--kind", $Kind,
    "--title", $Title,
    "--body-file", $BodyFile
)

foreach ($attachment in $Attachments) {
    $args += @("--attachment", $attachment)
}

foreach ($constraint in $Constraints) {
    $args += @("--constraint", $constraint)
}

& $Python @args
