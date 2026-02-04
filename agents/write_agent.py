
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import TARGET_CHARS, N_HASHTAGS
from agents.ollama_client import OllamaClient
from utils.prompt_loader import load_prompt, render_prompt
from utils.text_utils import (
    safe_list,
    safe_str,
    unique_list,
    soften_ai_tone,
    polish_text,
    polish_title,
    strip_special_markers,
    ensure_sentence_end,
    auto_paragraphs,
    split_sentences,
)


def _get_mbti_guide(mbti_data: Any) -> str:
    # mbti_data는 문자열일 수도 있고 딕셔너리일 수도 있음
    mbti = ""
    if isinstance(mbti_data, dict):
        mbti = safe_str(mbti_data.get("type"))
    else:
        mbti = safe_str(mbti_data)
    
    mbti = mbti.upper().strip()
    if not mbti or len(mbti) < 4:
        return ""

    # 간단한 MBTI 그룹별 가이드
    guide = []
    if "N" in mbti and "T" in mbti: # 분석가형 (INTJ, INTP, ENTJ, ENTP)
        guide.append("[NT 성향 반영] 논리적 구조와 객관적 사실, 통찰력을 중시하세요. 결론부터 명확히 제시하는 것이 좋습니다.")
    elif "N" in mbti and "F" in mbti: # 외교관형 (INFJ, INFP, ENFJ, ENFP)
        guide.append("[NF 성향 반영] 독자의 감정에 깊이 공감하고 의미 부여를 하세요. 따뜻한 스토리텔링과 가치 전달에 집중하세요.")
    elif "S" in mbti and "J" in mbti: # 관리자형 (ISTJ, ISFJ, ESTJ, ESFJ)
        guide.append("[SJ 성향 반영] 검증된 경험과 구체적인 데이터를 바탕으로 신뢰감을 주세요. 체계적이고 안정적인 톤이 어울립니다.")
    elif "S" in mbti and "P" in mbti: # 탐험가형 (ISTP, ISFP, ESTP, ESFP)
        guide.append("[SP 성향 반영] 트렌디하고 감각적인 표현을 사용하세요. 지금 이 순간의 생생한 느낌과 자유로운 에너지를 담으세요.")
    
    if "E" in mbti:
        guide.append("에너지가 넘치고 독자에게 말을 거는 듯한 적극적인 어조를 사용하세요.")
    else: # I
        guide.append("차분하고 사색적이며, 내면의 깊이 있는 생각을 나누는 어조를 사용하세요.")

    return " ".join(guide)





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
    merged = strip_special_markers(merged)
    return merged


def _recommend_hashtags(main_kw: str, sub_kws: List[str], img_tags: List[str]) -> List[str]:
    pool = []
    for v in [main_kw] + sub_kws + img_tags:
        v = safe_str(v)
        if v:
            pool.append(v)
    uniq = unique_list([p.replace("#", "").strip() for p in pool])
    hashtags = [f"#{x}" for x in uniq][:N_HASHTAGS]
    return hashtags


def _recommend_outro(main_kw: str, target_reader: str) -> str:
    main_kw = safe_str(main_kw) or "주제"
    target_reader = safe_str(target_reader) or "독자"
    return (
        f"오늘은 {main_kw}에 대해 핵심만 정리해봤습니다. "
        f"{target_reader}분들께 도움이 되었으면 좋겠습니다. "
        "실제로 적용해보고 느낀 점이나 질문이 있으면 댓글로 남겨주세요."
    )


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
    tags = safe_list(img_analysis.get("tags"))
    out = []
    for idx, img in enumerate(images):
        if isinstance(img, (bytes, bytearray)):
            size = len(img)
            desc = f"이미지 {idx} (bytes:{size})"
        else:
            desc = f"이미지 {idx} (ref)"
        if tags:
            desc += f" | tags: {', '.join([safe_str(t) for t in tags[:5]])}"
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
    client = client or OllamaClient()

    try:
        main_keyword = safe_str(subtopic) or safe_str(category) or "일상"
        sub_keywords = unique_list(
            [
                safe_str(category),
                safe_str(subtopic),
                safe_str(mood),
                safe_str(user_intent),
            ]
        )
    except Exception as e:
        raise

    template = load_prompt("title_generation")
    prompt = render_prompt(
        template,
        {
            "main_keyword": main_keyword,
            "sub_keywords": ", ".join([k for k in sub_keywords if k]),
            "target_reader": safe_str(user_intent) or "일반 독자",
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

    titles = safe_list((out or {}).get("titles"))
    titles = [safe_str(t) for t in titles if safe_str(t)]

    if not titles:
        titles = [
            f"{main_keyword} 이야기",
            f"{main_keyword} 기록",
            f"{main_keyword} 메모",
            f"{main_keyword} 정리",
            f"{main_keyword} 후기",
        ]

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

    try:
        temperature_step5 = float(final_params.get("temperature_step5", 0.6))
    except Exception:
        temperature_step5 = 0.6

    selected_title = (topic_flow.get("title", {}) or {}).get("selected")
    input_keyword = (topic_flow.get("title", {}) or {}).get("input_keyword")

    img_analysis = (topic_flow.get("images", {}) or {}).get("analysis", {}) or {}
    img_tags = [str(x).strip() for x in safe_list(img_analysis.get("tags")) if str(x).strip()]

    seo_opt = bool(final_toggles.get("seo_opt", False))
    publish_package = bool(final_toggles.get("publish_package", True))
    anti_ai_strong = bool(final_toggles.get("anti_ai_strong", True))

    main_kw = selected_title or input_keyword or ""

    image_list = _build_image_list(topic_flow)
    persona_line = _safe_persona_line(persona)
    avoid = safe_list(persona.get("avoid_keywords"))
    blog_style = safe_str((persona.get("blog") or {}).get("analyzed_style"))
    
    # 말투 예시 추출 (Step1에서 설정한 값)
    tone_info = persona.get("tone", {}) or {}
    tone_preset = tone_info.get("preset") or ""
    tone_custom = tone_info.get("custom_text") or ""
    
    # config.py의 TONE_PRESETS 사용
    from config import TONE_PRESETS
    if tone_preset and tone_preset in TONE_PRESETS:
        tone_example = f"[{tone_preset} 말투 예시] {TONE_PRESETS[tone_preset]}"
    elif tone_custom:
        tone_example = f"[사용자 정의 말투] {tone_custom}"
    else:
        tone_example = "(말투 예시 없음)"
    
    detail = options.get("detail", {}) or {}
    region = safe_str((detail.get("region_scope") or {}).get("text"))
    target_reader = safe_str((detail.get("target_reader") or {}).get("text"))
    extra_request = safe_str((detail.get("extra_request") or {}).get("text"))

    outline_summary = safe_str((brief.get("outline", {}) or {}).get("summary"))
    tone_summary = safe_str((brief.get("tone_manner", {}) or {}).get("summary"))
    target_context = safe_str((brief.get("target_context", {}) or {}).get("text"))
    length_note = safe_str((brief.get("length", {}) or {}).get("note")) or "공백 제외 2000~2200자"

    sub_kws = safe_list((brief.get("keywords", {}) or {}).get("sub"))
    sub_csv = ", ".join([safe_str(k) for k in sub_kws if safe_str(k)])

    final_options_block = _build_final_options_block(ctx.get("final_options", {}) or {})

    plan_prompt = render_prompt(
        load_prompt("image_plan"),
        {
            "title": main_kw or "",
            "main": (brief.get("keywords", {}) or {}).get("main") or main_kw,
            "target_context": target_context,
            "tone_summary": tone_summary,
            "outline_summary": outline_summary,
            "image_list": image_list,
        },
    )
    title_prompt = render_prompt(
        load_prompt("final_title"),
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

    try:
        image_plan = client.generate_json(
            "블로그 편집자",
            plan_prompt,
            temperature=0.2,
        )
    except Exception:
        image_plan = {}

    intro_body_prompt = render_prompt(
        load_prompt("blog_writing"),
        {
            "persona_line": persona_line,
            "avoid": ", ".join([safe_str(x) for x in avoid]),
            "blog_style": blog_style,
            "tone_example": tone_example,
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
            "mbti_guide": _get_mbti_guide(persona.get("mbti", {}) or {}),
        },
    )



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
        intro_txt = safe_str((raw or {}).get("intro_markdown"))
        body_txt = safe_str((raw or {}).get("body_markdown"))
        if not intro_txt or not body_txt:
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
            except Exception as retry_e:
                raise
    except Exception as e:
        # fallback: try shorter prompt via generate_text and manual JSON extract
        fallback_prompt = f"""
너는 블로그 작가다. 아래 정보를 바탕으로 JSON만 출력하라.

[주제] {main_kw}
[타겟 독자] {target_reader}
[글 구성] {outline_summary}
[섹션] {', '.join(safe_list((brief.get('outline', {}) or {}).get('sections')))}

출력 JSON:
{{"intro_markdown":"...","body_markdown":"...","hashtags":["#..."],"image_guide":"...","image_plan":{{}},"package":null}}
""".strip()
        try:
            text = client.generate_text("전문 블로거", fallback_prompt, temperature=0.2)
            raw = client._extract_first_json_object(text)
        except Exception as e2:
            # minimal non-empty fallback
            outline_sections = safe_list((brief.get("outline", {}) or {}).get("sections"))
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
        "title": safe_str(title_out.get("title")) or safe_str(raw.get("title")) or main_kw or "제목",
        "summary": safe_str(raw.get("intro_markdown")),
        "post_markdown": safe_str(raw.get("body_markdown")),
        "meta_description": safe_str(raw.get("meta_description")),
        "hashtags": safe_list(raw.get("hashtags")),
        "outro": safe_str(raw.get("outro")),
        "image_guide": safe_str(raw.get("image_guide")),
        "evidence_notes": safe_list(raw.get("evidence_notes")),
        "intro_markdown": safe_str(raw.get("intro_markdown")),
        "body_markdown": safe_str(raw.get("body_markdown")),
        "image_plan": raw.get("image_plan") or image_plan,
        "package": raw.get("package"),
    }

    if not out.get("image_guide"):
        if img_tags:
            out["image_guide"] = f"본문 중간에 이미지를 배치하고 캡션에 {', '.join(img_tags[:3])} 키워드를 활용하세요."
        else:
            out["image_guide"] = "본문 중간에 이미지를 1~2장 배치하고 짧은 캡션을 추가하세요."

    if anti_ai_strong:
        out["summary"] = soften_ai_tone(out.get("summary", ""), True)
        out["post_markdown"] = soften_ai_tone(out.get("post_markdown", ""), True)
        out["image_guide"] = soften_ai_tone(out.get("image_guide", ""), True)

    polish_level = safe_str(writing.get("polish_level") or "medium")
    humanize = bool(writing.get("humanize", True))
    auto_paragraph = bool(writing.get("auto_paragraph", True))

    if writing.get("title_polish", True):
        out["title"] = polish_title(out.get("title", ""), polish_level)
    if writing.get("intro_polish", True):
        out["summary"] = polish_text(out.get("summary", ""), polish_level, humanize, auto_paragraph)
    if writing.get("body_polish", True):
        out["post_markdown"] = polish_text(out.get("post_markdown", ""), polish_level, humanize, auto_paragraph)

    # 특수문자/마크다운 제거
    out["summary"] = strip_special_markers(out.get("summary", ""))
    out["post_markdown"] = strip_special_markers(out.get("post_markdown", ""))
    out["outro"] = strip_special_markers(out.get("outro", ""))

    # 본문 최소 길이 확보
    before_len = len(safe_str(out.get("post_markdown")))
    out["post_markdown"] = _ensure_min_length(out.get("post_markdown", ""), 1500, client)
    # 문장 끝 마침표 보정
    out["summary"] = ensure_sentence_end(out.get("summary", ""))
    out["post_markdown"] = ensure_sentence_end(out.get("post_markdown", ""))
    out["outro"] = ensure_sentence_end(out.get("outro", ""))

    out["intro_markdown"] = out.get("summary")
    out["body_markdown"] = out.get("post_markdown")

    if not publish_package:
        out["meta_description"] = ""
        out["hashtags"] = []

    if writing.get("outro_reco", True):
        if not out.get("outro") or len(safe_str(out.get("outro"))) < 20:
            target_reader = safe_str((options.get("detail", {}) or {}).get("target_reader", {}).get("text"))
            out["outro"] = _recommend_outro(main_kw, target_reader)

    if writing.get("hashtag_reco", True):
        if not out.get("hashtags"):
            sub_kws = safe_list((brief.get("keywords", {}) or {}).get("sub"))
            out["hashtags"] = _recommend_hashtags(main_kw, sub_kws, img_tags)

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
