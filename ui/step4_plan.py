import streamlit as st

def render_step_4():
    st.header("🛠️ 최종 옵션 설정")
    st.caption("더 완벽한 글 작성을 위한 마지막 설정을 선택하세요.")

    # 1. 옵션 선택 영역 (체크박스)
    #
    with st.container():
        st.markdown("###") # 약간의 여백
        seo = st.checkbox("🔍 SEO 최적화 (검색 엔진 친화적 배치)")
        human = st.checkbox("✍️ AI 티 제거 (강화된 문장 재구성)")
        package = st.checkbox("🎁 발행 패키지 (제목 3종, FAQ, CTA 포함)")
        evidence = st.checkbox("📋 근거 라벨 표시 (정보의 신뢰도 명시)")
        
    st.markdown("---")

    # 2. 생성 시작 버튼 (이전 버튼을 없애고 화면 중앙/전체에 배치)
    # 버튼을 누르면 모든 설정값이 저장되고 Step 5로 이동합니다.
    if st.button("🚀 블로그 글 생성하기", type="primary", use_container_width=True):
        # [옵션 데이터 저장]
        st.session_state.blog['options'] = {
            "seo": seo,
            "humanize": human,
            "package": package,
            "evidence": evidence
        }
        
        # [기존 결과 초기화] 새 생성을 위해 이전 결과물을 비웁니다.
        st.session_state.blog['result'] = None
        
        # [Step 5 이동]
        st.session_state.step = 5
        st.rerun()

    # 하단 안내 문구
    st.caption("※ '생성하기'를 누르면 AI가 설계안에 맞춰 집필을 시작합니다.")
