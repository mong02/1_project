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
# [메인 함수] UI에서 호출하는 이미지 분석 에이전트
# ==============================================================================
def analyze_image_agent(image_bytes: bytes, user_intent: str = "") -> str:
    """
    이미지 바이트를 받아 Vision 모델로 분석하고 결과를 문자열로 반환합니다.
    UI에서는 이 문자열을 그대로 저장하고 parse_image_analysis로 파싱합니다.
    """
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')

    # 사용자 의도 반영
    intent_instruction = ""
    if user_intent:
        intent_instruction = f"\n\n[사용자 의도 - 최우선 반영]: {user_intent}\n위 의도를 분석과 추천에 가장 중요하게 반영하세요."

    prompt = f"""
    당신은 블로그 사진 분석 전문가입니다.
    주어진 이미지를 보고 블로그 글의 주제를 추천해주세요.
    {intent_instruction}

    [출력 형식]
    반드시 아래 JSON 형식으로만 출력하세요. 다른 텍스트는 절대 포함하지 마세요.

    {{
        "mood": "이 사진으로 쓸 수 있는 블로그 주제를 한 문장으로 (예: 햇살 맛집 홈카페에서의 여유로운 오후)",
        "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
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