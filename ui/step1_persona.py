import streamlit as st
from config import MBTI, TONE_PRESETS
from state import reset_from_step, mark_dirty, save_persona_to_disk

print()


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

    DIRECT_LABEL = "직접 입력"

    # 처음 진입 시 preset None이면 기본을 "친근한"으로 저장 (UI/검증 일치)
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
            btn_text = lab 
            # 선택된 경우 type="primary" 적용 (오뚜기 레드 활성화)
            btn_type = "primary" if is_selected else "secondary"

            if st.button(btn_text, key=f"tone_{lab}", type=btn_type, use_container_width=True):
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
            label = mbti  # 이모지 제거
            # 선택된 경우 type="primary" 적용
            btn_type = "primary" if is_selected else "secondary"

            if st.button(label, key=f"mbti_{mbti}", type=btn_type, use_container_width=True):
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
    ENABLE_BLOG_ANALYSIS = True

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
            with st.spinner("블로그를 분석 중입니다..."):
                try:
                    from agents.topic_agent import analyze_blog_style
                    result = analyze_blog_style(persona["blog"]["url"])
                    
                    # 결과가 비어있거나 모든 값이 비어있는지 체크
                    if not result or not any(result.values()):
                        st.error("분석 결과가 비어있습니다. 블로그 URL을 확인해주세요.")
                        result = None
                    else:
                        # 결과 저장 (스키마에 맞게)
                        persona["blog"]["analyzed_style"] = result
                        persona["blog"]["use_analysis"] = True
                        mark_dirty("persona_changed")
                        save_persona_to_disk()
                        st.success("블로그 분석이 완료되었습니다!")
                        st.rerun()
                        
                except ImportError as e:
                    st.error(f"analyze_blog_style 함수를 찾을 수 없습니다: {e}")
                except Exception as e:
                    st.error(f"블로그 분석 중 에러 발생: {str(e)}")
                    st.caption(f"에러 타입: {type(e).__name__}")

        # 결과 표시(사진처럼 초록 박스 느낌은 st.success로 가장 비슷)
        if persona["blog"]["analyzed_style"]:
            a = persona["blog"]["analyzed_style"] or {}
            st.success("분석 완료! AI가 이 스타일을 기억합니다.")

            # 표시 텍스트 (키 이름이 달라도 최대한 안전하게)
            tone = a.get("tone") or a.get("말투") or ""
            structure = a.get("structure") or a.get("구성") or a.get("writingStyle") or ""
            feel = a.get("feel") or a.get("느낌") or a.get("impression") or ""
            signature_phrases = a.get("signature_phrases") or a.get("특징적 표현") or []
            recommendations = a.get("recommendations") or a.get("권장사항") or ""

            if tone:
                st.write(f"**말투:** {tone}")
            if structure:
                st.write(f"**구성:** {structure}")
            if feel:
                st.write(f"**느낌:** {feel}")
            if signature_phrases:
                phrases_text = ", ".join(signature_phrases) if isinstance(signature_phrases, list) else str(signature_phrases)
                st.write(f"**특징적 표현:** {phrases_text}")
            if recommendations:
                st.info(f"{recommendations}")
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