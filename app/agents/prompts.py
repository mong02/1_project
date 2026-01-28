SYSTEM = """당신은 소셜 미디어 운영 전문가이자 카피라이터입니다.
출력은 항상 요청된 형식(구조/길이/채널 규격)을 지키고, 과장/허위/법적 리스크 표현을 피합니다.
"""

def build_strategy_prompt(req) -> str:
    return f"""
아래 제품/서비스 정보를 바탕으로 소셜 캠페인 전략을 6줄 내로 작성하세요.

[입력]
- 제품명: {req.product_name}
- 타깃: {req.target}
- 타깃 고통: {req.pain_point}
- 해결: {req.solution}
- 차별점: {", ".join(req.differentiators) if req.differentiators else "없음"}
- 근거: {", ".join(req.proof) if req.proof else "없음"}
- 목표: {req.goal}
- 톤: {req.tone}

[출력 형식(JSON)]
{{
  "core_message": "...",
  "audience_insight": "...",
  "offer_angle": "...",
  "content_pillars": "...",
  "cta_style": "...",
  "risk_notes": "..."
}}
""".strip()

def build_hooks_prompt(req, strategy_json: str) -> str:
    return f"""
전략을 참고해 후킹 문장 {req.hook_variants}개를 생성하세요.
유형을 섞으세요: 질문형/공감형/오해깨기형/숫자형/비교형/스토리형.

[전략]
{strategy_json}

[금지어]
{", ".join(req.banned_words) if req.banned_words else "없음"}

[출력 형식(JSON)]
{{
  "hooks": ["...", "..."]
}}
""".strip()

def build_post_prompt(req, strategy_json: str, hook: str, channel: str, index: int) -> str:
    # 채널별 규격 간단 룰
    rules = {
        "instagram": "짧은 단락, 이모지 적당히, 줄바꿈 적극, 해시태그 8~15개",
        "thread": "짧고 직설, 1~3문단, 해시태그 0~3개",
        "blog": "조금 길게, 소제목 포함, 정보형 구성, 해시태그 3~7개",
        "linkedin": "업무 톤, 인사이트/근거 강조, 과장 금지, 해시태그 3~5개"
    }
    brand_rules = ""
    if req.brand_voice:
        brand_rules = "\n".join([f"- {r}" for r in req.brand_voice.rules]) if req.brand_voice.rules else ""
    brand_examples = ""
    if req.brand_voice and req.brand_voice.examples:
        brand_examples = "\n".join([f"* {ex}" for ex in req.brand_voice.examples])

    return f"""
다음 정보로 {channel} 게시글 1개를 생성하세요. 캠페인 시퀀스의 {index+1}번째 게시글입니다.
반드시 채널 규격을 지키고, 금지어/리스크 표현을 피하세요.

[채널 규격]
- {rules[channel]}

[전략]
{strategy_json}

[후킹(첫 문장)]
{hook}

[입력]
- 제품명: {req.product_name}
- 타깃: {req.target}
- 고통: {req.pain_point}
- 해결: {req.solution}
- 차별점: {", ".join(req.differentiators) if req.differentiators else "없음"}
- 근거: {", ".join(req.proof) if req.proof else "없음"}
- CTA: {req.cta}
- 목표: {req.goal}
- 톤: {req.tone}

[브랜드 보이스 규칙(있으면 따르기)]
{brand_rules if brand_rules else "없음"}

[브랜드 보이스 예시(있으면 참고)]
{brand_examples if brand_examples else "없음"}

[출력 형식(JSON)]
{{
  "title": "...",
  "body": "...",
  "hashtags": ["..."],
  "story_captions": ["...", "...", "..."],
  "comment_prompts": ["...", "..."]
}}
""".strip()
