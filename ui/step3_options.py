import streamlit as st
from datetime import datetime

from state import reset_from_step, save_step3_to_disk
from agents.topic_agent import generate_design_brief


def _inject_styles():
    st.markdown(
        """
        <style>
        .brief-wrap { max-width: 1024px; margin: 0 auto; }

        /* Persona Pill: 공중에 뜬 입체 카드 스타일 */
        .persona-pill {
            display: flex; align-items: center; gap: 10px;
            background: #FFFFFF; color: #000000;
            border: var(--neobrutal-border-thick) !important;
            border-radius: var(--border-radius) !important;
            padding: 16px 20px;
            margin: 12px 0 24px 0;
            box-shadow: var(--neobrutal-shadow-lg) !important;
            transition: all 0.2s ease;
        }
        .persona-pill:hover {
            transform: translate(-2px, -2px);
            box-shadow: 8px 8px 0px #000000 !important;
        }

        .persona-pill .icon {
            width: 32px; height: 32px;
            border-radius: 50%;
            background: var(--bg-main) !important; /* 오뚜기 옐로우 */
            color: #000000;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px;
            border: 2px solid #000000;
        }

        /* Brief Card: 기본 네오브루탈 박스 */
        .brief-card {
            border: var(--neobrutal-border) !important;
            border-radius: var(--border-radius) !important;
            padding: 20px 24px;
            margin-bottom: 20px;
            background: #FFFFFF;
            box-shadow: var(--neobrutal-shadow) !important;
        }

        /* H4: 무조건 스파이시 레드 (강조) */
        .brief-card h4 {
            margin: 0 0 12px 0;
            font-size: 1.05rem;
            color: var(--red-spicy) !important;
            font-weight: 800;
            letter-spacing: -0.01em;
            text-transform: uppercase;
        }

        .brief-title { font-size: 22px; font-weight: 800; color: #000; }
        .brief-muted { color: #666; font-size: 13px; font-weight: 500; }

        /* Chip: 둥근 알약 대신 각진 스타일 */
        .chip {
            display: inline-block;
            padding: 6px 14px;
            margin: 4px 6px 0 0;
            border: 2px solid #000000 !important;
            border-radius: var(--border-radius) !important;
            background: #FFFFFF;
            color: #000000;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 2px 2px 0px rgba(0,0,0,0.1);
        }

        /* Equal Height Utility */
        .brief-card-h {
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .brief-card-h > div:last-child {
            flex-grow: 1; /* 내용이 적어도 카드가 늘어나도록 */
        }

        /* Primary Button Override for "Generate" - Ultra Spicy */
        button[kind="primary"] {
            background: var(--red-spicy) !important;
            border: 3px solid #000000 !important;
            box-shadow: 4px 4px 0px #000000 !important;
            font-size: 1.1rem !important;
            padding: 14px 24px !important;
        }
        button[kind="primary"]:hover {
            background: var(--red-mild) !important;
            transform: translate(-1px, -1px) !important;
            box-shadow: 6px 6px 0px #000000 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_step2_selected(topic_flow: dict) -> str | None:
    """Step2에서 선택된 제목(또는 키워드)이 없으면 None."""
    return (topic_flow.get("title", {}) or {}).get("selected")


def _persona_line(persona: dict) -> str:
    role = persona.get("role_job") or "작성자"
    mbti_raw = persona.get("mbti")
    if isinstance(mbti_raw, dict):
        mbti = mbti_raw.get("type")
    else:
        mbti = mbti_raw

    tone_raw = persona.get("tone")
    if isinstance(tone_raw, dict):
        tone = tone_raw.get("custom_text")
    else:
        tone = persona.get("tone_text")

    line = role
    if mbti:
        line = f"{mbti} 성향의 {line}"
    if tone:
        line = f"{line} ({tone})"
    return line


def render(ctx: dict):
    # ctx는 app.py의 build_ctx() 구조를 전제로 합니다.
    persona = ctx.get("persona", {}) or {}
    topic_flow = ctx.get("topic_flow", {}) or {}

    st.title("설계안")
    st.caption("선택한 내용 기준으로 글 구조를 정리했습니다.")
    _inject_styles()

    selected_title = _ensure_step2_selected(topic_flow)
    if not selected_title:
        st.warning("Step2에서 제목(또는 키워드)을 먼저 선택/입력하세요.")
        if st.button("← Step2로 돌아가기"):
            st.session_state["step"] = 2
            st.rerun()
        return

    # Step3 진입 시 자동 생성 (사용자 편의성 개선)
    if st.session_state["design_brief"]["status"] == "idle":
        # 자동으로 설계안 생성 시작
        reset_from_step(3)
        st.session_state["design_brief"]["status"] = "generating"
        st.session_state["design_brief"]["error"] = None
        st.rerun()

    # generating 상태에서 실제 생성
    if st.session_state["design_brief"]["status"] == "generating":
        with st.spinner("설계안을 만드는 중입니다..."):
            try:
                brief = generate_design_brief(ctx)
                brief["status"] = "ready"
                brief["error"] = None
                brief["updated_at"] = datetime.now().isoformat(timespec="seconds")

                st.session_state["design_brief"] = brief
                st.session_state["dirty"]["design_brief_stale"] = False

                # 설계안이 갱신되었으니 변경 플래그 정리
                st.session_state["dirty"]["persona_changed"] = False
                st.session_state["dirty"]["topic_changed"] = False
                st.session_state["dirty"]["options_changed"] = False
            except Exception as e:
                st.session_state["design_brief"]["status"] = "error"
                st.session_state["design_brief"]["error"] = str(e)

        st.rerun()

    design_brief = st.session_state["design_brief"]

    if design_brief["status"] == "error":
        st.error(design_brief.get("error") or "설계안 생성에 실패했습니다.")
        return

    if design_brief["status"] != "ready":
        return

    st.markdown("<div class='brief-wrap'>", unsafe_allow_html=True)

    # Persona 표시
    st.markdown(
        f"""
        <div class="persona-pill">
            <div class="icon"></div>
            <div>
                <div class="brief-muted">적용된 페르소나</div>
                <div style="font-weight:700;">{_persona_line(persona)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 키워드
    main_kw = (design_brief.get("keywords", {}) or {}).get("main") or selected_title
    sub_kws = (design_brief.get("keywords", {}) or {}).get("sub") or []
    sub_kw_html = (
        " ".join([f"<span class='chip'>#{k}</span>" for k in sub_kws])
        if sub_kws
        else "<span class='brief-muted'>없음</span>"
    )

    st.markdown(
        f"""
        <div class="brief-card">
            <h4>핵심 키워드</h4>
            <div class="brief-muted">메인</div>
            <div class="brief-title">{main_kw}</div>
            <div class="brief-muted" style="margin-top:8px;">서브</div>
            <div>{sub_kw_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 타겟 상황
    target_text = (design_brief.get("target_context", {}) or {}).get("text") or "타겟 상황 요약"
    st.markdown(
        f"""
        <div class="brief-card">
            <h4>타겟 상황</h4>
            <div>{target_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 요약들
    tone_summary = (design_brief.get("tone_manner", {}) or {}).get("summary") or "입력 없음"
    outline_summary = (design_brief.get("outline", {}) or {}).get("summary") or "입력 없음"
    target_chars = (design_brief.get("length", {}) or {}).get("target_chars", 0) or 0
    length_text = f"공백 제외 약 {target_chars}자 내외"
    strategy_text = (design_brief.get("strategy", {}) or {}).get("text") or "입력 없음"

    # ROW 1: 톤앤매너 & 글 구성 (Pure CSS Grid for Equal Height)
    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: stretch; margin-bottom: 20px;">
            <div class="brief-card brief-card-h" style="margin-bottom: 0;">
                <h4>톤앤매너</h4>
                <div style="flex-grow:1;">{tone_summary}</div>
            </div>
            <div class="brief-card brief-card-h" style="margin-bottom: 0;">
                <h4>글 구성</h4>
                <div style="flex-grow:1;">{outline_summary}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ROW 2: 길이 & 전략 (Pure CSS Grid for Equal Height)
    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: stretch;">
            <div class="brief-card brief-card-h" style="margin-bottom: 0;">
                <h4>길이</h4>
                <div style="flex-grow:1;">{length_text}</div>
            </div>
            <div class="brief-card brief-card-h" style="margin-bottom: 0;">
                <h4>전략</h4>
                <div style="flex-grow:1;">{strategy_text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    left_btn, right_btn = st.columns([1, 2])
    with left_btn:
        if st.button("이전", use_container_width=True):
            st.session_state["step"] = 2
            st.rerun()
    with right_btn:
        if st.button("이대로 생성", type="primary", use_container_width=True):
            pass
            st.session_state["step"] = 4
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)