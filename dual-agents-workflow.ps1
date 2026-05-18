$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
try {
    py -3 "$ScriptDir\dual-agents-workflow.py" @args
} catch {
    python "$ScriptDir\dual-agents-workflow.py" @args
}
