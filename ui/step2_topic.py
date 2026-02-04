# 카테고리 선택
# 세부 주제/제목 후보 클릭
# step2_topic.py

import sys
import os

import io
from PIL import Image
from typing import Dict, Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import streamlit as st
from config import POST_TYPES, HEADLINE_STYLES, CATEGORIES, SUBTOPICS_MAP
from state import reset_from_step
from utils.prompt_loader import load_prompt, render_prompt

# 에이전트 임포트
try:
    from agents.image_agent import analyze_image_agent, parse_image_analysis
    from agents.write_agent import suggest_titles_agent
except ImportError as e:
    analyze_image_agent = None
    suggest_titles_agent = None


# =========================================================
# [Helper Functions] 공통 로직 및 유틸리티
# =========================================================




@st.cache_data
def resize_image_cached(image_bytes, max_size=400):
    """이미지 바이트를 받아 300~400px 내외로 리사이징하여 반환합니다."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # RGBA 등을 RGB로 변환 (JPEG 저장용)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        width, height = img.size
        # 긴 쪽을 max_size에 맞춤
        if width > height:
            if width > max_size:
                height = int((max_size / width) * height)
                width = max_size
        else:
            if height > max_size:
                width = int((max_size / height) * width)
                height = max_size
        
        img = img.resize((width, height), Image.LANCZOS)
        
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        return output.getvalue()
    except Exception as e:
        st.error(f"⚠️ 에이전트 로딩 실패 원인: {e}")
        print(f"Image resize error: {e}")
        return image_bytes


def _run_title_suggestion(topic_flow, subtopic_override=None, intensity=0.5, default_temp=0.4):
    """
    제목 추천 에이전트를 실행하고 결과를 업데이트하는 공통 로직
    """
    category = topic_flow["category"]["selected"] or "일상"
    subtopic = subtopic_override or topic_flow["category"]["selected_subtopic"] or "기타"
    
    # 분석 데이터 가져오기
    analysis = topic_flow["images"].get("analysis", {})
    analysis_mood = analysis.get("mood", "") or "일반적인"
    
    intent_data = topic_flow["images"].get("intent", {})
    user_intent = intent_data.get("custom_text", "") or analysis_mood
    
    current_temp = default_temp
    
    titles = suggest_titles_agent(
        category=category,
        subtopic=subtopic,
        mood=analysis_mood,
        user_intent=user_intent,
        temperature=current_temp,
        intensity=intensity
    )
    
    if not isinstance(titles, list):
        titles = ["AI 제안 제목 생성 불가"]
        
    topic_flow["title"]["candidates"] = titles
    st.session_state["show_ai_reco"] = True
    return titles


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
    # st.markdown('<div class="icon-label" style="margin-top:15px; margin-bottom:15px;">글 제목 또는 키워드</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="curry-header-only" style="margin-top:15px; margin-bottom:15px;">
        <span class="title">글 제목 또는 키워드</span>
        <span class="subtitle">독자의 눈길을 사로잡을 한 줄</span>
    </div>
    """, unsafe_allow_html=True)

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
    # UI 시작 - sam.css의 스타일 사용
    # ==========================

    # 1. 중앙 헤더
    st.markdown("""
        <div class="centered-header">
            <h2>어떤 이야기를 요리해볼까요?</h2>
            <p>블로그 주제를 정하고 사진 재료를 추가해보세요.</p>
        </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 1. 이미지 업로드 섹션
    # -------------------------------------------------
    with st.container(border=True):
        # st.markdown('<div class="icon-label">블로그 사진 추가 (선택)</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="curry-header-only">
            <span class="title">블로그 사진 추가 (선택)</span>
            <span class="subtitle">글의 재료가 될 사진을 넣어주세요</span>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "요리에 넣을 사진 재료를 골라주세요 (최대 10장)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            label_visibility="visible"
        )


        # 리사이징된 이미지 바이트를 담을 리스트
        processed_images = []

        if uploaded_files:
            if len(uploaded_files) > 10:
                st.warning("⚠️ 이미지는 최대 10장까지만 추가할 수 있습니다.")
                uploaded_files = uploaded_files[:10]

            # 모든 파일 리사이징 처리 (300~400px)
            for f in uploaded_files:
                resized_b = resize_image_cached(f.getvalue(), max_size=400)
                processed_images.append(resized_b)

            st.caption(f"사진 {len(uploaded_files)}장 선택됨 (자동 리사이징 400px 적용됨)")

            cols = st.columns(3)
            for idx, img_bytes in enumerate(processed_images):
                with cols[idx % 3]:
                    st.image(img_bytes, caption=f"{idx+1}", use_container_width=True)

            first_file_bytes = processed_images[0]
        else:
            first_file_bytes = None
            # [Fix] 페이지 갱신/이동 시 이미지가 날아가는 문제 해결
            # 업로드된 파일이 없더라도, 기존에 저장된 이미지가 있다면 유지합니다.
            if topic_flow["images"]["files"]:
                processed_images = topic_flow["images"]["files"]
                
                # 기존 이미지 다시 보여주기
                st.info("💡 이전에 분석한 사진이 남아있습니다.")
                cols = st.columns(3)
                for idx, img_bytes in enumerate(processed_images):
                    with cols[idx % 3]:
                        st.image(img_bytes, caption=f"{idx+1}", use_container_width=True)
            else:
                 # 정말 아무것도 없는 경우
                 pass

        render_photo_intent_section(topic_flow)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("사진 먼저 분석하기 (추천 주제 받기)", key="btn_analyze_first", type="primary", use_container_width=True):
            if processed_images:
                total_count = len(processed_images)
                with st.spinner(f"{total_count}장의 사진을 분석하여 주제를 추출 중입니다..."):
                    try:
                        # 사용자 의도를 최우선으로 전달
                        user_intent = topic_flow["images"]["intent"]["custom_text"] or ""
                        
                        # 모든 이미지를 analyze_image_agent에 전달 (단일/다중 모두 처리)
                        analysis_result = analyze_image_agent(processed_images, user_intent=user_intent)
                        mood, tags = parse_image_analysis(analysis_result)

                        # 02.02 추가: AI가 mood에 사용자 의도를 누락했거나 약하게 반영했을 경우를 대비해 수동 결합
                        if user_intent and user_intent.lower() not in mood.lower():
                            mood = f"{user_intent} {mood}"

                        # 모든 이미지를 저장 (다중 이미지 지원)
                        topic_flow["images"]["files"] = processed_images
                        topic_flow["images"]["analysis"]["raw"] = analysis_result
                        topic_flow["images"]["analysis"]["mood"] = mood
                        topic_flow["images"]["analysis"]["tags"] = tags

                        # 02.02 추가: 이미지 분석 직후 write_agent의 suggest_titles_agent 호출
                        # 리팩토링: 공통 함수 사용
                        with st.spinner("💡 분석된 분위기를 바탕으로 제목을 생성 중입니다..."):
                            _run_title_suggestion(
                                topic_flow=topic_flow,
                                subtopic_override=None, # 현재 선택된 세부 주제 사용됨 (보통 '기타'일 확률 높음)
                                intensity=0.9, # HIGH: 사진 의도 중심
                                default_temp=0.4
                            )

                        st.toast(f"{total_count}장 이미지 분석 및 제목 추천이 완료되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 이미지 분석 중 에러 발생: {str(e)}")
                        st.caption(f"에러 타입: {type(e).__name__}")
            else:
                st.info("사진을 먼저 업로드해주세요.")

    # 분석 결과 표시 - 통합 레시피 분석 카드
    if topic_flow["images"]["analysis"]["mood"]:
        with st.container(border=True):
            st.markdown('<div class="analysis-marker" style="display:none;"></div>', unsafe_allow_html=True)

            # 헤더: 사진 재료 분석 결과
            st.markdown("""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                    <h4 style="margin: 0; color: #000000; font-size: 1.2rem; font-weight: 800;">사진 재료 분석 결과</h4>
                </div>
            """, unsafe_allow_html=True)

            # 분위기 표시
            st.markdown(f"""
                <div style="margin-bottom: 12px;">
                    <span style="font-weight: 800; color: #000; font-size: 1.1rem;">분위기: </span>
                    <span style="color: #333; font-size: 1.1rem; line-height: 1.5;">{topic_flow['images']['analysis']['mood']}</span>
                </div>
            """, unsafe_allow_html=True)

            # 태그 표시 - 네오브루탈 스타일
            tags = topic_flow["images"]["analysis"].get("tags", [])
            if tags:
                tag_html = "".join([
                    f"<span style='display:inline-block; background:#FFD400; padding:6px 14px; border-radius:12px; margin-right:8px; margin-bottom:8px; font-size:0.9rem; border:2px solid #000; color:#000; font-weight:600;'>#{t.strip().replace('#','')}</span>"
                    for t in tags
                ])
                st.markdown(f"<div style='margin-bottom:16px;'>{tag_html}</div>", unsafe_allow_html=True)

            # 추천 주제 섹션
            st.markdown("""
                <div style="border-top: 2px solid #000; padding-top: 16px; margin-top: 8px;">
                    <div style="color: #E30613; font-weight: 800; font-size: 1.15rem; margin-bottom: 8px;">이 분위기로 추천하는 요리 주제</div>
                </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns([0.75, 0.25], vertical_alignment="center")
            with c1:
                st.markdown('<div class="analysis-input-box">', unsafe_allow_html=True)
                mood_title = st.text_input(
                    "추천 주제",
                    value=topic_flow["images"]["analysis"]["mood"],
                    label_visibility="collapsed",
                    key="mood_title_input"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                if st.button("제목 적용", key="apply_mood_title_final", type="primary", use_container_width=True):
                    topic_flow["title"]["selected"] = mood_title
                    st.session_state["title_input_field"] = mood_title
                    # 카테고리를 '기타'로 설정
                    topic_flow["category"]["selected"] = "기타"
                    topic_flow["category"]["selected_subtopic"] = "주제 직접 입력"
                    st.session_state["_auto_filled"] = True
                    st.rerun()


    # -------------------------------------------------
    # 2. 카테고리 선택 & 세부 주제 (통합 컨테이너)
    # -------------------------------------------------
    with st.container(border=True):
        st.markdown('<div class="category-marker" style="display:none;"></div>', unsafe_allow_html=True)
        # st.markdown('<div class="icon-label">카테고리 선택</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="curry-header-only">
            <span class="title">카테고리 선택</span>
            <span class="subtitle">오늘의 요리 주제를 골라보세요</span>
        </div>
        """, unsafe_allow_html=True)
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

        # 기본 카테고리 설정 (처음 로드 시)
        if not topic_flow["category"]["selected"]:
            topic_flow["category"]["selected"] = CATEGORIES[0]  # 첫 번째 카테고리를 기본값으로

        # 세부주제 항상 표시
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
            # 생성 중에는 기존 추천 목록을 비워서 창의성 바와 함께 숨김
            topic_flow["title"]["candidates"] = []
            st.session_state["show_ai_reco"] = False

            with st.spinner("AI가 주제어 후보를 생성 중입니다..."):
                try:
                    # 리팩토링: 공통 함수 사용
                    _run_title_suggestion(
                        topic_flow=topic_flow,
                        subtopic_override=effective_subtopic,
                        intensity=0.2, # LOW: 카테고리 중심
                        default_temp=0.5
                    )
                    st.session_state["last_gen_key"] = current_gen_key
                except Exception as e:
                    st.error(f"❌ 주제어 생성 중 에러 발생: {str(e)}")
                    st.caption(f"에러 타입: {type(e).__name__}")
                    topic_flow["title"]["candidates"] = ["AI 모델 연결 실패 - 직접 입력해주세요"]
                    st.session_state["show_ai_reco"] = True
            st.rerun()

        # 02.02 추가수정 : 기타/직접입력 선택인데 입력값이 비어있으면 추천 후보/표시 상태를 초기화
        elif selected_sub in custom_subtopic_triggers and not effective_subtopic:
            if topic_flow["category"]["selected_subtopic"] is not None:
                topic_flow["category"]["selected_subtopic"] = None
                topic_flow["title"]["candidates"] = []
                st.session_state["show_ai_reco"] = False

    # AI 추천 주제어 후보 영역 - 2열 그리드 및 스타일 개선
    if topic_flow["title"]["candidates"] and st.session_state.get("show_ai_reco", True):
        with st.container(border=True):
            st.markdown('<div class="reco-marker" style="display:none;"></div>', unsafe_allow_html=True)

            # 헤더 영역: 타이틀과 닫기 버튼
            h1, h2 = st.columns([0.9, 0.1])
            with h1:
                st.markdown(
                    '<div style="color: #000; font-size: 1.15rem; font-weight: 800; margin-bottom: 4px;">💡 AI가 요리한 추천 주제</div>',
                    unsafe_allow_html=True
                )
                st.caption("마음에 드는 제목을 클릭하면 바로 적용됩니다.")
            with h2:
                if st.button("✕", key="close_reco_btn", type="secondary"):
                    st.session_state["show_ai_reco"] = False
                    st.rerun()



            # 제목 후보 버튼 그리드 (2열)
            candidates = [str(t).strip() for t in topic_flow["title"]["candidates"] if str(t).strip()]
            
            if not candidates:
                st.info("추천된 주제가 없습니다. 다시 시도해보세요.")
            else:
                cols = st.columns(2) # 2열 그리드
                for idx, t in enumerate(candidates):
                    with cols[idx % 2]: # 홀/짝 번갈아가며 배치
                        st.markdown('<div class="title-candidate-wrapper">', unsafe_allow_html=True)
                        # use_container_width=True 로 너비 꽉 채움
                        if st.button(t, key=f"title_btn_{idx}", use_container_width=True):
                            topic_flow["title"]["selected"] = t
                            st.session_state["title_input_field"] = t
                            st.session_state["_auto_filled"] = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    render_title_input_section(topic_flow)

    # -------------------------------------------------
    # 5. 상세 설정
    # -------------------------------------------------
    with st.container(border=True):
        # st.markdown('<div class="icon-label" style="margin-top:5px; margin-bottom:10px;">추가 상세 설정 (선택)</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="curry-header-only">
            <span class="title">추가 상세 설정 (선택)</span>
            <span class="subtitle">맛을 더 풍부하게 만드는 양념치기</span>
        </div>
        """, unsafe_allow_html=True)

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
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">지역 또는 범위</div>', unsafe_allow_html=True)
                options["detail"]["region_scope"]["text"] = st.text_input(
                    "지역/범위",
                    value=options["detail"]["region_scope"]["text"],
                    placeholder="예: 강남구, 서울 전지역",
                    label_visibility="collapsed"
                )
            with col2:
                st.markdown('<div class="icon-label" style="margin-bottom:8px;">타겟 독자</div>', unsafe_allow_html=True)
                options["detail"]["target_reader"]["text"] = st.text_input(
                    "타겟 독자",
                    value=options["detail"]["target_reader"]["text"],
                    placeholder="예: 30대 직장인",
                    label_visibility="collapsed"
                )

            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="icon-label" style="margin-bottom:8px;">추가 요청사항</div>', unsafe_allow_html=True)
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
