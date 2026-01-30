# app.py
# 메인 실행 파일
# 역할 
# 앱 시작점 / 지금 몇 단계인지 판단 / 공통 레이아웃 관리

import streamlit as st
from state import init_state, load_persona_from_disk

from ui.step1_persona import render as render_step1
# from ui.step2_topic import render as render_step2
# from ui.step3_options import render as render_step3
# from ui.step4_preview import render as render_step4
# from ui.step4_preview import render as render_step5

st.set_page_config(page_title="AI Blog Generator", layout="wide")

init_state()
load_persona_from_disk()

def build_ctx():
    # ctx는 스키마에 존재하는 키만 담기
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


step = st.session_state["step"]

if step == 1:
    render_step1()
# elif step == 2:
#     render_step2(build_ctx())
# elif step == 3:
#     render_step3(build_ctx())
# elif step == 4:
#     render_step4(build_ctx())
else:
    st.session_state["step"] = 1
    st.rerun()
