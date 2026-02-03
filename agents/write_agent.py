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

# agents/write_agent.py 수정본

def generate_post(ctx: Dict[str, Any], client: Optional[OllamaClient] = None) -> Dict[str, Any]:
    client = client or OllamaClient()

    # 1. 데이터 추출 (Step 3의 상세 설계안을 모두 가져옵니다)
    persona = ctx.get("persona", {})
    topic_flow = ctx.get("topic_flow", {})
    options = ctx.get("options", {})
    final_toggles = ctx.get("final_options", {}).get("toggles", {}) or {}
    brief = ctx.get("design_brief", {}) # Step 3의 결과물

    # 변수 맵핑
    job = persona.get("role_job", "전문 블로거")
    mbti_type = persona.get("mbti", {}).get("type", "자유")
    tone = persona.get("tone", {}).get("custom_text") or "친절한"
    avoid_kws = ", ".join(persona.get("avoid_keywords", [])) or "상투적인 표현"
    
    # Step 3 설계안 상세 데이터 (본문 풍성함의 핵심 재료)
    target_context = brief.get("target_context", {}).get("text", "일반적인 상황")
    tone_summary = brief.get("tone_manner", {}).get("summary", "")
    outline_summary = brief.get("outline", {}).get("summary", "")
    length_note = brief.get("length", {}).get("note", "공백 제외 1500자 내외")
    main_kw = brief.get("keywords", {}).get("main", "")
    sub_kws = ", ".join(brief.get("keywords", {}).get("sub", []))
    post_processing_rules = []
    
    #step4 세부 사항 버튼
    if final_toggles.get("seo_opt"):
        post_processing_rules.append("""
        [SEO Optimization]
        - Reorganize the content using a search-engine-optimized structure.
        - Identify one primary keyword and two to three secondary keywords naturally from the text.
        - Distribute keywords organically across the title (H1) and subheadings (H2–H3).
        - Keep paragraphs concise (3–4 lines max) and place a summary in the introduction.
        """)

    if final_toggles.get("anti_ai_strong"):
        post_processing_rules.append("""
        [Anti-AI Humanization]
        - Refine the content so it reads as if written naturally by a human author.
        - Remove repetitive patterns, vary sentence rhythm, and add contextual nuance.
        """)

    if final_toggles.get("publish_package"):
        post_processing_rules.append("""
        [Publish Package Expansion]
        - Expand into a package: Include three title variations (Informational, Curiosity-driven, SEO-optimized), 
          a FAQ section (3-5 questions), and 1-2 appropriate CTAs.
        """)

    if final_toggles.get("evidence_label"):
        post_processing_rules.append("""
        [Credibility Labeling]
        - Append labels at the end of key paragraphs: [Based on official sources], [Based on statistics or research], 
          [Based on industry practice], [Based on experiential evidence], or [Interpretation or reasoning].
        """)
    # 2. 시스템 인스트럭션 (실험본의 '전문 블로거' 페르소나 주입)
    system_prompt = f"""
당신은 네이버 블로그 전문 작가입니다. 영문 지침을 따르되 반드시 한국어로 작성하세요.
지금부터 매우 풍부하고 길게, 읽는 사람이 끝까지 읽게 되는 고퀄리티 글을 씁니다.

[작성자 정체성]
- 직업: {job} ({mbti_type})
- 말투: '{tone}' 어조를 완벽하게 유지 (AI 말투 금지)
- 가치관: 독자의 상황에 진심으로 공감하고 실무적 통찰력을 제공함.

[최우선 목표]
- 단순히 정보를 나열하지 말고, 독자가 고개 끄덕이게 되는 '맥락'과 '판단 근거'를 제공한다.
- 글이 짧아지면 실패다. 반드시 길이 가이드({length_note})를 충족할 것.

[필수 규칙]
1. 금지어: {avoid_kws} 및 "결론적으로", "요약하자면" 같은 기계적 접속사 사용 금지.
2. 가독성: 한 문단은 3~4줄 내외로 짧게 끊을 것.
3. 분량 강제: 서론(Intro)은 최소 5문단 이상, 본문(Body)은 최소 10문단 이상의 풍부한 정보량을 확보할 것.
"""

    # 3. 사용자 프롬프트 (Step 3 설계안 + Step 4 옵션 통합)
    user_prompt = f"""
[설계안(Step 3) 반영]
- 주제: {topic_flow.get('title', {}).get('selected')}
- 타겟 상황: {target_context}
- 메인 키워드: {main_kw}
- 서브 키워드: {sub_kws}
- 톤앤매너: {tone_summary}
- 글 구성 가이드: {outline_summary}

[최종 옵션(Step 4) 적용 규칙]
{chr(10).join([f"- {k}: ON" for k, v in final_toggles.items() if v])}
- SEO 최적화: H2/H3 구조를 사용하고 키워드를 자연스럽게 배치할 것.
- AI 티 제거: 문장 길이를 다양화하고 사람이 쓴 듯한 리듬감을 부여할 것.

[출력 스키마]
{{
  "title": "클릭을 부르는 매력적인 제목",
  "summary": "독자의 호기심을 자극하는 서론 (5문단 이상)",
  "post_markdown": "상세한 정보와 통찰이 담긴 본문 (10문단 이상)",
  "hashtags": ["#10개이상", "..."]
}}
"""

    try:
        raw = client.generate_json(system_prompt, user_prompt)
        normalized = _normalize_result(raw)
        normalized["post_markdown"] = _humanize_text(normalized["post_markdown"])
        return normalized
    except Exception as e:
        return {"title": "Error", "post_markdown": f"생성 실패: {e}", "hashtags": []}
    
# agents/write_agent.py 내 해당 함수 교체

def _build_intensity_instruction(intensity: float, mood: str, user_intent: str, category: str, subtopic: str) -> str:
    """반영도(intensity)에 따라 AI에게 내릴 지침을 동적으로 만듭니다."""
    intensity = max(0.0, min(1.0, intensity))
    context = user_intent or mood or "없음"
    
    if intensity >= 0.7:
        # HIGH: 사진이 제목의 주인공이 됨
        return f"""
[★ 최우선 반영: 사진의 의도와 분위기 ★]
- 분석된 의도: "{context}"
- 위 의도가 제목 전체를 지배해야 합니다. 카테고리({category})는 보조적인 맥락으로만 활용하세요.
"""
    elif intensity <= 0.3:
        # LOW: 카테고리가 제목의 주인공이 됨
        return f"""
[★ 최우선 반영: 카테고리와 세부 주제 ★]
- 핵심 주제: "{category} - {subtopic}"
- 카테고리에 100% 집중하세요. 사진의 분위기("{context}")는 문체의 뉘앙스로만 아주 살짝 녹여내세요.
"""
    else:
        # MEDIUM: 카테고리와 사진의 균형 있는 조화
        return f"""
[균형적 반영]
- 카테고리: "{category} - {subtopic}"
- 분위기: "{context}"
- 두 가지를 적절히 조화시켜 클릭을 부르는 매력적인 제목을 작성하세요.
"""


# agents/write_agent.py 내 suggest_titles_agent 함수 교체

def suggest_titles_agent(
    category: str, 
    subtopic: str, 
    mood: str, 
    user_intent: str, 
    temperature: float = 0.4, 
    intensity: float = 0.5,
    client: Optional[OllamaClient] = None
) -> List[str]:
    """
    [Writer Agent] UI에서 설정한 창의성(temperature)과 반영도(intensity)를 적용해 제목 5개를 생성합니다.
    """
    client = client or OllamaClient()
    
    # 1. 반영도(intensity)에 따른 동적 지침 생성
    instruction = _build_intensity_instruction(intensity, mood, user_intent, category, subtopic)
    
    prompt = f"""
역할: 블로그 전문 에디터 (클릭을 부르는 제목 장인)

{instruction}

[공통 지침]
1. 독자의 클릭을 유도하는 매력적인 블로그 제목 5개를 한국어로 추천해줘.
2. 설명 없이 제목만 5줄로 출력해. (번호 매기기 금지)
3. 너무 뻔한 제목보다는 감성적이거나 호기심을 자극하는 스타일로 작성해.
4. 각 제목은 서로 다른 관점이나 접근 방식을 취해야 해.
"""
    
    try:
        # 2. AI 호출 (전달받은 temperature를 직접 적용)
        # OllamaClient의 generate_text 함수 구조에 맞춰 temperature를 전달합니다.
        raw_text = client.generate_text(
            system_role="블로그 제목 에디터", 
            prompt=prompt, 
            temperature=temperature
        )
        
        # 3. 결과 텍스트 정제 (따옴표 및 번호 제거)
        titles = [t.strip().replace('"', '').replace("'", "") for t in raw_text.split('\n') if t.strip()]
        # 문장 앞의 숫자(1., 2. 등)를 정규표현식으로 깔끔하게 제거합니다.
        titles = [re.sub(r'^\d+[\s.)-]+\s*', '', t) for t in titles] 
        
        return [t for t in titles if t][:5]
        
    except Exception as e:
        print(f"제목 추천 에러: {e}")
        return ["AI 모델 연결 실패 - 다시 시도해주세요"]
