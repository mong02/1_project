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

       # 2️⃣ 말투 (사진처럼: 박스 5개 + 예시 카드)
    st.subheader("선호하는 말투")

    # 프리셋(버튼 4개) + 직접 입력(버튼 1개)
    TONE_PRESETS = {
        "친근한": "이거 진짜 대박이죠? ㅎㅎ 저도 써보고 완전 반했잖아요~ 여러분도 꼭 한번 체험해보세요! 👍",
        "차분한": "이러한 현상은 우리 일상에서 흔히 발견할 수 있습니다. 조금 더 깊이 있게 살펴보겠습니다.",
        "정보중심": "핵심 포인트만 정리해드릴게요. 장단점과 체크리스트를 기준으로 선택하면 실수 확률이 줄어듭니다.",
        "감성적인": "창틈으로 스며드는 햇살을 보며 문득 그런 생각이 들었습니다. 우리의 일상은 작은 기적들로 채워져 있다고.",
    }
    DIRECT_LABEL = "직접 입력"

    # 현재 상태를 버튼 UI용 라벨로 변환
    current_mode = persona["tone"]["mode"]
    if current_mode == "custom":
        selected_label = DIRECT_LABEL
    else:
        # preset 저장값이 "친근한"처럼 들어있다고 가정 (없으면 기본값)
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
                    # custom_text는 유지 (사용자가 쓰던 내용 보존)
                else:
                    persona["tone"]["mode"] = "preset"
                    persona["tone"]["preset"] = lab
                    persona["tone"]["custom_text"] = ""
                st.rerun()

    st.write("")  # 살짝 여백

    # 선택된 말투에 따라: 예시 카드 or 직접입력
    if persona["tone"]["mode"] == "preset":
        preset = persona["tone"]["preset"] or "친근한"
        example = TONE_PRESETS.get(preset, "")

        # 사진처럼 "예시" 영역 보여주기 (깔끔하게)
        with st.container(border=True):
            st.markdown("**예시**")
            st.write(f"“{example}”")

    else:
        persona["tone"]["custom_text"] = st.text_input(
            "나만의 말투 설명",
            value=persona["tone"]["custom_text"],
            placeholder="예: 옆집 언니처럼 편하게, 하지만 정보는 정확하게",
        )


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
