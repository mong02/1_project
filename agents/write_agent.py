# 글 생성 담당


# write_agent.py
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import TARGET_CHARS, N_HASHTAGS
from agents.ollama_client import OllamaClient


def _read_prompt(name: str) -> str:
    """prompts 폴더에서 md 읽기 (없으면 빈 문자열)"""
    path = os.path.join("prompts", f"{name}.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _normalize_result(out: Dict[str, Any]) -> Dict[str, Any]:
    """모델 출력이 타입/키가 흔들려도 Step5 렌더링이 깨지지 않도록 정리"""
    if not isinstance(out, dict):
        out = {}

    title = _safe_str(out.get("title"))
    summary = _safe_str(out.get("summary"))
    meta_description = _safe_str(out.get("meta_description"))
    post_markdown = _safe_str(out.get("post_markdown"))

    hashtags = _safe_list(out.get("hashtags"))
    hashtags = [f"#{_safe_str(t).lstrip('#')}" for t in hashtags if _safe_str(t)]
    hashtags = hashtags[:N_HASHTAGS]

    evidence_notes = _safe_list(out.get("evidence_notes"))
    evidence_notes = [_safe_str(x) for x in evidence_notes if _safe_str(x)]

    return {
        "title": title,
        "summary": summary,
        "meta_description": meta_description,
        "hashtags": hashtags,
        "post_markdown": post_markdown,
        "evidence_notes": evidence_notes,
    }


def suggest_titles_agent(
    category: str,
    subtopic: str,
    mood: str,
    user_intent: str,
    client: Optional[OllamaClient] = None,
) -> List[str]:
    client = client or OllamaClient()

    base_prompt = f"""
너는 블로그 제목 기획자다.
아래 조건에 맞는 제목 후보 5개를 제안하라.
출력은 반드시 JSON 객체 한 덩어리만. (설명/코드블록 금지)

[조건]
- 카테고리: {category}
- 세부 주제: {subtopic}
- 분위기: {mood}
- 사용자 의도: {user_intent or "일반적인 정보 탐색"}

[OUTPUT]
{{"titles":["제목1","제목2","제목3","제목4","제목5"]}}
""".strip()

    try:
        out = client.generate_json("제목 기획자", base_prompt)
        titles = out.get("titles") if isinstance(out, dict) else None
        titles = [str(t).strip() for t in _safe_list(titles) if str(t).strip()]
    except Exception:
        titles = []

    if not titles:
        titles = [
            f"{category}에서 {subtopic}로 시작하는 쉬운 방법",
            f"{subtopic} 핵심만 정리한 {category} 가이드",
            f"{category} 초보를 위한 {subtopic} 입문",
            f"{subtopic}가 왜 중요한가? {category} 관점",
            f"{subtopic}로 만드는 작은 변화: {category} 이야기",
        ]

    return titles[:5]


def generate_post(ctx: Dict[str, Any], client: Optional[OllamaClient] = None) -> Dict[str, Any]:
    """
    Step1~4 선택값(ctx)을 반영해 최종 글 생성.
    - SEO 최적화
    - 근거 라벨 표시
    - 발행 패키지 포함(요약/메타/태그)
    - AI 티 제거(강함)
    - 이미지 기반 해시태그 추천
    """
    client = client or OllamaClient()

    persona = ctx.get("persona", {}) or {}
    topic_flow = ctx.get("topic_flow", {}) or {}
    options = ctx.get("options", {}) or {}
    final_toggles = (ctx.get("final_options", {}) or {}).get("toggles", {}) or {}
    brief = ctx.get("design_brief", {}) or {}

    # Step2 핵심(프로젝트 스키마에 맞춰 안전하게)
    category = (topic_flow.get("category", {}) or {}).get("selected")
    # 기존 코드가 여기서 자주 비었습니다. 흔한 케이스를 순서대로 fallback 처리합니다.
    subtopic = (
        (topic_flow.get("subtopic", {}) or {}).get("selected")
        or (topic_flow.get("category", {}) or {}).get("selected_subtopic")
        or topic_flow.get("selected_subtopic")
    )
    selected_title = (topic_flow.get("title", {}) or {}).get("selected")
    input_keyword = (topic_flow.get("title", {}) or {}).get("input_keyword")

    # 이미지 분석(있으면)
    img_analysis = (topic_flow.get("images", {}) or {}).get("analysis", {}) or {}
    img_mood = img_analysis.get("mood")
    img_tags = [str(x).strip() for x in _safe_list(img_analysis.get("tags")) if str(x).strip()]

    # 토글
    seo_opt = bool(final_toggles.get("seo_opt", False))
    evidence_label = bool(final_toggles.get("evidence_label", False))
    publish_package = bool(final_toggles.get("publish_package", True))
    anti_ai_strong = bool(final_toggles.get("anti_ai_strong", True))
    image_hashtag_reco = bool(final_toggles.get("image_hashtag_reco", False))

    # 글 길이
    try:
        target_chars = int((brief.get("length", {}) or {}).get("target_chars") or TARGET_CHARS)
    except Exception:
        target_chars = TARGET_CHARS

    # 키워드
    main_kw = (brief.get("keywords", {}) or {}).get("main") or selected_title or input_keyword or ""
    sub_kws = [str(x).strip() for x in _safe_list((brief.get("keywords", {}) or {}).get("sub")) if str(x).strip()]

    # 섹션
    sections = [str(x).strip() for x in _safe_list((brief.get("outline", {}) or {}).get("sections")) if str(x).strip()]
    if not sections:
        sections = ["핵심 요약", "준비/설정", "실전 활용", "자주 하는 실수", "마무리"]

    # 프롬프트 템플릿
    template = _read_prompt("write_post").strip()

    facts = {
        "persona": persona,
        "category": category,
        "subtopic": subtopic,
        "title": selected_title,
        "input_keyword": input_keyword,
        "post_type": options.get("post_type"),
        "headline_style": options.get("headline_style"),
        "target_reader": ((options.get("detail", {}) or {}).get("target_reader", {}) or {}).get("text", ""),
        "extra_request": ((options.get("detail", {}) or {}).get("extra_request", {}) or {}).get("text", ""),
        "design_brief": brief,
        "toggles": {
            "seo_opt": seo_opt,
            "evidence_label": evidence_label,
            "publish_package": publish_package,
            "anti_ai_strong": anti_ai_strong,
            "image_hashtag_reco": image_hashtag_reco,
        },
        "image": {
            "mood": img_mood,
            "tags": img_tags,
        },
        "constraints": {
            "target_chars": target_chars,
            "n_hashtags": N_HASHTAGS,
        },
        "keywords": {
            "main": main_kw,
            "sub": sub_kws,
        },
    }

    schema_hint = {
        "title": "string",
        "summary": "string (2~3문장)",
        "meta_description": "string (SEO용 120~160자)",
        "hashtags": ["string (#태그)"],
        "post_markdown": "string (마크다운 본문)",
        "evidence_notes": ["string (근거/출처/주의)"],
    }

    rule_lines = [
        f"- 전체 분량은 공백 제외 약 {target_chars}자 내외",
        "- 문장은 사람이 쓴 것처럼 자연스럽게",
        "- 과장, 뻔한 문구, AI스러운 접속사(결론적으로/따라서/요약하면 반복) 줄이기" if anti_ai_strong else "",
        "- 근거/추정 라벨을 문장 끝에 짧게 표시: [근거] / [추정]" if evidence_label else "",
        "- SEO 최적화: H2/H3 구조, 메인 키워드 자연 삽입" if seo_opt else "",
        "- 발행 패키지 포함: 요약/메타디스크립션/해시태그" if publish_package else "",
        "- 이미지 기반 해시태그: 제공된 이미지 태그를 우선 반영" if image_hashtag_reco else "",
        "- FACTS에 없는 사실은 만들지 말 것",
    ]
    rule_lines = [x for x in rule_lines if x]

    section_guide = "\n".join([f"- {s}" for s in sections])

    base_prompt = f"""
너는 블로그 글을 쓰는 전문 작가다.
출력은 반드시 JSON 객체 한 덩어리만. (설명/코드블록 금지)

[FACTS(JSON)]
{json.dumps(facts, ensure_ascii=False, indent=2)}

[구성(섹션/H2)]
{section_guide}

[규칙]
{chr(10).join(rule_lines)}

[OUTPUT SCHEMA HINT]
{json.dumps(schema_hint, ensure_ascii=False)}
""".strip()

    prompt = f"{template}\n\n{base_prompt}" if template else base_prompt

    system_role = "블로그 글 작성자"

    try:
        raw = client.generate_json(system_role, prompt)
    except Exception as e:
        # 최소한 Step5가 깨지지 않도록 안전 결과 반환
        raw = {
            "title": selected_title or main_kw or "제목",
            "summary": "",
            "meta_description": "",
            "hashtags": [],
            "post_markdown": "",
            "evidence_notes": [f"생성 실패: {e}"],
        }

    out = _normalize_result(raw)

    # 후처리: publish_package가 false면 meta/hashtags 비움
    if not publish_package:
        out["meta_description"] = ""
        out["hashtags"] = []

    return {
        "title": out["title"] or (selected_title or main_kw or "제목"),
        "summary": out["summary"],
        "meta_description": out["meta_description"],
        "hashtags": out["hashtags"],
        "post_markdown": out["post_markdown"],
        "evidence_notes": out["evidence_notes"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "debug": {"raw": raw},
    }

