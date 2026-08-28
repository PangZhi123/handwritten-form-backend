from __future__ import annotations


class BusinessError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


ERRORS = {
    "HF0101": "源文件缺失",
    "HF0102": "模板缺失",
    "HF0103": "文件格式不支持",
    "HF0104": "文件过大或数量超限",
    "HF0201": "图像无法解析",
    "HF0202": "未识别到表格",
    "HF0203": "模板无可填写表格",
    "HF0204": "表格结构不匹配",
    "HF0301": "手写识别失败",
    "HF0302": "Word生成失败",
    "HF0401": "结果文件不存在",
}


def fail(code: str, detail: str | None = None, http_status: int = 400) -> BusinessError:
    message = ERRORS[code]
    if detail:
        message = f"{message}：{detail}"
    return BusinessError(code, message, http_status)

