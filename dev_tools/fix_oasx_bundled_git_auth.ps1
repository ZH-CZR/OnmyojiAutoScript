<#
.SYNOPSIS
    修复 OASX 内置 Git 无法访问 Gitee 私库的问题。

.DESCRIPTION
    OASX 的内置 Git 是裁剪版，缺少 usr\bin\sh.exe。Git 执行凭据助手必须经过 shell，
    因此内置 Git 无法认证私有仓库（公开仓库不受影响）。

    本脚本对每个使用 Gitee 仓库的 OAS 实例做四件事：
    1. 从本机已安装的完整 Git 复制 sh.exe 与 msys 运行库到内置 Git 的 usr\bin；
    2. 把内置 Git 的 credential.helper 配置为 wincred（读取 Windows 凭据管理器）；
    3. 把 deploy.yaml 的 GitExecutable 恢复为内置 Git；
    4. 用内置 Git 实测私库访问。

    默认只处理 deploy.yaml 中 Repository 为 gitee.com 的实例；
    找不到 Gitee 实例时才处理全部实例。

.PARAMETER InstallRoot
    指定单个 OAS 安装目录（包含 toolkit\Git 与 config\deploy.yaml）。
    不传时自动查找 Gitee 实例。

.PARAMETER SourceGitRoot
    完整 Git 安装目录（包含 usr\bin\sh.exe），用于复制 sh。
    不传时自动从 PATH 或常见安装位置查找。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\fix_oasx_bundled_git_auth.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\fix_oasx_bundled_git_auth.ps1 -InstallRoot "D:\OAS\OnmyojiAutoScript-easy-install"
#>
param(
    [string]$InstallRoot = '',
    [string]$SourceGitRoot = ''
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Text) {
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Write-Ok([string]$Text) {
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Warn([string]$Text) {
    Write-Host "[WARN] $Text" -ForegroundColor Yellow
}

function Get-InstallCandidates {
    $candidates = @()
    foreach ($base in @('F:\tool\game\OAS', 'C:\tool\game\OAS', 'D:\tool\game\OAS', 'E:\tool\game\OAS')) {
        if (Test-Path -LiteralPath $base) {
            $candidates += Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
                ForEach-Object {
                    Get-ChildItem -LiteralPath $_.FullName -Directory -Filter 'OnmyojiAutoScript*' -ErrorAction SilentlyContinue
                }
        }
    }
    return @($candidates | Where-Object {
        Test-Path -LiteralPath (Join-Path $_.FullName 'toolkit\Git\mingw64\bin\git.exe') -PathType Leaf
    } | Sort-Object FullName -Unique)
}

function Find-InstallRoots {
    $all = Get-InstallCandidates
    if ($all.Count -eq 0) {
        throw '未找到 OAS 安装目录，请用 -InstallRoot 指定（目录内应包含 toolkit\Git 与 config\deploy.yaml）。'
    }
    $gitee = @($all | Where-Object {
        $yaml = Join-Path $_.FullName 'config\deploy.yaml'
        if (Test-Path -LiteralPath $yaml) {
            $line = Select-String -LiteralPath $yaml -Pattern '^\s*Repository:\s*https://gitee\.com/' -ErrorAction SilentlyContinue
            return [bool]$line
        }
        return $false
    })
    if ($gitee.Count -gt 0) {
        return @($gitee | ForEach-Object { $_.FullName })
    }
    return @($all | ForEach-Object { $_.FullName })
}

function Find-SourceGitRoot([string]$ExcludeRoot) {
    $roots = @()
    $cmd = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $roots += (Split-Path -Parent (Split-Path -Parent $cmd.Source))
    }
    $roots += @(
        'F:\tool\Git',
        'C:\Program Files\Git',
        'C:\Program Files (x86)\Git',
        'D:\tool\Git',
        'E:\tool\Git'
    )
    foreach ($root in ($roots | Select-Object -Unique)) {
        if (-not $root) { continue }
        if ($ExcludeRoot -and $root.TrimEnd('\') -ieq $ExcludeRoot.TrimEnd('\')) { continue }
        if (Test-Path -LiteralPath (Join-Path $root 'usr\bin\sh.exe') -PathType Leaf) {
            return $root
        }
    }
    throw '未找到包含 usr\bin\sh.exe 的完整 Git，请用 -SourceGitRoot 指定（例如 C:\Program Files\Git）。'
}

function Set-CredentialHelperToWincred([string]$ConfigPath) {
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        $null = New-Item -ItemType File -Path $ConfigPath -Force
    }
    $lines = @(Get-Content -LiteralPath $ConfigPath)
    $out = New-Object System.Collections.Generic.List[string]
    $skipSection = $false
    foreach ($line in $lines) {
        $trim = $line.Trim()
        if ($trim -match '^\[.*\]$') {
            $skipSection = ($trim -eq '[credential]')
        }
        if ($skipSection) {
            continue
        }
        $out.Add($line)
    }
    while ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -eq '') {
        $out.RemoveAt($out.Count - 1)
    }
    $out.Add('[credential]')
    $out.Add("`thelper = ")
    $out.Add("`thelper = wincred")
    $newText = ($out -join "`r`n") + "`r`n"
    $oldText = [System.IO.File]::ReadAllText($ConfigPath)
    if ($oldText -ne $newText) {
        $backup = "$ConfigPath.bak-$(Get-Date -Format 'yyyyMMddHHmmss')"
        [System.IO.File]::Copy($ConfigPath, $backup, $true)
        Get-ChildItem -Path "$ConfigPath.bak-*" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -Skip 1 |
            Remove-Item -Force -ErrorAction SilentlyContinue
        [System.IO.File]::WriteAllText($ConfigPath, $newText, (New-Object System.Text.UTF8Encoding($false)))
        Write-Ok "已更新 $ConfigPath（备份：$backup）"
    } else {
        Write-Ok "$ConfigPath 已是 wincred 配置"
    }
}

function Set-BundledGitExecutable([string]$DeployYaml) {
    if (-not (Test-Path -LiteralPath $DeployYaml)) {
        Write-Warn "未找到 $DeployYaml，跳过"
        return
    }
    $text = [System.IO.File]::ReadAllText($DeployYaml)
    $pattern = '(?m)^(\s*GitExecutable:\s*).*$'
    if ($text -notmatch $pattern) {
        Write-Warn "$DeployYaml 中没有 GitExecutable 字段，跳过"
        return
    }
    $newText = [System.Text.RegularExpressions.Regex]::Replace(
        $text, $pattern, '${1}./toolkit/Git/mingw64/bin/git.exe')
    if ($newText -ne $text) {
        $backup = "$DeployYaml.bak-$(Get-Date -Format 'yyyyMMddHHmmss')"
        [System.IO.File]::Copy($DeployYaml, $backup, $true)
        [System.IO.File]::WriteAllText($DeployYaml, $newText, (New-Object System.Text.UTF8Encoding($false)))
        Write-Ok "已把 GitExecutable 恢复为内置 Git（备份：$backup）"
    } else {
        Write-Ok 'deploy.yaml 已使用内置 Git'
    }
}

function Repair-Install([string]$Root, [string]$SrcGitRoot) {
    Write-Step "安装目录：$Root"
    $bundledGit = Join-Path $Root 'toolkit\Git\mingw64\bin\git.exe'
    if (-not (Test-Path -LiteralPath $bundledGit)) {
        Write-Warn "内置 Git 不存在：$bundledGit"
        return $false
    }

    $srcBin = Join-Path $SrcGitRoot 'usr\bin'
    $dstBin = Join-Path $Root 'toolkit\Git\usr\bin'
    $null = New-Item -ItemType Directory -Force -Path $dstBin
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $Root 'toolkit\Git\usr\tmp')
    $null = New-Item -ItemType Directory -Force -Path (Join-Path $Root 'toolkit\Git\tmp')

    Write-Step '复制 sh.exe 与 msys 运行库'
    [System.IO.File]::Copy((Join-Path $srcBin 'sh.exe'), (Join-Path $dstBin 'sh.exe'), $true)
    Get-ChildItem -LiteralPath $srcBin -Filter 'msys-*.dll' -File | ForEach-Object {
        [System.IO.File]::Copy($_.FullName, (Join-Path $dstBin $_.Name), $true)
    }
    Write-Ok "已复制到 $dstBin"

    Write-Step '配置内置 Git 凭据助手'
    Set-CredentialHelperToWincred (Join-Path $Root 'toolkit\Git\etc\gitconfig')
    Set-CredentialHelperToWincred (Join-Path $Root '.git\config')

    Write-Step '恢复 deploy.yaml 使用内置 Git'
    Set-BundledGitExecutable (Join-Path $Root 'config\deploy.yaml')

    Write-Step '验证内置 Git 访问私库'
    $oldPrompt = $env:GIT_TERMINAL_PROMPT
    $oldAskpass = $env:GIT_ASKPASS
    $env:GIT_TERMINAL_PROMPT = '0'
    Remove-Item Env:GIT_ASKPASS -ErrorAction SilentlyContinue
    try {
        $remote = (& $bundledGit -C $Root remote get-url origin 2>$null)
        if (-not $remote) {
            Write-Warn '无法读取 origin 地址，请确认该目录是 OAS 的 Git 仓库。'
            return $false
        }
        $refs = & $bundledGit -C $Root ls-remote origin 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "内置 Git 认证失败：$($refs -join ' ')"
            return $false
        }
        Write-Ok "私库访问成功：$remote"
        return $true
    } finally {
        $env:GIT_TERMINAL_PROMPT = $oldPrompt
        if ($oldAskpass) { $env:GIT_ASKPASS = $oldAskpass }
    }
}

if ($InstallRoot) {
    if (-not (Test-Path -LiteralPath $InstallRoot)) {
        throw "安装目录不存在：$InstallRoot"
    }
    $roots = @((Resolve-Path -LiteralPath $InstallRoot).Path)
} else {
    $roots = Find-InstallRoots
}

if (-not $SourceGitRoot) {
    $SourceGitRoot = Find-SourceGitRoot -ExcludeRoot (Join-Path $roots[0] 'toolkit\Git')
}
Write-Step "完整 Git：$SourceGitRoot"

$failed = @()
foreach ($root in $roots) {
    if (-not (Repair-Install -Root $root -SrcGitRoot $SourceGitRoot)) {
        $failed += $root
    }
}

if ($failed.Count -gt 0) {
    Write-Host ''
    Write-Warn "以下实例未能通过认证：$($failed -join ', ')"
    Write-Host '这台电脑还没有 Gitee 凭据。请先保存一次凭据，再重新运行本脚本：' -ForegroundColor Yellow
    Write-Host '  方式一（在任意目录运行，按提示输入账号和私人令牌）：' -ForegroundColor Yellow
    Write-Host '    git credential approve' -ForegroundColor Gray
    Write-Host '    protocol=https' -ForegroundColor Gray
    Write-Host '    host=gitee.com' -ForegroundColor Gray
    Write-Host '    username=你的Gitee账号' -ForegroundColor Gray
    Write-Host '    password=你的Gitee私人令牌' -ForegroundColor Gray
    Write-Host '  方式二：用系统 Git 执行一次 git ls-remote 并完成弹窗登录，' -ForegroundColor Yellow
    Write-Host '          凭据会进入 Windows 凭据管理器（git:https://gitee.com）。' -ForegroundColor Yellow
    exit 1
}

Write-Ok '全部实例修复完成，OASX 重启后即可正常拉取私库。'
exit 0
