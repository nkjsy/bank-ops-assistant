"""Simple input guardrails. Real safety comes from tools.py ("only see the current customer's data") and approval; this is just a first filter."""
import re

CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
INJECTION_HINTS = [
    "ignore all", "ignore previous", "ignore the above", "disregard", "system prompt",
    "you are now",
]


def mask_pii(text: str) -> str:
    """Replace card numbers and emails so they never reach the model / logs."""
    text = CARD_RE.sub("[CARD]", text)
    return EMAIL_RE.sub("[EMAIL]", text)


def injection_flags(text: str) -> list[str]:
    low = text.lower()
    return [h for h in INJECTION_HINTS if h in low]


def screen_input(text: str) -> tuple[str, list[str]]:
    """Return (processed text, suspicious phrases matched). Suspicious input only triggers a warning, not a rejection, because tool scoping is the backstop."""
    return mask_pii(text), injection_flags(text)
