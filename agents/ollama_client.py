# Ollama 호출 공통 함수 
# 에러 처리
# 모델 설정
# 중요! AI 호출은 여기서만!

# ollama_client.py
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

import ollama
from openai import OpenAI, RateLimitError

from config import (
    MODEL_TEXT,
    ASSETS_DIR,
    API_KEY,
    BASE_URL,
    ENV_API_MODE,
    resolve_api_mode,
    normalize_openai_model,
)

# =========================================================
# 🔐 환경설정 및 모드 자동 감지 (OpenAI/Ollama 하이브리드)
# =========================================================
# API 모드 결정 로직 (config와 동일한 기준)
API_MODE = resolve_api_mode()


class OllamaClient:
    def __init__(self, model: str = MODEL_TEXT):
        self.model = model
        self.mode = API_MODE
        self.client = None

        # OpenAI 모드면 모델명 보정 (로컬 모델명 방지)
        if self.mode == "openai":
            self.model = normalize_openai_model(self.model)
            if not API_KEY:
                # 키가 없으면 강제로 Ollama로 전환
                print("⚠️ [Warning] OpenAI 모드이나 API Key가 없습니다. Ollama로 전환됩니다.")
                self.mode = "ollama"
                self.model = MODEL_TEXT
            else:
                self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

        # 현재 모델/모드 기록 (assets에 로그)
        self._log_model_usage()

    def _log_model_usage(self) -> None:
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            log_path = os.path.join(ASSETS_DIR, "model_usage.log")
            record = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "mode": self.mode,
                "model": self.model,
                "base_url": BASE_URL if self.mode == "openai" else None,
                "env_api_mode": ENV_API_MODE or None,
                "api_key_present": bool(API_KEY),
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # 로깅 실패는 기능에 영향 주지 않도록 무시
            pass

    def _retry_openai(self, func):
        """OpenAI Rate Limit 재시도 로직"""
        for i in range(3):
            try:
                return func()
            except RateLimitError:
                print(f"⏳ Rate Limit. Retrying in {2**(i+1)}s...")
                time.sleep(2**(i+1))
            except Exception as e:
                raise e
        raise Exception("OpenAI API Retry Failed")

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        return text.strip()

    @staticmethod
    def _extract_first_json_object(text: str) -> Dict[str, Any]:
        """
        LLM 응답에 설명/잡텍스트가 섞여도 첫 JSON 객체를 최대한 복구.
        - 중괄호 카운팅으로 가장 앞쪽 JSON 객체 1개만 잘라냄
        """
        if not text or not text.strip():
            raise ValueError("빈 응답")

        text = OllamaClient._strip_code_fences(text)

        # 빠른 경로: 전체가 JSON이면 바로 파싱
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # 일반 경로
        start = text.find("{")
        if start == -1:
            raise ValueError(f"JSON 시작 '{{'를 찾지 못했습니다. 일부: {text[:200]}")

        depth = 0
        in_str = False
        esc = False

        for i in range(start, len(text)):
            ch = text[i]

            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue

            if ch == '"':
                in_str = True
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception as e:
                        raise ValueError(
                            f"JSON 파싱 실패: {e}. 후보 일부: {candidate[:200]}"
                        ) from e

        raise ValueError(f"JSON 객체를 끝까지 찾지 못했습니다. 일부: {text[:200]}")

    def generate_text(
        self,
        system_role: str,
        prompt: str,
        temperature: float = 0.4,
        top_p: float = 0.9,
    ) -> str:
        if self.mode == "openai" and self.client:
            def _call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_role},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    top_p=top_p,
                ).choices[0].message.content

            return self._retry_openai(_call) or ""

        res = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": temperature,
                "top_p": top_p,
            },
        )
        return (res.get("message") or {}).get("content", "") or ""

    def generate_json(
        self,
        system_role: str,
        prompt: str,
        temperature: float = 0.2,
        top_p: float = 0.9,
        retries: int = 2,
    ) -> Dict[str, Any]:
        """
        JSON 객체만 반환하도록 유도 + 파싱 실패 시 재시도
        retries=2면 총 3번 시도(1회 + 2회 재시도)
        """
        json_guard = (
            "반드시 JSON '객체'만 출력하세요.\n"
            "설명 문장, 마크다운, 코드블록, 주석은 출력하지 마세요."
        )

        last_err: Optional[Exception] = None
        cur_prompt = f"{json_guard}\n\n{prompt}"

        for attempt in range(retries + 1):
            text = self.generate_text(
                system_role=system_role,
                prompt=cur_prompt,
                temperature=temperature,
                top_p=top_p,
            )
            try:
                return self._extract_first_json_object(text)
            except Exception as e:
                last_err = e
                # 다음 시도에서 더 강하게 교정
                cur_prompt = (
                    f"{json_guard}\n\n"
                    f"[주의] 직전 출력은 JSON 형식이 아닙니다. JSON 객체만 다시 출력하세요.\n\n"
                    f"{prompt}"
                )

        raise last_err if last_err else ValueError("JSON 생성 실패")
