# agents/write_agent.py
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import TARGET_CHARS, N_HASHTAGS
from agents.ollama_client import OllamaClient

# =========================================================
# [설정] AI 말투 교정용 패턴 (기계적인 접속사 제거)
# =========================================================
_AI_FILTER_PATTERNS = [
    r"\b결론적으로\b", r"\b요약하면\b", r"\b정리하자면\b", 
    r"\b따라서\b", r"\b그러므로\b", r"\b한편\b", r"\b또한\b", 
    r"\b마지막으로\b", r"\b전반적으로\b", r"\b종합적으로\b",
    r"\b본 글에서는\b", r"\b이번 포스팅에서는\b", r"\b살펴보겠습니다\b",
    r"^\s*첫째,\s*", r"^\s*둘째,\s*", r"^\s*셋째,\s*",
]

def _normalize_result(out: Dict[str, Any]) -> Dict[str, Any]:
    """AI 응답이 포맷을 어겨도 최대한 살려내는 함수"""
    if not isinstance(out, dict):
        out = {}

    title = str(out.get("title") or out.get("subject") or "").strip()
    summary = str(out.get("summary") or "").strip()
    post_markdown = str(out.get("post_markdown") or out.get("body") or out.get("content") or "").strip()
    
    hashtags = out.get("hashtags", [])
    if isinstance(hashtags, str): 
        hashtags = hashtags.split()
    hashtags = [f"#{str(t).replace('#', '').strip()}" for t in hashtags if t]
    
    return {
        "title": title,
        "summary": summary,
        "post_markdown": post_markdown,
        "hashtags": hashtags[:N_HASHTAGS],
        "meta_description": str(out.get("meta_description") or "").strip(),
        "evidence_notes": out.get("evidence_notes", [])
    }

def _humanize_text(text: str) -> str:
    """기계적인 말투를 한번 더 다듬는 후처리"""
    for pattern in _AI_FILTER_PATTERNS:
        text = re.sub(pattern, "", text)
    text = re.sub(r"^# ", "## ", text, flags=re.MULTILINE)
    text = re.sub(r"  +", " ", text)
    return text.strip()

def generate_post(ctx: Dict[str, Any], client: Optional[OllamaClient] = None) -> Dict[str, Any]:
    """최종 블로그 글 생성 함수"""
    client = client or OllamaClient()

    topic_data = ctx.get("topic_flow", {})
    brief = ctx.get("design_brief", {})
    options = ctx.get("options", {})
    final_toggles = ctx.get("final_options", {}).get("toggles", {}) or {}
    
    title = (topic_data.get("title", {}) or {}).get("selected") or "제목 미정"
    category = (topic_data.get("category", {}) or {}).get("selected") or "일상"
    subtopic = (topic_data.get("category", {}) or {}).get("selected_subtopic") or ""
    
    keywords = (brief.get("keywords", {}) or {}).get("sub") or []
    tone_manner = (brief.get("tone_manner", {}) or {}).get("summary") or "친절하고 감성적인 말투"
    outline_sections = (brief.get("outline", {}) or {}).get("sections") or []
    
    POST_TYPE_PERSONAS = {
        "정보 전달형(설명/팁)": """
- 문체: 명확하고 깔끔한 설명체. "~입니다", "~해요" 체를 기본으로 사용.
- 성격: 신뢰감 있는 전문가처럼 정보를 전달하되, 딱딱하지 않게 친근함 유지.
- 특징: 핵심 포인트를 **굵게** 강조, 번호나 불릿 리스트로 정리, 팁 박스 활용.
- 예시 톤: "오늘은 제가 직접 써보고 알게 된 꿀팁을 공유해드릴게요!"
""",
        "리뷰형": """
- 문체: 생생한 경험 전달체. "~했어요", "~더라고요", "~이었답니다" 체 활용.
- 성격: 솔직하고 믿음직한 친구가 후기를 들려주는 느낌.
- 특징: 장단점을 균형있게 서술, 별점이나 총평 포함, 가격/위치 등 실용 정보 강조.
- 예시 톤: "솔직히 말씀드리면 이건 진짜 가성비 갑이에요!"
""",
        "경험담/에세이형": """
- 문체: 감성적이고 서정적인 에세이체. "~했다", "~이었다"의 일기 톤도 허용.
- 성격: 독자와 감정을 나누는 따뜻한 이야기꾼.
- 특징: 시간 순서대로 서술, 감정과 생각을 솔직하게 표현, 여운 있는 마무리.
- 예시 톤: "문득 그때의 기억이 떠올라 적어봅니다."
""",
        "비교/추천형": """
- 문체: 분석적이면서도 친근한 비교 설명체. "~인데요", "~거든요" 활용.
- 성격: 꼼꼼하게 비교해주는 똑똑한 쇼핑 메이트.
- 특징: 표나 리스트로 항목별 비교, 각각의 장단점 명시, 최종 추천과 이유 제시.
- 예시 톤: "두 제품을 직접 비교해봤는데, 결론부터 말씀드릴게요!"
"""
    }
    
    post_type = options.get("post_type", "정보 전달형(설명/팁)")
    post_type_persona = POST_TYPE_PERSONAS.get(post_type, POST_TYPE_PERSONAS["정보 전달형(설명/팁)"])
    
    HEADLINE_STYLE_PERSONAS = {
        "호기심 유발형(적당함)": """
- 스타일: 독자의 궁금증을 자극하는 질문형 또는 암시형 제목.
- 특징: "~일까?", "~한 이유", "~의 비밀" 등 호기심을 유발하는 표현 사용.
- 예시: "이 카페가 줄 서서 먹는 진짜 이유", "아무도 안 알려주는 꿀팁 3가지"
""",
        "직설 요약형": """
- 스타일: 핵심 내용을 바로 보여주는 간결하고 명확한 제목.
- 특징: 무엇에 대한 글인지 한눈에 파악 가능, 검색 친화적.
- 예시: "강남역 맛집 BEST 5 총정리", "아이폰16 실사용 후기"
""",
        "감성 공감형": """
- 스타일: 독자의 감정에 호소하는 따뜻하고 서정적인 제목.
- 특징: 계절감, 감정 표현, 여운 있는 문장 활용.
- 예시: "봄바람 부는 날, 혼자 떠난 여행", "오늘도 수고한 나에게 주는 작은 선물"
""",
        "문제 해결형": """
- 스타일: 독자의 고민이나 문제를 해결해준다는 메시지를 담은 제목.
- 특징: "~하는 방법", "~해결", "~완벽 가이드" 등 실용적 가치 강조.
- 예시: "초보자도 쉽게 따라하는 홈베이킹", "매번 실패했던 다이어트, 이렇게 해결했어요"
"""
    }
    
    headline_style = options.get("headline_style", "호기심 유발형(적당함)")
    headline_persona = HEADLINE_STYLE_PERSONAS.get(headline_style, HEADLINE_STYLE_PERSONAS["호기심 유발형(적당함)"])

    # 3. Step 4 체크박스 옵션별 규칙 생성
    rule_lines = [f"- 전체 분량은 공백 제외 약 {TARGET_CHARS}자 내외"]
    
    if final_toggles.get("seo_opt"):
        rule_lines.append("""[SEO Optimization]
- Reorganize content using a search-engine-optimized structure.
- Distribute keywords organically across H1, H2, and H3 tags.
- Place a search-intent-matching summary in the introduction.""")

    if final_toggles.get("anti_ai_strong"):
        rule_lines.append("""[Human-Like Refinement]
- Remove repetitive patterns and mechanical phrasing.
- Replace formulaic explanations with a natural thought flow and varied rhythm.""")

    if final_toggles.get("publish_package"):
        rule_lines.append("""[Publication Package]
- Include 3 title variations (Informational, Curiosity-driven, SEO-optimized).
- Add a FAQ section (3-5 items) and 1-2 appropriate CTAs.""")

    if final_toggles.get("evidence_label"):
        rule_lines.append("""[Credibility Labeling]
- Append labels like [Based on official sources] or [Based on experiential evidence] at the end of key paragraphs.""")

    # [중요] 한국어 출력 강제 규칙
    rule_lines.append("""[Language Rule]
- Even though instructions are in English, the final output MUST be written in Korean.
- 모든 본문과 결과물은 반드시 한국어(Korean)로 작성하세요.""")


    system_prompt = f"""
당신은 네이버 블로그에서 활동하는 '감성적이고 친근한 에세이 작가'입니다.
딱딱한 AI 말투(번역투, 보고서체)를 절대 쓰지 마세요.
독자에게 말을 걸듯이 자연스럽고 부드럽게 작성하세요.

[글 성격: {post_type}]
{post_type_persona}

[헤드라인 스타일: {headline_style}]
{headline_persona}

[필수 규칙]
1. 말투: "{tone_manner}" 유지. (~해요, ~했답니다, ~이더라고요 등 구어체 활용)
2. 금지어: "결론적으로", "요약하자면", "살펴보겠습니다", "첫째/둘째/셋째" 같은 접속사 금지.
3. 구성: 서론에서는 공감을 유도하고, 본론에서는 경험과 정보를 섞어서 서술.
4. 가독성: 문단은 3~4줄 내외로 짧게 끊고, 중요한 부분은 **굵게** 표시.
5. 포맷: 오직 JSON 형식으로만 출력.
"""

    user_prompt = f"""
다음 정보를 바탕으로 블로그 글을 작성해주세요.

- 주제: {title} ({category} - {subtopic})
- 필수 키워드: {', '.join(keywords)}
- 글 구성:
{chr(10).join(['  - ' + s for s in outline_sections])}

[출력 포맷 (JSON)]
{{
  "title": "확정된 제목 (매력적으로 다듬어도 됨)",
  "summary": "글의 요약 (검색 결과용, 2문장)",
  "post_markdown": "마크다운 형식의 본문 내용 (여기에 글 작성)",
  "hashtags": ["#태그1", "#태그2", "#태그3"]
}}
"""

    try:
        response = client.generate_json(system_prompt, user_prompt)
        normalized = _normalize_result(response)
        normalized["post_markdown"] = _humanize_text(normalized["post_markdown"])
        return normalized

    except Exception as e:
        print(f"글 생성 에러: {e}")
        return {
            "title": title,
            "summary": "글 생성 중 오류가 발생했습니다.",
            "post_markdown": f"### ⚠️ 생성 실패\n\n죄송합니다. 글을 작성하는 도중 문제가 생겼습니다.\n\n오류 내용: `{e}`",
            "hashtags": ["#오류", "#재시도"]
        }


def suggest_titles_agent(category: str, subtopic: str, mood: str, user_intent: str, client: Optional[OllamaClient] = None) -> List[str]:
    """
    [Writer Agent] 카테고리, 세부주제, 이미지 분위기 등을 바탕으로 제목 5개를 제안합니다.
    사용자의 '의도(user_intent)'가 있을 경우, 이를 최우선순위로 반영합니다.
    """
    client = client or OllamaClient()
    
    intent_focus = f"\n[최우선 반영 사항 - 분석 결과]: {user_intent}\n" if user_intent else ""
    
    prompt = f"""
    역할: 블로그 전문 에디터 (클릭을 부르는 제목 장인)
    {intent_focus}
    카테고리: {category} - {subtopic}
    참고용 이미지 분위기: {mood}
    
    지침:
    1. 분석 결과(의도)가 있다면 그 내용이 제목에 직접적으로 드러나거나 강력하게 암시되어야 합니다.
    2. 독자의 클릭을 유도하는 매력적인 블로그 제목 5개를 한국어로 추천해줘.
    3. 설명 없이 제목만 5줄로 출력해.
    4. 너무 뻔한 제목보다는 감성적이거나 호기심을 자극하는 스타일로 작성해.
    """
    
    try:
        raw_text = client.generate_text("블로그 전문 에디터", prompt)
        titles = [t.strip().replace('"', '').replace("'", "") for t in raw_text.split('\n') if t.strip()]
        titles = [re.sub(r'^\d+[\s.)-]+\s*', '', t) for t in titles]
        return [t for t in titles if t][:5]
        
    except Exception as e:
        print(f"제목 추천 에러: {e}")
        return ["AI 모델 연결 실패 - 직접 입력해주세요"]
