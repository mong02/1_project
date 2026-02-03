# agents/image_agent.py
# =========================================================
# [Bottom-up 방식] 개별 사진 정밀 분석 후 취합
# =========================================================
import ollama
import json
import re
from typing import List, Dict, Any
from collections import Counter

from config import MODEL_VISION, MODEL_TEXT

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
    
    Returns:
        {"img_id": int, "desc": str, "tags": [str, ...]}
    """
    intent_section = f"[사용자 의도]\n{user_intent.strip()}\n" if user_intent else ""
    
    prompt = f"""
{intent_section}
이 이미지를 정밀하게 분석하라.

[출력 규칙]
1. 설명: 보이는 장면을 사실 기반으로 1~2문장으로 서술 (추측/감정 금지)
2. 태그: 이미지의 핵심 요소를 나타내는 명사 3~5개 (# 포함, 쉼표 구분)

[출력 형식 - 반드시 아래 형태로]
설명: ...
태그: #태그1, #태그2, #태그3
""".strip()

    try:
        r = ollama.chat(
            model=MODEL_VISION,
            messages=[{"role": "user", "content": prompt, "images": [image_bytes]}]
        )
        out = r["message"]["content"]
        
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
                # 쉼표 또는 공백으로 분리
                raw_tags = re.split(r'[,\s]+', tag_part)
                for t in raw_tags:
                    t = t.strip()
                    if t:
                        # # 붙이기
                        if not t.startswith("#"):
                            t = "#" + t
                        # 특수문자 정리
                        t = "#" + re.sub(r'[^0-9A-Za-z가-힣_]', '', t.replace("#", ""))
                        if len(t) > 1 and t not in tags:
                            tags.append(t)
                break
        
        # 태그가 없으면 설명에서 추출
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
    
    Args:
        individual_analyses: [{"img_id": 1, "desc": "...", "tags": [...]}, ...]
        user_intent: 사용자의 의도
        n_topics: 생성할 주제 후보 개수
    
    Returns:
        {"merged_description", "mood", "tags", "topic_candidates", "best_topic"}
    """
    # 개별 분석 결과를 프롬프트용 텍스트로 변환
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
    
    # 태그 빈도 분석 (힌트용)
    tag_freq = Counter(all_tags_pool)
    frequent_tags = [t for t, _ in tag_freq.most_common(MAX_TAGS)]
    tag_hint = ", ".join(frequent_tags) if frequent_tags else "(없음)"
    
    prompt = f"""
너는 개별 사진들의 파편화된 정보를 모아 하나의 완결된 기획으로 엮는 에디터다.

아래에 나열된 [사진 1...N]의 개별 설명과 태그를 모두 포함할 수 있는 **공통 분모**를 찾아내어,
전체를 아우르는 매력적인 **제목**과 **분위기(Mood)**를 도출하라.

[사용자 의도]
{(user_intent or "").strip() or "(없음)"}

[개별 사진 분석 결과]
{images_text}

[태그 빈도 힌트]
{tag_hint}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[출력 지침]

1) merged_description (통합 설명)
   - 개별 사진들을 나열하지 말고, 전체를 관통하는 하나의 스토리로 2~3문장 서술
   - 사실 기반, 추측 금지

2) mood (분위기)
   - 사물/브랜드/색상/위치 언급 없이, 감정과 분위기만 담은 1문장 (20~35자)
   - 예: "설렘과 기대가 가득한 여행의 시작점"

3) tags (통합 태그)
   - 정확히 {MAX_TAGS}개, 명사 중심, 모든 사진을 아우르는 공통 키워드
   - 감정/무드 단어 제외, # 포함

4) topic_candidates (주제 후보)
   - {n_topics}개, 각각 한 문장으로 작성
   - 높임말 사용 금지
   - 아래 요소 중 최소 3가지 포함:
     a) 구체적인 독자/상황
     b) 끝까지 읽게 하는 문제 지점/판단 기준
     c) 글에서 초점을 맞추는 범위
     d) 다루지 않는 범위 암시
   - "설명한다/다룬다/알아본다" 같은 메타 표현 금지

5) best_topic
   - 후보 중 가장 매력적인 1개를 그대로 선택

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[출력 형식] - 반드시 JSON 객체 하나만 출력

{{
  "merged_description": "string",
  "mood": "string",
  "tags": ["#tag1", "#tag2", ... (exactly {MAX_TAGS})],
  "topic_candidates": ["string", ... (exactly {n_topics})],
  "best_topic": "string"
}}
""".strip()

    try:
        r = ollama.chat(model=MODEL_TEXT, messages=[{"role": "user", "content": prompt}])
        txt = r["message"]["content"]
        
        # JSON 파싱 (안전)
        try:
            result = json.loads(txt)
        except json.JSONDecodeError:
            # JSON 블록 추출 시도
            m = re.search(r"\{.*\}", txt, re.S)
            result = json.loads(m.group(0)) if m else {}
        
        # 태그 개수 보정
        tags = result.get("tags", [])
        tags = [t if t.startswith("#") else "#" + t for t in tags][:MAX_TAGS]
        while len(tags) < MAX_TAGS:
            if len(frequent_tags) > len(tags):
                candidate = frequent_tags[len(tags)]
                if candidate not in tags:
                    tags.append(candidate)
                else:
                    tags.append(f"#태그{len(tags)+1}")
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
    
    Process:
        Step 1: 각 이미지별로 독립적인 정밀 분석 (desc + tags)
        Step 2: 개별 분석 결과를 취합하여 통합 기획안 생성
        Step 3: UI 호환 JSON 형식으로 반환
    
    Args:
        images: 이미지 바이트 리스트 (단일 이미지도 가능)
        user_intent: 사용자가 입력한 의도
    
    Returns:
        JSON 문자열 (mood, tags, topic_candidates 등 포함)
    """
    # 이미지 리스트 처리 (단일 이미지일 경우 리스트로 변환)
    if not isinstance(images, list):
        images = [images]
    
    # ========== Step 1: 개별 이미지 정밀 분석 ==========
    individual_analyses = []
    
    for idx, img_bytes in enumerate(images, start=1):
        analysis = analyze_single_image(img_bytes, img_id=idx, user_intent=user_intent)
        individual_analyses.append(analysis)
    
    # ========== Step 2: 취합 및 통합 기획 ==========
    unified_result = aggregate_and_plan(
        individual_analyses=individual_analyses,
        user_intent=user_intent,
        n_topics=TOPIC_N
    )
    
    # ========== Step 3: UI 호환 형식으로 반환 ==========
    return json.dumps(unified_result, ensure_ascii=False)


def parse_image_analysis(raw_result: str):
    """
    [결과 파싱]
    analyze_image_agent의 결과(JSON 문자열)를 받아
    UI에 표시할 mood(분위기/설명)와 tags(태그)를 분리합니다.
    
    Returns:
        (display_text: str, tags: list)
    """
    try:
        # JSON 문자열을 딕셔너리로 변환
        if isinstance(raw_result, str):
            data = json.loads(raw_result)
        else:
            data = raw_result

        # 데이터 추출
        mood = data.get("mood", "")
        merged_desc = data.get("merged_description", "")
        tags = data.get("tags", [])
        
        # UI에 보여줄 텍스트 결정 (Mood가 없으면 설명으로 대체)
        display_text = mood if mood else merged_desc
        
        return display_text, tags

    except Exception as e:
        print(f"파싱 에러: {e}")
        return "분석 결과를 처리하는 중 오류가 발생했습니다.", []