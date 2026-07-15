$kernelDir = $PSScriptRoot
$line = @"
# ma 命令块
function ma {
    $env:PYTHONPATH = "$kernelDir\src"
    if ($args[0] -eq "ui" -or $args[0] -eq "web") {
        python -m kernel --web
    } else {
        python -m kernel @args
    }
}
"@
$profilePath = $PROFILE
$dir = Split-Path $profilePath -Parent
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$content = (Get-Content $profilePath -Raw -ErrorAction SilentlyContinue) -replace "`r`n", "`n"
$marker = "# ma 命令块"

# 移除旧版 function ma（单行或多行，直到空行或下一个声明）
$lines = $content -split "`n"
$newLines = @()
$skip = $false
foreach ($line in $lines) {
    if ($line -match '^function ma\b') { $skip = $true; continue }
    if ($skip) {
        if ($line -match '^$' -or $line -match '^function ') { $skip = $false }
        if ($skip) { continue }
    }
    $newLines += $line
}
$content = $newLines -join "`n"

# 写入当前版本
if ($content -and $content.Contains($marker)) {
    $content = $content -replace "(?s)# ma 命令块.*?(?=`n`n|`$)", $line.TrimEnd()
    Set-Content $profilePath $content
    Write-Host "已更新 ma 命令。"
} else {
    Add-Content $profilePath "`n$line"
    Write-Host "好了，重开终端后直接敲 ma 启动。"
}
