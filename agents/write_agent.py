#write_agent.py


import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import TARGET_CHARS, N_HASHTAGS
from agents.ollama_client import OllamaClient

def _debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, Any], run_id: str = "pre-fix"):
    return


def _read_prompt(name: str) -> str:
    path = os.path.join("prompts", f"{name}.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _unique_list(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        key = str(item).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _normalize_result(out: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(out, dict):
        out = {}

    title = _safe_str(out.get("title"))
    summary = _safe_str(out.get("summary"))
    meta_description = _safe_str(out.get("meta_description"))
    post_markdown = _safe_str(out.get("post_markdown"))
    outro = _safe_str(out.get("outro"))
    image_guide = _safe_str(out.get("image_guide"))

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
        "outro": outro,
        "image_guide": image_guide,
        "evidence_notes": evidence_notes,
    }


# 02.02 추가수정 : 사유 - 프롬프트만으로는 AI 말투가 남기 쉬워서, 생성 후 텍스트 후처리를 추가했습니다.
_AI_TONE_PATTERNS = [
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

_AI_OPENERS = [
    "먼저,",
    "우선,",
    "다음으로,",
    "마지막으로,",
    "정리하면,",
    "결론적으로,",
]


def _collapse_spaces(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _dedupe_lines(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    prev = None
    for ln in lines:
        cur = ln.strip()
        if prev is not None and cur and cur == prev:
            continue
        out.append(ln)
        prev = cur if cur else prev
    return "\n".join(out)


def _soften_ai_tone(text: str, strong: bool = True) -> str:
    if not text:
        return ""

    t = text

    if strong:
        for opener in _AI_OPENERS:
            t = re.sub(rf"(^|\n\n){re.escape(opener)}\s*", r"\1", t)

        for p in _AI_TONE_PATTERNS:
            t = re.sub(p, "", t)

    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\n[ \t]+\n", "\n\n", t)

    t = _dedupe_lines(t)
    t = _collapse_spaces(t)
    return t


_SENTENCE_RE = re.compile(
    r".+?(?:다\.|요\.|니다\.|습니다\.|입니다\.|했다\.|됐다\.|[.!?])(?=\s|$)"
)


def _split_sentences(text: str) -> List[str]:
    t = text.strip()
    if not t:
        return []
    sentences = _SENTENCE_RE.findall(t)
    if sentences:
        return [s.strip() for s in sentences if s.strip()]
    parts = re.split(r"\.\s+", t)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not p.endswith("."):
            p = f"{p}."
        out.append(p)
    return out


def _auto_paragraphs(text: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()
    out_lines: List[str] = []
    buf: List[str] = []

    def flush_buf():
        if not buf:
            return
        para = " ".join([x.strip() for x in buf if x.strip()]).strip()
        if not para:
            buf.clear()
            return

        is_heading = para.lstrip().startswith("#")
        is_list = para.lstrip().startswith(("-", "*")) or re.match(r"^\d+\.", para.strip())
        if is_heading or is_list:
            out_lines.append(para)
            out_lines.append("")
            buf.clear()
            return

        if len(para) > 220:
            sentences = _split_sentences(para)
            if len(sentences) >= 3:
                group = 3 if len(sentences) >= 6 else 2
                for i in range(0, len(sentences), group):
                    out_lines.append(" ".join(sentences[i : i + group]).strip())
                    out_lines.append("")
                buf.clear()
                return

        out_lines.append(para)
        out_lines.append("")
        buf.clear()

    for ln in lines:
        if not ln.strip():
            flush_buf()
            continue

        if ln.lstrip().startswith("#") or ln.lstrip().startswith(("-", "*")) or re.match(
            r"^\d+\.", ln.strip()
        ):
            flush_buf()
            out_lines.append(ln.strip())
            out_lines.append("")
            continue

        buf.append(ln)

    flush_buf()
    return "\n".join(out_lines).strip()


def _polish_text(text: str, level: str, humanize: bool, auto_paragraph: bool) -> str:
    t = text or ""
    if humanize:
        t = _soften_ai_tone(t, strong=(level != "low"))
    t = _collapse_spaces(t)
    if auto_paragraph:
        t = _auto_paragraphs(t)
    return t.strip()


def _polish_title(text: str, level: str) -> str:
    t = _safe_str(text)
    t = re.sub(r"[\"'“”‘’]", "", t)
    if level == "high":
        t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def _strip_special_markers(text: str) -> str:
    if not text:
        return ""
    t = text
    # markdown heading/list markers 제거
    t = re.sub(r"^\s*#{1,6}\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*[\-\*\d]+\.\s+", "", t, flags=re.MULTILINE)
    # 특수 마커 제거 (#, *)
    t = t.replace("#", "")
    t = t.replace("*", "")
    # 코드블록/백틱 제거
    t = t.replace("`", "")
    return _collapse_spaces(t)


def _ensure_min_length(text: str, target_len: int, client: Optional[OllamaClient]) -> str:
    t = text or ""
    if len(t) >= target_len:
        return t
    if client is None:
        return t
    prompt = (
        "아래 글을 사람 말투로 더 자연스럽게 확장하세요. "
        "특수문자(#, *, `)는 사용하지 마세요. "
        f"최소 {target_len}자 이상으로 늘리세요.\n\n"
        f"[본문]\n{t}\n\n[추가]"
    )
    try:
        extra = client.generate_text("블로그 작가", prompt, temperature=0.4)
    except Exception:
        return t
    merged = f"{t}\n\n{extra}"
    merged = _strip_special_markers(merged)
    return merged


def _ensure_sentence_end(text: str) -> str:
    t = (text or "").rstrip()
    if not t:
        return ""
    if t[-1] in [".", "!", "?", "…", "。", "！", "？"]:
        return t
    return t + "입니다."


def _recommend_hashtags(main_kw: str, sub_kws: List[str], img_tags: List[str]) -> List[str]:
    pool = []
    for v in [main_kw] + sub_kws + img_tags:
        v = _safe_str(v)
        if v:
            pool.append(v)
    uniq = _unique_list([p.replace("#", "").strip() for p in pool])
    hashtags = [f"#{x}" for x in uniq][:N_HASHTAGS]
    return hashtags


def _recommend_outro(main_kw: str, target_reader: str) -> str:
    main_kw = _safe_str(main_kw) or "주제"
    target_reader = _safe_str(target_reader) or "독자"
    return (
        f"오늘은 {main_kw}에 대해 핵심만 정리해봤습니다. "
        f"{target_reader}분들께 도움이 되었으면 좋겠습니다. "
        "실제로 적용해보고 느낀 점이나 질문이 있으면 댓글로 남겨주세요."
    )


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")

# =========================
# Step5 분리 프롬프트 템플릿
# =========================
TPL_IMAGE_PLAN = """
너는 블로그 편집자다. 아래 이미지들(설명 포함)을 보고,
'Intro(대표 이미지 1장)' + 'Body(맥락에 맞게 몇 장)' + '제외'로 분류한다.

[글 주제]
{title}

[설계안 요약]
메인키워드: {main}
타겟상황: {target_context}
톤앤매너: {tone_summary}
글구성(포맷): {outline_summary}

[이미지 목록]
{image_list}

규칙:
- Intro 대표 이미지는 반드시 1장만 선택
- Body 이미지는 맥락상 도움이 되는 것만 선택(전부 쓸 필요 없음)
- 맥락상 불필요/중복이면 excluded로 분류
- 각 선택된 이미지에 대해 alt_text를 작성
- index는 0부터 시작

출력 JSON:
{{
  "intro_image_index": 0,
  "body_image_indices": [1,2],
  "excluded_image_indices": [3],
  "alt_texts": {{
    "0": "....",
    "1": "...."
  }}
}}
""".strip()

TPL_TITLE_ONLY = """
너는 10년차 전문 카피라이터다.

[목표]
- 블로그 상단에서 "클릭하고 싶게" 만드는 제목을 만든다.
- 과장/광고티 금지, 하지만 궁금증/판단포인트/상황을 똑똑하게 건드린다.

[절대 금지]
- 해시태그, #, 이모지 과다, 느낌표 남발 금지
- "소개합니다/알아보았습니다/정리해보겠습니다" 같은 메타 표현 금지
- 너무 긴 제목(한 문장 안에서 자연스럽게)

[입력 정보]
주제: {title}
메인 키워드: {main}
서브 키워드(참고): {sub_csv}
타겟: {target}
지역/범위: {region}
글 성격(Type): {post_type}
헤드라인 스타일(참고): {headline_style}

[출력 규칙]
- title 1개만 생성
- JSON만 출력

출력 JSON:
{{"title":"..."}}
""".strip()

TPL_INTRO_BODY_ONLY = """
너는 전문 블로거다. 지금부터 매우 풍부하고 길게, 읽는 사람이 끝까지 읽는 글을 쓴다.

[최우선 목표]
- Intro와 Body의 완성도가 최우선이다.
- '정보'만 나열하지 말고, 독자가 실제로 읽으며 고개 끄덕이게 되는 맥락과 판단을 제공한다.
- 글이 짧아지면 실패다. 반드시 길이 가이드를 충족할 것.
- ** 등, AI 가 사용하는 특수 기호 쓰지 말것
- 본문은 최대한 글이 풍부하게

[절대 금지]
- 본문/서론에 해시태그 삽입 금지 (hashtags 필드에만)
- 소제목 남발 금지(필요 최소만, 흐름 전환용 2~4개)
- 체크리스트/번호 나열로만 때우기 금지
- 메타 표현(소개합니다/알아보았습니다/정리해보겠습니다) 금지

[작성자 페르소나]
{persona_line}
금지 표현: {avoid}
{blog_style}

[사용자 직접 입력(최우선)]
지역/범위: {region}
타겟 독자: {target}
추가 요청사항: {extra}

[설계안(Step3)]
주제(글 제목/키워드): {title}
글 성격(Type): {post_type}
메인 키워드: {main}
서브 키워드: {sub_csv}
타겟 상황: {target_context}
톤앤매너: {tone_summary}
글 구성(포맷): {outline_summary}
길이 가이드: {length_note}

[이미지 배치 플랜]
Intro 대표 이미지 index: {intro_idx}
Body 이미지 indices: {body_idxs}
제외 이미지 indices: {excluded_idxs}

[이미지 설명(작성에 반드시 반영)]
{image_list}

[Step4 최종 옵션 적용(★실제 규칙★)]
{final_options_block}

[Step4 옵션을 반드시 적용하는 방법]
- SEO 최적화 ON이면: 소제목(H2/H3)을 자연스럽게 사용하고, 메인 키워드를 서론/본문에 과하지 않게 포함
- AI 티 제거 ON이면: 문장 길이 다양화, 반복 제거, 기계적인 접속사/전개 최소화
- 근거 라벨 ON이면: 정보성 문장 일부에 (경험)/(추정)/(일반) 라벨을 아주 적게 포함
- 발행 패키지 ON이면: package 필드를 스키마에 맞게 채운다 / OFF면 null

[풍부한 글을 위한 강제 지침]
- Intro: 최소 5~7문단 분량. (한 문단은 2~4문장 정도)
- Body: 최소 9~14문단 분량. 단락마다 "상황 → 관찰 → 판단/근거 → 독자에게 도움이 되는 결론" 흐름 유지
- 제품 리뷰라면: 단점/주의점도 반드시 1~2문단 포함(과장 없이)
- 이미지가 있는 문단은: 이미지 설명을 토대로 '왜 이 장면/구성이 의미 있는지'를 자연스럽게 풀어쓴다.
- 기술/제품 용어는 친절하게 풀되, 얕게 요약하지 말고 실제 사용 맥락을 풍부하게 넣는다.

[해시태그 출력 규칙(최종 산출물용)]
- hashtags 필드에만 출력(본문/서론 금지)
- 반드시 10개 이상
- 롱테일 형태(상황/타겟/의도 포함)
- 지역/타겟이 있으면 일부 해시태그에 반드시 반영

출력 JSON 스키마:
{{
  "intro_markdown": "string",
  "body_markdown": "string",
  "hashtags": ["#..."],
  "image_guide": "string",
  "image_plan": {{
    "intro_image_index": 0,
    "body_image_indices": [1,2],
    "excluded_image_indices": [3],
    "alt_texts": {{"0":"...","1":"..."}}
  }},
  "package": {{
    "alt_titles": ["string","string","string"],
    "faq": [{{"q":"string","a":"string"}},{{"q":"string","a":"string"}},{{"q":"string","a":"string"}}],
    "cta": "string"
  }}
}}
""".strip()


def _render_prompt(template: str, data: Dict[str, Any]) -> str:
    if not template:
        return ""

    def _value(k: str) -> str:
        v = data.get(k)
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False, indent=2)
        return _safe_str(v)

    return _PLACEHOLDER_RE.sub(lambda m: _value(m.group(1)), template)


def _safe_persona_line(persona: Dict[str, Any]) -> str:
    role = persona.get("role_job") or "작성자"
    mbti_raw = persona.get("mbti")
    mbti = mbti_raw.get("type") if isinstance(mbti_raw, dict) else mbti_raw
    tone_raw = persona.get("tone")
    tone = tone_raw.get("custom_text") if isinstance(tone_raw, dict) else persona.get("tone_text")
    line = role
    if mbti:
        line = f"{mbti} 성향의 {line}"
    if tone:
        line = f"{line} ({tone})"
    return line


def _build_image_list(topic_flow: Dict[str, Any]) -> str:
    images = (topic_flow.get("images") or {}).get("files") or []
    img_analysis = (topic_flow.get("images") or {}).get("analysis") or {}
    tags = _safe_list(img_analysis.get("tags"))
    out = []
    for idx, img in enumerate(images):
        if isinstance(img, (bytes, bytearray)):
            size = len(img)
            desc = f"이미지 {idx} (bytes:{size})"
        else:
            desc = f"이미지 {idx} (ref)"
        if tags:
            desc += f" | tags: {', '.join([_safe_str(t) for t in tags[:5]])}"
        out.append(desc)
    return "\n".join(out) if out else "(이미지 없음)"


def _build_final_options_block(final_options: Dict[str, Any]) -> str:
    toggles = (final_options.get("toggles") or {})
    params = (final_options.get("params") or {})
    lines = [
        f"seo_opt: {bool(toggles.get('seo_opt', False))}",
        f"anti_ai_strong: {bool(toggles.get('anti_ai_strong', True))}",
        f"publish_package: {bool(toggles.get('publish_package', True))}",
        f"evidence_label: {bool(toggles.get('evidence_label', False))}",
    ]
    seo = params.get("seo") or {}
    anti_ai = params.get("anti_ai") or {}
    lines.append(f"seo.use_h2_h3: {bool(seo.get('use_h2_h3', True))}")
    lines.append(f"seo.keyword_density_level: {seo.get('keyword_density_level', 'medium')}")
    lines.append(f"anti_ai.level: {anti_ai.get('level', 'strong')}")
    lines.append(f"anti_ai.remove_repetition: {bool(anti_ai.get('remove_repetition', True))}")
    return "\n".join(lines)


def suggest_titles_agent(
    category: str,
    subtopic: Optional[str],
    mood: str,
    user_intent: str,
    temperature: float = 0.4,
    intensity: float = 0.2,
    client: Optional[OllamaClient] = None,
) -> List[str]:
    # region agent log
    _debug_log(
        "H6",
        "agents/write_agent.py:suggest_titles_agent:entry",
        "enter suggest_titles_agent",
        {
            "category": _safe_str(category),
            "subtopic": _safe_str(subtopic),
            "mood": _safe_str(mood),
            "user_intent": _safe_str(user_intent),
            "temperature": temperature,
            "intensity": intensity,
        },
    )
    # endregion

    client = client or OllamaClient()

    try:
        main_keyword = _safe_str(subtopic) or _safe_str(category) or "일상"
        sub_keywords = _unique_list(
            [
                _safe_str(category),
                _safe_str(subtopic),
                _safe_str(mood),
                _safe_str(user_intent),
            ]
        )
    except Exception as e:
        # region agent log
        _debug_log(
            "H6",
            "agents/write_agent.py:suggest_titles_agent:build_inputs_error",
            "error while building keywords",
            {"error": str(e), "error_type": type(e).__name__},
        )
        # endregion
        raise

    template = _read_prompt("write_title")
    prompt = _render_prompt(
        template,
        {
            "main_keyword": main_keyword,
            "sub_keywords": ", ".join([k for k in sub_keywords if k]),
            "target_reader": _safe_str(user_intent) or "일반 독자",
        },
    ).strip()

    extra_context = f"""
[CONTEXT]
- category: {category}
- subtopic: {subtopic}
- mood: {mood}
- user_intent: {user_intent}
- intensity: {intensity}
""".strip()

    try:
        out = client.generate_json(
            "블로그 제목 카피라이터",
            f"{prompt}\n\n{extra_context}",
            temperature=temperature,
        )
    except Exception:
        out = {}

    titles = _safe_list((out or {}).get("titles"))
    titles = [_safe_str(t) for t in titles if _safe_str(t)]

    if not titles:
        titles = [
            f"{main_keyword} 이야기",
            f"{main_keyword} 기록",
            f"{main_keyword} 메모",
            f"{main_keyword} 정리",
            f"{main_keyword} 후기",
        ]

    # region agent log
    _debug_log(
        "H6",
        "agents/write_agent.py:suggest_titles_agent:exit",
        "exit suggest_titles_agent",
        {"titles_count": len(titles)},
    )
    # endregion

    return titles


def generate_post(ctx: Dict[str, Any], client: Optional[OllamaClient] = None) -> Dict[str, Any]:
    client = client or OllamaClient()

    persona = ctx.get("persona", {}) or {}
    topic_flow = ctx.get("topic_flow", {}) or {}
    options = ctx.get("options", {}) or {}
    writing = (options.get("detail", {}) or {}).get("writing", {}) or {}
    final_toggles = (ctx.get("final_options", {}) or {}).get("toggles", {}) or {}
    final_params = (ctx.get("final_options", {}) or {}).get("params", {}) or {}
    brief = ctx.get("design_brief", {}) or {}
    # region agent log
    _debug_log(
        "H7",
        "agents/write_agent.py:generate_post:entry",
        "enter generate_post",
        {
            "has_topic_flow": bool(topic_flow),
            "has_design_brief": bool(brief),
            "has_final_options": bool(ctx.get("final_options")),
        },
    )
    # endregion

    try:
        temperature_step5 = float(final_params.get("temperature_step5", 0.6))
    except Exception:
        temperature_step5 = 0.6

    selected_title = (topic_flow.get("title", {}) or {}).get("selected")
    input_keyword = (topic_flow.get("title", {}) or {}).get("input_keyword")

    img_analysis = (topic_flow.get("images", {}) or {}).get("analysis", {}) or {}
    img_tags = [str(x).strip() for x in _safe_list(img_analysis.get("tags")) if str(x).strip()]

    seo_opt = bool(final_toggles.get("seo_opt", False))
    publish_package = bool(final_toggles.get("publish_package", True))
    anti_ai_strong = bool(final_toggles.get("anti_ai_strong", True))

    main_kw = selected_title or input_keyword or ""

    image_list = _build_image_list(topic_flow)
    persona_line = _safe_persona_line(persona)
    avoid = _safe_list(persona.get("avoid_keywords"))
    blog_style = _safe_str((persona.get("blog") or {}).get("analyzed_style"))
    detail = options.get("detail", {}) or {}
    region = _safe_str((detail.get("region_scope") or {}).get("text"))
    target_reader = _safe_str((detail.get("target_reader") or {}).get("text"))
    extra_request = _safe_str((detail.get("extra_request") or {}).get("text"))

    outline_summary = _safe_str((brief.get("outline", {}) or {}).get("summary"))
    tone_summary = _safe_str((brief.get("tone_manner", {}) or {}).get("summary"))
    target_context = _safe_str((brief.get("target_context", {}) or {}).get("text"))
    length_note = _safe_str((brief.get("length", {}) or {}).get("note")) or "공백 제외 2000~2200자"

    sub_kws = _safe_list((brief.get("keywords", {}) or {}).get("sub"))
    sub_csv = ", ".join([_safe_str(k) for k in sub_kws if _safe_str(k)])

    final_options_block = _build_final_options_block(ctx.get("final_options", {}) or {})

    # region agent log
    _debug_log(
        "H15",
        "agents/write_agent.py:generate_post:image_list",
        "image list prepared",
        {"image_count": len((topic_flow.get("images") or {}).get("files") or []), "list_len": len(image_list)},
    )
    # endregion

    plan_prompt = _render_prompt(
        TPL_IMAGE_PLAN,
        {
            "title": main_kw or "",
            "main": (brief.get("keywords", {}) or {}).get("main") or main_kw,
            "target_context": target_context,
            "tone_summary": tone_summary,
            "outline_summary": outline_summary,
            "image_list": image_list,
        },
    )
    title_prompt = _render_prompt(
        TPL_TITLE_ONLY,
        {
            "title": main_kw or "",
            "main": (brief.get("keywords", {}) or {}).get("main") or main_kw,
            "sub_csv": sub_csv,
            "target": target_reader,
            "region": region,
            "post_type": options.get("post_type") or "",
            "headline_style": options.get("headline_style") or "",
        },
    )

    # region agent log
    _debug_log(
        "H16",
        "agents/write_agent.py:generate_post:title_prompt",
        "title prompt prepared",
        {"prompt_len": len(title_prompt)},
    )
    # endregion

    try:
        image_plan = client.generate_json(
            "블로그 편집자",
            plan_prompt,
            temperature=0.2,
        )
    except Exception:
        image_plan = {}

    intro_body_prompt = _render_prompt(
        TPL_INTRO_BODY_ONLY,
        {
            "persona_line": persona_line,
            "avoid": ", ".join([_safe_str(x) for x in avoid]),
            "blog_style": blog_style,
            "region": region,
            "target": target_reader,
            "extra": extra_request,
            "title": main_kw or "",
            "post_type": options.get("post_type") or "",
            "main": (brief.get("keywords", {}) or {}).get("main") or main_kw,
            "sub_csv": sub_csv,
            "target_context": target_context,
            "tone_summary": tone_summary,
            "outline_summary": outline_summary,
            "length_note": length_note,
            "intro_idx": image_plan.get("intro_image_index"),
            "body_idxs": image_plan.get("body_image_indices"),
            "excluded_idxs": image_plan.get("excluded_image_indices"),
            "image_list": image_list,
            "final_options_block": final_options_block,
        },
    )
    # region agent log
    _debug_log(
        "H17",
        "agents/write_agent.py:generate_post:intro_body_prompt",
        "intro/body prompt prepared",
        {"prompt_len": len(intro_body_prompt)},
    )
    # endregion

    try:
        title_out = client.generate_json(
            "카피라이터",
            title_prompt,
            temperature=0.4,
        )
    except Exception:
        title_out = {}

    def _extract_json_with_marker(text: str) -> Dict[str, Any]:
        if not text:
            raise ValueError("빈 응답")
        if "<END_JSON>" in text:
            text = text.split("<END_JSON>", 1)[0]
        return client._extract_first_json_object(text)

    def _repair_missing_brace(text: str) -> str:
        if not text:
            return text
        open_cnt = text.count("{")
        close_cnt = text.count("}")
        if open_cnt > close_cnt:
            text = text + ("}" * (open_cnt - close_cnt))
        return text

    try:
        prompt_with_marker = intro_body_prompt + "\n\n[출력 끝에 <END_JSON>를 반드시 추가]"
        text = client.generate_text(
            "전문 블로거",
            prompt_with_marker,
            temperature=temperature_step5,
        )
        try:
            raw = _extract_json_with_marker(text)
        except Exception:
            raw = _extract_json_with_marker(_repair_missing_brace(text))
        intro_txt = _safe_str((raw or {}).get("intro_markdown"))
        body_txt = _safe_str((raw or {}).get("body_markdown"))
        if not intro_txt or not body_txt:
            # region agent log
            _debug_log(
                "H18",
                "agents/write_agent.py:generate_post:intro_body_retry",
                "empty intro/body detected; retrying",
                {"intro_len": len(intro_txt), "body_len": len(body_txt)},
            )
            # endregion
            retry_prompt = (
                intro_body_prompt
                + "\n\n[주의] 직전 출력의 intro_markdown/body_markdown가 비어있습니다. 반드시 채워서 다시 출력하세요. 끝에 <END_JSON> 추가."
            )
            try:
                retry_text = client.generate_text(
                    "전문 블로거",
                    retry_prompt,
                    temperature=0.2,
                )
                try:
                    raw = _extract_json_with_marker(retry_text)
                except Exception:
                    raw = _extract_json_with_marker(_repair_missing_brace(retry_text))
                # region agent log
                _debug_log(
                    "H20",
                    "agents/write_agent.py:generate_post:intro_body_retry_result",
                    "retry completed",
                    {
                        "intro_len": len(_safe_str((raw or {}).get("intro_markdown"))),
                        "body_len": len(_safe_str((raw or {}).get("body_markdown"))),
                    },
                )
                # endregion
            except Exception as retry_e:
                # region agent log
                _debug_log(
                    "H21",
                    "agents/write_agent.py:generate_post:intro_body_retry_error",
                    "retry failed",
                    {"error": str(retry_e), "error_type": type(retry_e).__name__},
                )
                # endregion
                raise
    except Exception as e:
        # region agent log
        _debug_log(
            "H19",
            "agents/write_agent.py:generate_post:intro_body_error",
            "intro/body generation failed",
            {"error": str(e), "error_type": type(e).__name__},
        )
        # endregion
        # fallback: try shorter prompt via generate_text and manual JSON extract
        fallback_prompt = f"""
너는 블로그 작가다. 아래 정보를 바탕으로 JSON만 출력하라.

[주제] {main_kw}
[타겟 독자] {target_reader}
[글 구성] {outline_summary}
[섹션] {', '.join(_safe_list((brief.get('outline', {}) or {}).get('sections')))}

출력 JSON:
{{"intro_markdown":"...","body_markdown":"...","hashtags":["#..."],"image_guide":"...","image_plan":{{}},"package":null}}
""".strip()
        try:
            # region agent log
            _debug_log(
                "H22",
                "agents/write_agent.py:generate_post:fallback_text",
                "fallback generate_text start",
                {"prompt_len": len(fallback_prompt)},
            )
            # endregion
            text = client.generate_text("전문 블로거", fallback_prompt, temperature=0.2)
            raw = client._extract_first_json_object(text)
            # region agent log
            _debug_log(
                "H23",
                "agents/write_agent.py:generate_post:fallback_parsed",
                "fallback parse success",
                {
                    "intro_len": len(_safe_str((raw or {}).get("intro_markdown"))),
                    "body_len": len(_safe_str((raw or {}).get("body_markdown"))),
                },
            )
            # endregion
        except Exception as e2:
            # region agent log
            _debug_log(
                "H22",
                "agents/write_agent.py:generate_post:fallback_error",
                "fallback failed",
                {"error": str(e2), "error_type": type(e2).__name__},
            )
            # endregion
            # minimal non-empty fallback
            outline_sections = _safe_list((brief.get("outline", {}) or {}).get("sections"))
            intro_fallback = f"{main_kw}에 대해 핵심 흐름을 정리해보겠습니다. {target_reader}에게 필요한 맥락부터 차근히 짚어볼게요."
            body_parts = []
            for s in outline_sections[:5]:
                body_parts.append(f"### {s}\n{s}에 대해 핵심 포인트를 정리합니다. 실제 상황에서 어떻게 적용되는지 함께 살펴보세요.")
            body_fallback = "\n\n".join(body_parts) if body_parts else f"{main_kw}의 핵심 내용을 정리합니다."
            raw = {
                "intro_markdown": intro_fallback,
                "body_markdown": body_fallback,
                "hashtags": [],
                "image_guide": "",
                "image_plan": image_plan,
                "package": None,
                "evidence_notes": [f"생성 실패: {e}"],
            }

    out = {
        "title": _safe_str(title_out.get("title")) or _safe_str(raw.get("title")) or main_kw or "제목",
        "summary": _safe_str(raw.get("intro_markdown")),
        "post_markdown": _safe_str(raw.get("body_markdown")),
        "meta_description": _safe_str(raw.get("meta_description")),
        "hashtags": _safe_list(raw.get("hashtags")),
        "outro": _safe_str(raw.get("outro")),
        "image_guide": _safe_str(raw.get("image_guide")),
        "evidence_notes": _safe_list(raw.get("evidence_notes")),
        "intro_markdown": _safe_str(raw.get("intro_markdown")),
        "body_markdown": _safe_str(raw.get("body_markdown")),
        "image_plan": raw.get("image_plan") or image_plan,
        "package": raw.get("package"),
    }
    # region agent log
    def _heading_stats(text: str) -> Dict[str, Any]:
        t = text or ""
        return {
            "count_h2": t.count("## "),
            "count_h3": t.count("### "),
            "has_inline_h2": bool(re.search(r"\S\s##\s", t)),
        }

    def _marker_stats(text: str) -> Dict[str, Any]:
        t = text or ""
        return {
            "len": len(t),
            "count_hash": t.count("#"),
            "count_bold": t.count("**"),
            "has_inline_hash": bool(re.search(r"\S\s##\s", t)),
        }

    _debug_log(
        "H25",
        "agents/write_agent.py:generate_post:heading_stats",
        "heading/marker stats",
        {
            "intro_heading": _heading_stats(out.get("summary", "")),
            "body_heading": _heading_stats(out.get("post_markdown", "")),
            "intro_markers": _marker_stats(out.get("summary", "")),
            "body_markers": _marker_stats(out.get("post_markdown", "")),
        },
    )
    # endregion
    # region agent log
    _debug_log(
        "H9",
        "agents/write_agent.py:generate_post:after_normalize",
        "normalized output metrics",
        {
            "title_len": len(_safe_str(out.get("title"))),
            "summary_len": len(_safe_str(out.get("summary"))),
            "post_len": len(_safe_str(out.get("post_markdown"))),
            "summary_sentences": len(_split_sentences(_safe_str(out.get("summary")))),
            "post_sentences": len(_split_sentences(_safe_str(out.get("post_markdown")))),
        },
    )
    # endregion
    # region agent log
    _debug_log(
        "H14",
        "agents/write_agent.py:generate_post:raw_keys",
        "raw output keys snapshot",
        {
            "raw_keys": list((raw or {}).keys()) if isinstance(raw, dict) else [],
            "has_intro_markdown": bool((raw or {}).get("intro_markdown")) if isinstance(raw, dict) else False,
            "has_body_markdown": bool((raw or {}).get("body_markdown")) if isinstance(raw, dict) else False,
            "has_image_plan": bool((raw or {}).get("image_plan")) if isinstance(raw, dict) else False,
        },
    )
    # endregion

    if not out.get("image_guide"):
        if img_tags:
            out["image_guide"] = f"본문 중간에 이미지를 배치하고 캡션에 {', '.join(img_tags[:3])} 키워드를 활용하세요."
        else:
            out["image_guide"] = "본문 중간에 이미지를 1~2장 배치하고 짧은 캡션을 추가하세요."

    if anti_ai_strong:
        out["summary"] = _soften_ai_tone(out.get("summary", ""), True)
        out["post_markdown"] = _soften_ai_tone(out.get("post_markdown", ""), True)
        out["image_guide"] = _soften_ai_tone(out.get("image_guide", ""), True)

    polish_level = _safe_str(writing.get("polish_level") or "medium")
    humanize = bool(writing.get("humanize", True))
    auto_paragraph = bool(writing.get("auto_paragraph", True))

    if writing.get("title_polish", True):
        out["title"] = _polish_title(out.get("title", ""), polish_level)
    if writing.get("intro_polish", True):
        out["summary"] = _polish_text(out.get("summary", ""), polish_level, humanize, auto_paragraph)
    if writing.get("body_polish", True):
        out["post_markdown"] = _polish_text(out.get("post_markdown", ""), polish_level, humanize, auto_paragraph)

    # 특수문자/마크다운 제거
    out["summary"] = _strip_special_markers(out.get("summary", ""))
    out["post_markdown"] = _strip_special_markers(out.get("post_markdown", ""))
    out["outro"] = _strip_special_markers(out.get("outro", ""))

    # 본문 최소 길이 확보
    before_len = len(_safe_str(out.get("post_markdown")))
    out["post_markdown"] = _ensure_min_length(out.get("post_markdown", ""), 1500, client)
    # 문장 끝 마침표 보정
    out["summary"] = _ensure_sentence_end(out.get("summary", ""))
    out["post_markdown"] = _ensure_sentence_end(out.get("post_markdown", ""))
    out["outro"] = _ensure_sentence_end(out.get("outro", ""))
    # region agent log
    _debug_log(
        "H26",
        "agents/write_agent.py:generate_post:enforce_length",
        "body length enforced",
        {
            "before_len": before_len,
            "after_len": len(_safe_str(out.get("post_markdown"))),
            "ends_with_punct": _safe_str(out.get("post_markdown"))[-1:] in [".", "!", "?", "…", "。", "！", "？"],
        },
    )
    # endregion

    out["intro_markdown"] = out.get("summary")
    out["body_markdown"] = out.get("post_markdown")

    if not publish_package:
        out["meta_description"] = ""
        out["hashtags"] = []

    if writing.get("outro_reco", True):
        if not out.get("outro") or len(_safe_str(out.get("outro"))) < 20:
            target_reader = _safe_str((options.get("detail", {}) or {}).get("target_reader", {}).get("text"))
            out["outro"] = _recommend_outro(main_kw, target_reader)

    if writing.get("hashtag_reco", True):
        if not out.get("hashtags"):
            sub_kws = _safe_list((brief.get("keywords", {}) or {}).get("sub"))
            out["hashtags"] = _recommend_hashtags(main_kw, sub_kws, img_tags)

    # region agent log
    _debug_log(
        "H10",
        "agents/write_agent.py:generate_post:after_polish",
        "post-polish metrics",
        {
            "title_len": len(_safe_str(out.get("title"))),
            "summary_len": len(_safe_str(out.get("summary"))),
            "post_len": len(_safe_str(out.get("post_markdown"))),
            "summary_sentences": len(_split_sentences(_safe_str(out.get("summary")))),
            "post_sentences": len(_split_sentences(_safe_str(out.get("post_markdown")))),
        },
    )
    # endregion

    return {
        "title": out["title"],
        "summary": out["summary"],
        "meta_description": out["meta_description"],
        "hashtags": out["hashtags"],
        "post_markdown": out["post_markdown"],
        "outro": out["outro"],
        "image_guide": out["image_guide"],
        "evidence_notes": out["evidence_notes"],
        "intro_markdown": out.get("intro_markdown"),
        "body_markdown": out.get("body_markdown"),
        "image_plan": out.get("image_plan"),
        "package": out.get("package"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "debug": {
            "raw": raw,
            "prompts": {
                "image_plan": plan_prompt,
                "title": title_prompt,
                "intro_body": intro_body_prompt,
                "final_options_block": final_options_block,
            },
        },
    }
