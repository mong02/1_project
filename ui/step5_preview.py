# 이런 글이 나온다는 미리 보기
# 최종 생성 버튼
# step5_preview.py

import re
import streamlit as st

from agents.write_agent import generate_post 
from state import reset_all

def render(ctx):
    """
    최종 결과 미리보기 및 편집 화면 (Step 5)
    개별 섹션 재생성 및 복사 기능을 지원합니다.
    """
    
    # --- [1단계: 글 생성 실행] ---
    if st.session_state["outputs"]["status"] == "idle":
        
        # 1) 로딩 화면 표시 (Lottie Animation)
        ph = st.empty()
        
        with ph.container():
            # 로딩 메시지 표시
            # 메시지
            st.markdown(
                """
                <div style='text-align:center; padding-top: 20px;'>
                    <h2 style='color:#E30613; margin-bottom:10px; font-weight: 800;'>AI 셰프가 요리 중입니다!</h2>
                    <p style='font-size:1.2rem; color:#333; font-weight: 600; line-height: 1.6;'>
                        선택하신 재료로 맛있는 글을 볶고 있어요.<br>
                        <span style='font-size:1rem; color:#888; font-weight:500;'>(약 15~30초 정도 소요됩니다)</span>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        try:
            # 3) 실제 생성 작업
            content = generate_post(ctx)
            
            # 생성 후 로딩 화면 제거
            ph.empty()
            
            st.session_state["outputs"]["result"] = content
            st.session_state["outputs"]["status"] = "ready"
            st.rerun()
            
        except Exception as e:
            ph.empty() # 에러 시에도 로딩 제거
            st.session_state["outputs"]["status"] = "error"
            st.error(f"생성 중 오류 발생: {e}")
            return

    content = st.session_state["outputs"]["result"]
    if not content:
        return

    def _normalize_markdown(text: str) -> str:
        if not text:
            return ""
        t = str(text)
        # 헤딩이 문장 중간에 붙는 경우를 분리
        t = re.sub(r"([^\n])(\s*###\s+)", r"\1\n\n### ", t)
        # 과도한 연속 공백/줄바꿈 정리
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    def _render_preview_markdown(text: str):
        # Neo-Brutalist Typography applied via global CSS, just need clean HTML wrapper
        st.markdown(f"<div style='line-height:1.7; color:#111;'>{_normalize_markdown(text)}</div>", unsafe_allow_html=True)

    # --- [2단계: 상단 헤더 및 액션 버튼] ---
    # Global Style의 Container를 사용하여 통일감 부여
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("""
                <div style="display: flex; align-items: center; gap: 8px;">
                    <h3 style="margin:0; font-weight:800; color:#E30613;">작성이 완료되었습니다!</h3>
                </div>
            """, unsafe_allow_html=True)
            role = st.session_state['persona'].get('role_job', 'AI Editor')
            st.caption(f"Designed by {role} Persona")
        
        with col2:
            # 전체 텍스트 구성
            hashtags = content.get("hashtags") or []
            if isinstance(hashtags, str):
                hashtags = [hashtags]
            
            full_text = (
                f"제목: {content.get('title')}\n\n"
                f"{content.get('intro_markdown') or content.get('summary')}\n\n"
                f"{content.get('body_markdown') or content.get('post_markdown')}\n\n"
                f"{content.get('conclusion_markdown') or content.get('outro')}\n\n"
                f"{' '.join(['#'+t.strip().replace('#','') for t in hashtags])}"
            )
            
            # 팝오버를 사용하여 '복사하기' 버튼처럼 동작하게 구현
            with st.popover("📋 전체 복사", use_container_width=True):
                st.caption("우측 상단 아이콘을 눌러 복사하세요")
                st.code(full_text, language=None)

        
        with col3:
            if st.button("전체 다시 생성", use_container_width=True):
                st.session_state["outputs"]["status"] = "idle"
                st.rerun()

    # --- [3단계: 섹션별 렌더링] ---
    
    # 1. 제목 (TITLE)
    with st.container(border=True):
        st.markdown("""
            <div style="margin-bottom:12px; border-bottom:2px solid #000; padding-bottom:8px;">
                <span style="font-size:1.1rem; font-weight:800; color:#000;">제목</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<h2 style='margin:0; font-weight:800; color:#E30613;'>{content.get('title', '제목 없음')}</h2>", unsafe_allow_html=True)

    # 2. 서론 (INTRO)
    with st.container(border=True):
        st.markdown("""
            <div style="margin-bottom:12px; border-bottom:2px solid #000; padding-bottom:8px;">
                <span style="font-size:1.1rem; font-weight:800; color:#000;">서론 및 대표 이미지</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 이미지
        images = st.session_state["topic_flow"]["images"]["files"]
        image_plan = content.get("image_plan") or {}
        
        if images:
            intro_idx = image_plan.get("intro_image_index")
            target_img = images[0]
            if isinstance(intro_idx, int) and 0 <= intro_idx < len(images):
                target_img = images[intro_idx]
            
            st.image(target_img, width=400, caption="대표 이미지 (AI 선정)")
        
        st.markdown("<br>", unsafe_allow_html=True)
        intro_text = content.get("intro_markdown") or content.get("summary") or "서론 생성 중..."
        _render_preview_markdown(intro_text)

    # 3. 본문 (MAIN BODY)
    with st.container(border=True):
        st.markdown("""
            <div style="margin-bottom:12px; border-bottom:2px solid #000; padding-bottom:8px;">
                <span style="font-size:1.1rem; font-weight:800; color:#000;">본문 내용</span>
            </div>
        """, unsafe_allow_html=True)
        
        main_text = (content.get("body_markdown") or content.get("post_markdown") or "").strip()
        if main_text:
            _render_preview_markdown(main_text)
        else:
            st.warning("본문 내용을 불러오지 못했습니다. '전체 다시 생성'을 눌러주세요.")

    # 4. 결론 및 해시태그 (Combined)
    with st.container(border=True):
        st.markdown("""
            <div style="margin-bottom:12px; border-bottom:2px solid #000; padding-bottom:8px;">
                <span style="font-size:1.1rem; font-weight:800; color:#000;">결론 및 해시태그</span>
            </div>
        """, unsafe_allow_html=True)
        
        conclusion = content.get("conclusion_markdown") or content.get("outro") or ""
        hashtags = content.get("hashtags") or []
        
        if conclusion:
            _render_preview_markdown(conclusion)
            st.markdown("---")
            
        if hashtags:
            if isinstance(hashtags, str):
                hashtags = [hashtags] # Normalize if string
            
            # Chip Style
            tags_html = " ".join([
                f"<span style='display:inline-block; background:#FFD400; padding:4px 12px; border-radius:20px; border:2px solid #000; font-weight:700; font-size:0.9rem; margin-right:6px; margin-bottom:6px; box-shadow:2px 2px 0px #000;'>#{tag.strip().replace('#','')}</span>" 
                for tag in hashtags
            ])
            st.markdown(tags_html, unsafe_allow_html=True)

    # --- [4단계: 전체 복사 기능 (코드 블록 활용)] ---
    # --- [4단계: 전체 복사 기능 (코드 블록 활용)] ---
    # (상단 버튼으로 통합되어 제거됨)


    # 하단 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("새 글 작성하기", use_container_width=True, type="primary"):
        reset_all() # state 초기화
        st.rerun()