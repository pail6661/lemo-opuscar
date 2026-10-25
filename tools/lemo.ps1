# Run the shared tools with the library's environment, including paths with spaces.
param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('still','render','events','readcheck','mux','tts','tts-zh','asr','srt','sheet','fetch')]
    [string]$Tool,
    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$Arguments = @()
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'codex-env.ps1')
$NodeTools = @{ still='still'; render='video'; events='events'; readcheck='readcheck' }
$PythonTools = @{
    mux='core/render/mux.py'; tts='core/tts/tts.py'; 'tts-zh'='core/tts/tts_zh.py'
    asr='core/tts/asr_check.py'; srt='core/render/srt.py'; sheet='core/render/sheet.py'; fetch='tools/fetch_assets.py'
}
Push-Location -LiteralPath $LemoLibraryRoot
try {
    if ($NodeTools.ContainsKey($Tool)) {
        & node (Join-Path $LemoLibraryRoot ('core/render/' + $NodeTools[$Tool] + '.mjs')) @Arguments
    } else {
        if (-not (Test-Path -LiteralPath $LemoPython)) { throw 'Install the core tier first: tools/setup-codex.ps1 -Tier core' }
        & $LemoPython (Join-Path $LemoLibraryRoot $PythonTools[$Tool]) @Arguments
    }
    $LemoExitCode = $LASTEXITCODE
} finally { Pop-Location }
exit $LemoExitCode
