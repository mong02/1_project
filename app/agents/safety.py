from typing import List, Tuple

DEFAULT_RISK_PATTERNS = [
    ("100%", "과장 가능"),
    ("무조건", "과장 가능"),
    ("완치", "의료/효능 과장 리스크"),
    ("최고", "비교/과장 리스크"),
    ("1등", "근거 없는 우월 주장 리스크"),
]

def scan_risks(text: str, banned_words: List[str]) -> List[str]:
    flags = []
    for w in banned_words:
        if w and w in text:
            flags.append(f"금지어 포함: {w}")
    for pat, reason in DEFAULT_RISK_PATTERNS:
        if pat in text:
            flags.append(f"리스크 표현: '{pat}' ({reason})")
    return flags
