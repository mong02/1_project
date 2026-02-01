# AI 이미지 분석 에이전트
# Ollama 호출을 한 곳으로 모음

import ollama
import re
from config import MODEL_VISION

def analyze_image_agent(image_bytes):
    """
    [Vision Agent] 이미지를 보고 분위기와 태그를 한국어로 분석합니다.
    """
    # 프롬프트 전략:
    # 1. 역할 부여: "감성적인 에세이 작가"라고 최면을 겁니다.
    # 2. 명확한 제약: "번역투 금지", "블로그 제목 스타일" 요청.
    try:
        response = ollama.chat(
            model=MODEL_VISION,
            messages=[{
                'role': 'user',
                'content': """Please analyze this image and answer in KOREAN.
Follow this format strictly:

분위기: (Write a short, emotional, and poetic sentence suitable for a Instagram/Blog title. roughly 20~40 characters.)
태그: #Tag1 #Tag2 #Tag3

[Rules]
1. Output MUST be in Korean.
2. Do not describe facts (e.g., "There is a cup"). Describe the 'Mood' (e.g., "A cozy afternoon tea time").
3. Do not use English in the output.

[Example Output]
분위기: 따스한 햇살이 스며드는 나른한 주말의 오후
태그: #휴식 #카페 #감성 #인테리어 #힐링""",
                'images': [image_bytes]
            }]
        )
        return response['message']['content']
    except Exception as e:
        print(f"이미지 분석 모델({MODEL_VISION}) 오류: {e}")
        return "분위기: 이미지 분석 중 오류가 발생했습니다.\n태그: #오류 #재시도"


def parse_image_analysis(raw_text):
    """
    분석 결과를 파싱하여 분위기와 태그를 분리합니다.
    (특수문자 제거 및 파싱 로직 강화)
    """
    mood = ""
    tags = []

    # 1. 텍스트 정리 (마크다운, 따옴표 등 제거)
    clean_text = raw_text.replace("**", "").replace("##", "").replace('"', '').replace("'", "").strip()
    
    lines = clean_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # "분위기" 파싱 (구분자 유연하게 처리)
        if "분위기" in line and (":" in line or "mood" in line.lower()):
            # 콜론(:) 기준으로 나눔
            parts = re.split(r'[:：]', line, 1) # 전각/반각 콜론 모두 처리
            if len(parts) > 1:
                mood = parts[1].strip()
        
        # "태그" 파싱
        elif "태그" in line and (":" in line or "tag" in line.lower()):
            parts = re.split(r'[:：]', line, 1)
            if len(parts) > 1:
                tag_part = parts[1].strip()
                # 콤마, 공백 등으로 태그 분리
                raw_tags = re.split(r'[, ]+', tag_part)
                # #기호가 중복되지 않게 처리하며 리스트 생성
                tags = ["#" + t.replace("#", "").strip() for t in raw_tags if t.strip()]

    # 파싱 실패 시 예외 처리
    if not mood:
        # 첫 줄이 비어있지 않다면 그것을 분위기로 간주
        if lines and len(lines[0]) > 5:
            mood = lines[0]
            # 너무 길면 자르기
            if len(mood) > 50: 
                mood = mood[:50] + "..."
        else:
            mood = "분위기 분석 결과가 없습니다."

    # 태그가 비었을 때 기본값
    if not tags:
        tags = ["#사진", "#일상", "#기록"]

    return mood, tags