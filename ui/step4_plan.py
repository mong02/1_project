import streamlit as st

def render_step_4():
    st.header("🛠️ 마지막 옵션 설정")
    
    # --- 옵션 선택 공간 ---
    with st.container():
        seo = st.checkbox("🔍 SEO 최적화 (검색 노출 강화)")
        human = st.checkbox("✍️ AI 티 제거 (강화된 자연스러움)")
        package = st.checkbox("🎁 발행 패키지 (제목 3종, FAQ 포함)")
        evidence = st.checkbox("📋 근거 라벨 표시 (신뢰도 업)")

    st.markdown("---")

    # --- 하단 버튼 ---
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("이전으로"):
            st.session_state.step = 3
            st.rerun()
            
    with col2:
        if st.button("🚀 블로그 글 생성 시작", type="primary"):
            # 1. 옵션값 저장
            st.session_state.blog['options'] = {
                "seo": seo,
                "humanize": human,
                "package": package,
                "evidence": evidence
            }
            
            # 2. 기존 생성 결과 초기화 (새로 생성하기 위함)
            st.session_state.blog['result'] = None
            
            # 3. STEP 5로 이동
            st.session_state.step = 5
            st.rerun()
