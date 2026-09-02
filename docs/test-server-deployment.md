# 后端测试服务器部署

## 1. 准备运行目录

源码、Python 环境、模型和运行数据应分开：

```text
D:/apps/handwritten-form-backend/   源码
D:/python-envs/handwritten-form/    Python 环境
D:/models/qwen3-vl-30b/             GGUF 与 mmproj
D:/handwritten-form-runtime/        上传文件、结果和元数据
```

不要在源码目录创建 `.venv`，也不要把模型复制进源码包。

## 2. 启动模型服务

```powershell
.\scripts\start-qwen-vl.ps1 `
  -LlamaServer "D:\llama.cpp\llama-server.exe" `
  -ModelRoot "D:\models\qwen3-vl-30b" `
  -GpuLayers 20 `
  -Port 8080
```

模型服务只需监听 `127.0.0.1`，无需向前端或公网开放。

## 3. 配置算法后端

根据 `.env.test-server.example` 设置系统环境变量。关键项：

- `HF_MODEL_BASE_URL`：算法后端访问模型服务的内部地址。
- `HF_PUBLIC_BASE_URL`：前端访问算法后端的公开地址。
- `HF_CORS_ORIGINS`：允许联调的前端站点 Origin。
- `HF_RUNTIME_ROOT`：源码目录之外的运行数据目录。

## 4. 启动 API

```powershell
python -m pip install -r .\requirements.txt
python -m pip install --no-deps -e .
python -m uvicorn handwritten_form_api.main:app --host 0.0.0.0 --port 8000
```

测试：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8080/v1/models
```

服务器防火墙只需向前端测试网络开放 API 端口 `8000`；模型端口 `8080` 保持本机访问。
