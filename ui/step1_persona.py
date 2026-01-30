# 페르소나 입력 화면
# 직업, 톤, 금지어 등 세팅 구간

#step1_persona.py


import streamlit as st
from state import mark_dirty, reset_from_step, save_persona_to_disk

def render():
    st.title("작성자 프로필 설정")

    persona = st.session_state["persona"]

    role_job = st.text_input(
        "현재 역할/직업 (필수)",
        value=persona["role_job"]
    )

    tone_custom = st.text_input(
        "선호하는 말투 설명 (필수)",
        value=persona["tone"]["custom_text"]
    )

    mbti = st.selectbox(
        "MBTI (선택)",
        options=[None,
            "ISTJ","ISFJ","INFJ","INTJ","ISTP","ISFP","INFP","INTP",
            "ESTP","ESFP","ENFP","ENTP","ESTJ","ESFJ","ENFJ","ENTJ"
        ],
        index=0
    )

    avoid_raw = st.text_input(
        "피하고 싶은 키워드 (콤마 구분)",
        value=",".join(persona["avoid_keywords"])
    )
    avoid_keywords = [x.strip() for x in avoid_raw.split(",") if x.strip()]

    changed = (
        role_job != persona["role_job"]
        or tone_custom != persona["tone"]["custom_text"]
        or mbti != persona["mbti"]["type"]
        or avoid_keywords != persona["avoid_keywords"]
    )

    if changed:
        persona["role_job"] = role_job
        persona["tone"]["mode"] = "custom"
        persona["tone"]["custom_text"] = tone_custom
        persona["mbti"]["type"] = mbti
        persona["avoid_keywords"] = avoid_keywords

        mark_dirty("persona_changed")
        reset_from_step(1)


    disabled = not role_job.strip() or not tone_custom.strip()
    if st.button("저장", disabled=disabled, use_container_width=True):
        save_persona_to_disk()
        st.success("저장됐습니다. (Step1 유지)")
        st.rerun()

    # disabled = not role_job.strip() or not tone_custom.strip()
    #   if st.button("저장하고 다음 단계", disabled=disabled, use_container_width=True):
    #      save_persona_to_disk()
    #     st.session_state["step"] = 2
    #      st.rerun()
