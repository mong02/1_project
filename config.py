# 고정 설정값
# 자주 바뀌지 않은 값 보관
# 예 : 카테고리 목록, 기본 옵션 on/off
# 중요! stat.py 담당이 하는 분이 건들어야 함

# config.py 변하지 않는 값

# 모델

MODEL_TEXT = "llama3.1:8b"  
MODEL_VISION = "llava:7b"     

# 후보 개수
N_SUBTOPICS = 6
N_TITLES = 5
N_HASHTAGS = 10
# 추가해야함 ㅠㅠ

# 글 길이 가이드
TARGET_CHARS = 1500

# 카테고리/고정값
MBTI = {
    "ISTJ": "원칙과 기준을 중시하는 체계적 설명형",
    "ISFJ": "배려 깊고 안정적인 안내형",
    "INFJ": "의미와 흐름을 중시하는 스토리형",
    "INTJ": "논리 중심의 전략적 분석형",
    "ISTP": "간결하고 실용적인 문제해결형",
    "ISFP": "부드럽고 감각적인 공감형",
    "INFP": "가치와 감정을 중시하는 진정성형",
    "INTP": "개념 중심의 탐구형",
    "ESTP": "현장감 1위! 생생한 경험 전달형",
    "ESFP": "밝고 친근한 에너지형",
    "ENFP": "아이디어와 공감을 섞은 확산형",
    "ENTP": "재미와 논리를 넘나드는 토론형",
    "ESTJ": "명확하고 단정적인 리더형",
    "ESFJ": "독자 친화적인 설명형",
    "ENFJ": "독자를 이끄는 설득형",
    "ENTJ": "결론 중심의 강한 추진형",
}

CATEGORIES = [
    "비즈니스/경제",
    "IT/기술",
    #나중에 써야함
]

SUBTOPICS_MAP = {
    "IT/기술": ["프로그래밍", "앱 사용법", "소프트웨어", "디지털 기기"],
    #나중에 써야함 ㅠㅠ
}

POST_TYPES = [
    "정보 전달형(설명/팁)",
    "리뷰형",
    "경험담/에세이형",
    "비교/추천형",
]

HEADLINE_STYLES = [
    "호기심 유발형(적당함)",
    "직설 요약형",
    "감성 공감형",
    "문제 해결형",
]

FINAL_OPTION_DEFAULTS = {
    "seo_opt": False,
    "evidence_label": False,
    "publish_package": True,
    "anti_ai_strong": True,
    "image_hashtag_reco": False,
}


# 저장 공간 

ASSETS_DIR = "assets"
PROFILE_PATH = f"{ASSETS_DIR}/persona_profile.json"
STEP2_PATH = f"{ASSETS_DIR}/step2_snapshot.json"
STEP3_PATH = f"{ASSETS_DIR}/step3_snapshot.json"
STEP4_PATH = f"{ASSETS_DIR}/step4_snapshot.json"
