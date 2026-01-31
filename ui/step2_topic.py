# 카테고리 선택
# 세부 주제/제목 후보 클릭
import sys
import os
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from config import POST_TYPES, HEADLINE_STYLES, CATEGORIES, SUBTOPICS_MAP

try:
    from agents.image_agent import analyze_image_agent, parse_image_analysis
    from agents.write_agent import suggest_titles_agent
except ImportError as e:
    st.error(f"파일을 찾을 수 없습니다: {e}")
    st.stop()
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
# 단일 스크롤 페이지 - 모든 내용 통합
# ====================================================
def render_step3(ctx):
    """
    단일 스크롤 페이지: 주제 선정 + 제목 + 상세 설정 통합
    """
    # 세션 상태 로드
    topic_flow = st.session_state.get("topic_flow", None)
    options = st.session_state.get("options", None)

    if not topic_flow or not options:
        st.error("세션 데이터가 초기화되지 않았습니다.")
        return

    # _auto_filled 플래그 초기화
    if "_auto_filled" not in st.session_state:
        st.session_state["_auto_filled"] = False

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

        /* 3. Pills (알약 버튼) 스타일링 */
        div[data-testid="stPills"] button {
            border: 1px solid #E0E0E0 !important;
            background-color: white !important;
            color: #666 !important;
            padding: 8px 16px !important;
            border-radius: 20px !important;
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

        /* AI 추천 주제 전체 컨테이너 (연보라 배경) - 콤팩트 레이아웃 */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .reco-marker) {
            background-color: #F0F2FF !important;
            border: 1px solid #D6CCFF !important;
            border-radius: 16px !important;
            padding: 8px 28px !important; /* 위아래 패딩을 8로 축소 */
            margin-top: 10px !important;
            margin-bottom: 25px !important;
        }
        .reco-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px; /* 헤더 여백을 8로 조정 */
            padding: 0;
        }
        .reco-header h5 {
            color: #624AFF !important;
            font-size: 1.05rem !important;
            margin: 0 !important;
            font-weight: 600 !important;
        }
        .ai-close-btn {
            color: #AAA;
            cursor: pointer;
            font-size: 1.2rem;
            line-height: 1;
        }

        /* 추천 제목 버튼 (일관된 8px 간격 적용) */
        div.title-candidate-wrapper {
            margin-bottom: 3px !important; /* 버튼들 사이의 간격도 8로 통일 */
        }
        div.title-candidate-wrapper button {
            background-color: white !important;
            border: 1px solid #D6CCFF !important;
            border-radius: 30px !important;
            padding: 12px 26px !important; /* 이미지의 알약 형태 재현 */
            text-align: left !important;
            justify-content: flex-start !important;
            color: #624AFF !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            width: auto !important;
            max-width: 100% !important;
            box-shadow: 0 1px 3px rgba(98, 74, 255, 0.05) !important;
            transition: all 0.2s ease !important;
        }
        div.title-candidate-wrapper button:hover {
            border-color: #624AFF !important;
            background-color: #F9F9FF !important;
            box-shadow: 0 4px 10px rgba(98, 74, 255, 0.1) !important;
            transform: translateX(4px);
        }

        /* 분석 결과 전용 컨테이너 (누출 방지 강화) */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .analysis-marker) {
            background-color: #F0F2FF !important;
            border: 1px solid #D6CCFF !important;
            border-radius: 16px !important;
            padding: 24px !important;
            margin-bottom: 20px !important;
        }

        /* 텍스트 입력 필드 */
        div[data-testid="stTextInput"] input {
            border-radius: 12px !important;
            border: 1px solid #EBE4FF !important;
            padding: 18px 24px !important;
            font-size: 1.15rem !important;
            background-color: #FAFAFF !important;
        }

        /* 흰색 추천 주제 카드 (분석 결과 내부용) */
        div[data-testid="stVerticalBlock"]:has(> div:first-child .recommendation-marker) {
            background-color: white !important;
            border: 1px solid #EBE4FF !important;
            border-radius: 12px !important;
            padding: 15px 20px !important;
            margin-top: 0px !important;
        }

        /* 제목적용 버튼 정렬 */
        div[data-testid="column"]:has(button[key*="apply_mood_title_final"]) {
            display: flex;
            justify-content: flex-end;
            align-items: center;
        }
        button[key*="apply_mood_title_final"] {
            width: auto !important;
            min-width: 110px !important;
            padding: 6px 16px !important;
            border-radius: 8px !important;
        }

        /* 헤더 텍스트 색상 */
        h3, h4, h5 {
            color: #333 !important;
            font-weight: 600 !important;
        }

        /* 아이콘 라벨 스타일 (샘플 기준 그레이 텍스트) */
        .icon-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 500;
            color: #888;
            font-size: 0.95rem;
            margin-bottom: 12px;
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

    # ─────────────────────────────────────────
    # 1. 이미지 업로드 섹션
    # ─────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="icon-label">📷 블로그 사진 추가 (선택)</div>', unsafe_allow_html=True)

        # 멀티 파일 업로더
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
            
            # 그리드 표시
            cols = st.columns(3)
            for idx, file in enumerate(uploaded_files):
                with cols[idx % 3]:
                    st.image(file, caption=f"{idx+1}", use_container_width=True)

            # 첫 번째 이미지 파일 바이트 저장 (분석용으로 대기)
            first_file_bytes = uploaded_files[0].getvalue()
        else:
            first_file_bytes = None
            if topic_flow["images"]["files"]:
                topic_flow["images"]["files"] = None
                topic_flow["images"]["analysis"] = {"raw": "", "mood": "", "tags": []}

        # 사진의 의도
        st.markdown('<div class="icon-label">✉️ 사진의 의도 (선택)</div>', unsafe_allow_html=True)
        topic_flow["images"]["intent"]["custom_text"] = st.text_input(
            "사진의 의도",
            value=topic_flow["images"]["intent"]["custom_text"],
            placeholder="예: 여행의 설렘을 강조하고 싶어, 제품의 디테일을 보여주고 싶어",
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 분석 버튼 (AI 제목 추천받기처럼 UI 변경)
        if st.button("✨ 사진 먼저 분석하기 (추천 주제 받기)", key="btn_analyze_first", type="primary", use_container_width=True):
             if uploaded_files:
                 with st.spinner("🔍 사진을 분석하여 주제를 추출 중입니다..."):
                     # 첫 번째 사진 기반 분석 수행
                     first_file_bytes = uploaded_files[0].getvalue()
                     analysis_result = analyze_image_agent(first_file_bytes)
                     mood, tags = parse_image_analysis(analysis_result)
                     
                     # 세션 상태 업데이트
                     topic_flow["images"]["files"] = first_file_bytes
                     topic_flow["images"]["analysis"]["raw"] = analysis_result
                     topic_flow["images"]["analysis"]["mood"] = mood
                     topic_flow["images"]["analysis"]["tags"] = tags
                     st.toast("이미지 분석이 완료되었습니다!")
                     st.rerun() # 레이아웃 갱신을 위해 rerun
             else:
                 st.info("사진을 먼저 업로드해주세요.")


    # 분석 결과 표시 (업로드 컨테이너 밖으로 이동하여 너비를 카테고리 박스와 맞춤)
    if topic_flow["images"]["analysis"]["mood"]:
        # st.container()를 사용하여 불필요한 테두리 제거 (CSS로 배경 적용)
        outer_container = st.container()
        with outer_container:
            # 마커 클래스 삽입 (보라색 박스용 - 공간 차지하지 않도록 style 추가)
            st.markdown('<div class="analysis-marker" style="display:none;"></div>', unsafe_allow_html=True)
            
            # 분석 결과 헤더 (샘플처럼 보라색 강조)
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="color: #624AFF; font-size: 1.4rem;">✨</span>
                    <h4 style="margin: 0; color: #5D5CDE; font-size: 1.15rem; font-weight: 700;">분석 결과</h4>
                </div>
                <div style="margin-bottom: 20px;">
                    <span style="font-weight: 700; color: #333; font-size: 1.2rem;">분위기: </span>
                    <span style="color: #444; font-size: 1.15rem; line-height: 1.5;">{topic_flow['images']['analysis']['mood']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # 태그 (샘플 스타일)
            tags = topic_flow["images"]["analysis"].get("tags", [])
            if tags:
                tag_html = "".join([f"<span style='display:inline-block; background:white; padding:7px 16px; border-radius:10px; margin-right:8px; margin-bottom:12px; font-size:0.95rem; border:1px solid #D6CCFF; color:#624AFF; font-weight:500;'>#{t.strip().replace('#','')}</span>" for t in tags])
                st.markdown(f"<div style='margin-bottom:10px;'>{tag_html}</div>", unsafe_allow_html=True)
            
            # 내부 하얀색 추천 주제 카드
            with st.container():
                st.markdown('<div class="recommendation-marker" style="display:none;"></div>', unsafe_allow_html=True)
                c1, c2 = st.columns([0.76, 0.24], vertical_alignment="center")
                with c1:
                    st.markdown(f'<div style="color: #624AFF; font-weight: 600; font-size: 1.05rem; margin-bottom: 6px;">추천 주제</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="color: #333; font-size: 1.1rem; line-height: 1.4; font-weight: 400;">"{topic_flow["images"]["analysis"]["mood"]}"</div>', unsafe_allow_html=True)
                with c2:
                    if st.button("제목적용 ↓", key="apply_mood_title_final", type="primary"):
                         topic_flow["title"]["selected"] = topic_flow["images"]["analysis"]["mood"]
                         st.session_state["title_input_field"] = topic_flow["title"]["selected"]
                         st.session_state["_auto_filled"] = True
                         st.rerun()


    # ─────────────────────────────────────────
    # ─────────────────────────────────────────
    # 2. 카테고리 선택 & AI 제목 추천 (통합)
    # ─────────────────────────────────────────
    # 카테고리 대주제 박스 (흰색 배경 유지)
    with st.container():
        st.markdown('<div class="category-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="icon-label">카테고리 선택</div>', unsafe_allow_html=True)
        st.markdown('<div class="category-grid-marker" style="display:none;"></div>', unsafe_allow_html=True)
        
        # 카테고리 목록 확장 (샘플 2 기준)
        CATEGORIES_EXTENDED = [
            "비즈니스/경제", "IT/기술", "생활/라이프",
            "건강/자기계발", "교육/학습", "쇼핑/소비",
            "자동차/교통", "취업/직장", "기타"
        ]

        selected_cat = st.pills(
            "대주제",
            CATEGORIES_EXTENDED,
            selection_mode="single",
            default=topic_flow["category"]["selected"],
            label_visibility="collapsed"
        )
        
        # 이전 생성 정보 기록
        if "last_gen_key" not in st.session_state:
            st.session_state["last_gen_key"] = None

        # 카테고리가 바뀌면 제목 후보 초기화 및 세부주제 초기화
        if selected_cat and selected_cat != topic_flow["category"]["selected"]:
            topic_flow["category"]["selected"] = selected_cat
            topic_flow["category"]["selected_subtopic"] = None
            topic_flow["title"]["candidates"] = [] # 초기화
            st.rerun()

        if topic_flow["category"]["selected"]:
            st.markdown('<div class="icon-label" style="margin-top:30px;">세부 주제</div>', unsafe_allow_html=True)
            current_cat = topic_flow["category"]["selected"]
            # SUBTOPICS_MAP에 없으면 기본값 생성
            subtopics = SUBTOPICS_MAP.get(current_cat, ["기타", "트렌드", "정보공유", "궁금증", "도전기"])
            
            selected_sub = st.pills(
                "세부 주제 목록",
                subtopics,
                selection_mode="single",
                default=topic_flow["category"]["selected_subtopic"],
                label_visibility="collapsed"
            )

            # 세부주제까지 선택되었을 때만 트리거
            current_gen_key = f"{topic_flow['category']['selected']}_{selected_sub}"
            
            if selected_sub and selected_sub != topic_flow["category"]["selected_subtopic"]:
                topic_flow["category"]["selected_subtopic"] = selected_sub
                # 자동 생성 실행
                with st.spinner("💡 AI가 제목을 설계 중입니다..."):
                    titles = suggest_titles_agent(
                        category=topic_flow["category"]["selected"],
                        subtopic=selected_sub,
                        mood=topic_flow["images"]["analysis"]["raw"] or "일반적인",
                        user_intent=topic_flow["images"]["intent"]["custom_text"]
                    )
                    topic_flow["title"]["candidates"] = titles
                    st.session_state["last_gen_key"] = current_gen_key
                st.rerun()

    # AI 추천 주제 영역 (카테고리 박스 밖으로 이동하여 독립적인 박스로 표시)
    if topic_flow["title"]["candidates"]:
        with st.container():
            st.markdown('<div class="reco-marker" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="reco-header">
                    <h5>AI 추천 주제 (클릭하여 적용)</h5>
                    <div class="ai-close-btn">×</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 버튼들은 HTML 외부에 배치하여 클릭 이벤트 캡처
            for idx, t in enumerate(topic_flow["title"]["candidates"]):
                # 앞에 숫자와 점(1. 2. 등) 제거 (LLM 응답 정제)
                cleaned_t = re.sub(r'^\d+[\s.)-]+\s*', '', t).strip()
                if not cleaned_t: continue
                
                st.markdown(f'<div class="title-candidate-wrapper">', unsafe_allow_html=True)
                if st.button(cleaned_t, key=f"title_btn_{idx}", use_container_width=False):
                    topic_flow["title"]["selected"] = cleaned_t
                    st.session_state["title_input_field"] = cleaned_t
                    st.session_state["_auto_filled"] = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # 3. 글 제목 입력
    # ─────────────────────────────────────────
    st.markdown('<div class="icon-label" style="margin-top:10px; margin-bottom:5px;">글 제목 또는 키워드</div>', unsafe_allow_html=True)
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

    # ─────────────────────────────────────────
    # 5. 상세 설정
    # ─────────────────────────────────────────
    with st.container(border=True):
        st.subheader("⚙️ 추가 상세 설정")
        with st.expander("더 많은 설정 옵션 보기", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                try: idx_post = POST_TYPES.index(options["post_type"])
                except: idx_post = 0
                options["post_type"] = st.selectbox("글 성격", POST_TYPES, index=idx_post)
            with c2:
                try: idx_head = HEADLINE_STYLES.index(options["headline_style"])
                except: idx_head = 0
                options["headline_style"] = st.selectbox("헤드라인 스타일", HEADLINE_STYLES, index=idx_head)

            st.markdown("")
            st.caption("🔗 **이전 시리즈 연결 (선택)**")
            options["detail"]["series"]["prev_url"] = st.text_input(
                "이전 글 URL",
                value=options["detail"]["series"]["prev_url"] or "",
                placeholder="https://...",
                label_visibility="collapsed"
            )

            st.markdown("")
            options["detail"]["region_scope"]["text"] = st.text_input(
                "📍 지역 또는 범위 (선택)",
                value=options["detail"]["region_scope"]["text"],
                placeholder="예: 강남구, 서울 전지역"
            )
            options["detail"]["target_reader"]["text"] = st.text_input(
                "👥 타겟 독자 (선택)",
                value=options["detail"]["target_reader"]["text"],
                placeholder="예: 30대 직장인"
            )
            options["detail"]["extra_request"]["text"] = st.text_area(
                "🗒️ 추가 요청",
                value=options["detail"]["extra_request"]["text"],
                placeholder="AI에게 전달할 추가 요청사항"
            )

    # ─────────────────────────────────────────
    # 7. 하단 완료 버튼
    # ─────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("▷ AI 설계 내역 확인 및 생성 시작", type="primary", use_container_width=True):
        if not topic_flow["title"]["selected"]:
            st.error("글 제목을 최소한으로라도 완성해주세요!")
        else:
            st.session_state["step"] = 4
            st.rerun()


# render 함수를 render_step3로 연결
def render(ctx):
    render_step3(ctx)
