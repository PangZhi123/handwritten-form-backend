# 前端联调说明

## 联调架构

前端只访问算法后端公开地址，不直接访问 Qwen3-VL，也不需要持有模型文件。

```text
前端浏览器
  -> POST /api/handwritten-form/v1/convert
算法后端
  -> http://127.0.0.1:8080/v1/chat/completions
Qwen3-VL llama-server（后端测试服务器内部）
```

测试服务器管理员需提供类似 `http://192.168.1.100:8000` 的算法后端地址，并将前端站点地址加入 `HF_CORS_ORIGINS`。

## 上传并转换

浏览器示例：

```javascript
const form = new FormData();
for (const file of sourceFiles) form.append("sourceFiles", file);
form.append("templateFile", templateFile);
form.append("documentName", "施工记录表");
form.append("language", "zh-CN");
form.append("preserveOriginalText", "true");

const response = await fetch(`${algorithmBaseUrl}/api/handwritten-form/v1/convert`, {
  method: "POST",
  body: form,
});
const result = await response.json();
if (!result.success) throw new Error(`${result.code}: ${result.message}`);
```

不要手动设置 `Content-Type`；浏览器会自动生成带 boundary 的 `multipart/form-data`。

成功响应中的 `data.downloadUrl` 在测试服务器配置 `HF_PUBLIC_BASE_URL` 后为绝对地址，前端可直接用于下载。

## 下载结果

```javascript
window.location.assign(result.data.downloadUrl);
```

也可以使用 `fetch` 获取 Blob；响应会暴露 `Content-Disposition`，供前端读取文件名。

## 错误处理

业务错误仍返回统一 JSON：

```json
{
  "requestId": "req_xxx",
  "success": false,
  "code": "HF0204",
  "message": "表格结构不匹配",
  "data": null,
  "timestamp": "2026-08-28T15:30:00+08:00"
}
```

前端应展示 `message`，并保留 `requestId` 便于后端查日志。

## 联调前检查

1. 浏览器能够访问算法后端 `/health`。
2. 测试服务器上的 llama-server 已加载主 GGUF 和 mmproj。
3. `HF_PUBLIC_BASE_URL` 是前端可访问的地址，不是 `127.0.0.1`。
4. 前端 Origin 已加入 `HF_CORS_ORIGINS`。
5. 测试服务器运行目录具有写权限且位于源码目录之外。

