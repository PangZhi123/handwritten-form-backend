# 测试样本 case-01

本目录保存一组手写表格电子化联调样本：

- `table_handwritten_img.jpg`：待识别的手写表格图片。
- `table_template.docx`：对应的可编辑 Word 表格模板。

接口测试示例：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/handwritten-form/v1/convert" `
  -F "sourceFiles=@test-data/case-01/table_handwritten_img.jpg" `
  -F "templateFile=@test-data/case-01/table_template.docx" `
  -F "documentName=防渗墙造孔清孔质量检查合格证" `
  -F "language=zh-CN" `
  -F "preserveOriginalText=true"
```

SHA-256：

```text
4881ac3ed8046be98b200f25fae7959b4910e4b6c6bea081a4712654abdf3f6a  table_template.docx
b08752fc4fa7d57b86a220f6b16a1c4e25410962bcae0e3b96344c93e3556280  table_handwritten_img.jpg
```

