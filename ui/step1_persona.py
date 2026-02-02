# 페르소나 입력 화면
# 직업, 톤, 금지어 등 세팅 구간

#step1_persona.py

import streamlit as st
from typing import Dict, List
def render(ctx): st.write("Step 1: Persona 화면")
# -----------------------------
# 데이터/상수
# -----------------------------
TONE_EXAMPLES: Dict[str, str] = {
    "친근한/구어체": "이거 진짜 대박이죠? ㅎㅎ 저도 써보고 완전 반했잖아요~ 여러분도 꼭 한번 체험해보세요! 👍",
    "차분한/경어체": "이러한 현상은 우리 일상에서 흔히 발견할 수 있습니다. 조금 더 깊이 있게 살펴보겠습니다.",
    "정보중심/건조체": "핵심 스펙은 다음과 같습니다. 전작 대비 약 15% 성능이 향상되었으며, 배터리 효율은 20% 개선되었습니다.",
    "감성적인/에세이": "창틈으로 스며드는 햇살을 보며 문득 그런 생각이 들었습니다. 우리의 일상은 작은 기적들로 채워져 있다고.",
}

MBTI_TYPES: List[str] = [
    "ISTJ","ISFJ","INFJ","INTJ",
    "ISTP","ISFP","INFP","INTP",
    "ESTP","ESFP","ENFP","ENTP",
    "ESTJ","ESFJ","ENFJ","ENTJ",
]

MBTI_PERSONAS: Dict[str, str] = {
    "ISTJ": "원칙과 기준이 분명해 ‘정리-근거-결론’ 구조로 신뢰감 있게 쓰는 스타일",
    "ISFJ": "독자 배려가 강해 ‘주의사항/도움 팁’을 친절하게 챙기는 따뜻한 스타일",
    "INFJ": "의미와 메시지를 담아 ‘인사이트+스토리’로 깊게 풀어내는 스타일",
    "INTJ": "목표 지향적으로 ‘문제-해결-전략’ 흐름을 설계하는 분석형 스타일",
    "ISTP": "군더더기 없이 핵심만 ‘체크리스트/요약’으로 정리하는 실전형 스타일",
    "ISFP": "감각적 표현이 살아있고 ‘분위기/경험’ 중심으로 담백하게 쓰는 스타일",
    "INFP": "진정성과 감성이 강해 ‘공감-경험-느낀 점’으로 연결하는 에세이 스타일",
    "INTP": "호기심이 많아 ‘왜?→원리→결론’처럼 논리적으로 파고드는 스타일",
    "ESTP": "속도감 있게 ‘바로 실행’ 위주로, 현실적인 팁을 던지는 액션형 스타일",
    "ESFP": "밝고 에너지 넘치게 ‘후기/리액션’ 중심으로 재미있게 쓰는 스타일",
    "ENFP": "아이디어가 풍부해 ‘예시/비유/스토리’로 확장하는 창의형 스타일",
    "ENTP": "반전과 논쟁을 즐겨 ‘관점 제시-반박-대안’으로 설득하는 스타일",
    "ESTJ": "명확하고 단호하게 ‘규칙/방법/프로세스’를 안내하는 리더형 스타일",
    "ESFJ": "사람 중심으로 ‘추천/상황별 가이드’에 강한 친화형 스타일",
    "ENFJ": "동기부여가 강해 ‘독자 행동 유도’와 메시지 전달이 뛰어난 코치형 스타일",
    "ENTJ": "큰 그림으로 ‘목표-전략-성과’ 프레임으로 끌고 가는 경영자 스타일",
}

def analyze_blog_style(blog_url: str) -> Dict[str, str]:
    # TODO: 실제 분석 함수로 교체
    return {
        "tone": "차분한/경어체",
        "writingStyle": "소제목-요약-근거-실전팁 구조",
        "impression": "정돈되고 신뢰감 있는 느낌",
    }

# -----------------------------
# 세션 상태 초기화
# -----------------------------
def init_state():
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "job": "",
            "tone": "",
            "mbti": "",
            "avoidKeywords": "",
            "blogUrl": "",
            "analyzedStyle": None,
            "customToneMode": False,
        }
    if "blog_url_input" not in st.session_state:
        st.session_state.blog_url_input = ""

init_state()

st.set_page_config(page_title="작성자 프로필 설정", page_icon="📝", layout="centered")

st.title("작성자 프로필 설정")
st.caption("AI가 선생님을 흉내낼 수 있도록 정보를 알려주세요.")

with st.container(border=True):
    # 1) 직업/역할 (필수)
    st.subheader("현재 역할/직업 (필수)")
    job_placeholder = "예: IT 개발자 / 30대 직장인 / 육아맘 / 맛집 탐험가"
    st.session_state.profile["job"] = st.text_input(
        "현재 역할/직업",
        value=st.session_state.profile["job"],
        placeholder=job_placeholder,
        label_visibility="collapsed",
    )

    st.divider()

    # 2) 말투
    st.subheader("선호하는 말투")

    preset_labels = list(TONE_EXAMPLES.keys())
    options = preset_labels + ["직접 입력"]

    current_tone = st.session_state.profile["tone"]
    is_preset = current_tone in TONE_EXAMPLES
    if current_tone and not is_preset:
        st.session_state.profile["customToneMode"] = True

    default_choice = "직접 입력" if st.session_state.profile["customToneMode"] else (current_tone if current_tone in options else options[0])
    choice = st.radio(
        "말투 선택",
        options=options,
        horizontal=True,
        index=options.index(default_choice) if default_choice in options else 0,
        label_visibility="collapsed",
    )

    if choice == "직접 입력":
        st.session_state.profile["customToneMode"] = True
        st.session_state.profile["tone"] = st.text_input(
            "나만의 말투 설명",
            value="" if is_preset else st.session_state.profile["tone"],
            placeholder="예: 유행어를 많이 쓰는, 사투리를 섞어 쓰는, 옆집 언니 같은...",
        )
    else:
        st.session_state.profile["customToneMode"] = False
        st.session_state.profile["tone"] = choice
        st.info(f'예시: "{TONE_EXAMPLES.get(choice, "말투를 선택하면 예시가 표시됩니다.")}"')

    st.divider()

    # 3) MBTI (선택) - 박스(버튼) 그리드
    st.subheader("나의 MBTI (선택)")
    st.caption("원하는 MBTI를 클릭하세요. 다시 누르면 해제됩니다.")

    cols = st.columns(8)
    selected = st.session_state.profile["mbti"]

    for i, mbti in enumerate(MBTI_TYPES):
        with cols[i % 8]:
            is_selected = (selected == mbti)
            btn_label = f"✅ {mbti}" if is_selected else mbti

            if st.button(btn_label, key=f"mbti_{mbti}", use_container_width=True):
                st.session_state.profile["mbti"] = "" if is_selected else mbti
                st.rerun()

    if st.session_state.profile["mbti"]:
        mbti = st.session_state.profile["mbti"]
        desc = MBTI_PERSONAS[mbti]
        st.success(f'{mbti} 스타일: "{desc}"')

    st.divider()

    # 4) 피하고 싶은 키워드 (선택)
    st.subheader("피하고 싶은 키워드 (선택)")
    st.session_state.profile["avoidKeywords"] = st.text_input(
        "피하고 싶은 키워드",
        value=st.session_state.profile["avoidKeywords"],
        placeholder="예: 솔직히, ~인 것 같아요, 사실",
        label_visibility="collapsed",
    )
    st.caption("* 입력하신 단어는 글 작성 시 사용하지 않도록 AI에게 요청합니다.")

    st.divider()

    # 5) 블로그 URL 분석 (선택)
    st.subheader("운영 중인 블로그 분석 (선택)")

    col1, col2 = st.columns([3, 1])

    with col1:
        # ✅ 수정한 부분(핵심):
        # on_change 없이, 위젯 값 자체를 매 rerun마다 즉시 읽어서 profile에 반영
        st.text_input(
            "블로그 URL",
            key="blog_url_input",
            placeholder="https://blog.naver.com/my-blog-id",
            label_visibility="collapsed",
        )
        st.session_state.profile["blogUrl"] = st.session_state.blog_url_input.strip()

    with col2:
        analyze_clicked = st.button(
            "스타일 분석",
            use_container_width=True,
            disabled=(not st.session_state.profile["blogUrl"]),
        )

    if analyze_clicked:
        with st.spinner("블로그 스타일 분석 중..."):
            analysis = analyze_blog_style(st.session_state.profile["blogUrl"])
            st.session_state.profile["analyzedStyle"] = analysis

    if st.session_state.profile["analyzedStyle"]:
        a = st.session_state.profile["analyzedStyle"]
        st.success("분석 완료! AI가 이 스타일을 기억합니다.")
        st.write(f"**말투:** {a.get('tone','')}")
        st.write(f"**구성:** {a.get('writingStyle','')}")
        st.write(f"**느낌:** {a.get('impression','')}")
    else:
        st.caption("* 블로그 URL을 말투 분석에 활용할 수 있습니다.")

# 하단 버튼 (필수 조건: 직업 + 말투)
job_ok = st.session_state.profile["job"].strip() != ""
tone_ok = st.session_state.profile["tone"].strip() != ""
is_ready = job_ok and tone_ok

st.markdown("---")
colA, colB = st.columns([2, 1])

with colA:
    st.write("필수 조건: **직업/역할 + 말투**")

with colB:
    if st.button("설정 완료 및 글쓰기 시작", disabled=not is_ready, use_container_width=True):
        st.success("프로필 설정 완료!")
        st.json(st.session_state.profile)
