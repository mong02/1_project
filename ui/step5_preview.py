# 이런 글이 나온다는 미리 보기
# 최종 생성 버튼
import streamlit as st
from agents.write_agent import generate_post 
from state import reset_all, save_step3_to_disk

def render(ctx):
    """
    최종 결과 미리보기 및 편집 화면 (Step 5)
    개별 섹션 재생성 및 복사 기능을 지원합니다.
    """
    
    # --- [1단계: 글 생성 실행] ---
    if st.session_state["outputs"]["status"] == "idle":
        with st.spinner("✍️ AI가 블로그 글을 작성 중입니다... 잠시만 기다려주세요."):
            try:
                # write_agent의 통합 생성 함수 호출
                content = generate_post(ctx)
                st.session_state["outputs"]["result"] = content
                st.session_state["outputs"]["status"] = "ready"
                st.rerun()
            except Exception as e:
                st.session_state["outputs"]["status"] = "error"
                st.error(f"생성 중 오류 발생: {e}")
                return

    content = st.session_state["outputs"]["result"]
    if not content:
        return

    # CSS 주입: 카드형 UI 스타일
    st.markdown("""
        <style>
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            border: 1px solid #E6E9F2;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- [2단계: 상단 헤더 및 액션 버튼] ---
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### ✨ 작성이 완료되었습니다!")
        st.caption(f"👤 Designed by {st.session_state['persona'].get('role_job')} Persona")
    
    with col2:
        if st.button("💾 저장하기", use_container_width=True):
            save_step3_to_disk() # 현재 상태 저장
            st.success("저장되었습니다!")
    
    with col3:
        if st.button("🔄 전체 다시 생성", use_container_width=True):
            st.session_state["outputs"]["status"] = "idle"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- [3단계: 섹션별 렌더링 및 개별 재생성] ---
    
    # 1. 제목 (TITLE)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**📌 제목**")
    st.markdown(f"### {content.get('title', '제목 없음')}")
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. 서론 (INTRO)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**📝 서론 (Intro)**")
    # [에러 해결] 이미지 리스트와 캡션 리스트의 갯수를 맞춰줍니다.
    images = st.session_state["topic_flow"]["images"]["files"]
    if images:
        # 사진 갯수만큼 캡션을 복제하여 에러를 방지합니다.
        captions = ["분석된 이미지 기반 컨셉"] * len(images)
        st.image(images, use_container_width=400, caption=captions)
    
    st.markdown(content.get('summary', '서론 생성 중...'))
    st.markdown("</div>", unsafe_allow_html=True)

    # 3. 본문 (MAIN BODY)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**📖 본문 (Body)**")
    main_text = content.get('post_markdown', '').strip()
    if main_text:
            st.markdown(main_text)
    else:
            st.warning("⚠️ 본문 내용을 불러오지 못했습니다. '전체 다시 생성'을 눌러주세요.")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # 4. 해시태그 (HASHTAGS)
    st.markdown("<div class='card' style='background: #1E293B; color: white;'>", unsafe_allow_html=True)
    st.markdown("**#️⃣ 해시태그**")
    tags = " ".join(content.get("hashtags", []))
    st.markdown(f"<div style='color: #818CF8;'>{tags}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 5. AI 이미지 가이드
    st.markdown("<div class='card' style='background: #FEF3C7; border: 1px solid #F59E0B;'>", unsafe_allow_html=True)
    st.markdown("**📷 AI 이미지 배치 가이드**")
    st.markdown(content.get('image_guide', '제공된 이미지를 본문 중간에 배치하여 가독성을 높여보세요.'))
    st.markdown("</div>", unsafe_allow_html=True)

    # --- [4단계: 전체 복사 기능 (코드 블록 활용)] ---
    with st.expander("📋 전체 텍스트 복사하기"):
        full_text = f"제목: {content.get('title')}\n\n[서론]\n{content.get('summary')}\n\n[본문]\n{content.get('post_markdown')}\n\n{tags}"
        st.code(full_text, language=None)
        st.caption("위 박스의 우측 상단 아이콘을 클릭해 복사하세요.")

    # 하단 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✍️ 새 글 작성하기", use_container_width=True, type="primary"):
        reset_all() # state 초기화
        st.rerun()

