# Scoped environment for this library; no machine/user environment is changed.
$LemoLibraryRoot = Split-Path -Parent $PSScriptRoot
$LemoCacheRoot = if (Test-Path -LiteralPath 'F:\tools') { 'F:\tools' } else { Join-Path $LemoLibraryRoot '.cache' }
$LemoCacheDefaults = @{
    PLAYWRIGHT_BROWSERS_PATH = (Join-Path $LemoCacheRoot 'playwright-browsers')
    UV_CACHE_DIR = (Join-Path $LemoCacheRoot 'uv-cache')
    UV_PYTHON_INSTALL_DIR = (Join-Path $LemoCacheRoot 'uv-python')
    PIP_CACHE_DIR = (Join-Path $LemoCacheRoot 'pip-cache')
    npm_config_cache = (Join-Path $LemoCacheRoot 'npm-cache')
    HF_HOME = (Join-Path $LemoCacheRoot 'huggingface')
    NUMBA_CACHE_DIR = (Join-Path $LemoCacheRoot 'numba-cache')
    LEMO_TEST_TEMP = (Join-Path $LemoCacheRoot 'temp')
}
foreach ($LemoCacheName in $LemoCacheDefaults.Keys) {
    if (-not [Environment]::GetEnvironmentVariable($LemoCacheName, 'Process')) {
        [Environment]::SetEnvironmentVariable($LemoCacheName, $LemoCacheDefaults[$LemoCacheName], 'Process')
    }
}
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$LemoPython = Join-Path $LemoLibraryRoot '.venv\Scripts\python.exe'
$LemoPosixPython = Join-Path $LemoLibraryRoot '.venv/bin/python'
if (-not (Test-Path -LiteralPath $LemoPython) -and (Test-Path -LiteralPath $LemoPosixPython)) { $LemoPython = $LemoPosixPython }
