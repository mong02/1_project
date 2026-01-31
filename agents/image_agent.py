# AI 이미지 분석 에이전트
# Ollama 호출을 한 곳으로 모음

import ollama
from config import MODEL_VISION


def analyze_image_agent(image_bytes):
    """
    [Vision Agent] 이미지를 보고 분위기와 태그를 한국어로 분석합니다.
    """
    try:
        response = ollama.chat(
            model=MODEL_VISION,
            messages=[{
                'role': 'user',
                'content': """이 이미지를 분석해서 다음 형식으로 한국어로 답변해주세요:

분위기: (이미지에서 느껴지는 분위기를 30자 이내의 매력적인 블로그 제목 스타일로 한 줄 작성)
태그: #태그1 #태그2 #태그3 #태그4 #태그5

예시:
분위기: 따뜻한 햇살이 가득한 주말 오후의 여유로운 홈카페
태그: #카페 #커피 #인테리어 #휴식 #감성""",
                'images': [image_bytes]
            }]
        )
        return response['message']['content']
    except Exception as e:
        print(f"이미지 분석 모델({MODEL_VISION}) 오류: {e}")
        return "분위기: 분석 실패 (서버 연결 확인 필요)\n태그: #오류"


def parse_image_analysis(raw_text):
    """
    분석 결과를 파싱하여 분위기와 태그를 분리합니다.

    Returns:
        tuple: (mood_str, tags_list)
    """
    mood = ""
    tags = []

    lines = raw_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("분위기:"):
            mood = line.replace("분위기:", "").strip()
        elif line.startswith("태그:"):
            tag_part = line.replace("태그:", "").strip()
            tags = [t.strip() for t in tag_part.split("#") if t.strip()]
            tags = ["#" + t for t in tags]

    # 파싱 실패 시 원본 사용
    if not mood:
        mood = raw_text[:100] + "..." if len(raw_text) > 100 else raw_text

    return mood, tags
