param(
    [string]$LlamaServer = "llama-server.exe",
    [Parameter(Mandatory = $true)]
    [string]$ModelRoot,
    [int]$GpuLayers = 20,
    [int]$Port = 8080
)

$model = Join-Path $modelRoot "Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf"
$mmproj = Join-Path $modelRoot "mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf"

if (-not (Test-Path -LiteralPath $model) -or -not (Test-Path -LiteralPath $mmproj)) {
    throw "Qwen3-VL 主模型或 mmproj 文件不存在。"
}

& $LlamaServer `
    --model $model `
    --mmproj $mmproj `
    --alias qwen3-vl-30b-a3b-thinking `
    --host 127.0.0.1 `
    --port $Port `
    --ctx-size 8192 `
    --parallel 1 `
    --jinja `
    --reasoning on `
    --n-gpu-layers $GpuLayers
