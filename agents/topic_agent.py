# 카테고리 - 세부 주제
# 세부 주제 - 제목 후보

import os
import re
import requests
from typing import Any, Dict, List

from config import TARGET_CHARS, MODEL_TEXT
from agents.ollama_client import OllamaClient

def _safe_list(x) -> List[str]:
    if isinstance(x, list):
        return x
    return []

class TopicAgent:
    def __init__(self, client):
        # Ollama와 대화할 수 있는 클라이언트를 가져옵니다.
        self.client = client
        # 프롬프트가 저장된 폴더 이름이에요.
        self.folder = "prompts"

    def read_file(self, file_name):
        """폴더에서 마크다운 파일을 읽어오는 간단한 함수입니다."""
        path = f"{self.folder}/{file_name}.md"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def suggest_topics(self, category, job):
        """1. 카테고리를 보고 제목 후보 5개를 제안합니다."""
        # 파일에서 지침서를 읽어옵니다.
        prompt = self.read_file("topic_titles")
        
        # 지침서 안의 빈칸({category}, {job})을 실제 내용으로 채웁니다.
        prompt = prompt.replace("{category}", category)
        prompt = prompt.replace("{job}", job)
        
        # AI에게 물어보고 결과를 받습니다.
        result = self.client.generate_json("주제 기획자", prompt)
        
        # AI가 리스트 형식이 아니라 엉뚱하게 줄 때를 대비한 '정규화'
        if isinstance(result, list):
            return result[:5]
        elif isinstance(result, dict):
            return result.get("topics", ["제목 생성 실패"])
        
        return ["추천 제목 1", "추천 제목 2", "추천 제목 3"]

    def generate_plan(self, topic, job, mbti):
        """2. 선택한 제목으로 블로그 설계도를 만듭니다."""
        # 설계도 작성용 지침서를 읽어옵니다.
        prompt = self.read_file("outline")
        
        # 빈칸 채우기
        prompt = prompt.replace("{topic}", topic)
        prompt = prompt.replace("{job}", job)
        prompt = prompt.replace("{mbti}", mbti)
        
        # AI 호출
        raw_data = self.client.generate_json("콘텐츠 전략가", prompt)
        
        # [정규화] 데이터가 비어있어도 UI가 안 깨지게 기본값을 채워줍니다.
        # .get("키이름", "기본값")을 쓰면 데이터가 없어도 에러가 안 나요!
        plan = {
            "targetSituation": raw_data.get("targetSituation", "정보를 찾는 독자"),
            "format": raw_data.get("format", "정보 전달형"),
            "tone": raw_data.get("tone", "차분한 말투"),
            "keywords": raw_data.get("keywords", {"main": topic, "sub": []})
        }
        
        return plan


def generate_design_brief(ctx: Dict[str, Any], client: OllamaClient | None = None) -> Dict[str, Any]:
    if client is None:
        client = OllamaClient(model=MODEL_TEXT)

    persona = ctx.get("persona", {})
    topic_flow = ctx.get("topic_flow", {})
    options = ctx.get("options", {})
    final_options = ctx.get("final_options", {})

    selected_title = (topic_flow.get("title", {}) or {}).get("selected")
    input_keyword = (topic_flow.get("title", {}) or {}).get("input_keyword")
    main_kw = selected_title or input_keyword or ""

    toggles = final_options.get("toggles", {}) or {}
    seo_opt = bool(toggles.get("seo_opt", False))

    target_chars = int((ctx.get("design_brief", {}) or {}).get("length", {}).get("target_chars") or TARGET_CHARS)

    facts = {
        "persona": {
            "role_job": persona.get("role_job"),
            "tone": persona.get("tone", {}),
            "mbti": (persona.get("mbti", {}) or {}).get("type"),
            "avoid_keywords": _safe_list(persona.get("avoid_keywords")),
        },
        "topic": {
            "category": (topic_flow.get("category", {}) or {}).get("selected"),
            "subtopic": (topic_flow.get("category", {}) or {}).get("selected_subtopic"),
            "title": selected_title,
            "input_keyword": input_keyword,
        },
        "options": {
            "post_type": options.get("post_type"),
            "headline_style": options.get("headline_style"),
            "target_reader": (options.get("detail", {}) or {}).get("target_reader", {}).get("text"),
            "extra_request": (options.get("detail", {}) or {}).get("extra_request", {}).get("text"),
            "seo_opt": bool(final_options.get("toggles", {}).get("seo_opt")),
            #####step3.option 코드 추가
            "evidence_label": bool(final_options.get("toggles", {}).get("evidence_label")),
            "publish_package": bool(final_options.get("toggles", {}).get("publish_package")),
            "ai_tone_remove_strong": bool(final_options.get("toggles", {}).get("ai_tone_remove_strong")),
            "image_hashtag": bool(final_options.get("toggles", {}).get("image_hashtag")),
        },
        "constraints": {
            "target_chars": target_chars,
            "seo_opt": seo_opt,
        },
    }

    schema_hint = {
        "applied_persona_text": "string",
        "keywords": {"main": "string", "sub": ["string"]},
        "target_context": {"text": "string"},
        "tone_manner": {"summary": "string", "rules": ["string"]},
        "outline": {"summary": "string", "sections": ["string"]},
        "length": {"target_chars": "number", "note": "string"},
        "strategy": {"text": "string", "seo": {"enabled": "boolean", "notes": "string"}, "hashtags": ["string"]},
    }

    prompt = f"""
너는 블로그 설계안을 만드는 콘텐츠 전략가다.
출력은 반드시 JSON 객체 한 덩어리만. (설명/코드블록 금지)
모든 문장은 존댓말로 작성하라. 반말은 절대 금지.

아래 FACTS를 기반으로 반드시 다음을 포함해 설명하라:
- 타겟 상황: 다정한 존댓말로 2줄, 실제 상황 설명만 작성
- 톤앤매너: 다정한 존댓말로 2줄, 페르소나를 반영한 결과 설명만 작성
- 글 구성: 다정한 존댓말로 2줄, 섹션의 목적과 전개 흐름을 실제 내용으로 설명
- 전략: 다정한 존댓말로 2줄, 타겟 독자/추가 요청/SEO 옵션을 반영한 실행 전략을 설명

금지 규칙:
- “예를 들어”, “설명할게/하겠다” 같은 메타 문장 금지
- 지시문을 반복하거나 형식을 설명하는 문장 금지
- 키워드 나열 금지, 실제 내용만 문장으로 작성

[FACTS]
{facts}

[OUTPUT SCHEMA HINT]
{schema_hint}
""".strip()

    try:
        out = client.generate_json("콘텐츠 전략가", prompt)
    except Exception as e:
        raise

    result = {
        "status": "ready",
        "error": None,
        "applied_persona_text": out.get("applied_persona_text") or "",
        "keywords": {
            "main": (out.get("keywords", {}) or {}).get("main") or main_kw,
            "sub": _safe_list((out.get("keywords", {}) or {}).get("sub")),
        },
        "target_context": {"text": (out.get("target_context", {}) or {}).get("text") or ""},
        "tone_manner": {
            "summary": (out.get("tone_manner", {}) or {}).get("summary") or "",
            "rules": _safe_list((out.get("tone_manner", {}) or {}).get("rules")),
        },
        "outline": {
            "summary": (out.get("outline", {}) or {}).get("summary") or "",
            "sections": _safe_list((out.get("outline", {}) or {}).get("sections")),
        },
        "length": {
            "target_chars": int((out.get("length", {}) or {}).get("target_chars") or target_chars),
            "note": (out.get("length", {}) or {}).get("note") or "",
        },
        "strategy": {
            "text": (out.get("strategy", {}) or {}).get("text") or "",
            "seo": {
                "enabled": bool((out.get("strategy", {}) or {}).get("seo", {}).get("enabled", seo_opt)),
                "notes": (out.get("strategy", {}) or {}).get("seo", {}).get("notes") or "",
            },
            "hashtags": _safe_list((out.get("strategy", {}) or {}).get("hashtags")),
        },
        "sources": {"from_step1": {}, "from_step2": {}, "agent_raw": out},
        "updated_at": None,
    }

    return result


# 수정( 스텝1 블로그 분석 코드)
def _fetch_url_text(url: str, max_chars: int = 6000) -> str:
    """
    URL의 HTML을 받아서 대충 텍스트만 뽑아옵니다.
    (완벽한 크롤링이 아니라 '스타일 분석용 요약 텍스트'만 추출하는 목적)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        html = r.text

        # script/style 제거
        html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.S)
        html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.S)

        # 태그 제거(아주 단순)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:max_chars]
    except Exception:
        return ""


def analyze_blog_style(blog_url: str, client: OllamaClient | None = None) -> Dict[str, Any]:
    """
    Step1에서 입력된 블로그 URL을 실제로 읽고(가능하면) 스타일을 분석합니다.
    반환 스키마(권장):
      {
        "tone": "...",
        "structure": "...",
        "feel": "..."
      }
    """
    if client is None:
        client = OllamaClient(model=MODEL_TEXT)

    # 1) 프롬프트(md) 읽기: prompts/analyzed_style.md
    prompt_path = os.path.join("prompts", "analyzed_style.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()
    else:
        # md 없을 때 최소 프롬프트(백업)
        base_prompt = """
너는 블로그 문체 분석가다.
아래 INPUT을 보고 말투/구성/느낌을 한국어로 요약해라.
출력은 반드시 JSON만.
키는 tone, structure, feel.
""".strip()

    # 2) URL에서 텍스트 가져오기(가능한 경우)
    page_text = _fetch_url_text(blog_url)

    # 3) LLM에게 줄 입력 구성
    #    - 블로그 내용이 제대로 못 가져와질 수 있으니 url도 같이 보냄
    prompt = f"""
{base_prompt}

[INPUT_URL]
{blog_url}

[INPUT_TEXT_EXCERPT]
{page_text if page_text else "(본문을 가져오지 못했습니다. URL과 일반적인 블로그 문체 신호로 추정하되, 불확실하면 그렇게 명시하세요.)"}

[OUTPUT FORMAT]
반드시 JSON 객체 한 덩어리만 출력:
{{
  "tone": "말투 1줄",
  "structure": "구성 1줄",
  "feel": "느낌 1줄"
}}
""".strip()

    out = client.generate_json("블로그 문체 분석가", prompt)

    # 4) 정규화(키가 조금 달라도 UI가 안깨지게)
    result = {
        "tone": out.get("tone") or out.get("말투") or "",
        "structure": out.get("structure") or out.get("구성") or out.get("writingStyle") or "",
        "feel": out.get("feel") or out.get("느낌") or out.get("impression") or "",
    }

    # 완전 비었으면 fallback
    if not any(result.values()):
        result = {
            "tone": "분석 실패(데이터 부족)",
            "structure": "분석 실패(데이터 부족)",
            "feel": "분석 실패(데이터 부족)",
        }

    return result

