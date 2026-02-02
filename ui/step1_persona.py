# ui/step1_persona.py
import streamlit as st
from config import MBTI
from state import reset_from_step, mark_dirty, save_persona_to_disk

def render(ctx):
    persona = st.session_state["persona"]

    st.subheader("작성자 페르소나 설정")

    # 1️⃣ 직업 / 역할 (필수)
    persona["role_job"] = st.text_input(
        "현재 역할 / 직업",
        value=persona["role_job"],
        placeholder="예: IT 개발자 / 육아맘 / 마케터"
    )

    st.divider()

    # 2️⃣ 말투
    tone_mode = st.radio(
        "말투 입력 방식",
        ["preset", "custom"],
        index=0 if persona["tone"]["mode"] == "preset" else 1,
        horizontal=True
    )
    persona["tone"]["mode"] = tone_mode

    if tone_mode == "preset":
        persona["tone"]["preset"] = st.selectbox(
            "기본 말투 선택",
            ["친근한/구어체", "차분한/경어체", "정보중심/건조체"],
            index=0
        )
        persona["tone"]["custom_text"] = ""
    else:
        persona["tone"]["custom_text"] = st.text_input(
            "나만의 말투 설명",
            value=persona["tone"]["custom_text"],
            placeholder="예: 옆집 언니처럼 편하게, 하지만 정보는 정확하게"
        )
        persona["tone"]["preset"] = None

    st.divider()

    # 3️⃣ MBTI (선택)
    mbti_options = ["선택 안 함"] + list(MBTI.keys())
    selected_mbti = persona["mbti"]["type"] or "선택 안 함"

    choice = st.selectbox(
        "MBTI (선택)",
        mbti_options,
        index=mbti_options.index(selected_mbti)
    )

    if choice == "선택 안 함":
        persona["mbti"] = {"type": None, "style_desc": None}
    else:
        persona["mbti"]["type"] = choice
        persona["mbti"]["style_desc"] = MBTI[choice]
        st.caption(persona["mbti"]["style_desc"])

    st.divider()

    # 4️⃣ 피하고 싶은 키워드
    raw = st.text_input(
        "피하고 싶은 키워드 (쉼표로 구분)",
        value=", ".join(persona["avoid_keywords"]),
        placeholder="예: 솔직히, 사실은, 개인적으로"
    )
    persona["avoid_keywords"] = [k.strip() for k in raw.split(",") if k.strip()]

    st.divider()

    # 5️⃣ 다음 단계
    is_ready = bool(persona["role_job"]) and (
        persona["tone"]["preset"] or persona["tone"]["custom_text"]
    )

    if st.button("다음 단계로", disabled=not is_ready):
        save_persona_to_disk()
        reset_from_step(1)
        mark_dirty("persona_changed")
        st.session_state["step"] = 2
        st.rerun()
