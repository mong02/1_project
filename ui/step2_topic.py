# 카테고리 선택
# 세부 주제/제목 후보 클릭
# step2_topic.py

import sys
import os
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from config import POST_TYPES, HEADLINE_STYLES, CATEGORIES, SUBTOPICS_MAP
from state import reset_from_step

try:
    from agents.image_agent import analyze_image_agent, parse_image_analysis
    from agents.write_agent import suggest_titles_agent
except ImportError as e:
    # render 함수 내부에서 에러를 띄우기 위해 여기서 멈추지 않음
    analyze_image_agent = None
    suggest_titles_agent = None


def inject_custom_css():
    st.markdown(
        """
        <style>
        /* 선택된 Pills의 배경색과 글자색 변경 */
        div[data-testid="stPills"] button[aria-selected="true"] {
            background-color: #624AFF !important; /* 원하는 색 */
            color: white !important;
            border-color: #624AFF !important;
        }
        /* 마우스 올렸을 때 테두리 색 */
        div[data-testid="stPills"] button:hover {
            border-color: #624AFF !important;
            color: #624AFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# ====================================================
# UI 내부 컴포넌트 분리 (코드 가독성 및 유지보수)
# ====================================================

def render_photo_intent_section(topic_flow):
    """사진의 의도 입력 섹션 - 기본 스타일 사용"""
    st.markdown('<div class="icon-label">사진의 의도 (선택)</div>', unsafe_allow_html=True)
    topic_flow["images"]["intent"]["custom_text"] = st.text_input(
        "사진의 의도",
        value=topic_flow["images"]["intent"]["custom_text"],
        placeholder="예: 여행의 설렘을 강조하고 싶어, 제품의 디테일을 보여주고 싶어",
        label_visibility="collapsed"
    )


def render_title_input_section(topic_flow):
    """글 제목 입력 섹션 - 16pt 볼드 강조 스타일 사용"""
    st.markdown('<div class="icon-label" style="margin-top:15px; margin-bottom:15px;">🟪글 제목 또는 키워드</div>', unsafe_allow_html=True)

    # 전용 컨테이너 마커 적용 (CSS에서 .title-input-container 하위 요소를 스타일링함)
    st.markdown('<div class="title-input-container">', unsafe_allow_html=True)
    with st.container(border=False):
        current_title = topic_flow["title"]["selected"] or ""
        new_title = st.text_input(
            "글 제목",
            value=current_title,
            placeholder="추천 제목을 선택하거나 직접 입력하세요.",
            label_visibility="collapsed",
            key="title_input_field"
        )
        if new_title != current_title:
            topic_flow["title"]["selected"] = new_title
            st.session_state["_auto_filled"] = False
    st.markdown('</div>', unsafe_allow_html=True)


# ====================================================
# 단일 스크롤 페이지 - 모든 내용 통합
# ====================================================
def render_step2(ctx):
    """
    단일 스크롤 페이지: 주제 선정 + 제목 + 상세 설정 통합
    """
    inject_custom_css()

    if analyze_image_agent is None or suggest_titles_agent is None:
        st.error("에이전트 파일을 불러올 수 없습니다. 경로를 확인해주세요.")
        st.stop()

    # 세션 상태 로드
    topic_flow = st.session_state.get("topic_flow", None)
    options = st.session_state.get("options", None)

    if not topic_flow or not options:
        st.error("세션 데이터가 초기화되지 않았습니다.")
        return

    # _auto_filled 플래그 초기화
    if "_auto_filled" not in st.session_state:
        st.session_state["_auto_filled"] = False

    # AI 추천 주제 숨김/보임 상태 초기화
    if "show_ai_reco" not in st.session_state:
        st.session_state["show_ai_reco"] = True

    # ==========================
    # UI 색상 통일용 커스텀 CSS (Periwinkle Purple #624AFF)
    # ==========================
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        /* 1. 메인 포인트 컬러 설정 (보라색) */
        :root {
            --primary-color: #624AFF;
            --light-purple: #F0F0FF;
            --border-color: #E0E0E0;
            --card-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        /* 폰트 설정 */
        .stApp {
            font-family: 'Inter', -apple-system, sans-serif;
        }

        /* 헤더 중앙 정렬 */
        .centered-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .centered-header h2 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1A1A1A;
            margin-bottom: 10px;
        }
        .centered-header p {
            color: #666;
            font-size: 1.1rem;
        }

        /* 2. 컨테이너 (카드 UI) 스타일링 */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #EDEDED !important;
            border-radius: 16px !important;
            padding: 24px !important;
            background-color: white !important;
            box-shadow: var(--card-shadow) !important;
            margin-bottom: 20px !important;
        }

        /* 3. Pills (알약 버튼) 스타일링 - 이미지 연계 */
        div[data-testid="stPills"] button {
            border: 1px solid #EDEDED !important; /* 더 연한 테두리 */
            background-color: white !important;
            color: #666 !important;
            padding: 8px 16px !important;
            border-radius: 20px !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stPills"] button[aria-selected="true"] {
            border: 1px solid var(--primary-color) !important;
            background-color: var(--primary-color) !important;
            color: white !important;
            font-weight: 600 !important;
        }
        div[data-testid="stPills"] button:hover {
            border-color: var(--primary-color) !important;
            color: var(--primary-color) !important;
            background-color: #F8F7FF !important;
        }

        /* 4. Primary 버튼 (하단 완료 버튼 등) */
        button[kind="primary"] {
            background-color: var(--primary-color) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        button[kind="primary"]:hover {
            background-color: #5039D1 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(98, 74, 255, 0.2);
        }

        /* 6. 파일 업로더 커스텀 (점선 박스 느낌) */
        div[data-testid="stFileUploader"] section {
            background-color: #FAFAFF !important;
            border: 2px dashed #D6D6FF !important;
            border-radius: 12px !important;
            padding: 20px !important;
        }

        /* 카테고리 전용 컨테이너 (흰색 배경) - 누출 방지 강화 */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .category-marker) {
            background-color: white !important;
            border: 1px solid #EBE4FF !important;
            border-radius: 16px !important;
            padding: 24px !important;
            margin-bottom: 20px !important;
        }

        /* 카테고리 3열 그리드 적용 */
        div[data-testid="stVerticalBlock"]:has(.category-grid-marker) div[data-testid="stPills"] > div {
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 12px !important;
        }
        div[data-testid="stPills"] button {
            border: 1px solid #EBE4FF !important;
            border-radius: 12px !important;
            padding: 12px 10px !important;
        }

        /* AI 추천 주제 전체 컨테이너 (연보라 배경) - 이미지 스타일 반영 */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .reco-marker) {
            background-color: #F2F5FF !important; /* 이미지와 유사한 아주 연한 블루/퍼플 */
            border: 1px solid #E8EBF2 !important;
            border-radius: 18px !important;
            padding: 24px 30px !important; /* 여유로운 내부 간격 */
            margin-top: 15px !important;
            margin-bottom: 30px !important;
        }
        .reco-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding: 0;
        }
        .ai-close-btn {
            color: #ADB5BD; /* 이미지의 연한 회색 X */
            cursor: pointer;
            font-size: 1.4rem;
            font-weight: 300;
        }

        /* 추천 제목 버튼 (이미지 알약 형태 정밀 재현) */
        div.title-candidate-wrapper {
            margin-bottom: 12px !important; /* 버튼들 사이의 간격 확대 */
        }
        div.title-candidate-wrapper button {
            background-color: white !important;
            border: 1px solid #E6E9FC !important;
            border-radius: 40px !important;
            padding: 14px 28px !important;
            text-align: left !important;
            justify-content: flex-start !important;
            color: #4C51BF !important; /* 조금 더 차분한 퍼플 블루 */
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            width: auto !important;
            max-width: 100% !important;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03) !important;
            transition: all 0.2s ease !important;
        }
        div.title-candidate-wrapper button:hover {
            border-color: #624AFF !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 6px 15px rgba(98, 74, 255, 0.08) !important;
            transform: translateY(-1px);
        }

        /* 분석 결과 전용 컨테이너 (이미지 스타일 동기화) */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .analysis-marker) {
            background-color: #F2F5FF !important;
            border: 1px solid #E8EBF2 !important;
            border-radius: 18px !important;
            padding: 24px 30px !important;
            margin-bottom: 20px !important;
        }

        /* 기본 텍스트 입력 필드 (사진의 의도 등에 적용) */
        div[data-testid="stTextInput"] input {
            border-radius: 12px !important;
            border: 1px solid #EBE4FF !important;
            padding: 12px 20px !important;
            font-size: 1rem !important;
            background-color: #FAFAFF !important;
            color: #333 !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: #BBBBBB !important;
        }

        /* 글 제목 입력창 전용 스타일 (이미지처럼 강조) */
        .title-input-container div[data-testid="stTextInput"] input {
            font-size: 18pt !important; /* 이미지 느낌에 맞춰 조금 더 확대 */
            font-weight: 700 !important;
            color: #444444 !important;
            background-color: #FFFFFF !important;
            padding-top: 25px !important;
            padding-bottom: 25px !important;
            padding-left: 0px !important; /* 이미지처럼 왼쪽 여백 최소화 가능 시 */
            border: none !important; /* 이미지에서는 하단 보더나 아예 없는 느낌 */
            border-bottom: 2px solid #EEEEEE !important;
            border-radius: 0px !important;
        }
        .title-input-container div[data-testid="stTextInput"] input:focus {
            border-bottom: 2px solid #624AFF !important;
            box-shadow: none !important;
        }
        .title-input-container div[data-testid="stTextInput"] input::placeholder {
            color: #CCCCCC !important;
            font-weight: 700 !important;
        }

        /* 흰색 추천 주제 카드 (분석 결과 내부용) */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .recommendation-marker) {
            background-color: white !important;
            border: 1px solid #EBE4FF !important;
            border-radius: 12px !important;
            padding: 10px 18px !important; /* 패딩 축소 (15 -> 10) */
            margin-top: 0px !important;
        }

        /* 제목적용 버튼 정렬 */
        div[data-testid="column"]:has(button[key*="apply_mood_title_final"]) {
            display: flex;
            justify-content: flex-end;
            align-items: center;
        }
        button[key*="apply_mood_title_final"] {
            width: 100% !important; /* 너비를 채워서 상단 버튼과 정렬감 유지 */
            max-width: 120px !important;
            padding: 6px 12px !important;
            border-radius: 20px !important; /* 알약 형태 유지 */
        }

        /* 섹션 라벨 (이미지 기준 연한 그레이) */
        .icon-label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
            color: #8E8E8E !important;
            font-size: 1.15rem !important; /* 0.85rem에서 약 5px(0.3rem) 증가 */
            margin-bottom: 15px !important;
            letter-spacing: -0.01em;
        }

        /* 닫기 버튼 전용 스타일 및 주변 박스 제거 */
        div.reco-header-container button {
            background: transparent !important;
            border: none !important;
            color: #AAA !important;
            padding: 0 !important;
            font-size: 1.2rem !important;
            line-height: 1 !important;
            min-width: 20px !important;
            width: 20px !important;
            height: 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div.reco-header-container button:hover {
            color: #666 !important;
            background: rgba(0,0,0,0.05) !important;
            border-radius: 50% !important;
        }

        /* 추가 상세 설정 (Selectbox, TextArea) 스타일링 */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            border: 1px solid #EBE4FF !important;
            background-color: #FAFAFF !important;
            padding: 2px 4px !important;
        }
        div[data-testid="stTextArea"] textarea {
            border-radius: 12px !important;
            border: 1px solid #EBE4FF !important;
            background-color: #FAFAFF !important;
            padding: 12px 20px !important;
            font-size: 1rem !important;
            color: #333 !important;
        }

        /* Expander 스타일 개선 */
        div[data-testid="stExpander"] {
            border: 1px solid #F0F0FF !important;
            border-radius: 12px !important;
            background-color: white !important;
            box-shadow: none !important;
        }
        div[data-testid="stExpander"] summary {
            font-weight: 600 !important;
            color: #624AFF !important;
        }

        /* 하단 뒤로가기 버튼 스타일 - 분석 결과 헤더와 같은 색상 (#5D5CDE) */
        div.back-btn-container {
            display: flex;
            justify-content: center;
            margin-top: 30px;
        }
        div.back-btn-container button {
            color: #5D5CDE !important;
            background-color: transparent !important;
            border: 1px solid #EBE4FF !important;
            border-radius: 20px !important;
            padding: 4px 12px !important;
            font-size: 0.85rem !important;
            transition: all 0.2s ease !important;
        }
        div.back-btn-container button:hover {
            background-color: #F8F7FF !important;
            border-color: #5D5CDE !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. 중앙 헤더
    st.markdown("""
        <div class="centered-header">
            <h2>어떤 이야기를 써볼까요?</h2>
            <p>블로그 주제를 정하고 사진을 추가해보세요.</p>
        </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 1. 이미지 업로드 섹션
    # -------------------------------------------------
    with st.container(border=True):
        st.markdown('<div class="icon-label">📷 블로그 사진 추가 (선택)</div>', unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "여러 장 선택 가능",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            if len(uploaded_files) > 10:
                st.warning("⚠️ 이미지는 최대 10장까지만 추가할 수 있습니다.")
                uploaded_files = uploaded_files[:10]

            st.caption(f"사진 {len(uploaded_files)}장 선택됨")

            cols = st.columns(3)
            for idx, file in enumerate(uploaded_files):
                with cols[idx % 3]:
                    st.image(file, caption=f"{idx+1}", use_container_width=True)

            first_file_bytes = uploaded_files[0].getvalue()
        else:
            first_file_bytes = None
            if topic_flow["images"]["files"]:
                topic_flow["images"]["files"] = None
                topic_flow["images"]["analysis"] = {"raw": "", "mood": "", "tags": []}

        render_photo_intent_section(topic_flow)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("✨ 사진 먼저 분석하기 (추천 주제 받기)", key="btn_analyze_first", type="primary", use_container_width=True):
            if uploaded_files:
                with st.spinner("🔍 사진을 분석하여 주제를 추출 중입니다..."):
                    first_file_bytes = uploaded_files[0].getvalue()
                    # 사용자 의도를 최우선으로 전달
                    user_intent = topic_flow["images"]["intent"]["custom_text"] or ""
                    analysis_result = analyze_image_agent(first_file_bytes, user_intent=user_intent)
                    mood, tags = parse_image_analysis(analysis_result)

                    topic_flow["images"]["files"] = first_file_bytes
                    topic_flow["images"]["analysis"]["raw"] = analysis_result
                    topic_flow["images"]["analysis"]["mood"] = mood
                    topic_flow["images"]["analysis"]["tags"] = tags
                    st.toast("이미지 분석이 완료되었습니다!")
                    st.rerun()
            else:
                st.info("사진을 먼저 업로드해주세요.")

    # 분석 결과 표시
    if topic_flow["images"]["analysis"]["mood"]:
        outer_container = st.container()
        with outer_container:
            st.markdown('<div class="analysis-marker" style="display:none;"></div>', unsafe_allow_html=True)

            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="color: #624AFF; font-size: 1.4rem;">✨</span>
                    <h4 style="margin: 0; color: #5D5CDE; font-size: 1.15rem; font-weight: 700;">분석 결과</h4>
                </div>
                <div style="margin-bottom: 12px;">
                    <span style="font-weight: 700; color: #333; font-size: 1.1rem;">분위기: </span>
                    <span style="color: #444; font-size: 1.1rem; line-height: 1.5;">{topic_flow['images']['analysis']['mood']}</span>
                </div>
            """, unsafe_allow_html=True)

            tags = topic_flow["images"]["analysis"].get("tags", [])
            if tags:
                tag_html = "".join([
                    f"<span style='display:inline-block; background:white; padding:5px 12px; border-radius:8px; margin-right:8px; margin-bottom:8px; font-size:0.9rem; border:1px solid #D6CCFF; color:#624AFF; font-weight:500;'>#{t.strip().replace('#','')}</span>"
                    for t in tags
                ])
                st.markdown(f"<div style='margin-bottom:5px;'>{tag_html}</div>", unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="recommendation-marker" style="display:none;"></div>', unsafe_allow_html=True)
                c1, c2 = st.columns([0.72, 0.28], vertical_alignment="center")
                with c1:
                    st.markdown(
                        '<div style="color: #624AFF; font-weight: 600; font-size: 1.3rem; margin-bottom: 2px;">추천 주제</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<div style="color: #333; font-size: 1.05rem; line-height: 1.4; font-weight: 400;">"{topic_flow["images"]["analysis"]["mood"]}"</div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("제목적용 ↓", key="apply_mood_title_final", type="primary", use_container_width=True):
                        topic_flow["title"]["selected"] = topic_flow["images"]["analysis"]["mood"]
                        st.session_state["title_input_field"] = topic_flow["title"]["selected"]
                        st.session_state["_auto_filled"] = True
                        st.rerun()

    # -------------------------------------------------
    # 2. 카테고리 선택 & AI 제목 추천 (통합)
    # -------------------------------------------------
    with st.container():
        st.markdown('<div class="category-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="icon-label">🟪카테고리 선택</div>', unsafe_allow_html=True)
        st.markdown('<div class="category-grid-marker" style="display:none;"></div>', unsafe_allow_html=True)

        CATEGORIES_EXTENDED = CATEGORIES

        selected_cat = st.pills(
            "대주제",
            CATEGORIES_EXTENDED,
            selection_mode="single",
            default=topic_flow["category"]["selected"],
            label_visibility="collapsed"
        )

        if "last_gen_key" not in st.session_state:
            st.session_state["last_gen_key"] = None

        if selected_cat and selected_cat != topic_flow["category"]["selected"]:
            topic_flow["category"]["selected"] = selected_cat
            topic_flow["category"]["selected_subtopic"] = None
            topic_flow["title"]["candidates"] = []
            st.rerun()

        if topic_flow["category"]["selected"]:
            st.markdown('<div class="icon-label" style="margin-top:30px;">세부 주제</div>', unsafe_allow_html=True)
            current_cat = topic_flow["category"]["selected"]
            subtopics = SUBTOPICS_MAP.get(current_cat, ["기타", "트렌드", "정보공유", "궁금증", "도전기"])

            # 02.02 추가수정 : 기타/직접입력 선택 시 텍스트 입력으로 세부 주제를 받을 수 있도록 트리거 값 정의
            custom_subtopic_triggers = {"기타", "주제 직접 입력"}

            # 02.02 추가수정 : 이전에 직접 입력했던 값이 subtopics 목록에 없으면 pills 기본 선택값을 안전하게 보정
            default_sub = topic_flow["category"]["selected_subtopic"]
            if default_sub not in subtopics:
                fallback = next((t for t in subtopics if t in custom_subtopic_triggers), None)
                default_sub = fallback

            # 02.02 추가수정 : pills default를 default_sub로 변경 (직접입력 후 rerun 시 UI 깨짐 방지)
            selected_sub = st.pills(
                "세부 주제 목록",
                subtopics,
                selection_mode="single",
                default=default_sub,
                label_visibility="collapsed"
            )

            # 02.02 추가수정 : 직접입력 세부 주제 보관용 필드(custom_subtopic) 추가 및 로드
            custom_subtopic = topic_flow["category"].get("custom_subtopic", "")
            custom_input = custom_subtopic

            # 02.02 추가수정 : 기타/직접입력 선택 시에만 입력창 노출
            if selected_sub in custom_subtopic_triggers:
                custom_input = st.text_input(
                    "주제 직접 입력",
                    value=custom_subtopic or "",
                    placeholder="예: 혼자 떠나는 일본 소도시 여행기",
                    label_visibility="collapsed"
                )
                # 02.02 추가수정 : 입력값 변경 시 topic_flow에 저장
                if custom_input != custom_subtopic:
                    topic_flow["category"]["custom_subtopic"] = custom_input

            # 02.02 추가수정 : AI에 전달할 최종 세부 주제(effective_subtopic) 계산
            if selected_sub in custom_subtopic_triggers:
                effective_subtopic = custom_input.strip() if custom_input else None
            else:
                effective_subtopic = selected_sub
                # 02.02 추가수정 : 일반 선택으로 돌아오면 이전 custom_subtopic을 비워서 상태 꼬임 방지
                if custom_subtopic:
                    topic_flow["category"]["custom_subtopic"] = ""

            # 02.02 추가수정 : gen_key도 effective_subtopic 기준으로 생성(직접입력값 반영)
            current_gen_key = None
            if effective_subtopic:
                current_gen_key = f"{topic_flow['category']['selected']}_{effective_subtopic}"

            # 02.02 추가수정 : 트리거 조건을 selected_sub가 아닌 effective_subtopic 기준으로 변경(직접입력 반영)
            if effective_subtopic and effective_subtopic != topic_flow["category"]["selected_subtopic"]:
                topic_flow["category"]["selected_subtopic"] = effective_subtopic

                with st.spinner("💡 AI가 제목을 설계 중입니다..."):
                    # 분석 결과의 mood를 AI 추천에 반영
                    analysis_mood = topic_flow["images"]["analysis"]["mood"] or ""
                    titles = suggest_titles_agent(
                        category=topic_flow["category"]["selected"],
                        subtopic=effective_subtopic,
                        mood=analysis_mood or "일반적인",
                        user_intent=analysis_mood  # 분석 결과를 의도로 전달
                    )
                    topic_flow["title"]["candidates"] = titles
                    st.session_state["last_gen_key"] = current_gen_key
                    st.session_state["show_ai_reco"] = True
                st.rerun()

            # 02.02 추가수정 : 기타/직접입력 선택인데 입력값이 비어있으면 추천 후보/표시 상태를 초기화
            elif selected_sub in custom_subtopic_triggers and not effective_subtopic:
                if topic_flow["category"]["selected_subtopic"] is not None:
                    topic_flow["category"]["selected_subtopic"] = None
                    topic_flow["title"]["candidates"] = []
                    st.session_state["show_ai_reco"] = False

    # AI 추천 주제 영역
    if topic_flow["title"]["candidates"] and st.session_state.get("show_ai_reco", True):
        with st.container():
            st.markdown('<div class="reco-marker" style="display:none;"></div>', unsafe_allow_html=True)

            st.markdown('<div class="reco-header-container">', unsafe_allow_html=True)
            h1, h2 = st.columns([0.94, 0.06])
            with h1:
                st.markdown(
                    '<div style="color: #624AFF; font-size: 1.15rem; font-weight: 600; font-family: \'Inter\', sans-serif;">AI 추천 주제 (클릭하여 적용)</div>',
                    unsafe_allow_html=True
                )
            with h2:
                if st.button("X", key="close_reco_btn", type="tertiary"):
                    st.session_state["show_ai_reco"] = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-bottom: 15px;"></div>', unsafe_allow_html=True)

            for idx, t in enumerate(topic_flow["title"]["candidates"]):
                cleaned_t = re.sub(r'^\d+[\s.)-]+\s*', '', t).strip()
                if not cleaned_t:
                    continue

                st.markdown('<div class="title-candidate-wrapper">', unsafe_allow_html=True)
                if st.button(cleaned_t, key=f"title_btn_{idx}", use_container_width=False):
                    topic_flow["title"]["selected"] = cleaned_t
                    st.session_state["title_input_field"] = cleaned_t
                    st.session_state["_auto_filled"] = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    render_title_input_section(topic_flow)

    # -------------------------------------------------
    # 5. 상세 설정
    # -------------------------------------------------
    with st.container(border=True):
        st.markdown('<div class="icon-label" style="margin-top:5px; margin-bottom:10px;">⚙️ 추가 상세 설정 (선택)</div>', unsafe_allow_html=True)

        with st.expander("더 많은 설정 옵션 보기", expanded=False):
            st.markdown('<div style="margin-top:15px;"></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                try:
                    idx_post = POST_TYPES.index(options["post_type"])
                except:
                    idx_post = 0
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">글 성격</div>', unsafe_allow_html=True)
                options["post_type"] = st.selectbox("글 성격", POST_TYPES, index=idx_post, label_visibility="collapsed")
            with c2:
                try:
                    idx_head = HEADLINE_STYLES.index(options["headline_style"])
                except:
                    idx_head = 0
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">헤드라인 스타일</div>', unsafe_allow_html=True)
                options["headline_style"] = st.selectbox("헤드라인 스타일", HEADLINE_STYLES, index=idx_head, label_visibility="collapsed")

            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">📍 지역 또는 범위</div>', unsafe_allow_html=True)
                options["detail"]["region_scope"]["text"] = st.text_input(
                    "지역/범위",
                    value=options["detail"]["region_scope"]["text"],
                    placeholder="예: 강남구, 서울 전지역",
                    label_visibility="collapsed"
                )
            with col2:
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">👥 타겟 독자</div>', unsafe_allow_html=True)
                options["detail"]["target_reader"]["text"] = st.text_input(
                    "타겟 독자",
                    value=options["detail"]["target_reader"]["text"],
                    placeholder="예: 30대 직장인",
                    label_visibility="collapsed"
                )

            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="icon-label" style="margin-bottom:8px;">🗒️ 추가 요청사항</div>', unsafe_allow_html=True)
            options["detail"]["extra_request"]["text"] = st.text_area(
                "추가 요청",
                value=options["detail"]["extra_request"]["text"],
                placeholder="AI에게 전달할 추가 요청사항을 자유롭게 입력하세요.",
                label_visibility="collapsed"
            )

    # -------------------------------------------------
    # 7. 하단 완료 버튼
    # -------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("▷ AI 설계 내역 확인 및 생성 시작", type="primary", use_container_width=True):
        if not topic_flow["title"]["selected"]:
            st.error("글 제목을 최소한으로라도 완성해주세요!")
        else:
            reset_from_step(3)
            st.session_state["step"] = 3
            st.rerun()

    st.markdown('<div class="back-btn-container">', unsafe_allow_html=True)
    if st.button("← 이전 단계", key="back_to_step1"):
        st.session_state["step"] = 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def render(ctx):
    """app.py에서 'render'라는 이름으로 호출할 때 대응"""
    render_step2(ctx)