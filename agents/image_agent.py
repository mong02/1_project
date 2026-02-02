# AI 이미지 분석 에이전트
# Ollama 호출을 한 곳으로 모음

import ollama
import re
import json
from config import MODEL_VISION

def analyze_image_agent(image_bytes_list):
    """
    [Vision Agent] 제공된 모든 이미지를 분석하여 전체적인 상황(Situation)과 분위기(Mood)를 종합해 JSON 문자열로 반환합니다.
    """
    try:
        # 단일 바이트가 들어올 경우 리스트로 변환
        if isinstance(image_bytes_list, bytes):
            image_bytes_list = [image_bytes_list]

        response = ollama.chat(
            model=MODEL_VISION,
            messages=[{
                'role': 'user',
                'content': """제공된 모든 이미지들을 전체적으로 분석하여 하나의 상황(Situation)과 분위기(Mood)로 취합해 JSON 문자열로 반환해줘.
모든 사진을 정확하게 읽고, 전체를 아우르는 한국어 요약을 제공해야 해.

응답은 반드시 아래와 같은 JSON 형식이어야 해:
{
  "situation": "전체 사진들을 아우르는 종합적인 상황 설명",
  "mood": "전체 사진들의 공통적인 분위기 설명",
  "tags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"]
}

[규칙]
1. 반드시 한국어로 답변할 것.
2. JSON 외의 다른 텍스트는 포함하지 말 것.
3. 상황(situation)은 여러 장의 사진이 보여주는 흐름이나 공통된 테마를 블로그 에세이 스타일로 자연스럽게 정리할 것.
4. 분위기(mood)는 사진 전체의 느낌을 한 문장으로 감성적으로 표현할 것.
5. 태그는 사진들에서 추출된 핵심 키워드 5개 내외로 작성할 것.""",
                'images': image_bytes_list
            }]
        )
        return response['message']['content']
    except Exception as e:
        print(f"이미지 분석 모델({MODEL_VISION}) 오류: {e}")
        return json.dumps({
            "situation": "이미지들을 분석하는 도중 오류가 발생했습니다.",
            "mood": "분석 오류",
            "tags": ["#오류", "#재시도"]
        }, ensure_ascii=False)


def parse_image_analysis(raw_text):
    """
    JSON 문자열을 파싱하여 분위기와 태그를 분리합니다.
    """
    try:
        # JSON 부분만 추출 (가끔 AI가 백틱 등을 포함할 수 있음)
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(raw_text)
        
        situation = data.get("situation", "")
        mood = data.get("mood", "")
        tags = data.get("tags", [])
        
        # UI에서 mood를 제목 추천 등으로 사용하므로, 
        # 상황(situation)과 분위기(mood)를 적절히 조합하여 반환하거나 mood를 우선순위로 둠
        # 여기서는 기존 step2_topic.py와의 호환성을 위해 mood를 반환하되, 
        # 필요시 situation을 활용할 수 있도록 함.
        
        return mood if mood else situation, tags
    except Exception as e:
        print(f"JSON 파싱 오류: {e}")
        # 실패 시 기존의 텍스트 기반 파싱 시도 (폴백)
        mood = ""
        tags = []
        clean_text = raw_text.replace("**", "").replace("##", "").replace('"', '').replace("'", "").strip()
        lines = clean_text.split("\n")
        for line in lines:
            line = line.strip()
            if "분위기" in line and ":" in line:
                mood = line.split(":", 1)[1].strip()
            elif "태그" in line and ":" in line:
                tag_part = line.split(":", 1)[1].strip()
                tags = ["#" + t.replace("#", "").strip() for t in re.split(r'[, ]+', tag_part) if t.strip()]
        
        if not mood:
            mood = "분위기 분석 결과가 없습니다."
        if not tags:
            tags = ["#사진", "#일상", "#기록"]
        return mood, tags