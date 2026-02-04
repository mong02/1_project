"""
텍스트 처리 유틸리티

AI 생성 텍스트의 후처리, 문단 나누기, 특수문자 제거 등을 담당합니다.
"""

import re
from typing import List, Any


# ============================================
# 기본 유틸리티 함수
# ============================================

def safe_list(x: Any) -> List[Any]:
    """값이 리스트인지 확인하고, 아니면 빈 리스트 반환"""
    return x if isinstance(x, list) else []


def safe_str(x: Any) -> str:
    """값을 안전하게 문자열로 변환"""
    return str(x).strip() if x is not None else ""


def unique_list(items: List[str]) -> List[str]:
    """
    리스트에서 중복을 제거하고 순서를 유지합니다.
    
    Args:
        items: 문자열 리스트
    
    Returns:
        중복이 제거된 리스트
    """
    seen = set()
    result = []
    
    for item in items:
        key = str(item).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    
    return result


# ============================================
# AI 톤 제거 (Anti-AI Tone)
# ============================================

# AI가 자주 사용하는 패턴들
AI_TONE_PATTERNS = [
    r"\b결론적으로\b",
    r"\b요약하면\b",
    r"\b정리하자면\b",
    r"\b따라서\b",
    r"\b그러므로\b",
    r"\b한편\b",
    r"\b또한\b",
    r"\b추가로\b",
    r"\b마지막으로\b",
    r"\b전반적으로\b",
    r"\b종합적으로\b",
    r"\b본 글에서는\b",
    r"\b이번 글에서는\b",
    r"\b지금부터\b",
    r"\b아래에서\b",
    r"\b살펴보겠습니다\b",
    r"\b알아보겠습니다\b",
    r"\b설명하겠습니다\b",
]

AI_OPENERS = [
    "먼저,",
    "우선,",
    "다음으로,",
    "마지막으로,",
    "정리하면,",
    "결론적으로,",
]


def collapse_spaces(text: str) -> str:
    """연속된 공백과 줄바꿈을 정리합니다."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def dedupe_lines(text: str) -> str:
    """연속으로 중복된 라인을 제거합니다."""
    lines = text.splitlines()
    result: List[str] = []
    prev = None
    
    for line in lines:
        current = line.strip()
        # 이전 라인과 같으면서 비어있지 않으면 스킵
        if prev is not None and current and current == prev:
            continue
        result.append(line)
        prev = current if current else prev
    
    return "\n".join(result)


def soften_ai_tone(text: str, strong: bool = True) -> str:
    """
    AI 특유의 톤을 부드럽게 만듭니다.
    
    Args:
        text: 처리할 텍스트
        strong: True면 강하게 제거, False면 약하게 제거
    
    Returns:
        AI 톤이 제거된 텍스트
    """
    if not text:
        return ""
    
    result = text
    
    if strong:
        # AI가 자주 쓰는 문장 시작 패턴 제거
        for opener in AI_OPENERS:
            result = re.sub(rf"(^|\n\n){re.escape(opener)}\s*", r"\1", result)
        
        # AI 톤 패턴 제거
        for pattern in AI_TONE_PATTERNS:
            result = re.sub(pattern, "", result)
    
    # 공백 정리
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\n[ \t]+\n", "\n\n", result)
    
    result = dedupe_lines(result)
    result = collapse_spaces(result)
    
    return result


# ============================================
# 문단 나누기 (Auto Paragraphs)
# ============================================

# 한국어 문장 종결 패턴
SENTENCE_PATTERN = re.compile(
    r".+?(?:다\.|요\.|니다\.|습니다\.|입니다\.|했다\.|됐다\.|[.!?])(?=\s|$)"
)


def split_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    text = text.strip()
    if not text:
        return []
    
    sentences = SENTENCE_PATTERN.findall(text)
    if sentences:
        return [s.strip() for s in sentences if s.strip()]
    
    # 패턴 매칭 실패 시 마침표 기준으로 분리
    parts = re.split(r"\.\s+", text)
    result = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if not part.endswith("."):
            part = f"{part}."
        result.append(part)
    
    return result


def auto_paragraphs(text: str) -> str:
    """
    긴 문장을 자동으로 문단으로 나눕니다.
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        문단이 나뉜 텍스트
    """
    if not text:
        return ""
    
    lines = text.splitlines()
    output_lines: List[str] = []
    buffer: List[str] = []
    
    def flush_buffer():
        """버퍼의 내용을 출력 라인에 추가합니다."""
        if not buffer:
            return
        
        paragraph = " ".join([x.strip() for x in buffer if x.strip()]).strip()
        if not paragraph:
            buffer.clear()
            return
        
        # 제목이나 리스트는 그대로 유지
        is_heading = paragraph.lstrip().startswith("#")
        is_list = paragraph.lstrip().startswith(("-", "*")) or re.match(r"^\d+\.", paragraph.strip())
        
        if is_heading or is_list:
            output_lines.append(paragraph)
            output_lines.append("")
            buffer.clear()
            return
        
        # 긴 문단은 문장 단위로 나누기
        if len(paragraph) > 220:
            sentences = split_sentences(paragraph)
            if len(sentences) >= 3:
                # 문장이 많으면 2-3개씩 묶어서 문단으로
                group_size = 3 if len(sentences) >= 6 else 2
                for i in range(0, len(sentences), group_size):
                    output_lines.append(" ".join(sentences[i:i + group_size]).strip())
                    output_lines.append("")
                buffer.clear()
                return
        
        output_lines.append(paragraph)
        output_lines.append("")
        buffer.clear()
    
    for line in lines:
        # 빈 줄이면 버퍼 처리
        if not line.strip():
            flush_buffer()
            continue
        
        # 제목이나 리스트면 버퍼 처리 후 바로 추가
        if line.lstrip().startswith("#") or line.lstrip().startswith(("-", "*")) or re.match(r"^\d+\.", line.strip()):
            flush_buffer()
            output_lines.append(line.strip())
            output_lines.append("")
            continue
        
        buffer.append(line)
    
    # 마지막 버퍼 처리
    flush_buffer()
    
    return "\n".join(output_lines).strip()


# ============================================
# 텍스트 폴리싱 (Text Polishing)
# ============================================

def polish_text(text: str, level: str = "medium", humanize: bool = True, auto_paragraph: bool = True) -> str:
    """
    텍스트를 다듬습니다.
    
    Args:
        text: 처리할 텍스트
        level: 처리 강도 ("low", "medium", "high")
        humanize: AI 톤 제거 여부
        auto_paragraph: 자동 문단 나누기 여부
    
    Returns:
        다듬어진 텍스트
    """
    result = text or ""
    
    if humanize:
        result = soften_ai_tone(result, strong=(level != "low"))
    
    result = collapse_spaces(result)
    
    if auto_paragraph:
        result = auto_paragraphs(result)
    
    return result.strip()


def polish_title(text: str, level: str = "high") -> str:
    """제목 텍스트를 다듬습니다."""
    result = safe_str(text)
    # 따옴표 제거
    result = re.sub(r'[\"\'""'']', "", result)
    if level == "high":
        result = re.sub(r"\s{2,}", " ", result)
    return result.strip()


def strip_special_markers(text: str) -> str:
    """마크다운 특수 문자를 제거합니다."""
    if not text:
        return ""
    
    result = text
    # 마크다운 헤딩/리스트 마커 제거
    result = re.sub(r"^\s*#{1,6}\s+", "", result, flags=re.MULTILINE)
    result = re.sub(r"^\s*[\-\*\d]+\.\s+", "", result, flags=re.MULTILINE)
    # 특수 마커 제거
    result = result.replace("#", "")
    result = result.replace("*", "")
    # 코드블록/백틱 제거
    result = result.replace("`", "")
    
    return collapse_spaces(result)


def ensure_sentence_end(text: str) -> str:
    """문장이 적절한 종결어미로 끝나도록 합니다."""
    text = (text or "").rstrip()
    if not text:
        return ""
    
    # 이미 종결 부호가 있으면 그대로 반환
    if text[-1] in [".", "!", "?", "…", "。", "！", "？"]:
        return text
    
    return text + "입니다."
