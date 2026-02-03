# 고정 설정값
# 자주 바뀌지 않은 값 보관
# 예 : 카테고리 목록, 기본 옵션 on/off
# 중요! stat.py 담당이 하는 분이 건들어야 함

# config.py 변하지 않는 값

# 모델

MODEL_TEXT = "llama3.1:8b"
MODEL_VISION = "llava:7b"
# MODEL_TEXT = "llama3.1:70b"
# MODEL_VISION = "llava:13b"

# 후보 개수
N_SUBTOPICS = 6
N_TITLES = 5
N_HASHTAGS = 10


# 글 길이 가이드
TARGET_CHARS = 2000

# 카테고리/고정값
MBTI = {
"ISTJ": "신뢰감 1위! 팩트와 논리 중심의 꼼꼼한 정보 요약가",
    "ISFJ": "친절함 1위! 차분하고 따뜻한 어조의 공감 가이드",
    "INFJ": "울림 1위! 깊이 있는 통찰력을 가진 감성 에세이스트",
    "INTJ": "전문성 1위! 군더더기 없이 핵심만 꿰뚫는 분석 전문가",
    "ISTP": "솔직함 1위! 미사여구 없이 현실적인 찐 리뷰어",
    "ISFP": "디테일 1위! 감각적인 취향을 나누는 섬세한 기록가",
    "INFP": "감수성 1위! 진심을 담아 이야기하는 스토리텔러",
    "INTP": "독창성 1위! 남다른 관점으로 파고드는 지식 탐험가",
    "ESTP": "현장감 1위! 생생한 경험을 그대로 전하는 행동대장",
    "ESFP": "즐거움 1위! 에너지 넘치고 유쾌한 분위기 메이커",
    "ENFP": "흡입력 1위! 톡톡 튀는 리액션의 아이디어 뱅크",
    "ENTP": "트렌드 1위! 재치 있는 입담으로 흥미를 끄는 이슈 메이커",
    "ESTJ": "가독성 1위! 체계적이고 확실하게 알려주는 정보 전달자",
    "ESFJ": "친근감 1위! 세심하게 챙겨주는 다정한 이웃",
    "ENFJ": "설득력 1위! 긍정 에너지를 전파하는 동기부여가",
    "ENTJ": "정보력 1위! 시원시원하게 방향을 제시하는 비전 리더",
}

CATEGORIES = [
    "비즈니스/경제",
    "IT/기술",
    "생활/라이프",
    "건강/자기계발",
    "교육/학습",
    "쇼핑/소비",
    "자동차/교통",
    "취업/직장",
    "기타"

]

SUBTOPICS_MAP = {
    "비즈니스/경제" : ["부동산", "주식", "연금", "세금", "대출"],
    "IT/기술": ["프로그래밍", "앱 사용법", "소프트웨어", "디지털 기기"],
    "생활/라이프" : ["인테리어", "요리", "미니멀라이프", "반려동물"],
    "건강/자기계발" : ["운동", "독서", "습관", "정신건강"],
    "교육/학습" : ["외국어", "자격증", "온라인강의", "공부법"],
    "쇼핑/소비" : ["온라인쇼핑", "중고거래", "할인혜택", "가성비제품"],
    "자동차/교통" : ["자동차 보험", "중고차 매매", "교통법규", "차량관리"],
    "취업/직장" :["이직/퇴사", "자기소개서", "면접꿀팁", "직장생활"],
    "기타" : ["주제 직접 입력"]
    #02.02 카테고리 작성 완료
}

POST_TYPES = [
    "정보 전달형",
    "리뷰/후기형",
    "소식/이슈형",
    "칼럼/인사이트",
]

HEADLINE_STYLES = [
    "담백함 (Level 1)",
    "매력적 담백함 (Level 2)",
    "강렬함(Level 3)"
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
