import streamlit as st
import ollama
import json
import re
import uuid
from datetime import datetime
from collections import Counter

from config import MODEL_VISION, MODEL_TEXT

MAX_TAGS = 6
TOPIC_N = 2

STOPWORDS = {
    "사진","이미지","장면","제품","구성","포함","있는","위","아래","옆","앞","뒤",
    "같은","위해","정도","부분","사용","가능","보임","보이는","있다","없다","그리고",
    "너무","정말","느낌","분위기","순간","오늘","이번","그냥","관련"
}

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def new_id():
    return str(uuid.uuid4())

def intent_block(t: str) -> str:
    t = (t or "").strip()
    return f"[사용자 의도]\n{t}\n" if t else ""

def pick_line(text: str, prefix: str) -> str:
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if ln.startswith(prefix):
            return ln.replace(prefix, "", 1).strip()
    return ""

def clean_tokens_korean(text: str):
    # 아주 단순 토큰화: 한글/숫자/영문/언더스코어 덩어리만
    toks = re.findall(r"[0-9A-Za-z가-힣_]{2,}", text or "")
    out = []
    for t in toks:
        tl = t.lower()
        if tl in STOPWORDS:
            continue
        if re.match(r"^\d+$", t):
            continue
        out.append(t)
    return out

def local_tags_from_desc(desc: str, k: int = 4):
    # 사진별 저장용 태그: 로컬 빈도 기반(가볍게)
    toks = clean_tokens_korean(desc)
    cnt = Counter(toks)
    top = [w for w, _ in cnt.most_common(k)]
    tags = []
    for w in top:
        tag = "#" + re.sub(r"[^0-9A-Za-z가-힣_]", "", w)
        if len(tag) > 1 and tag not in tags:
            tags.append(tag)
    return tags if tags else ["#사진", "#기록"]

def analyze_fact(image_bytes: bytes, user_intent: str) -> str:
    prompt = f"""
{intent_block(user_intent)}
이미지를 보고 사실 기반으로만 설명한다.

규칙:
- 1~2문장
- 보이는 것만
- 추측/해석/감정 금지

출력:
설명: ...
""".strip()

    r = ollama.chat(
        model=MODEL_VISION,
        messages=[{"role": "user", "content": prompt, "images": [image_bytes]}]
    )
    out = r["message"]["content"]
    desc = pick_line(out, "설명:")
    return desc if desc else out.strip()

def unify_all_with_llama(user_intent: str, descriptions: list, merged_tags_hint: list, n: int = TOPIC_N):
    joined = "\n".join(f"- {d}" for d in descriptions)
    tag_hint = " ".join(merged_tags_hint) if merged_tags_hint else ""

    prompt = f"""
너는 사진 묶음 기반으로 블로그 기획을 완성하는 편집장이다.

아래 입력은 사진 N장의 사실 설명과 사용자 의도, 그리고 빈도 기반 태그 힌트다.
이걸 바탕으로 통합 결과를 JSON으로만 출력한다.

[우선순위 규칙]
- 사용자 의도 키워드 + 통합 설명 + 태그에서 공통으로 반복되는 핵심 키워드가 있으면
  반드시 그 키워드를 중심축으로 삼는다.

[출력 요구]
1) merged_description: 사진들을 나열하지 말고 한 덩어리로 정의하는 2~3문장 사실 설명(추측 금지)
2) mood: 사물/브랜드/색상/위치/구성품 언급 없이 감정만 담은 1문장(20~35자)
3) tags: 정확히 {MAX_TAGS}개, 명사 중심, 감정/무드 제외, 사실 설명 기반, 중복 없이
4) topic_candidates: {n}개, 아래 “주제어 기준”을 만족하는 한 문장(길게)
5) best_topic: 후보 중 1개를 그대로 선택

[주제어 기준]
- 각 후보는 한 문장
- 높임말 사용하지 않는다
- 제목처럼 짧지 않게 작성
- 아래 요소 중 최소 3가지를 반드시 포함
  1) 구체적인 독자/상황
  2) 끝까지 읽게 만드는 문제 지점/판단 기준
  3) 글에서 초점을 맞추는 범위
  4) 다루지 않는 범위에 대한 암시
- “설명한다/다룬다/알아본다” 금지
- 키워드 나열/추상 남용 금지
- 코드블록/목록/추가 설명 금지

[사용자 의도]
{(user_intent or "").strip()}

[사진 설명]
{joined}

[태그 힌트]
{tag_hint}

[출력 JSON 스키마]
{{
  "merged_description": "string",
  "mood": "string",
  "tags": ["#tag", "... (exactly {MAX_TAGS})"],
  "topic_candidates": ["string", "... (exactly {n})"],
  "best_topic": "string"
}}

반드시 JSON 객체 한 덩어리만 출력한다.
""".strip()

    r = ollama.chat(model=MODEL_TEXT, messages=[{"role": "user", "content": prompt}])
    txt = r["message"]["content"]

    # JSON 파싱 (안전)
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else {}

def analyze_image_agent(images: list, user_intent: str = "") -> str:
    """
    [메인 진입점]
    Step 2에서 호출하는 함수입니다.
    여러 장의 이미지를 받아 각각 사실 관계를 분석한 뒤, Llama로 통합하여 결과를 반환합니다.
    """
    # 1. 이미지 리스트 처리 (단일 이미지일 경우 리스트로 변환)
    if not isinstance(images, list):
        images = [images]

    # 2. 각 이미지별 사실(Fact) 추출 (Vision Model)
    descriptions = []
    all_tags = []
    
    for img_bytes in images:
        # 개별 이미지 분석
        desc = analyze_fact(img_bytes, user_intent)
        descriptions.append(desc)
        # 로컬 태그 추출
        all_tags.extend(local_tags_from_desc(desc))

    # 3. 통합 및 기획 (Text Model)
    # 수집된 사실들과 태그를 바탕으로 통합 기획안 생성
    result_dict = unify_all_with_llama(user_intent, descriptions, all_tags)

    # 4. 결과 반환 (UI와의 호환성을 위해 JSON 문자열로 변환)
    return json.dumps(result_dict, ensure_ascii=False)


def parse_image_analysis(raw_result: str):
    """
    [결과 파싱]
    analyze_image_agent의 결과(JSON 문자열)를 받아
    UI에 표시할 mood(분위기/설명)와 tags(태그)를 분리합니다.
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