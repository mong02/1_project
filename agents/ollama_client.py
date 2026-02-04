# Ollama 호출 공통 함수 
# 에러 처리
# 모델 설정
# 중요! AI 호출은 여기서만!

# ollama_client.py
import json
import re
from typing import Any, Dict, Optional

import ollama
from config import MODEL_TEXT


class OllamaClient:
    def __init__(self, model: str = MODEL_TEXT):
        self.model = model

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