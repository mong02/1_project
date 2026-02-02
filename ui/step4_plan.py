# ui/step4_plan.py
import streamlit as st
from state import init_state, reset_from_step, save_step4_to_disk

def render(ctx):
    init_state()  # 세션 상태 스키마 보장

    st.header("🛠️ 최종 옵션 설정")
    st.caption("더 완벽한 글 작성을 위한 마지막 설정을 선택하세요.")

    toggles = st.session_state["final_options"]["toggles"]

    with st.container():
        st.markdown("###")
        seo = st.checkbox("🔍 SEO 최적화 (검색 엔진 친화적 배치)", value=toggles["seo_opt"])
        anti_ai = st.checkbox("✍️ AI 티 제거 (강화된 문장 재구성)", value=toggles["anti_ai_strong"])
        package = st.checkbox("🎁 발행 패키지 (제목 3종, FAQ, CTA 포함)", value=toggles["publish_package"])
        evidence = st.checkbox("📋 근거 라벨 표시 (정보의 신뢰도 명시)", value=toggles["evidence_label"])

    st.markdown("---")

    if st.button("🚀 블로그 글 생성하기", type="primary", use_container_width=True):
        st.session_state["final_options"]["toggles"].update({
            "seo_opt": seo,
            "anti_ai_strong": anti_ai,
            "publish_package": package,
            "evidence_label": evidence,
        })

        reset_from_step(4)
        save_step4_to_disk()

        st.session_state["step"] = 5
        st.rerun()

    # ✅ UX 안내 문구 (누락됐던 부분)
    st.caption("※ '생성하기'를 누르면 AI가 설계안에 맞춰 집필을 시작합니다.")

import streamlit as st

if __name__ == "__main__":
    if "blog" not in st.session_state:
        st.session_state.blog = {"options": {}, "result": None}
    if "step" not in st.session_state:
        st.session_state.step = 4

     render(ctx)
