# Native Codex setup. Does not invoke Claude, reset Git, or change global settings.
param(
    [ValidateSet('core','voice','music')][string[]]$Tier = @(),
    [ValidateSet('voice','hdri','instruments-freepats','instruments-karoryfer','instruments-salamander','instruments-vcsl','instruments-vsco2ce')]
    [string[]]$Assets = @(),
    [switch]$Diagnose,
    [switch]$InstallSkill
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'codex-env.ps1')
function Invoke-LemoChecked {
    param([string]$Program, [string[]]$CommandArguments)
    & $Program @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE)" }
}
function Assert-LemoPythonVersion {
    param([string]$Program, [string]$Context)
    $Version = & $Program -c 'import sys; print(sys.version.split()[0])'
    if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^3\.(11|12)\.') {
        throw "$Context uses an unsupported Python ($Version). Use Python 3.11-3.12 for the offline voice dependencies. An existing .venv is preserved; inspect or move it before retrying."
    }
}
function Install-LemoSkill {
    $CodexBase = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex' }
    $Destination = Join-Path $CodexBase 'skills/lemo-opuscar'
    $Marker = Join-Path $Destination '.lemo-install.json'
    if (Test-Path -LiteralPath $Destination) {
        if (-not (Test-Path -LiteralPath $Marker)) { throw "Skill already exists: $Destination. Inspect it before replacing it." }
        $Installed = Get-Content -LiteralPath $Marker -Raw | ConvertFrom-Json
        if ($Installed.source_library -ne $LemoLibraryRoot) { throw "The existing skill points to a different library: $($Installed.source_library)" }
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $LemoLibraryRoot 'codex/lemo-opuscar') | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
    [IO.File]::WriteAllText((Join-Path $Destination 'library-path.txt'), "$LemoLibraryRoot`n", [Text.UTF8Encoding]::new($false))
    @{ source_library=$LemoLibraryRoot; installed_at=[DateTime]::UtcNow.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $Marker -Encoding utf8
    Write-Output "Skill installed: $Destination"
}
Push-Location -LiteralPath $LemoLibraryRoot
try {
    if (-not $Diagnose -and (-not $InstallSkill -or $Tier.Count -gt 0 -or $Assets.Count -gt 0)) {
        foreach ($Name in @('node','ffmpeg','ffprobe')) {
            if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "Missing system tool: $Name" }
        }
        $NodeVersion = & node --version
        if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(\d+)\.') { throw 'Could not read the Node.js version' }
        $NodeMajor = [int]$Matches[1]
        if ($NodeMajor -lt 20) { throw 'Node 20+ is required' }
        $UvAvailable = [bool](Get-Command uv -ErrorAction SilentlyContinue)
        if (Test-Path -LiteralPath $LemoPython) {
            Assert-LemoPythonVersion $LemoPython 'Existing .venv'
        } elseif (Test-Path -LiteralPath (Join-Path $LemoLibraryRoot '.venv')) {
            throw 'An existing .venv has no runnable Python. It has been preserved; inspect or move it before retrying.'
        } elseif (-not $UvAvailable) {
            if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install uv, or provide Python 3.11-3.12 on PATH' }
            Assert-LemoPythonVersion 'python' 'System Python (uv is unavailable)'
        }
        foreach ($CacheName in $LemoCacheDefaults.Keys) {
            New-Item -ItemType Directory -Path ([Environment]::GetEnvironmentVariable($CacheName, 'Process')) -Force | Out-Null
        }
        if (-not (Test-Path -LiteralPath $LemoPython)) {
            if ($UvAvailable) { Invoke-LemoChecked 'uv' @('venv','--python','3.12','.venv') }
            else { Invoke-LemoChecked 'python' @('-m','venv','.venv') }
        }
        . (Join-Path $PSScriptRoot 'codex-env.ps1')
        Assert-LemoPythonVersion $LemoPython 'Library .venv'
        $Npm = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { 'npm.cmd' } else { 'npm' }
        Invoke-LemoChecked $Npm @('ci','--ignore-scripts','--no-audit','--no-fund')
        Invoke-LemoChecked 'node' @('node_modules/playwright-core/cli.js','install','chromium','--only-shell')
        $RequestedTiers = @('core') + $Tier | Select-Object -Unique
        $Requirements = @('-r','requirements.txt')
        foreach ($Name in $RequestedTiers) { if ($Name -ne 'core') { $Requirements += @('-r',"requirements-$Name.txt") } }
        if ($UvAvailable) { Invoke-LemoChecked 'uv' (@('pip','install','--python',$LemoPython) + $Requirements) }
        else { Invoke-LemoChecked $LemoPython (@('-m','pip','install') + $Requirements) }
        $RequestedPacks = @($Assets)
        if ($RequestedTiers -contains 'voice') { $RequestedPacks += 'voice' }
        foreach ($Pack in ($RequestedPacks | Select-Object -Unique)) {
            Invoke-LemoChecked $LemoPython @('tools/fetch_assets.py',$Pack)
        }
    }
    if ($InstallSkill) { Install-LemoSkill }
    if ($Diagnose) {
        $Tools = [ordered]@{}
        $ActiveCaches = [ordered]@{}
        foreach ($CacheName in $LemoCacheDefaults.Keys) { $ActiveCaches[$CacheName] = [Environment]::GetEnvironmentVariable($CacheName, 'Process') }
        foreach ($Name in @('node','python','ffmpeg','ffprobe','uv')) {
            $Found = Get-Command $Name -ErrorAction SilentlyContinue
            $Tools[$Name] = if ($Found) { $Found.Source } else { $null }
        }
        $Browser = @{ installed=$false; version=$null; error='Node dependencies are missing' }
        if (Test-Path -LiteralPath 'node_modules/playwright-core') {
            $BrowserJson = & node (Join-Path $PSScriptRoot 'diagnose-browser.mjs')
            if ($LASTEXITCODE -ne 0) { throw 'Browser diagnosis failed' }
            $Browser = $BrowserJson | ConvertFrom-Json
        }
        [ordered]@{
            library=$LemoLibraryRoot; tools=$Tools; python_environment=(Test-Path -LiteralPath $LemoPython)
            browser=$Browser; browser_installed=$Browser.installed
            offline_voice_model=(Test-Path -LiteralPath 'core/tts/kokoro-v1.0.onnx')
            offline_voice_voices=(Test-Path -LiteralPath 'core/tts/voices-v1.0.bin')
            styles=@(Get-ChildItem -LiteralPath 'styles' -Directory | Where-Object { $_.Name -ne '_template' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'STYLE.md')) }).Count
            caches=$ActiveCaches
        } | ConvertTo-Json -Depth 4
    }
} finally { Pop-Location }
