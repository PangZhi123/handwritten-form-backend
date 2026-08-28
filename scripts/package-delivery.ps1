param(
    [Parameter(Mandatory = $true)]
    [string]$ModelRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
if ($resolvedOutput -eq [System.IO.Path]::GetPathRoot($resolvedOutput)) {
    throw "OutputRoot不能是磁盘根目录。"
}
if (Test-Path -LiteralPath $resolvedOutput) {
    throw "输出目录已存在，请指定一个新的空目录：$resolvedOutput"
}

$modelFile = Join-Path $ModelRoot "Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf"
$mmprojFile = Join-Path $ModelRoot "mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf"
if (-not (Test-Path -LiteralPath $modelFile) -or -not (Test-Path -LiteralPath $mmprojFile)) {
    throw "ModelRoot缺少主GGUF或mmproj文件。"
}

$backendOutput = Join-Path $resolvedOutput "backend"
$modelOutput = Join-Path $resolvedOutput "models"
New-Item -ItemType Directory -Path $backendOutput,$modelOutput | Out-Null

foreach ($name in @("src","tests","scripts","docs","test-data")) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $name) -Destination $backendOutput -Recurse
}
foreach ($name in @("pyproject.toml","requirements-lock.txt","requirements-dev-lock.txt",
                     "README.md",".env.example",".env.test-server.example",".gitignore")) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $name) -Destination $backendOutput
}
Copy-Item -LiteralPath $modelFile,$mmprojFile -Destination $modelOutput

$checksumFile = Join-Path $resolvedOutput "SHA256SUMS.txt"
Get-ChildItem -LiteralPath $modelOutput -File | ForEach-Object {
    $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
    "$($hash.Hash.ToLower())  models/$($_.Name)"
} | Set-Content -LiteralPath $checksumFile -Encoding UTF8

Write-Output "交付目录已生成：$resolvedOutput"
