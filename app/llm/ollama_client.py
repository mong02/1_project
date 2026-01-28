import httpx
from typing import Any, Dict, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", default_model: str = "gemma3:4b"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model  # ✅ 이게 없어서 터졌던 것

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        payload = {
            "model": model or self.default_model,  # ✅ 요청 모델 우선, 없으면 기본 모델
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{self.base_url}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "").strip()
