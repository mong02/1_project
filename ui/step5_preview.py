# 이런 글이 나온다는 미리 보기
# 최종 생성 버튼
# step5_preview.py

import re
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

    def _count_heading_marks(text: str) -> dict:
        t = text or ""
        return {
            "h1": t.count("\n# "),
            "h2": t.count("\n## "),
            "h3": t.count("\n### "),
        }

    # CSS 주입: 카드형 UI 스타일 + 가독성 개선
    st.markdown("""
        <style>
        .preview-wrap {
            max-width: 820px;
            margin: 0 auto;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            border: 1px solid #E6E9F2;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .section-title {
            font-size: 14px;
            font-weight: 700;
            color: #6B7280;
            letter-spacing: 0.02em;
            margin-bottom: 8px;
        }
        .card .preview-body {
            font-size: 16px !important;
            line-height: 1.7;
            color: #222;
            max-width: 760px;
        }
        .card .preview-body p,
        .card .preview-body li {
            font-size: 16px !important;
        }
        .card .preview-body p {
            margin: 0 0 12px 0;
        }
        .card .preview-body h2,
        .card .preview-body h3,
        .card .preview-body h4 {
            margin: 18px 0 10px 0;
            line-height: 1.4;
        }
        .card .preview-body h1,
        .card .preview-body h2,
        .card .preview-body h3,
        .card .preview-body h4 {
            font-size: 16px !important;
            font-weight: 700;
            margin: 18px 0 10px 0;
            line-height: 1.4;
        }
        .card .preview-body h3 {
            font-size: 18px;
            font-weight: 700;
        }
        .card .preview-body li {
            margin-bottom: 6px;
        }
        .section-header {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 10px;
        }
        .section-header .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4F46E5;
            display: inline-block;
        }
        .section-title.body-title {
            font-size: 16px;
            font-weight: 800;
            color: #374151;
        }
        </style>
    """, unsafe_allow_html=True)

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
        st.markdown("<div class='preview-body'>", unsafe_allow_html=True)
        st.markdown(_normalize_markdown(text))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='preview-wrap'>", unsafe_allow_html=True)

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
    st.markdown(
        "<div class='section-header'><span class='dot'></span><div class='section-title'>제목</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"### {content.get('title', '제목 없음')}")
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. 서론 (INTRO)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-header'><span class='dot'></span><div class='section-title'>서론</div></div>",
        unsafe_allow_html=True,
    )
    # [에러 해결] 이미지 리스트와 캡션 리스트의 갯수를 맞춰줍니다.
    images = st.session_state["topic_flow"]["images"]["files"]
    image_plan = content.get("image_plan") or {}
    if images:
        # 사진 갯수만큼 캡션을 복제하여 에러를 방지합니다.
        captions = ["분석된 이미지 기반 컨셉"] * len(images)
        intro_idx = image_plan.get("intro_image_index")
        if isinstance(intro_idx, int) and 0 <= intro_idx < len(images):
            st.image(images[intro_idx], width=400, caption=captions[intro_idx])
        else:
            st.image(images[0], width=400, caption=captions[0])
    
    intro_text = content.get("intro_markdown") or content.get("summary") or "서론 생성 중..."
    _render_preview_markdown(intro_text)
    st.markdown("</div>", unsafe_allow_html=True)

    # 3. 본문 (MAIN BODY)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-header'><span class='dot'></span><div class='section-title body-title'>본문</div></div>",
        unsafe_allow_html=True,
    )
    main_text = (content.get("body_markdown") or content.get("post_markdown") or "").strip()
    if main_text:
            _render_preview_markdown(main_text)
    else:
            st.warning("⚠️ 본문 내용을 불러오지 못했습니다. '전체 다시 생성'을 눌러주세요.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 4. 아웃트로 (OUTRO)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-header'><span class='dot'></span><div class='section-title'>마무리</div></div>",
        unsafe_allow_html=True,
    )
    outro_text = content.get('outro', '').strip()
    if outro_text:
        _render_preview_markdown(outro_text)
    else:
        st.caption("아웃트로가 없습니다. 옵션에서 추천을 켜보세요.")
    st.markdown("</div>", unsafe_allow_html=True)

    # 5. 해시태그 (HASHTAGS)
    st.markdown("<div class='card' style='background: #1E293B; color: white;'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>해시태그</div>", unsafe_allow_html=True)
    tags = " ".join(content.get("hashtags", []))
    st.markdown(f"<div style='color: #818CF8;'>{tags}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 6. AI 이미지 가이드
    st.markdown("<div class='card' style='background: #FEF3C7; border: 1px solid #F59E0B;'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>이미지 배치 가이드</div>", unsafe_allow_html=True)
    st.markdown(content.get('image_guide', '제공된 이미지를 본문 중간에 배치하여 가독성을 높여보세요.'))
    st.markdown("</div>", unsafe_allow_html=True)

    # --- [4단계: 전체 복사 기능 (코드 블록 활용)] ---
    with st.expander("📋 전체 텍스트 복사하기"):
        full_text = (
            f"제목: {content.get('title')}\n\n"
            f"[서론]\n{content.get('intro_markdown') or content.get('summary')}\n\n"
            f"[본문]\n{content.get('body_markdown') or content.get('post_markdown')}\n\n"
            f"[마무리]\n{content.get('outro')}\n\n"
            f"{tags}"
        )
        st.code(full_text, language=None)
        st.caption("위 박스의 우측 상단 아이콘을 클릭해 복사하세요.")

    # 하단 버튼
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✍️ 새 글 작성하기", use_container_width=True, type="primary"):
        reset_all() # state 초기화
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
