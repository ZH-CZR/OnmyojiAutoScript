# OASX versions that predate Git 2.56 still check the mingw64 directory.
function Initialize-GitLayout([string]$gitRoot) {
    $legacy = Join-Path $gitRoot 'mingw64'
    if (Test-Path -LiteralPath (Join-Path $legacy 'bin/git.exe') -PathType Leaf) {
        return
    }
    $modern = Join-Path $gitRoot 'ucrt64'
    if (-not (Test-Path -LiteralPath (Join-Path $modern 'bin/git.exe') -PathType Leaf)) {
        throw 'Git is incomplete: neither mingw64/bin/git.exe nor ucrt64/bin/git.exe exists.'
    }
    if (Get-Item -LiteralPath $legacy -Force -ErrorAction SilentlyContinue) {
        throw 'Existing mingw64 entry is incomplete. It has not been replaced.'
    }
    $directory = Get-Item -LiteralPath $gitRoot
    if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Git links to an external directory. Use project-local Git before creating OASX compatibility paths.'
    }
    New-Item -ItemType Junction -Path $legacy -Target (Resolve-Path -LiteralPath $modern).Path | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $legacy 'bin/git.exe') -PathType Leaf)) {
        throw 'Failed to create the OASX-compatible Git path.'
    }
    Write-Host 'Git compatibility ready: mingw64 points to the existing ucrt64 directory.'
}
