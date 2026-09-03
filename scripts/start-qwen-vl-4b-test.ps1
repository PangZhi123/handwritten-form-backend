param(
    [string]$LlamaServer = "",
    [string]$ModelRoot = "E:\QwenModels\Qwen3-VL-4B-Instruct-GGUF",
    [int]$GpuLayers = 99,
    [int]$Port = 8081,
    [int]$ContextSize = 16384
)

# 测试部署脚本：使用 Qwen3-VL-4B-Instruct GGUF（小、快，适合测试/联调环境）。
# 与正式部署脚本 start-qwen-vl-30b-prod.ps1 完全分离，互不影响。
#
# 用法：
#   .\scripts\start-qwen-vl-4b-test.ps1
#   .\scripts\start-qwen-vl-4b-test.ps1 -GpuLayers 40 -Port 8082
#   .\scripts\start-qwen-vl-4b-test.ps1 -LlamaServer "D:\llama.cpp\llama-server.exe"
#
# 启动后后端环境变量（测试场景）：
#   HF_MODEL_BASE_URL = "http://127.0.0.1:8081/v1"
#   HF_MODEL_NAME     = "qwen3-vl-4b-instruct"
# 详见 .env.4b-local-test.example

if (-not $LlamaServer) {
    $resolved = Get-Command llama-server.exe -ErrorAction SilentlyContinue
    if ($resolved) { $LlamaServer = $resolved.Source }
    else { throw "未找到 llama-server.exe，请用 -LlamaServer 指定完整路径。" }
}

$model = Join-Path $ModelRoot "Qwen3VL-4B-Instruct-Q4_K_M.gguf"
$mmproj = Join-Path $ModelRoot "mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf"
if (-not (Test-Path -LiteralPath $model) -or -not (Test-Path -LiteralPath $mmproj)) {
    throw "4B 模型目录缺少主 GGUF 或 mmproj：$ModelRoot"
}

Write-Host "Starting Qwen3-VL-4B-Instruct (TEST) on http://127.0.0.1:$Port"
Write-Host "  model alias : qwen3-vl-4b-instruct"
Write-Host "  ctx-size    : $ContextSize  (4B 识别 128 格表格需 16384，勿调低)"
Write-Host "  gpu layers  : $GpuLayers"

& $LlamaServer `
    --model $model `
    --mmproj $mmproj `
    --alias qwen3-vl-4b-instruct `
    --host 127.0.0.1 `
    --port $Port `
    --ctx-size $ContextSize `
    --parallel 1 `
    --jinja `
    --reasoning off `
    --n-gpu-layers $GpuLayers
