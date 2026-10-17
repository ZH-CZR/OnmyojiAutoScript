param(
    [string]$PythonPath,
    [ValidateRange(1, 65535)]
    [int]$Port = 22267,
    [Parameter(Mandatory = $true)]
    [string]$GitDirectory
)

$ErrorActionPreference = 'Stop'
$backendRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonPath) {
    $PythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$GitDirectory = (Resolve-Path -LiteralPath $GitDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $GitDirectory 'mingw64\bin\git.exe') -PathType Leaf)) {
    throw 'GitDirectory must be a complete Git for Windows directory containing mingw64\bin\git.exe.'
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw 'Python executable does not exist.'
}

$toolkitPath = Join-Path $backendRoot 'toolkit'
New-Item -ItemType Directory -Path $toolkitPath -Force | Out-Null
$gitLink = Join-Path $toolkitPath 'Git'
if (-not (Test-Path -LiteralPath $gitLink)) {
    New-Item -ItemType Junction -Path $gitLink -Target $GitDirectory | Out-Null
}
if (-not (Test-Path -LiteralPath (Join-Path $gitLink 'mingw64\bin\git.exe') -PathType Leaf)) {
    throw 'Existing toolkit\Git is incomplete. It has not been replaced.'
}

$deployPath = Join-Path $backendRoot 'config\deploy.yaml'
New-Item -ItemType Directory -Path (Split-Path -Parent $deployPath) -Force | Out-Null
$sourcePath = if (Test-Path -LiteralPath $deployPath) { $deployPath } else { Join-Path $backendRoot 'deploy\template' }
$deployText = [IO.File]::ReadAllText($sourcePath)
$settings = [ordered]@{
    PythonExecutable = $PythonPath.Replace('\', '/')
    GitExecutable = './toolkit/Git/mingw64/bin/git.exe'
    AutoUpdate = 'false'
    KeepLocalChanges = 'true'
    InstallDependencies = 'false'
    ReplaceAdb = 'false'
    AutoConnect = 'false'
    InstallUiautomator2 = 'false'
    WebuiHost = '127.0.0.1'
    WebuiPort = "$Port"
}
foreach ($entry in $settings.GetEnumerator()) {
    $pattern = '(?m)^(\s*' + [regex]::Escape($entry.Key) + ':)[^\r\n]*'
    if (-not [regex]::IsMatch($deployText, $pattern)) {
        throw "Missing deploy setting: $($entry.Key)"
    }
    $settingValue = $entry.Value
    $deployText = [regex]::Replace($deployText, $pattern, {
        param($match)
        $match.Groups[1].Value + ' ' + $settingValue
    })
}
[IO.File]::WriteAllText($deployPath, $deployText, [Text.UTF8Encoding]::new($false))
Write-Output "OASX root: $backendRoot"
Write-Output "OASX address: http://127.0.0.1:$Port"
Write-Output "Python: $PythonPath"
Write-Output "Git: $gitLink"
Write-Output 'Local startup configured; automatic repository/dependency/ADB changes disabled.'
