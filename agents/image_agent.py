import json
import base64
import re
import ollama
from typing import Dict, Any, List, Optional, Tuple
from agents.ollama_client import OllamaClient
from config import MODEL_VISION, MODEL_TEXT


# ==============================================================================
# [헬퍼] 더러운 JSON 문자열 청소부
# ==============================================================================
def _clean_json_text(text: str) -> str:
    """
    AI가 마크다운(```json)이나 잡담(Here is...)을 섞어서 줘도
    순수 JSON 객체({ ... }) 부분만 추출합니다.
    """
    if not text:
        return "{}"
    
    # 1. ``` 또는 ```json 블록 안에 있으면 그 안의 내용만 추출
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1)
    
    # 2. 가장 바깥쪽 중괄호 {} 찾기
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)
        
    return text.strip()


# ==============================================================================
# [메인 함수] UI에서 호출하는 이미지 분석 에이전트   ------- (260202) 다 갈아엎음 코드 끝까지. ==============================================================================
def analyze_image_agent(image_bytes: bytes, user_intent: str = "") -> str:
    """
    이미지 바이트를 받아 Vision 모델로 분석하고 결과를 문자열로 반환합니다.
    UI에서는 이 문자열을 그대로 저장하고 parse_image_analysis로 파싱합니다.
    """
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')

    # 사용자 의도 반영 (최우선순위로 제목과 주제에 녹여야 함)
    intent_instruction = ""
    print(f"[DEBUG] 전달받은 사용자 의도: '{user_intent}'")  # 디버그용
    if user_intent:
        intent_instruction = f"""

★★★ [사용자 의도 - 최우선 반영]: "{user_intent}" ★★★
출력 예시: 의도가 "힐링"이면 → "힐링이 필요한 날, ..." 또는 "힐링 여행, ..."
사진 요소는 의도 뒤에 자연스럽게 붙여주세요.
사진에서 보이는 요소들과 이 의도를 창의적으로 결합하여 하나의 매력적인블로그 주제로 만드세요.
"""

    prompt = f"""
당신은 10년 경력의 블로그 콘텐츠 기획 전문가입니다.
업로드된 이미지를 면밀히 분석하여 사람들이 읽고 싶어하는 블로그 주제를 도출해주세요.
{intent_instruction}

⚠️ 중요: 모든 출력은 반드시 한국어로 작성하세요! 영어 출력 금지!

[분석 프로세스]
1. 이미지에서 핵심 피사체, 분위기, 장소, 상황을 파악합니다.
2. 사용자 의도가 있다면 이를 최우선으로, 이미지 요소와 자연스럽게 융합합니다.
3. "이 사진으로 어떤 이야기를 쓸 수 있을까?"를 고민하며 독자를 끌어당기는 주제를 만듭니다.
4. 클릭하고 싶은 매력적인 블로그 제목 스타일로 주제를 작성합니다.

[좋은 주제 예시 - 한국어로!]
- 사진: 카페 + 의도: "혼자만의 시간" → "북적이는 도심 속, 나만의 조용한 아지트를 찾았다"
- 사진: 음식 + 의도: "가성비" → "이 가격에 이 맛? 직장인 점심 맛집 인정"
- 사진: 여행지 + 의도: 없음 → "인생샷 명소, 여기 안 가면 후회해요"

[나쁜 주제 예시 - 피하세요]
- "카페에서 찍은 사진입니다" (단순 묘사)
- "커피와 케이크" (키워드 나열)
- 영어로 된 모든 출력 (절대 금지)

[출력 형식]
반드시 아래 JSON만 출력하세요. 한국어로! 설명이나 마크다운 없이 순수 JSON만!

{{
    "mood": "한국어로 작성한 매력적인 블로그 주제 한 문장",
    "tags": ["한국어태그1", "한국어태그2", "태그3", "태그4", "태그5"]
}}
"""

    try:
        response = ollama.generate(
            model=MODEL_VISION,
            prompt=prompt,
            images=[img_b64],
            stream=False
        )
        raw_text = response.get('response', '')
        print(f"[DEBUG] Raw Vision Response: {raw_text[:200]}...")
        
        # JSON 정리
        cleaned = _clean_json_text(raw_text)
        
        # 파싱 테스트
        json.loads(cleaned)
        
        return cleaned
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        # 파싱 실패 시 기본값 반환
        return json.dumps({
            "mood": "사진 분석 결과를 가져오지 못했습니다.",
            "tags": ["사진", "일상"]
        }, ensure_ascii=False)
    except Exception as e:
        print(f"Image Analysis Error: {e}")
        return json.dumps({
            "mood": f"분석 오류: {str(e)}",
            "tags": []
        }, ensure_ascii=False)


# ==============================================================================
# [파싱 함수] 분석 결과 문자열에서 mood와 tags 추출
# ==============================================================================
def parse_image_analysis(analysis_result: str) -> Tuple[str, List[str]]:
    """
    analyze_image_agent의 결과 문자열을 파싱하여 (mood, tags) 튜플로 반환합니다.
    """
    try:
        # 한번 더 정리 (혹시 모를 이중 저장 대비)
        cleaned = _clean_json_text(analysis_result)
        data = json.loads(cleaned)
        
        mood = data.get("mood", "")
        tags = data.get("tags", [])
        
        # 태그에서 # 제거
        clean_tags = [str(t).replace("#", "").strip() for t in tags if t]
        
        return mood, clean_tags
        
    except Exception as e:
        print(f"Parse Error: {e}")
        return "분석 결과를 파싱할 수 없습니다.", []


# ==============================================================================
# [하위 호환] 기존 2단계 분석 흐름 (필요시 사용)
# ==============================================================================
def analyze_image_flow(file_list: List[Any], user_intent: str = "") -> Dict[str, Any]:
    """2단계 분석 흐름 (Vision -> Text). 필요시 사용."""
    if not file_list:
        return {"error": "No image files provided.", "is_success": False}
    
    try:
        if hasattr(file_list[0], 'getvalue'):
            first_image_bytes = file_list[0].getvalue()
        else:
            first_image_bytes = file_list[0]
        
        result_str = analyze_image_agent(first_image_bytes, user_intent)
        mood, tags = parse_image_analysis(result_str)
        
        return {
            "is_success": True,
            "creative": {"main_angle": mood, "tags": tags},
            "facts": {}
        }
    except Exception as e:
        return {"error": str(e), "is_success": False}


def parse_analysis_for_ui(full_result: Dict[str, Any]) -> Dict[str, Any]:
    """분석 결과를 UI에 보여주기 편한 형태로 정리"""
    creative = full_result.get("creative", {})
    
    return {
        "angle_title": creative.get("main_angle", "사진 분석 완료"),
        "display_text": creative.get("intro_sentence", ""),
        "tags": creative.get("tags", []),
        "fact_check": ""
    }