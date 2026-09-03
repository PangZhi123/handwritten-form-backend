param(
    [string]$LlamaServer = "",
    [string]$ModelRoot = "E:\QwenModels\Qwen3-VL-30B-A3B-Thinking-GGUF",
    [int]$GpuLayers = 20,
    [int]$Port = 8080,
    [int]$ContextSize = 8192
)

# 正式部署脚本：使用 Qwen3-VL-30B-A3B-Thinking GGUF（精度高，正式环境使用）。
# 与测试部署脚本 start-qwen-vl-4b-test.ps1 完全分离，互不影响。
#
# 用法：
#   .\scripts\start-qwen-vl-30b-prod.ps1
#   .\scripts\start-qwen-vl-30b-prod.ps1 -GpuLayers 12 -Port 8080
#   .\scripts\start-qwen-vl-30b-prod.ps1 -LlamaServer "D:\llama.cpp\llama-server.exe"
#
# 启动后后端环境变量（正式场景）：
#   HF_MODEL_BASE_URL = "http://127.0.0.1:8080/v1"
#   HF_MODEL_NAME     = "qwen3-vl-30b-a3b-thinking"
# 详见 .env.test-server.example
#
# 显存不足时按顺序降低 GpuLayers：20 -> 16 -> 12 -> 8 -> 0

if (-not $LlamaServer) {
    $resolved = Get-Command llama-server.exe -ErrorAction SilentlyContinue
    if ($resolved) { $LlamaServer = $resolved.Source }
    else { throw "未找到 llama-server.exe，请用 -LlamaServer 指定完整路径。" }
}

$model = Join-Path $ModelRoot "Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf"
$mmproj = Join-Path $ModelRoot "mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf"
if (-not (Test-Path -LiteralPath $model) -or -not (Test-Path -LiteralPath $mmproj)) {
    throw "30B 模型目录缺少主 GGUF 或 mmproj：$ModelRoot"
}

Write-Host "Starting Qwen3-VL-30B-A3B-Thinking (PROD) on http://127.0.0.1:$Port"
Write-Host "  model alias : qwen3-vl-30b-a3b-thinking"
Write-Host "  ctx-size    : $ContextSize"
Write-Host "  gpu layers  : $GpuLayers"

& $LlamaServer `
    --model $model `
    --mmproj $mmproj `
    --alias qwen3-vl-30b-a3b-thinking `
    --host 127.0.0.1 `
    --port $Port `
    --ctx-size $ContextSize `
    --parallel 1 `
    --jinja `
    --reasoning on `
    --n-gpu-layers $GpuLayers
