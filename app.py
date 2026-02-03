# app.py
# 메인 실행 파일
# 역할 
# 앱 시작점 / 지금 몇 단계인지 판단 / 공통 레이아웃 관리

# app.py

import streamlit as st
from state import init_state, load_persona_from_disk

from ui.step1_persona import render as render_step1
from ui.step2_topic import render as render_step2
from ui.step3_options import render as render_step3
from ui.step4_plan import render as render_step4
from ui.step5_preview import render as render_step5


st.set_page_config(page_title="AI Blog Generator", layout="wide")

# ============================================================
# 전역 CSS 로드
# - style.css 파일을 읽어 Streamlit에 주입
# - 모든 페이지에 공통으로 적용되는 스타일 정의
# ============================================================
def load_css(file_path: str):
    """외부 CSS 파일을 읽어 Streamlit에 적용합니다."""
    with open(file_path, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# style.css 로드 (루트 디렉토리 기준)
load_css("style.css")

init_state()
load_persona_from_disk()


def build_ctx():
    # ctx는 스키마 키만
    return {
        "step": st.session_state["step"],
        "persona": st.session_state["persona"],
        "topic_flow": st.session_state["topic_flow"],
        "options": st.session_state["options"],
        "design_brief": st.session_state["design_brief"],
        "final_options": st.session_state["final_options"],
        "outputs": st.session_state["outputs"],
        "dirty": st.session_state["dirty"],
    }


step = st.session_state.get("step", 1)

if step == 1:
    render_step1(build_ctx())
elif step == 2:
    render_step2(build_ctx())
elif step == 3:
    render_step3(build_ctx())
elif step == 4:
    render_step4(build_ctx())
elif step == 5:
    render_step5(build_ctx())
else:
    st.session_state["step"] = 1
    st.rerun()