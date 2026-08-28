# 手写表格电子化算法后端

依据《手写表格电子化转换功能及前后端接口规范-0825》实现的 FastAPI 服务。后端接收一个或多个手写表格图片/PDF和对应的DOCX模板，将全部图片页面与模板表格结构一次性提交给Qwen3-VL，获得最终单元格映射，再生成保持模板结构的可编辑DOCX。

## 处理流程

```text
图片/PDF + DOCX模板
  -> 文件校验与页面解码
  -> 提取模板表格、固定文字和合并单元格结构
  -> 一次请求提交给Qwen3-VL
  -> 校验模型返回的表格数量、行列和坐标
  -> 写入模板副本
  -> 返回识别统计和DOCX下载地址
```

- 原始模板只读，结果始终写入副本。
- 固定文字默认保留，不被模型结果覆盖。
- 表格结构不匹配时返回 `HF0204`，不猜测或错位填充。
- 模型、Python环境和运行数据均应放在源码目录之外。
- 不要在百度网盘同步工程中创建 `.venv`、模型缓存或运行输出。

## 交付内容

发送给测试人员的交付包应包含：

```text
handwritten-form-backend-v0.1.0/
  backend/                 后端源码、依赖、文档和测试样本
  models/
    Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf
    mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf
  SHA256SUMS.txt           模型文件完整性校验
```

可使用 `scripts/package-delivery.ps1` 组装交付包。输出目录必须是尚不存在的新目录：

```powershell
.\scripts\package-delivery.ps1 `
  -ModelRoot "E:\QwenModels\Qwen3-VL-30B-A3B-Thinking-GGUF" `
  -OutputRoot "E:\deliveries\handwritten-form-backend-v0.1.0"
```

模型总大小约19.3 GB，打包前应确保输出磁盘和传输介质具有足够空间。接收方应使用 `Get-FileHash -Algorithm SHA256` 对照 `SHA256SUMS.txt` 验证模型文件。

## 测试服务器要求

- Windows 10/11或Windows Server 2019及以上。
- Python 3.10及以上，推荐3.11或3.12。
- 支持Qwen3-VL多模态GGUF的新版llama.cpp，包含 `llama-server.exe`。
- 建议至少32 GB系统内存；模型主文件约18.6 GB，内存不足时可能无法加载。
- GPU并非强制，但CPU推理会很慢。8 GB显存设备需要CPU/GPU混合加载，并根据显存降低 `GpuLayers`。
- 模型、源码、Python环境和运行数据建议位于不同目录。

推荐目录：

```text
D:/apps/handwritten-form-backend/   后端源码
D:/models/qwen3-vl-30b/             主GGUF和mmproj
D:/python-envs/handwritten-form/    Python环境
D:/handwritten-form-runtime/        上传文件、元数据和结果文件
D:/llama.cpp/                        llama-server及依赖DLL
```

## 一、验证模型文件

模型目录必须包含：

```text
Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf
mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf
```

不要遗漏 `mmproj`；缺少视觉投影文件时模型无法处理图片。

在交付包根目录执行：

```powershell
Get-Content .\SHA256SUMS.txt
Get-FileHash .\models\*.gguf -Algorithm SHA256
```

两边的哈希值必须一致。

## 二、安装llama.cpp

测试服务器需要准备支持CUDA和多模态输入的新版llama.cpp Windows构建，目录中至少包含：

```text
llama-server.exe
llama-cli.exe
CUDA构建对应的DLL文件（使用CUDA版本时）
```

检查运行时：

```powershell
D:\llama.cpp\llama-server.exe --version
D:\llama.cpp\llama-server.exe --help
```

如果提示缺少DLL，应使用完整的llama.cpp发布包，不能只复制 `llama-server.exe`。

## 三、启动Qwen3-VL模型服务

进入 `backend` 目录后运行：

```powershell
.\scripts\start-qwen-vl.ps1 `
  -LlamaServer "D:\llama.cpp\llama-server.exe" `
  -ModelRoot "D:\models\qwen3-vl-30b" `
  -GpuLayers 20 `
  -Port 8080
```

脚本等价于使用以下关键参数：

- 主模型：`Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf`
- 视觉模型：`mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf`
- 模型别名：`qwen3-vl-30b-a3b-thinking`
- 上下文：8192
- 并发：1
- 推理模式：Thinking开启
- 监听地址：`127.0.0.1:8080`

模型端口只供算法后端访问，不需要向前端或公网开放。

若发生显存不足，按顺序尝试降低 `GpuLayers`：

```text
20 -> 16 -> 12 -> 8 -> 0
```

模型启动后验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models
```

能够返回 `qwen3-vl-30b-a3b-thinking` 后再启动算法后端。

## 四、安装后端依赖

不要在同步源码目录中创建虚拟环境。以下示例将环境放在独立目录：

```powershell
python -m venv D:\python-envs\handwritten-form
& D:\python-envs\handwritten-form\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\requirements-lock.txt
python -m pip install --no-deps -e .
```

## 五、配置环境变量

以 `.env.test-server.example` 为参考，在启动后端的PowerShell窗口设置：

```powershell
$env:HF_RUNTIME_ROOT = "D:\handwritten-form-runtime"
$env:HF_OCR_BACKEND = "qwen_vl"
$env:HF_MODEL_BASE_URL = "http://127.0.0.1:8080/v1"
$env:HF_MODEL_NAME = "qwen3-vl-30b-a3b-thinking"
$env:HF_MODEL_API_KEY = "local"
$env:HF_MODEL_TIMEOUT_SECONDS = "600"
$env:HF_MODEL_RETRIES = "2"
$env:HF_MODEL_MAX_TOKENS = "8192"
$env:HF_MODEL_MAX_CONCURRENCY = "1"
$env:HF_PUBLIC_BASE_URL = "http://测试服务器IP:8000"
$env:HF_CORS_ORIGINS = "http://前端测试地址:端口"
```

注意：

- `HF_PUBLIC_BASE_URL` 必须是前端能够访问的算法后端地址，不能填写 `127.0.0.1`。
- `HF_CORS_ORIGINS` 填写前端页面的Origin；多个地址使用英文逗号分隔。
- `HF_RUNTIME_ROOT` 必须具有写权限，并位于源码目录之外。

## 六、启动算法后端

```powershell
python -m uvicorn handwritten_form_api.main:app --host 0.0.0.0 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

正常响应：

```json
{"status":"ok","version":"0.1.0"}
```

服务器防火墙应向前端测试网络开放端口8000；端口8080保持服务器本机访问。

## 七、使用内置样本验证

工程已经包含测试图片和对应DOCX模板：

```text
test-data/case-01/table_handwritten_img.jpg
test-data/case-01/table_template.docx
```

执行完整转换：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/handwritten-form/v1/convert" `
  -F "sourceFiles=@test-data/case-01/table_handwritten_img.jpg" `
  -F "templateFile=@test-data/case-01/table_template.docx" `
  -F "documentName=防渗墙造孔清孔质量检查合格证" `
  -F "language=zh-CN" `
  -F "preserveOriginalText=true"
```

成功响应会返回：

- `resultFileId`
- `resultFileName`
- `downloadUrl`
- 表格、单元格、填充和低置信度统计

使用返回的 `downloadUrl` 下载DOCX，并检查：

1. Microsoft Word能够正常打开。
2. 模板固定文字、表格结构和合并单元格保持不变。
3. 手写内容填入正确单元格。
4. 输出文字和表格仍可编辑。
5. 低置信度数量与需要人工复核的内容基本一致。

## 八、接口

- `POST /api/handwritten-form/v1/convert`
- `GET /api/handwritten-form/v1/files/{resultFileId}/download`
- `GET /health`
- Swagger：`http://测试服务器IP:8000/docs`

前端调用方式参见 `docs/frontend-integration.md`。

## 九、自动化测试

```powershell
python -m pip install -r .\requirements-dev-lock.txt
python -m pytest
```

自动化测试使用模拟模型响应，不需要加载19 GB模型；内置业务样本测试必须在真实模型服务启动后执行。

## 十、常见问题

### 无法连接模型

检查 `http://127.0.0.1:8080/v1/models`，确认模型别名与 `HF_MODEL_NAME` 一致。

### 模型不识别图片

确认启动参数包含正确的 `--mmproj`，并使用支持Qwen3-VL多模态的llama.cpp版本。

### CUDA显存不足

降低 `GpuLayers`，关闭其他占用显存的程序；必要时设置为0使用CPU和系统内存。

### 转换返回HF0204

模型判定源表格与DOCX模板结构不一致。检查图片是否完整、模板是否对应，不要强制绕过结构校验。

### 请求超时

30B模型在低显存或CPU环境中可能非常慢。确认网关和前端请求超时不小于后端的 `HF_MODEL_TIMEOUT_SECONDS`。

## 其他文档

- `docs/test-server-deployment.md`：测试服务器部署摘要。
- `docs/frontend-integration.md`：前端接口调用说明。
- `docs/delivery-package.md`：交付包制作说明。
- `.env.test-server.example`：测试服务器配置样例。
