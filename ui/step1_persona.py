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

    # 3️⃣ MBTI (선택) - 박스 버튼형
    st.subheader("MBTI (선택)")
    st.caption("원하는 MBTI를 클릭하세요. 다시 누르면 해제됩니다.")

    mbti_list = list(MBTI.keys())
    selected = persona["mbti"]["type"]

    cols = st.columns(4)  # 4 x 4 = 16개

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
                st.rerun()

    if persona["mbti"]["type"]:
        st.info(persona["mbti"]["style_desc"])

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
