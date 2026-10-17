param(
    [switch]$InstallOnly,
    [switch]$SkipModels,
    [string]$PypiMirror = 'https://pypi.tuna.tsinghua.edu.cn/simple'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64' -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    throw 'This installer requires Windows 10/11 x64.'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$toolkit = Join-Path $root 'toolkit'
$cache = Join-Path $toolkit 'downloads'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-downloads.json') -Raw | ConvertFrom-Json

function Get-VerifiedDownload($entry) {
    $target = Join-Path $cache $entry.filename
    if ((Test-Path -LiteralPath $target) -and (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $entry.sha256) {
        return $target
    }
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Write-Host "Downloading $($entry.filename) (attempt $attempt/3)..."
            if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
                # curl honors HTTPS_PROXY on Windows, unlike Windows PowerShell 5's WebRequest.
                & curl.exe --fail --location --connect-timeout 30 --max-time 900 --retry 2 --output "$target.part" $entry.url
                if ($LASTEXITCODE -ne 0) { throw "Download failed (curl $LASTEXITCODE): $($entry.url)" }
            } else {
                Invoke-WebRequest -UseBasicParsing -Uri $entry.url -OutFile "$target.part" -TimeoutSec 900
            }
            if ((Get-FileHash -LiteralPath "$target.part" -Algorithm SHA256).Hash -ne $entry.sha256) {
                throw "SHA256 verification failed: $($entry.filename)"
            }
            Move-Item -LiteralPath "$target.part" -Destination $target -Force
            return $target
        } catch {
            if ($attempt -eq 3) { throw }
            Write-Warning $_.Exception.Message
            Start-Sleep -Seconds 2
        }
    }
}

function Invoke-Checked([string]$executable, [string[]]$arguments) {
    & $executable @arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $executable $arguments" }
}

function Find-Git {
    foreach ($relative in @('toolkit/Git/cmd/git.exe', 'toolkit/Git/mingw64/bin/git.exe', 'toolkit/Git/ucrt64/bin/git.exe')) {
        $candidate = Join-Path $root $relative
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return $null
}

$installLock = $null
try {
    try {
        $installLock = [IO.File]::Open((Join-Path $toolkit 'first-run.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch { throw 'Another first-run installer is already running. Close it before retrying.' }
    $venvPython = Join-Path $root '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        if (Test-Path -LiteralPath (Join-Path $root '.venv')) {
            throw 'An incomplete .venv already exists. Move it aside before retrying; it has not been overwritten.'
        }
        $basePython = Join-Path $toolkit 'python/python.exe'
        if (-not (Test-Path -LiteralPath $basePython -PathType Leaf)) {
            if (Test-Path -LiteralPath (Join-Path $toolkit 'python')) {
                throw 'toolkit/python exists but is incomplete. It has not been overwritten.'
            }
            $archive = Get-VerifiedDownload $manifest.python
            $stage = Join-Path $toolkit ('python-extract-' + [guid]::NewGuid().ToString('N'))
            New-Item -ItemType Directory -Path $stage | Out-Null
            if (-not (Get-Command tar.exe -ErrorAction SilentlyContinue)) { throw 'Windows tar.exe is required (Windows 10 1809 or newer).' }
            Invoke-Checked 'tar.exe' @('-xf', $archive, '-C', $stage)
            if (-not (Test-Path -LiteralPath (Join-Path $stage 'python/python.exe'))) { throw 'Python archive is incomplete.' }
            Move-Item -LiteralPath (Join-Path $stage 'python') -Destination (Join-Path $toolkit 'python')
        }
        Invoke-Checked $basePython @('-m', 'venv', (Join-Path $root '.venv'))
    }
    Invoke-Checked $venvPython @('-c', 'import sys; assert sys.version_info[:2] == (3,10) and sys.maxsize > 2**32')
    $git = Find-Git
    if (-not $git) {
        if (Test-Path -LiteralPath (Join-Path $toolkit 'Git')) { throw 'toolkit/Git exists but is incomplete. It has not been overwritten.' }
        $archive = Get-VerifiedDownload $manifest.git
        $stage = Join-Path $toolkit ('git-extract-' + [guid]::NewGuid().ToString('N'))
        Expand-Archive -LiteralPath $archive -DestinationPath $stage
        Move-Item -LiteralPath $stage -Destination (Join-Path $toolkit 'Git')
        $git = Find-Git
        if (-not $git) { throw 'Downloaded Git executable is missing.' }
    }
    Invoke-Checked $git @('--version')
    $arguments = @('-m', 'deploy.first_run', '--git', $git, '--index-url', $PypiMirror)
    if ($SkipModels) { $arguments += '--skip-models' }
    Invoke-Checked $venvPython $arguments
} finally {
    if ($installLock) { $installLock.Dispose() }
}
if (-not $InstallOnly) {
    Write-Host "Backend root: $root"
    Write-Host 'Keep this console open while using the backend.'
    Invoke-Checked $venvPython @('server.py')
}
