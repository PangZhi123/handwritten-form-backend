# 测试部署（4B 模型）说明

> 本说明针对**测试环境**：使用 Qwen3-VL-4B-Instruct 模型（约 2.8 GB，速度快、占用低），适合测试/联调。
> **正式环境**使用 30B 模型（精度更高），部署步骤见根目录 `README.md` 与 `docs/test-server-deployment.md`。
> 测试（4B）与正式（30B）共用同一套后端代码，仅模型服务不同，两套脚本、配置完全分离，互不影响。

---

## 1. 需要准备的文件

### 1.1 模型文件（4B，共约 2.8 GB）

测试部署需要两个模型文件，来自目录 `E:\QwenModels\Qwen3-VL-4B-Instruct-GGUF`：

| 文件 | 大小 | 必需 | 说明 |
|---|---|---|---|
| `Qwen3VL-4B-Instruct-Q4_K_M.gguf` | 2.5 GB | ✅ 必须 | 主模型 |
| `mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf` | 0.43 GB | ✅ 必须 | 视觉投影，缺少时模型无法识别图片 |

> ⚠️ 只复制这两个 `.gguf` 文件。模型目录中的 `.msc`、`.mv`、`._____temp`、`configuration.json` 是下载残留，**不要**随模型一起同步。

### 1.2 llama.cpp（模型运行组件）

- 支持 Qwen3-VL 多模态输入的新版 llama.cpp Windows 构建。
- 必须使用**完整发布包**：`llama-server.exe` + 同目录下全部 DLL 文件（`ggml.dll`、`llama.dll`、`mtmd.dll` 等）。
- ⚠️ 不能只复制 `llama-server.exe`，缺少 DLL 会启动失败。

### 1.3 后端源码包（backend）

测试环境需要后端完整源码，至少包含：

```text
backend/
  src/                       后端代码
  scripts/
    start-qwen-vl-4b-test.ps1    测试(4B)模型启动脚本  ← 关键
    start-qwen-vl-30b-prod.ps1   正式(30B)模型启动脚本（测试环境可不用）
    smoke-local-qwen.py          冒烟测试脚本（可选）
  requirements.txt           Python 依赖
  test-data/case-01/         内置测试样本（图片 + DOCX 模板）
  .env.4b-local-test.example 4B 测试环境变量样例
```

### 1.4 Python 环境

- Python 3.10 及以上（推荐 3.10 / 3.11）。
- 依赖：`pip install -r requirements.txt`。

### 1.5 运行数据目录（runtime）

- 一个**空目录**，有读写权限，用于存放上传文件、识别结果和元数据。
- 必须放在源码目录之外，不要放进百度网盘同步目录。

---

## 2. 推荐目录规划

```text
D:/apps/handwritten-form-backend/   后端源码（1.3）
D:/models/qwen3-vl-4b/             4B 两个 .gguf 文件（1.1）
D:/llama.cpp/                        llama-server.exe + DLL（1.2）
D:/python-envs/handwritten-form/    Python 环境（1.4）
D:/handwritten-form-runtime/        运行数据目录（1.5）
```

---

## 3. 部署启动步骤

### 3.1 放置模型文件

把 4B 两个 `.gguf` 放入模型目录（如 `D:/models/qwen3-vl-4b/`）：

```powershell
Copy-Item "E:\QwenModels\Qwen3-VL-4B-Instruct-GGUF\Qwen3VL-4B-Instruct-Q4_K_M.gguf" "D:\models\qwen3-vl-4b\"
Copy-Item "E:\QwenModels\Qwen3-VL-4B-Instruct-GGUF\mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf" "D:\models\qwen3-vl-4b\"
```

### 3.2 确认 llama.cpp 可运行

```powershell
D:\llama.cpp\llama-server.exe --version
```

能输出版本号说明 DLL 完整；提示缺少 DLL 则改用完整发布包。

### 3.3 安装后端依赖

```powershell
cd D:\apps\handwritten-form-backend
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
python -m pip install --no-deps -e .
```

### 3.4 启动 4B 模型服务

```powershell
cd D:\apps\handwritten-form-backend
.\scripts\start-qwen-vl-4b-test.ps1
```

脚本关键参数（均已内置，无需手动指定）：

- 主模型：`Qwen3VL-4B-Instruct-Q4_K_M.gguf`
- 视觉模型：`mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf`
- 模型别名：`qwen3-vl-4b-instruct`
- 监听：`127.0.0.1:8081`（测试专用端口，与正式 8080 不冲突）
- 上下文：**16384**（128 格表格完整输出必需，不要调低）
- 推理模式：关闭（Instruct 非 Thinking 模型）

如果模型文件不在默认目录，可指定：

```powershell
.\scripts\start-qwen-vl-4b-test.ps1 -ModelRoot "D:\models\qwen3-vl-4b"
```

启动后保持该窗口运行，看到 `model loaded` 后验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8081/v1/models
```

能返回 `qwen3-vl-4b-instruct` 即为成功，再启动算法后端。

### 3.5 配置环境变量

以 `.env.4b-local-test.example` 为参考，在**启动后端的 PowerShell 窗口**设置：

```powershell
$env:HF_RUNTIME_ROOT = "D:\handwritten-form-runtime"
$env:HF_OCR_BACKEND = "qwen_vl"
$env:HF_MODEL_BASE_URL = "http://127.0.0.1:8081/v1"
$env:HF_MODEL_NAME = "qwen3-vl-4b-instruct"
$env:HF_MODEL_API_KEY = "local"
$env:HF_MODEL_TIMEOUT_SECONDS = "600"
$env:HF_MODEL_RETRIES = "2"
$env:HF_MODEL_MAX_TOKENS = "8192"
$env:HF_MODEL_MAX_CONCURRENCY = "1"
$env:HF_PUBLIC_BASE_URL = "http://测试服务器IP:8000"
$env:HF_CORS_ORIGINS = "http://前端测试地址:端口"
```

注意：

- `HF_MODEL_BASE_URL` 端口必须是 **8081**（对应 4B 模型服务）。
- `HF_MODEL_NAME` 必须是 `qwen3-vl-4b-instruct`（对应 4B 别名）。
- `HF_PUBLIC_BASE_URL` 是前端能访问的地址，不能填 `127.0.0.1`。
- `HF_RUNTIME_ROOT` 必须存在且有写权限。

### 3.6 启动算法后端

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

防火墙只需向前端测试网络开放 **8000** 端口；模型端口 **8081** 保持服务器本机访问。

---

## 4. 端到端测试（内置样本）

后端和模型服务都启动后，在 backend 目录执行：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/handwritten-form/v1/convert" `
  -F "sourceFiles=@test-data/case-01/table_handwritten_img.jpg" `
  -F "templateFile=@test-data/case-01/table_template.docx" `
  -F "documentName=防渗墙造孔清孔质量检查合格证" `
  -F "language=zh-CN" `
  -F "preserveOriginalText=true"
```

成功时返回 `success=true`，实测 4B 模型的识别统计：

```text
recognizedTableCount = 1
recognizedCellCount  = 128
filledCellCount      = 14
lowConfidenceCellCount = 0
```

返回的 `resultFileId` 拼出下载地址：`http://测试服务器IP:8000/api/handwritten-form/v1/results/{resultFileId}`，下载的 DOCX 可打开检查 14 处手写值是否正确填入、模板结构是否保留。

也可直接打开浏览器访问 Swagger 页面操作：`http://127.0.0.1:8000/docs`。

---

## 5. 常见问题

### 模型服务启动报缺少 DLL

必须使用完整 llama.cpp 发布包，把 `llama-server.exe` 和同目录 DLL 一起复制，不能只复制 exe。

### `/v1/models` 连接失败或返回 503

模型还在加载，稍等几秒重试；或检查 4B 模型服务端口是否为 8081。

### 转换返回 HF0204

模型判定源表格与 DOCX 模板结构不一致。检查图片是否完整、模板是否对应。4B 模型上下文若被调低到 8192 以下可能导致输出截断而误报结构不匹配，确认上下文保持 16384。

### 请求超时 / 识别慢

4B 模型已很快（单次识别约 7 秒）。若仍超时，检查 `HF_MODEL_TIMEOUT_SECONDS` 是否不小于 600。

### 识别内容有少量误差

4B 模型精度低于正式 30B，个别手写字符可能识别不准（例如字母 I 漏识别）。测试阶段以流程跑通为主，精度验收请以正式 30B 结果为准。

---

## 6. 与正式部署（30B）的差异速查

| 项目 | 测试（4B） | 正式（30B） |
|---|---|---|
| 启动脚本 | `start-qwen-vl-4b-test.ps1` | `start-qwen-vl-30b-prod.ps1` |
| 模型文件 | 4B 两个 `.gguf`（约 2.8 GB） | 30B 两个 `.gguf`（约 19.3 GB） |
| 模型别名 | `qwen3-vl-4b-instruct` | `qwen3-vl-30b-a3b-thinking` |
| 端口 | 8081 | 8080 |
| 上下文 | 16384 | 8192 |
| 推理模式 | 关闭 | Thinking 开启 |
| GPU 层 | 99（全量 GPU） | 20（按显存调整） |
| 环境变量样例 | `.env.4b-local-test.example` | `.env.test-server.example` |
| 用途 | 测试 / 联调 | 正式验收 / 生产 |
