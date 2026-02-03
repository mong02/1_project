# topic_agent.py
# 카테고리 - 세부 주제
# 세부 주제 - 제목 후보

import json
import os
import re
from typing import Any, Dict, List, Optional

from config import MODEL_TEXT

from agents.ollama_client import OllamaClient


def _safe_list(x) -> List[str]:
    return x if isinstance(x, list) else []


def _safe_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _compact_join(parts: List[str], sep: str = " ") -> str:
    return sep.join([p for p in parts if p])


def _unique_list(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _render_prompt(template: str, data: Dict[str, Any]) -> str:
    """
    prompts/*.md 안의 {placeholder}를 data로 안전 치환
    - 없는 키는 빈 문자열
    - dict/list는 JSON 문자열로 넣음
    """
    if not template:
        return ""

    def _value(k: str) -> str:
        v = data.get(k)
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False, indent=2)
        return _safe_str(v)

    def _sub(m: re.Match) -> str:
        key = m.group(1)
        return _value(key)

    return _PLACEHOLDER_RE.sub(_sub, template)


def generate_design_brief(ctx: Dict[str, Any], client: Optional[OllamaClient] = None) -> Dict[str, Any]:
    if client is None:
        client = OllamaClient(model=MODEL_TEXT)

    persona = ctx.get("persona", {}) or {}
    topic_flow = ctx.get("topic_flow", {}) or {}
    options = ctx.get("options", {}) or {}
    final_options = ctx.get("final_options", {}) or {}

    selected_title = (topic_flow.get("title", {}) or {}).get("selected")
    input_keyword = (topic_flow.get("title", {}) or {}).get("input_keyword")
    selected_source = (topic_flow.get("title", {}) or {}).get("selected_source")
    main_kw = selected_title or input_keyword or ""

    toggles = final_options.get("toggles", {}) or {}
    seo_opt = bool(toggles.get("seo_opt", False))

    detail = options.get("detail", {}) or {}
    region_scope = _safe_str((detail.get("region_scope", {}) or {}).get("text"))
    target_reader = _safe_str((detail.get("target_reader", {}) or {}).get("text"))
    target_situation = _safe_str((detail.get("target_situation", {}) or {}).get("text"))

    main_kw_base = _safe_str(selected_title or input_keyword)
    main_kw = _compact_join([main_kw_base, region_scope]) or main_kw_base or region_scope

    sub_candidates = _unique_list(
        [
            main_kw_base,
            region_scope,
            target_reader,
            target_situation,
        ]
    )

    target_chars = 1550

    img_analysis = (topic_flow.get("images", {}) or {}).get("analysis", {}) or {}
    img_mood = _safe_str(img_analysis.get("mood"))
    img_tags = [str(x).strip() for x in _safe_list(img_analysis.get("tags")) if str(x).strip()]
    img_source = img_analysis.get("source") or ("image_analysis" if (img_mood or img_tags) else None)

    tone_raw = persona.get("tone")
    if isinstance(tone_raw, dict):
        tone_custom = tone_raw.get("custom_text")
        tone_field = tone_raw
    else:
        tone_custom = persona.get("tone_text")
        tone_field = {}

    mbti_raw = persona.get("mbti")
    if isinstance(mbti_raw, dict):
        mbti_value = mbti_raw.get("type")
    else:
        mbti_value = mbti_raw

    role_job = persona.get("role_job") or "작성자"
    tone_persona = _safe_str(tone_custom)
    tone_summary = ""
    tone_rules = []

    persona_tone = _safe_str(tone_custom)
    mood_value = img_mood or persona_tone
    mood_source = "image_analysis" if img_mood else ("persona_tone" if persona_tone else None)

    if selected_title:
        main_kw_source = selected_source or "unknown"
    elif input_keyword:
        main_kw_source = "input_keyword"
    else:
        main_kw_source = "unknown"

    facts = {
        "persona": {
            "role_job": role_job,
            "tone": tone_field,
            "tone_text": persona_tone,
            "mbti": mbti_value,
            "avoid_keywords": _safe_list(persona.get("avoid_keywords")),
        },
        "topic": {
            "category": (topic_flow.get("category", {}) or {}).get("selected"),
            "subtopic": (topic_flow.get("category", {}) or {}).get("selected_subtopic"),
            "title": selected_title,
            "input_keyword": input_keyword,
            "image_mood": img_mood,
            "image_tags": img_tags,
            "title_source": selected_source,
            "main_keyword_source": main_kw_source,
        },
        "options": {
            "post_type": options.get("post_type"),
            "headline_style": options.get("headline_style"),
            "region_scope": region_scope,
            "target_reader": target_reader,
            "target_situation": target_situation,
            "extra_request": (detail.get("extra_request", {}) or {}).get("text"),
        },
        "constraints": {
            "target_chars": target_chars,
            "seo_opt": seo_opt,
        },
    }

    schema_hint = {
        "applied_persona_text": "string",
        "keywords": {"main": "string", "sub": ["string"]},
        "target_context": {"text": "string"},
        "tone_manner": {"summary": "string", "rules": ["string"]},
        "outline": {"summary": "string", "sections": ["string"]},
        "length": {"target_chars": "number", "note": "string"},
        "strategy": {"text": "string", "seo": {"enabled": "boolean", "notes": "string"}, "hashtags": ["string"]},
    }

    template = ""
    template_path = os.path.join("prompts", "outline.md")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

    placeholders = {
        "topic": selected_title or input_keyword or "",
        "category": (topic_flow.get("category", {}) or {}).get("selected") or "",
        "subtopic": (topic_flow.get("category", {}) or {}).get("selected_subtopic") or "",
        "title": selected_title or "",
        "job": persona.get("role_job") or "",
        "mbti": mbti_value or "",
        "post_type": options.get("post_type") or "",
        "headline_style": options.get("headline_style") or "",
        "region_scope": region_scope,
        "target_reader": target_reader,
        "target_situation": target_situation,
        "extra_request": (detail.get("extra_request", {}) or {}).get("text") or "",
    }

    rendered_template = _render_prompt(template, placeholders).strip()

    base_prompt = f"""
너는 블로그 설계안을 만드는 콘텐츠 전략가다.
출력은 반드시 JSON 객체 한 덩어리만. (설명/코드블록 금지)
모든 문장은 존댓말로 작성하라. 반말은 절대 금지.

[FACTS]
{facts}

[MAPPING GUIDANCE]
- keywords.main: '글 제목/키워드'와 '지역/범위'를 참고해 1개 추천
- keywords.sub: '글 제목/키워드' + '지역/범위' + '타겟 독자'를 조합해 5~8개 추천 (해시태그용, 중복/나열 금지)
- target_context: '글 제목/키워드' + '타겟 상황' + '지역/범위'를 요약해 1~2문장 추천
- tone_manner: 페르소나(직업/MBTI/톤 성격)를 반영해 요약/규칙 작성
- length.target_chars: 공백 제외 1500~1600자 내외로 고정
- outline/strategy: 위 입력을 종합해 실제 글 구성과 전략을 추천

[OUTPUT SCHEMA HINT]
{schema_hint}
""".strip()

    prompt = f"{rendered_template}\n\n{base_prompt}" if rendered_template else base_prompt

    out = client.generate_json("콘텐츠 전략가", prompt)
    if not isinstance(out, dict):
        out = {}

    inputs = {
        "mood": {"value": mood_value, "source": mood_source},
        "image_tags": {"values": img_tags, "source": img_source},
        "title": {"value": selected_title or "", "source": selected_source or None},
        "keywords": {"main": main_kw or "", "main_source": main_kw_source, "sub": sub_candidates},
        "options": {
            "post_type": options.get("post_type") or "",
            "headline_style": options.get("headline_style") or "",
            "region_scope": region_scope,
            "target_situation": target_situation,
            "target_reader": target_reader,
            "extra_request": (detail.get("extra_request", {}) or {}).get("text") or "",
        },
        "constraints": {"target_chars": target_chars, "seo_opt": seo_opt},
    }

    sub_keyword_sources = [{"value": k, "source": "mapped_from_step2"} for k in sub_candidates if str(k).strip()]

    result = {
        "status": "ready",
        "error": None,
        "applied_persona_text": out.get("applied_persona_text") or "",
        "keywords": {
            "main": (out.get("keywords", {}) or {}).get("main") or main_kw or "",
            "sub": _safe_list((out.get("keywords", {}) or {}).get("sub")),
        },
        "target_context": {"text": (out.get("target_context", {}) or {}).get("text") or ""},
        "tone_manner": {
            "summary": (out.get("tone_manner", {}) or {}).get("summary") or "",
            "rules": _safe_list((out.get("tone_manner", {}) or {}).get("rules")),
        },
        "outline": {
            "summary": (out.get("outline", {}) or {}).get("summary") or "",
            "sections": _safe_list((out.get("outline", {}) or {}).get("sections")),
        },
        "length": {
            "target_chars": 1550,
            "note": "공백 제외 약 1500~1600자 내외",
        },
        "strategy": {
            "text": (out.get("strategy", {}) or {}).get("text") or "",
            "seo": {
                "enabled": bool((out.get("strategy", {}) or {}).get("seo", {}).get("enabled", seo_opt)),
                "notes": (out.get("strategy", {}) or {}).get("seo", {}).get("notes") or "",
            },
            "hashtags": _safe_list((out.get("strategy", {}) or {}).get("hashtags")),
        },
        "inputs": inputs,
        "sources": {
            "from_step1": {
                "role_job": persona.get("role_job"),
                "tone_text": persona_tone,
                "mbti": mbti_value,
                "avoid_keywords": _safe_list(persona.get("avoid_keywords")),
            },
            "from_step2": {
                "title": {"value": selected_title, "source": selected_source},
                "category": (topic_flow.get("category", {}) or {}).get("selected"),
                "subtopic": (topic_flow.get("category", {}) or {}).get("selected_subtopic"),
                "image": {"mood": img_mood, "tags": img_tags, "source": img_source},
            },
            "keyword_sources": {
                "main": {"value": main_kw, "source": main_kw_source},
                "sub": sub_keyword_sources,
            },
            "agent_raw": out,
        },
        "updated_at": None,
    }

    return result
