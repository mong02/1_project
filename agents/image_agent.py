# image_agent.py

import json
import re
import time
import base64  # <-- [중요] OpenAI 이미지 전송을 위해 필요
from typing import List, Dict, Any
from collections import Counter

# [1] 환경설정 및 라이브러리 로드
from openai import OpenAI, RateLimitError
import ollama

# config에서 모델명/모드 가져오기
from config import (
    MODEL_VISION,
    MODEL_TEXT,
    API_KEY,
    BASE_URL,
    resolve_api_mode,
    normalize_openai_model,
)

# 프롬프트 로더 추가
from utils.prompt_loader import load_prompt, render_prompt

# =========================================================
# 🔐 환경설정 및 모드 자동 감지 (하이브리드 로직)
# =========================================================
# API 모드 결정 로직 (config와 동일한 기준)
API_MODE = resolve_api_mode()

# 모델명 안전장치 (OpenAI 모드인데 로컬 모델명이면 gpt-4o로 강제)
if API_MODE == "openai":
    USE_MODEL_VISION = normalize_openai_model(MODEL_VISION)
    USE_MODEL_TEXT = normalize_openai_model(MODEL_TEXT)
else:
    USE_MODEL_VISION = MODEL_VISION
    USE_MODEL_TEXT = MODEL_TEXT

# =========================================================
# 🤖 통합 클라이언트 (Vision 기능 내장)
# =========================================================
class UnifiedClient:
    def __init__(self):
        self.mode = API_MODE
        self.client = None
        if self.mode == "openai":
            if not API_KEY:
                 print("⚠️ [Warning] OpenAI 모드이나 API Key가 없습니다. Vision 기능이 제한될 수 있습니다.")
            else:
                self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    def _retry_openai(self, func):
        """OpenAI Rate Limit 재시도 로직"""
        for i in range(3):
            try: return func()
            except RateLimitError:
                print(f"⏳ Rate Limit (Vision). Retrying in {2**(i+1)}s...")
                time.sleep(2**(i+1))
            except Exception as e: raise e
        raise Exception("OpenAI API Retry Failed")

    # [핵심] 이미지 분석 함수
    def chat_vision(self, prompt: str, image_bytes: bytes) -> str:
        """이미지 데이터를 받아서 분석 결과를 문자열로 반환"""
        if not image_bytes:
            return "이미지 데이터가 없습니다."

        if self.mode == "openai" and self.client:
            # --- OpenAI Logic (Base64 인코딩 필요) ---
            try:
                # 1. 이미지를 Base64 문자열로 변환
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                def _call():
                    response = self.client.chat.completions.create(
                        model=USE_MODEL_VISION,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    # 2. 이미지 URL 형식으로 전송
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ],
                            }
                        ],
                        max_tokens=500,
                    )
                    return response.choices[0].message.content
                return self._retry_openai(_call)
            except Exception as e:
                 return f"OpenAI Vision Error: {str(e)}"

        else:
            # --- Ollama Logic (바이트 직접 전송 가능) ---
            try:
                response = ollama.chat(
                    model=USE_MODEL_VISION,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                            # Ollama는 images 리스트에 바이너리를 직접 넣습니다.
                            "images": [image_bytes],
                        }
                    ],
                )
                return response["message"]["content"]
            except Exception as e:
                return f"Ollama Vision Error: {str(e)} (모델이 설치되어 있는지 확인해주세요: {USE_MODEL_VISION})"

    # 텍스트 생성 함수 (종합 분석용)
    def chat_text(self, prompt: str, system_role: str = "assistant") -> str:
        if self.mode == "openai" and self.client:
            def _call():
                return self.client.chat.completions.create(
                    model=USE_MODEL_TEXT,
                    messages=[{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
                    temperature=0.7
                ).choices[0].message.content
            return self._retry_openai(_call)
        else:
            try:
                resp = ollama.chat(
                    model=USE_MODEL_TEXT,
                    messages=[{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
                    options={"temperature": 0.7}
                )
                return resp['message']['content']
            except Exception as e:
                return f"Ollama Text Error: {str(e)}"

# 클라이언트 인스턴스 생성
client = UnifiedClient()

# =========================================================
# 🧹 헬퍼 함수 (태그 추출 및 JSON 파싱)
# =========================================================

def _extract_tags_from_text(text: str, k: int = 4) -> List[str]:
    """텍스트에서 빈도 기반으로 태그 추출 (백업용)"""
    STOPWORDS = {
        "사진", "이미지", "장면", "제품", "구성", "포함", "있는", "위", "아래", "옆", "앞", "뒤",
        "같은", "위해", "정도", "부분", "사용", "가능", "보임", "보이는", "있다", "없다", "그리고",
        "너무", "정말", "느낌", "분위기", "순간", "오늘", "이번", "그냥", "관련", "것", "수"
    }
    # 한글/영문 명사형 단어 추출 시도
    toks = re.findall(r"[가-힣A-Za-z0-9_]{2,}", text or "")
    toks = [t for t in toks if t.lower() not in STOPWORDS and not re.match(r"^\d+$", t)]
    cnt = Counter(toks)
    return ["#" + w for w, _ in cnt.most_common(k)]

def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """AI 응답에서 JSON 추출 (Ollama 대비 강화)"""
    try:
        # 마크다운 코드 블록 제거
        text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
        
        # 가장 바깥쪽 중괄호 찾기
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            return json.loads(json_str)
        else:
            # 중괄호가 없으면 전체 시도
            return json.loads(text)
    except:
        return {}




# =========================================================
# [설정]
# =========================================================
MAX_TAGS = 6
TOPIC_N = 2


# =========================================================
# [Step 1] Vision Model - 개별 이미지 정밀 분석
# =========================================================
def analyze_single_image(image_bytes: bytes, img_id: int, user_intent: str = "") -> Dict[str, Any]:
    """
    [Step 1] 단일 이미지를 정밀 분석하여 설명(desc)과 태그(tags)를 함께 추출합니다.
    프롬프트는 prompts/image_analysis.md에서 로드합니다.
    """
    prompt_template = load_prompt("image_analysis")
    prompt = render_prompt(prompt_template, {
        "user_intent": user_intent.strip() if user_intent else "(없음)"
    })


    
    try:
        # ★ UnifiedClient 사용
        out = client.chat_vision(prompt, image_bytes)
        
        # 설명 추출
        desc = ""
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("설명:"):
                desc = line.replace("설명:", "", 1).strip()
                break
        if not desc:
            desc = out.split("\n")[0].strip()  # fallback: 첫 줄
        
        # 태그 추출
        tags = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("태그:"):
                tag_part = line.replace("태그:", "", 1).strip()
                raw_tags = re.split(r'[,\s]+', tag_part)
                for t in raw_tags:
                    t = t.strip()
                    if t:
                        if not t.startswith("#"): t = "#" + t
                        t = "#" + re.sub(r'[^0-9A-Za-z가-힣_]', '', t.replace("#", ""))
                        if len(t) > 1 and t not in tags:
                            tags.append(t)
                break
        
        if not tags:
            tags = _extract_tags_from_text(desc, k=4)
        
        return {"img_id": img_id, "desc": desc, "tags": tags[:5]}
        
    except Exception as e:
        print(f"[이미지 {img_id}] 분석 에러: {e}")
        return {"img_id": img_id, "desc": "분석 실패", "tags": ["#사진"]}


def _extract_tags_from_text(text: str, k: int = 4) -> List[str]:
    """텍스트에서 빈도 기반으로 태그 추출 (백업용)"""
    STOPWORDS = {
        "사진", "이미지", "장면", "제품", "구성", "포함", "있는", "위", "아래", "옆", "앞", "뒤",
        "같은", "위해", "정도", "부분", "사용", "가능", "보임", "보이는", "있다", "없다", "그리고",
        "너무", "정말", "느낌", "분위기", "순간", "오늘", "이번", "그냥", "관련", "것", "수"
    }
    toks = re.findall(r"[가-힣A-Za-z0-9_]{2,}", text or "")
    toks = [t for t in toks if t.lower() not in STOPWORDS and not re.match(r"^\d+$", t)]
    cnt = Counter(toks)
    return ["#" + w for w, _ in cnt.most_common(k)]


# =========================================================
# [Step 2] Text Model - 개별 분석 결과 취합 및 통합 기획
# =========================================================
def aggregate_and_plan(
    individual_analyses: List[Dict[str, Any]], 
    user_intent: str = "",
    n_topics: int = TOPIC_N
) -> Dict[str, Any]:
    """
    [Step 2] 개별 이미지 분석 결과들을 취합하여 통합 기획안을 생성합니다.
    """
    image_sections = []
    all_tags_pool = []
    
    for item in individual_analyses:
        img_id = item.get("img_id", "?")
        desc = item.get("desc", "")
        tags = item.get("tags", [])
        tag_str = ", ".join(tags) if tags else "(없음)"
        image_sections.append(f"[사진 {img_id}]\n- 설명: {desc}\n- 태그: {tag_str}")
        all_tags_pool.extend(tags)
    
    images_text = "\n\n".join(image_sections)
    tag_freq = Counter(all_tags_pool)
    frequent_tags = [t for t, _ in tag_freq.most_common(MAX_TAGS)]
    tag_hint = ", ".join(frequent_tags) if frequent_tags else "(없음)"
    
    # 프롬프트 파일에서 로드
    prompt_template = load_prompt("image_aggregate")
    prompt = render_prompt(prompt_template, {
        "user_intent": (user_intent or "").strip() or "(없음)",
        "images_text": images_text,
        "tag_hint": tag_hint,
        "n_topics": str(n_topics),
        "max_tags": str(MAX_TAGS),
    })

    try:
        # ★ UnifiedClient 사용
        txt = client.chat_text(prompt)
        
        try:
            result = json.loads(txt)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", txt, re.S)
            result = json.loads(m.group(0)) if m else {}
        
        # 태그 보정
        tags = result.get("tags", [])
        tags = [t if t.startswith("#") else "#" + t for t in tags][:MAX_TAGS]
        while len(tags) < MAX_TAGS:
            if len(frequent_tags) > len(tags):
                candidate = frequent_tags[len(tags)]
                if candidate not in tags: tags.append(candidate)
                else: tags.append(f"#태그{len(tags)+1}")
            else:
                tags.append(f"#태그{len(tags)+1}")
        result["tags"] = tags
        
        return result
        
    except Exception as e:
        print(f"[통합 기획] 에러: {e}")
        return {
            "merged_description": "통합 분석 실패",
            "mood": "분석 중 오류 발생",
            "tags": frequent_tags[:MAX_TAGS] if frequent_tags else ["#사진", "#기록"],
            "topic_candidates": [],
            "best_topic": ""
        }


# =========================================================
# [메인 진입점] Step2에서 호출
# =========================================================
def analyze_image_agent(images: list, user_intent: str = "") -> str:
    """
    [메인 진입점 - Bottom-up 방식]
    Step 2에서 호출하는 함수입니다.
    """
    # 이미지 리스트 처리
    if not isinstance(images, list):
        images = [images]
    
    # Step 1: 개별 분석
    individual_analyses = []
    for idx, img_bytes in enumerate(images, start=1):
        analysis = analyze_single_image(img_bytes, img_id=idx, user_intent=user_intent)
        individual_analyses.append(analysis)
    
    # Step 2: 통합 기획
    unified_result = aggregate_and_plan(
        individual_analyses=individual_analyses,
        user_intent=user_intent,
        n_topics=TOPIC_N
    )
    
    return json.dumps(unified_result, ensure_ascii=False)


def parse_image_analysis(raw_result: str):
    """결과 파싱 Helper"""
    try:
        if isinstance(raw_result, str):
            data = json.loads(raw_result)
        else:
            data = raw_result
        
        mood = data.get("mood", "")
        merged_desc = data.get("merged_description", "")
        tags = data.get("tags", [])
        
        display_text = mood if mood else merged_desc
        return display_text, tags

    except Exception as e:
        return "분석 결과를 처리하는 중 오류가 발생했습니다.", []
