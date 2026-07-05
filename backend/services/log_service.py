import re


KEY_ASSIGNMENT_RE = re.compile(r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD))\s*=\s*([^\s]+)")
BEARER_RE = re.compile(r"(?i)(Authorization:\s*Bearer\s+)([^\s]+)")
SK_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b")


def mask_sensitive_text(text: str) -> str:
    masked = KEY_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=***", text)
    masked = BEARER_RE.sub(lambda match: f"{match.group(1)}***", masked)
    return SK_KEY_RE.sub("***", masked)
