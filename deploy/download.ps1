# Shared by the first-run bootstrap and its offline download/failover tests.
function Get-DownloadHash([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    } finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

function Receive-Download([string]$url, [string]$destination) {
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        & curl.exe --fail --location --connect-timeout 15 --max-time 600 --speed-limit 1024 --speed-time 45 --output $destination $url
        if ($LASTEXITCODE -ne 0) { throw "Download failed (curl $LASTEXITCODE): $url" }
    } else {
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $destination -TimeoutSec 120
    }
}

function Get-VerifiedDownload($entry, [string]$cache) {
    $target = Join-Path $cache $entry.filename
    if ((Test-Path -LiteralPath $target) -and (Get-DownloadHash $target) -eq $entry.sha256) {
        Write-Host "Using verified cached download: $($entry.filename)"
        return $target
    }
    $urls = @()
    if ($entry.PSObject.Properties['mirrors']) { $urls += @($entry.mirrors) }
    $urls += $entry.url
    $lastError = ''
    foreach ($url in $urls) {
        for ($attempt = 1; $attempt -le 2; $attempt++) {
            try {
                Write-Host "Downloading $($entry.filename) from $url (attempt $attempt/2)..."
                Receive-Download $url "$target.part"
                if ((Get-DownloadHash "$target.part") -ne $entry.sha256) {
                    throw "SHA256 verification failed: $($entry.filename) from $url"
                }
                Move-Item -LiteralPath "$target.part" -Destination $target -Force
                return $target
            } catch {
                $lastError = $_.Exception.Message
                Write-Warning $lastError
            }
        }
    }
    throw "All download sources failed for $($entry.filename). Check your network or HTTPS_PROXY and retry. Last error: $lastError"
}
