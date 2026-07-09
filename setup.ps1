$line = "function ma { python '$PSScriptRoot\main.py' @args }"
$profilePath = $PROFILE
$dir = Split-Path $profilePath -Parent
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$content = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
if ($content -and $content.Contains($line)) {
    Write-Host "已配过，直接敲 ma 启动。"
} else {
    Add-Content $profilePath "`n$line"
    Write-Host "好了，重开终端后直接敲 ma 启动。"
}
