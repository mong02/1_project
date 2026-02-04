# app.py
# 메인 실행 파일
# 역할 
# 앱 시작점 / 지금 몇 단계인지 판단 / 공통 레이아웃 관리

import streamlit as st
import os
import base64
from state import init_state, load_persona_from_disk

# UI Components Import
from ui.step1_persona import render as render_step1
from ui.step2_topic import render as render_step2
from ui.step3_options import render as render_step3
from ui.step4_plan import render as render_step4
from ui.step5_preview import render as render_step5


st.set_page_config(page_title="3-Minute Blog", layout="wide")

def load_global_css():
    css_file = "style.css"  # Root directory
    
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.error(f"⚠️ 스타일 파일({css_file})을 찾을 수 없습니다.")

def render_header():
    """모든 페이지 상단에 로고 배치"""
    logo_path = "images/logo.png"
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            st.markdown(f"""
                <div class="logo-container">
                    <img src="data:image/png;base64,{data}" class="logo-img" alt="3-Minute Blog Logo">
                </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"Logo Load Error: {e}")
    else:
        # Fallback Header if logo missing
        st.markdown("""
            <div class="logo-container">
                <h1>🍳 3-Minute Blog</h1>
            </div>
        """, unsafe_allow_html=True)

# 1. Load CSS
load_global_css()

# 2. Render Header (Global)
render_header()

# 3. Init State
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