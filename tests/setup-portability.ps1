# Isolated Windows bootstrap regression checks; no package installs or downloads.
$ErrorActionPreference = 'Stop'
$TestRepository = Split-Path -Parent $PSScriptRoot
$TestTempBase = if ($env:LEMO_TEST_TEMP) { $env:LEMO_TEST_TEMP } elseif (Test-Path -LiteralPath 'F:\tools\temp') { 'F:\tools\temp' } else { [IO.Path]::GetTempPath() }
$TestRoot = Join-Path $TestTempBase ('lemo-setup-test-' + [guid]::NewGuid().ToString('N'))
$TestCodexHomeBefore = $env:CODEX_HOME
$TestPassed = 0
function Assert-LemoTest {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}
try {
    # Resolving Python before creating a venv must still select the executable the venv creates.
    $FreshLibrary = Join-Path $TestRoot 'fresh library 中文'
    New-Item -ItemType Directory -Path (Join-Path $FreshLibrary 'tools') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $TestRepository 'tools/codex-env.ps1') -Destination (Join-Path $FreshLibrary 'tools')
    . (Join-Path $FreshLibrary 'tools/codex-env.ps1')
    $SelectedBeforeCreation = $LemoPython
    & python -m venv --without-pip (Join-Path $FreshLibrary '.venv')
    Assert-LemoTest ($LASTEXITCODE -eq 0) 'Could not create the isolated test venv'
    Assert-LemoTest (Test-Path -LiteralPath $SelectedBeforeCreation) "Fresh setup selected a Python path that the venv did not create: $SelectedBeforeCreation"
    $TestPassed++

    # An unsupported existing environment must fail before npm/downloads and remain intact.
    $FreshPythonVersion = & $SelectedBeforeCreation -c 'import sys; print(sys.version.split()[0])'
    if ($FreshPythonVersion -notmatch '^3\.(11|12)\.') {
        Copy-Item -LiteralPath (Join-Path $TestRepository 'tools/setup-codex.ps1') -Destination (Join-Path $FreshLibrary 'tools')
        $RejectedPython = $false
        try { & (Join-Path $FreshLibrary 'tools/setup-codex.ps1') -Tier core } catch { $RejectedPython = $_.Exception.Message -like '*Python 3.11-3.12*' }
        Assert-LemoTest $RejectedPython 'An unsupported existing venv was not rejected before package installation'
        Assert-LemoTest (Test-Path -LiteralPath $SelectedBeforeCreation) 'The unsupported venv was deleted'
        Assert-LemoTest (-not (Test-Path -LiteralPath (Join-Path $FreshLibrary 'node_modules'))) 'Package installation started before the venv check'
        $TestPassed++
    }

    # Install into a private CODEX_HOME, validate its library pointer, then update it in place.
    $env:CODEX_HOME = Join-Path $TestRoot 'codex home 中文'
    $Setup = Join-Path $TestRepository 'tools/setup-codex.ps1'
    & $Setup -InstallSkill
    & $Setup -InstallSkill
    $SkillDirectory = Join-Path $env:CODEX_HOME 'skills/lemo-opuscar'
    Assert-LemoTest (Test-Path -LiteralPath (Join-Path $SkillDirectory 'SKILL.md')) 'Installed skill has no SKILL.md'
    Assert-LemoTest (Test-Path -LiteralPath (Join-Path $SkillDirectory 'agents/openai.yaml')) 'Installed skill has no UI metadata'
    $Pointer = (Get-Content -LiteralPath (Join-Path $SkillDirectory 'library-path.txt') -Raw).Trim()
    Assert-LemoTest ($Pointer -eq $TestRepository) 'The installed skill does not point to this library'
    Assert-LemoTest (@(Get-ChildItem -LiteralPath $SkillDirectory -Recurse -Filter openai.yaml).Count -eq 1) 'A repeated install nested the agents directory'
    $TestPassed++

    # A same-named skill owned by a different checkout must not be silently replaced.
    $MarkerPath = Join-Path $SkillDirectory '.lemo-install.json'
    @{ source_library=(Join-Path $TestRoot 'another-library') } | ConvertTo-Json | Set-Content -LiteralPath $MarkerPath -Encoding utf8
    $Refused = $false
    try { & $Setup -InstallSkill } catch { $Refused = $_.Exception.Message -like '*different library*' }
    Assert-LemoTest $Refused 'Installer did not refuse a skill belonging to another checkout'
    Assert-LemoTest (((Get-Content -LiteralPath $MarkerPath -Raw | ConvertFrom-Json).source_library) -eq (Join-Path $TestRoot 'another-library')) 'Installer overwrote the other-library marker'
    $TestPassed++

    # Windows ships PowerShell 5.1: its legacy native argument passing must work too.
    if (Get-Command powershell.exe -ErrorAction SilentlyContinue) {
        $LegacyProbe = Join-Path $TestRoot 'legacy-probe.ps1'
        @'
param([string]$Setup)
$ErrorActionPreference = 'Stop'
$NodeVersion = & node --version
if ($LASTEXITCODE -ne 0 -or $NodeVersion -notmatch '^v(\d+)\.') { throw 'Node version check failed in Windows PowerShell' }
if ([int]$Matches[1] -lt 20) { throw 'Node 20+ required' }
$PythonOk = & python -c 'import sys; print(int((3, 11) <= sys.version_info[:2] < (3, 14)))'
if ($LASTEXITCODE -ne 0 -or $PythonOk -ne '1') { throw 'Python version check failed in Windows PowerShell' }
& $Setup -Diagnose
'@ | Set-Content -LiteralPath $LegacyProbe -Encoding utf8
        $LegacyJson = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $LegacyProbe -Setup $Setup
        Assert-LemoTest ($LASTEXITCODE -eq 0) 'Environment diagnosis failed in Windows PowerShell 5.1'
        $LegacyResult = $LegacyJson | ConvertFrom-Json
        Assert-LemoTest ($LegacyResult.library -eq $TestRepository) 'Legacy diagnosis selected the wrong library'
        Assert-LemoTest ($LegacyResult.styles -eq 59) 'Legacy diagnosis did not find the style library'
        if (Test-Path -LiteralPath (Join-Path $TestRepository 'node_modules/playwright-core')) {
            Assert-LemoTest $LegacyResult.browser_installed 'Legacy diagnosis could not launch the installed headless browser'
        }
        $TestPassed++
    }

    Write-Output "$TestPassed isolated setup checks passed"
} finally {
    $env:CODEX_HOME = $TestCodexHomeBefore
    # Verify the absolute cleanup target stays under the explicitly selected test parent.
    $ResolvedTestParent = [IO.Path]::GetFullPath($TestTempBase).TrimEnd('\', '/')
    $ResolvedTestRoot = [IO.Path]::GetFullPath($TestRoot)
    if (-not $ResolvedTestRoot.StartsWith($ResolvedTestParent + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing cleanup outside test parent: $ResolvedTestRoot"
    }
    if (Test-Path -LiteralPath $ResolvedTestRoot) { Remove-Item -LiteralPath $ResolvedTestRoot -Recurse -Force }
}
