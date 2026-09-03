param(
    [string]$OllamaBaseUrl = "http://127.0.0.1:11434/v1",
    [string]$ModelName = "handwritten-form-qwen3-vl:4b-ctx",
    [int]$Port = 8000,
    [string]$RuntimeRoot = "E:\BaiduSyncdisk\G-Program_Related\handwritten-form-runtime",
    [string]$Python = "auto"
)

# 一键启动手写表格电子化后端，使用本地 Ollama 千问视觉模型。
# 依赖：本机已运行 Ollama，且已创建 handwritten-form-qwen3-vl:4b-ctx
#       （用项目根目录 Modelfile.qwen3-vl-4b-instruct 创建）。
#
# 用法：
#   .\scripts\start-local-ollama-backend.ps1
#   .\scripts\start-local-ollama-backend.ps1 -Port 9000
#   .\scripts\start-local-ollama-backend.ps1 -Python "C:\...\python.exe"

$srcRoot = Join-Path $PSScriptRoot "..\src"

# 选择可用的 Python（本机默认 python 可能是空的沙箱环境，优先 py -3.10）
$pythonCmd = @()
if ($Python -eq "auto") {
    $candidate = $null
    & py -3.10 -c "import fastapi, uvicorn, cv2, docx" 2>$null
    if ($LASTEXITCODE -eq 0) { $candidate = @("py", "-3.10") }
    else {
        & python -c "import fastapi, uvicorn, cv2, docx" 2>$null
        if ($LASTEXITCODE -eq 0) { $candidate = @("python") }
    }
    if (-not $candidate) { throw "未找到已安装后端依赖的 Python，请用 -Python 指定解释器路径。" }
    $pythonCmd = $candidate
} else {
    $pythonCmd = @($Python)
}

$env:HF_RUNTIME_ROOT = $RuntimeRoot
$env:HF_OCR_BACKEND = "qwen_vl"
$env:HF_MODEL_BASE_URL = $OllamaBaseUrl
$env:HF_MODEL_NAME = $ModelName
$env:HF_MODEL_API_KEY = "ollama"
$env:HF_MODEL_TIMEOUT_SECONDS = "600"
$env:HF_MODEL_RETRIES = "2"
$env:HF_MODEL_MAX_TOKENS = "8192"
$env:HF_MODEL_MAX_CONCURRENCY = "1"
$env:HF_PUBLIC_BASE_URL = "http://127.0.0.1:$Port"
$env:HF_CORS_ORIGINS = "http://localhost:5173"
$env:PYTHONPATH = $srcRoot

Write-Host "Starting handwritten-form backend on http://127.0.0.1:$Port"
Write-Host "  python: $($pythonCmd -join ' ')"
Write-Host "  model : $ModelName  via $OllamaBaseUrl"
Write-Host "  runtime root: $RuntimeRoot"
& $pythonCmd[0] @($pythonCmd[1..($pythonCmd.Count - 1)]) -m uvicorn handwritten_form_api.main:app --host 127.0.0.1 --port $Port
