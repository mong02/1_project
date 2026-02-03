# llm_client.py


# OpenAI / Ollama 공통 호출 라우터
# - API_MODE=openai  -> OpenAI 호출
# - API_MODE=ollama  -> Ollama 호출

import os
import time
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

# region agent log
def _debug_log(message: str, data: Dict[str, Any], hypothesis_id: str, location: str, run_id: str = "pre"):
    return
# endregion

# Ollama는 ollama 모드에서만 실제 호출됩니다.
import ollama

# 프로젝트 고정 기본값(로컬 ollama 기본 모델명)
from config import MODEL_TEXT as CFG_MODEL_TEXT, MODEL_VISION as CFG_MODEL_VISION

# =========================================================
# [1] .env 로드 (프로젝트 루트에서 찾기)
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # agents/ -> project/
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =========================================================
# [2] 설정 읽기
# =========================================================
API_MODE = (os.getenv("API_MODE", "ollama") or "ollama").strip().lower()

OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY")
    or os.getenv("LLM_API_KEY")
    or os.getenv("openai_api_key")
    or ""
).strip()
OPENAI_API_BASE = (os.getenv("OPENAI_API_BASE") or os.getenv("LLM_BASE_URL") or "").strip() or None

# 모델은 .env가 있으면 덮어쓰기, 없으면 config.py 기본값
MODEL_TEXT = (os.getenv("MODEL_TEXT") or CFG_MODEL_TEXT).strip()
MODEL_VISION = (os.getenv("MODEL_VISION") or CFG_MODEL_VISION).strip()

# region agent log
_debug_log(
    message="llm_client config loaded",
    data={
        "api_mode": API_MODE,
        "model_text": MODEL_TEXT,
        "model_vision": MODEL_VISION,
        "openai_key_present": bool(OPENAI_API_KEY),
        "openai_base_present": bool(OPENAI_API_BASE),
    },
    hypothesis_id="A",
    location="agents/llm_client.py:config",
)
# endregion

# =========================================================
# [3] OpenAI 클라이언트 지연 초기화
# =========================================================
_openai_client = None


def get_openai_client():
    global _openai_client

    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다.\n"
            f".env 파일 위치: {ENV_PATH}\n"
            "예) OPENAI_API_KEY=sk-...\n"
            "또는 LLM_API_KEY 로도 설정 가능합니다."
        )

    if _openai_client is None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai 패키지가 설치되어 있지 않습니다. pip install openai 필요") from e

        _openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    return _openai_client


# =========================================================
# [4] Rate limit 대응 (429) 재시도
# =========================================================
def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            msg = str(e).lower()
            if "rate_limit" in msg or "429" in msg:
                last_exception = e
                wait_time = initial_delay * (2 ** attempt)
                time.sleep(wait_time)
                continue
            raise

    raise last_exception if last_exception else RuntimeError("재시도 실패")


# =========================================================
# [5] 공통 채팅 호출 (텍스트/비전 둘 다)
# =========================================================
def chat(
    model: str,
    user_prompt: str,
    system_prompt: str = "",
    image_bytes: Optional[bytes] = None,
    max_tokens: int = 1024,
    temperature: float = 0.4,
    top_p: float = 0.9,
) -> str:
    """
    model: OpenAI 모델명 또는 Ollama 모델명
    image_bytes가 있으면 비전 호출로 처리합니다.
    """
    # region agent log
    _debug_log(
        message="chat entry",
        data={
            "api_mode": API_MODE,
            "model_arg": model,
            "has_image": bool(image_bytes),
            "temperature": temperature,
            "top_p": top_p,
        },
        hypothesis_id="B",
        location="agents/llm_client.py:chat:entry",
    )
    # endregion

    if API_MODE == "openai":
        client = get_openai_client()

        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})

        # region agent log
        _debug_log(
            message="openai request prepared",
            data={
                "model_arg": model,
                "messages_count": len(messages),
                "has_system": bool(system_prompt),
                "has_image": bool(image_bytes),
            },
            hypothesis_id="B",
            location="agents/llm_client.py:chat:openai:pre",
        )
        # endregion

        def api_call():
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return (resp.choices[0].message.content or "").strip()

        out = retry_with_backoff(api_call, max_retries=3, initial_delay=1.0)
        # region agent log
        _debug_log(
            message="openai response received",
            data={"output_len": len(out)},
            hypothesis_id="B",
            location="agents/llm_client.py:chat:openai:post",
        )
        # endregion
        time.sleep(0.3)
        return out

    # API_MODE == "ollama"
    # region agent log
    _debug_log(
        message="ollama request prepared",
        data={
            "model_arg": model,
            "has_system": bool(system_prompt),
            "has_image": bool(image_bytes),
        },
        hypothesis_id="C",
        location="agents/llm_client.py:chat:ollama:pre",
    )
    # endregion
    msgs: List[Dict[str, Any]] = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})

    if image_bytes:
        msgs.append({"role": "user", "content": user_prompt, "images": [image_bytes]})
    else:
        msgs.append({"role": "user", "content": user_prompt})

    res = ollama.chat(
        model=model,
        messages=msgs,
        options={"temperature": temperature, "top_p": top_p},
    )
    out = (res.get("message") or {}).get("content", "") or ""
    # region agent log
    _debug_log(
        message="ollama response received",
        data={"output_len": len(out)},
        hypothesis_id="C",
        location="agents/llm_client.py:chat:ollama:post",
    )
    # endregion
    return out


def chat_text(user_prompt: str, system_prompt: str = "", model: str = MODEL_TEXT, **kw) -> str:
    return chat(model=model, user_prompt=user_prompt, system_prompt=system_prompt, image_bytes=None, **kw)


def chat_vision(user_prompt: str, image_bytes: bytes, system_prompt: str = "", model: str = MODEL_VISION, **kw) -> str:
    return chat(model=model, user_prompt=user_prompt, system_prompt=system_prompt, image_bytes=image_bytes, **kw)
