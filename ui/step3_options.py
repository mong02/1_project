# step3_topic.py


import streamlit as st
from datetime import datetime

from state import reset_from_step, save_step3_to_disk
from agents.topic_agent import generate_design_brief


def _inject_styles():
    st.markdown(
        """
        <style>
        .brief-wrap { max-width: 1024px; margin: 0 auto; }

        .persona-pill{
            display:flex; align-items:center; gap:10px;
            background:#fff; color:#111827;
            border:1px solid #E6E9F2;
            border-radius:14px;
            padding:14px 16px;
            margin:12px 0 18px 0;
            box-shadow:0 6px 18px rgba(18,18,18,.05);
        }
        .persona-pill .icon{
            width:28px; height:28px;
            border-radius:50%;
            background:#F3F4F6;
            display:flex; align-items:center; justify-content:center;
            font-size:14px;
        }

        .brief-card{
            border:1px solid #E6E9F2;
            border-radius:16px;
            padding:18px 20px;
            margin-bottom:16px;
            background:#fff;
            box-shadow:0 2px 10px rgba(18,18,18,.04);
        }
        .brief-card h4{
            margin:0 0 10px 0;
            font-size:14px;
            color:#7A8199;
            letter-spacing:.02em;
        }
        .brief-title{ font-size:20px; font-weight:700; }
        .brief-muted{ color:#6B7280; font-size:13px; }

        .chip{
            display:inline-block;
            padding:6px 10px;
            margin:4px 6px 0 0;
            border:1px solid #E6E9F2;
            border-radius:999px;
            background:#F8FAFF;
            color:#4B5563;
            font-size:12px;
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

    # 생성 버튼: 자동 실행 대신 사용자가 눌렀을 때만 생성
    if st.session_state["design_brief"]["status"] == "idle":
        if st.button("설계안 생성", type="primary", use_container_width=True):
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
            <div class="icon">👤</div>
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

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="brief-card">
                <h4>톤앤매너</h4>
                <div>{tone_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="brief-card">
                <h4>길이</h4>
                <div>{length_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="brief-card">
                <h4>글 구성</h4>
                <div>{outline_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="brief-card">
                <h4>전략</h4>
                <div>{strategy_text}</div>
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
