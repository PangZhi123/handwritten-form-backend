# 联调交付包制作

交付包应同时包含后端源码、主GGUF、视觉投影模型和校验文件。不要把模型长期放进源码工程；仅在最终交付目录中组装。

```powershell
.\scripts\package-delivery.ps1 `
  -ModelRoot "D:\models\qwen3-vl-30b" `
  -OutputRoot "D:\deliveries\handwritten-form-backend-v0.1.0"
```

脚本要求输出目录不存在，避免覆盖已有交付物。生成结构：

```text
handwritten-form-backend-v0.1.0/
  backend/
  models/
    Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf
    mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf
  SHA256SUMS.txt
```

接收方应先执行 `Get-FileHash -Algorithm SHA256` 并与 `SHA256SUMS.txt` 对比，再进行部署。

