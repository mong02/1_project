#step1_persona.py

import streamlit as st
from config import MBTI
from state import reset_from_step, mark_dirty, save_persona_to_disk


def render(ctx):
    persona = st.session_state["persona"]

    st.subheader("작성자 페르소나 설정")

    # 1) 직업 / 역할 (필수)
    persona["role_job"] = st.text_input(
        "현재 역할 / 직업",
        value=persona["role_job"],
        placeholder="예: IT 개발자 / 육아맘 / 마케터"
    )

    st.divider()

    # 2) 말투 (박스 5개 + 예시 카드)
    st.subheader("선호하는 말투")

    TONE_PRESETS = {
        "친근한": "이거 진짜 대박이죠? ㅎㅎ 저도 써보고 완전 반했잖아요~ 여러분도 꼭 한번 체험해보세요! 👍",
        "차분한": "이러한 현상은 우리 일상에서 흔히 발견할 수 있습니다. 조금 더 깊이 있게 살펴보겠습니다.",
        "정보중심": "핵심 포인트만 정리해드릴게요. 장단점과 체크리스트를 기준으로 선택하면 실수 확률이 줄어듭니다.",
        "감성적인": "창틈으로 스며드는 햇살을 보며 문득 그런 생각이 들었습니다. 우리의 일상은 작은 기적들로 채워져 있다고.",
    }
    DIRECT_LABEL = "직접 입력"

    # ✅ 처음 진입 시 preset None이면 기본을 "친근한"으로 저장 (UI/검증 일치)
    if persona["tone"]["mode"] == "preset" and not persona["tone"]["preset"]:
        persona["tone"]["preset"] = "친근한"
        persona["tone"]["custom_text"] = ""
        mark_dirty("persona_changed")
        save_persona_to_disk()

    # 현재 상태를 버튼 UI용 라벨로 변환
    current_mode = persona["tone"]["mode"]
    if current_mode == "custom":
        selected_label = DIRECT_LABEL
    else:
        selected_label = persona["tone"]["preset"] or "친근한"

    labels = list(TONE_PRESETS.keys()) + [DIRECT_LABEL]
    cols = st.columns(len(labels))

    # 버튼 5개 렌더
    for i, lab in enumerate(labels):
        with cols[i]:
            is_selected = (selected_label == lab)
            btn_text = f"✅ {lab}" if is_selected else lab

            if st.button(btn_text, key=f"tone_{lab}", use_container_width=True):
                if lab == DIRECT_LABEL:
                    persona["tone"]["mode"] = "custom"
                    persona["tone"]["preset"] = None
                    # custom_text는 유지
                else:
                    persona["tone"]["mode"] = "preset"
                    persona["tone"]["preset"] = lab
                    persona["tone"]["custom_text"] = ""

                mark_dirty("persona_changed")
                save_persona_to_disk()
                st.rerun()

    st.write("")

    # 선택된 말투에 따라: 예시 카드 or 직접입력
    if persona["tone"]["mode"] == "preset":
        preset = persona["tone"]["preset"] or "친근한"
        example = TONE_PRESETS.get(preset, "")
        with st.container(border=True):
            st.markdown("**예시**")
            st.write(f"“{example}”")
    else:
        persona["tone"]["custom_text"] = st.text_input(
            "나만의 말투 설명",
            value=persona["tone"]["custom_text"],
            placeholder="예: 옆집 언니처럼 편하게, 하지만 정보는 정확하게",
        )

    # 3) MBTI (선택) - 박스 버튼형
    st.subheader("MBTI (선택)")
    st.caption("원하는 MBTI를 클릭하세요. 다시 누르면 해제됩니다.")

    mbti_list = list(MBTI.keys())
    selected = persona["mbti"]["type"]

    cols = st.columns(4)

    for idx, mbti in enumerate(mbti_list):
        with cols[idx % 4]:
            is_selected = (selected == mbti)
            label = f"✅ {mbti}" if is_selected else mbti

            if st.button(label, key=f"mbti_{mbti}", use_container_width=True):
                if is_selected:
                    persona["mbti"] = {"type": None, "style_desc": None}
                else:
                    persona["mbti"]["type"] = mbti
                    persona["mbti"]["style_desc"] = MBTI[mbti]

                mark_dirty("persona_changed")
                save_persona_to_disk()
                st.rerun()

    if persona["mbti"]["type"]:
        st.info(persona["mbti"]["style_desc"])

    st.divider()

    # 4) 피하고 싶은 키워드
    raw = st.text_input(
        "피하고 싶은 키워드 (쉼표로 구분)",
        value=", ".join(persona["avoid_keywords"]),
        placeholder="예: 솔직히, 사실은, 개인적으로"
    )
    persona["avoid_keywords"] = [k.strip() for k in raw.split(",") if k.strip()]

    # 5️⃣ 운영 중인 블로그 분석 (선택)
    ENABLE_BLOG_ANALYSIS = False

    if ENABLE_BLOG_ANALYSIS:
        st.divider()
        st.subheader("운영 중인 블로그 분석 (선택)")

        # state 스키마 보장 (혹시 누락됐을 때 대비)
        if "blog" not in persona:
            persona["blog"] = {"use_analysis": False, "url": None, "analyzed_style": None}

        col1, col2 = st.columns([3, 1])

        with col1:
            blog_url = st.text_input(
                "블로그 URL",
                value=persona["blog"]["url"] or "",
                placeholder="https://blog.naver.com/your-id",
                label_visibility="collapsed",
            )
            persona["blog"]["url"] = blog_url.strip() or None

        with col2:
            analyze_clicked = st.button(
                "스타일 분석",
                use_container_width=True,
                disabled=(not persona["blog"]["url"]),
            )

        if analyze_clicked:
            # ✅ 여기서 실제 분석 에이전트를 호출하도록 연결
            # (프로젝트 구조상 agent에 두는 게 정석)
            try:
                from agents.topic_agent import analyze_blog_style  # 너희 프로젝트에 이 함수가 있으면 사용
                result = analyze_blog_style(persona["blog"]["url"])
            except Exception as e:
                # 함수가 아직 없거나 import 실패 시: 임시 더미 결과 (UI 테스트용)
                result = {
                    "tone": "친근하고 상냥한 대화체",
                    "structure": "모바일 가독성을 고려한 짧은 문장 + 여백 위주 구성",
                    "feel": "일상/유용한 정보를 친근하게 공유하는 느낌",
                }

            # 결과 저장 (스키마에 맞게)
            persona["blog"]["analyzed_style"] = result
            persona["blog"]["use_analysis"] = True
            mark_dirty("persona_changed")
            save_persona_to_disk()
            st.rerun()

        # 결과 표시(사진처럼 초록 박스 느낌은 st.success로 가장 비슷)
        if persona["blog"]["analyzed_style"]:
            a = persona["blog"]["analyzed_style"] or {}
            st.success("분석 완료! AI가 이 스타일을 기억합니다.")

            # 표시 텍스트 (키 이름이 달라도 최대한 안전하게)
            tone = a.get("tone") or a.get("말투") or ""
            structure = a.get("structure") or a.get("구성") or a.get("writingStyle") or ""
            feel = a.get("feel") or a.get("느낌") or a.get("impression") or ""

            if tone:
                st.write(f"**말투:** {tone}")
            if structure:
                st.write(f"**구성:** {structure}")
            if feel:
                st.write(f"**느낌:** {feel}")
    else:
        blog_state = persona.get("blog")
        if blog_state and (
            blog_state.get("use_analysis")
            or blog_state.get("url")
            or blog_state.get("analyzed_style")
        ):
            persona["blog"] = {"use_analysis": False, "url": None, "analyzed_style": None}
            mark_dirty("persona_changed")
            save_persona_to_disk()

    # 다음 단계
    is_ready = bool(persona["role_job"]) and (
        persona["tone"]["preset"] or persona["tone"]["custom_text"]
    )

    if st.button("다음 단계로", disabled=not is_ready):
        save_persona_to_disk()
        reset_from_step(1)
        mark_dirty("persona_changed")
        st.session_state["step"] = 2
        st.rerun()
