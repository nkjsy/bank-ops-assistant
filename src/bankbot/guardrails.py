"""简单的输入护栏。真正的安全靠 tools.py 里"只能看当前客户的数据"和审批，这里只是第一道过滤。"""
import re

CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
INJECTION_HINTS = [
    "ignore all", "ignore previous", "ignore the above", "disregard", "system prompt",
    "you are now", "忽略以上", "忽略之前",
]


def mask_pii(text: str) -> str:
    """把卡号和邮箱替换掉，不让它们进入模型 / 日志。"""
    text = CARD_RE.sub("[CARD]", text)
    return EMAIL_RE.sub("[EMAIL]", text)


def injection_flags(text: str) -> list[str]:
    low = text.lower()
    return [h for h in INJECTION_HINTS if h in low]


def screen_input(text: str) -> tuple[str, list[str]]:
    """返回 (处理后的文本, 命中的可疑短语)。可疑只告警，不直接拒绝，因为后面还有工具范围限制兜底。"""
    return mask_pii(text), injection_flags(text)
