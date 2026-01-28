import streamlit as st
import requests
import json
from datetime import datetime

# ✅ 서버 주소 (필요하면 포트만 바꾸세요)
API_BASE = "http://127.0.0.1:8000"
API_URL = f"{API_BASE}/generate"

st.set_page_config(page_title="SNS 포스팅 자동 생성기", page_icon="🐰", layout="wide")

# ----------------------------
# 귀엽고 깔끔한 UI (가독성 최우선)
# ----------------------------
st.markdown("""
<style>
/* 전체 배경: 밝은 파스텔 + 점무늬 */
.stApp {
  background:
    radial-gradient(circle at 10% 10%, rgba(255, 224, 240, 0.55), transparent 40%),
    radial-gradient(circle at 90% 15%, rgba(210, 244, 255, 0.65), transparent 45%),
    radial-gradient(circle at 40% 95%, rgba(255, 255, 210, 0.6), transparent 45%),
    linear-gradient(180deg, #fff 0%, #f7f8ff 100%);
  color: #1f2a44;
}

/* 폭 제한 */
.block-container { max-width: 1200px; padding-top: 24px; }

/* 헤더 */
.hero {
  display:flex; align-items:center; gap:12px;
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(31,42,68,0.08);
  box-shadow: 0 10px 30px rgba(31,42,68,0.08);
}
.hero h1 { font-size: 30px; margin: 0; letter-spacing: -0.5px; }
.hero p  { margin: 2px 0 0 0; opacity: 0.75; }

/* 카드 */
.card {
  background: rgba(255,255,255,0.85);
  border: 1px solid rgba(31,42,68,0.08);
  box-shadow: 0 10px 30px rgba(31,42,68,0.08);
  border-radius: 18px;
  padding: 16px 16px 6px 16px;
}

/* 섹션 타이틀 */
.section-title{
  font-size: 18px;
  font-weight: 800;
  margin: 0 0 8px 0;
}

/* 뱃지 */
.badge{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  background: #f1f4ff;
  border: 1px solid rgba(31,42,68,0.08);
  font-size: 12px;
  margin-right: 6px;
}

/* 버튼: uiverse 느낌 */
.stButton > button {
  width: 100%;
  border-radius: 14px !important;
  border: 1px solid rgba(31,42,68,0.10) !important;
  background: linear-gradient(135deg, #7c5cff, #ff6fb1) !important;
  color: white !important;
  box-shadow: 0 12px 28px rgba(124,92,255,0.22);
  transition: transform .05s ease;
}
.stButton > button:active { transform: scale(0.98); }

/* 입력창 라운드 */
textarea, input { border-radius: 12px !important; }

/* 결과 카드 */
.out {
  background: #ffffff;
  border: 1px solid rgba(31,42,68,0.08);
  border-radius: 18px;
  padding: 14px;
  margin-bottom: 12px;
}
.out-title{
  font-weight: 900;
  font-size: 15px;
  margin-bottom: 6px;
}
.mini{
  font-size: 12px;
  opacity: 0.7;
}

/* 경고 박스 */
div[data-testid="stAlert"] { border-radius: 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div style="font-size:34px;">🐰</div>
  <div>
    <h1>SNS 포스팅 자동 생성기</h1>
    <p>캠페인 세트 · 채널별 변환 · 후킹 A/B · 전략형 해시태그까지 한 번에 생성합니다.</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.write("")

# ----------------------------
# 레이아웃
# ----------------------------
left, right = st.columns([0.46, 0.54], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✍️ 입력</div>', unsafe_allow_html=True)

    model = st.selectbox("Ollama 모델", ["gemma3:4b", "llama3.1:8b", "qwen2.5:7b", "mistral:7b"], index=0)
    goal = st.selectbox("목표", ["공지(announce)", "홍보(promo)", "유입(traffic)", "참여(engage)", "채용(recruit)"], index=0)
    tone = st.selectbox("톤", ["친근하게(friendly)", "차분하게(calm)", "캐주얼(casual)", "공식(formal)", "유머(humorous)"], index=0)

    channels = st.multiselect(
        "채널",
        ["instagram", "thread", "blog", "linkedin"],
        default=["instagram", "thread", "blog", "linkedin"]
    )

    st.divider()

    product_name = st.text_input("제품/서비스명", value="신제품 런칭 이벤트")
    target = st.text_input("타깃(누구에게?)", value="20~30대 직장인")
    pain_point = st.text_area("타깃의 불편/고통", value="바쁜 일상으로 자기관리 시간이 부족함", height=80)
    solution = st.text_area("해결(무엇을 어떻게?)", value="5분 루틴 키트로 시간 부담을 줄임", height=80)

    differentiators = st.text_area("차별점(줄바꿈으로 여러 개)", value="5분 루틴\n휴대/보관 간편\n초보자용 가이드 포함", height=90)
    proof = st.text_area("근거/신뢰(줄바꿈으로 여러 개)", value="리뷰 기반 만족도 4.8/5 목표\n런칭 2주 한정 혜택", height=90)

    cta = st.text_input("CTA(행동 유도 문장)", value="지금 바로 신청하세요")
    banned_words = st.text_input("금지어(쉼표로 구분)", value="무조건,100%,완치,1등")

    campaign_size = st.slider("캠페인 게시글 개수(채널별 생성)", 1, 12, 5)
    hook_variants = st.slider("후킹 A/B 후보 수", 3, 20, 10)

    with st.expander("🎀 브랜드 보이스(선택) — 말투를 고정하고 싶으면 쓰세요"):
        br_name = st.text_input("보이스 이름", value="cute-simple")
        br_rules = st.text_area("규칙(줄바꿈)", value="과장 금지\n짧고 명확하게\n부드럽고 귀엽게", height=90)
        br_examples = st.text_area("예시(줄바꿈)", value="오늘도 가볍게, 딱 5분만.\n바쁜 날엔 간단한 게 최고예요.", height=80)

    st.write("")
    generate = st.button("✨ 생성하기")

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📦 결과</div>', unsafe_allow_html=True)

    # API 상태 체크 버튼
    colA, colB = st.columns([0.6, 0.4])
    with colA:
        st.caption(f"API: {API_URL}")
    with colB:
        if st.button("🔌 API 상태 확인"):
            try:
                r = requests.get(f"{API_BASE}/health", timeout=5)
                st.success(f"서버 정상 응답: {r.text}")
            except Exception as e:
                st.error(f"서버 연결 실패: {e}")

    if "result" not in st.session_state:
        st.session_state.result = None

    # 생성 요청
    if generate:
        # UI에서 보이는 한글 선택값 → 서버 값으로 변환
        goal_map = {
            "공지(announce)": "announce",
            "홍보(promo)": "promo",
            "유입(traffic)": "traffic",
            "참여(engage)": "engage",
            "채용(recruit)": "recruit",
        }
        tone_map = {
            "친근하게(friendly)": "friendly",
            "차분하게(calm)": "calm",
            "캐주얼(casual)": "casual",
            "공식(formal)": "formal",
            "유머(humorous)": "humorous",
        }

        payload = {
            "model": model,
            "product_name": product_name,
            "target": target,
            "pain_point": pain_point,
            "solution": solution,
            "differentiators": [x.strip() for x in differentiators.splitlines() if x.strip()],
            "proof": [x.strip() for x in proof.splitlines() if x.strip()],
            "cta": cta,
            "banned_words": [x.strip() for x in banned_words.split(",") if x.strip()],
            "channels": channels,
            "goal": goal_map[goal],
            "tone": tone_map[tone],
            "campaign_size": int(campaign_size),
            "hook_variants": int(hook_variants),
            "brand_voice": {
                "name": br_name,
                "rules": [x.strip() for x in br_rules.splitlines() if x.strip()],
                "examples": [x.strip() for x in br_examples.splitlines() if x.strip()],
            }
        }

        try:
            r = requests.post(API_URL, json=payload, timeout=240)
            r.raise_for_status()
            st.session_state.result = r.json()
        except Exception as e:
            st.error(f"API 호출 실패: {e}")

    result = st.session_state.result

    if result:
        st.markdown(
            f'<span class="badge">모델: {model}</span>'
            f'<span class="badge">목표: {goal}</span>'
            f'<span class="badge">톤: {tone}</span>',
            unsafe_allow_html=True
        )

        strategy = result.get("strategy", {})
        st.write("")
        st.markdown("#### 🧠 전략 요약")
        st.code(json.dumps(strategy, ensure_ascii=False, indent=2), language="json")

        campaign = result.get("campaign", [])

        st.write("")
        st.markdown("#### 🪄 생성 결과")
        tabs = st.tabs(["인스타", "스레드", "블로그", "링크드인", "전체"])
        key_map = {"인스타":"instagram", "스레드":"thread", "블로그":"blog", "링크드인":"linkedin"}

        def render(items):
            for item in items:
                title = item.get("title","")
                body = item.get("body","")
                hashtags = item.get("hashtags", [])
                stories = item.get("story_captions", [])
                comments = item.get("comment_prompts", [])
                flags = item.get("risk_flags", [])

                st.markdown('<div class="out">', unsafe_allow_html=True)
                st.markdown(f'<div class="out-title">[{item.get("channel")}] {title}</div>', unsafe_allow_html=True)
                st.write(body)

                if hashtags:
                    st.markdown("**해시태그**")
                    st.write(" ".join([f"#{h.lstrip('#')}" for h in hashtags]))

                if stories:
                    st.markdown("**스토리 캡션**")
                    st.write(" / ".join(stories))

                if comments:
                    st.markdown("**댓글 유도**")
                    st.write(" / ".join(comments))

                if flags:
                    st.warning("검수: " + " | ".join(flags))

                copy_text = f"{title}\n\n{body}\n\n" + (" ".join([f"#{h.lstrip('#')}" for h in hashtags]))
                st.markdown("**복사용 텍스트**")
                st.code(copy_text, language="markdown")

                st.markdown('</div>', unsafe_allow_html=True)

        with tabs[0]:
            render([x for x in campaign if x.get("channel") == "instagram"])
        with tabs[1]:
            render([x for x in campaign if x.get("channel") == "thread"])
        with tabs[2]:
            render([x for x in campaign if x.get("channel") == "blog"])
        with tabs[3]:
            render([x for x in campaign if x.get("channel") == "linkedin"])
        with tabs[4]:
            render(campaign)
    else:
        st.info("왼쪽에서 입력하고 ‘생성하기’를 누르세요. (오른쪽의 ‘API 상태 확인’부터 눌러도 됩니다.)")

    st.markdown('</div>', unsafe_allow_html=True)
