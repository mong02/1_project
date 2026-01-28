import json
from typing import Dict, Any, List
from app.llm.ollama_client import OllamaClient
from app.agents.prompts import SYSTEM, build_strategy_prompt, build_hooks_prompt, build_post_prompt
from app.agents.safety import scan_risks

def _safe_json_loads(text: str) -> Dict[str, Any]:
    # LLM이 가끔 앞뒤 텍스트를 섞으니 JSON만 추출
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON 형태 응답을 받지 못했습니다.")
    return json.loads(text[start:end+1])

class SocialAgent:
    def __init__(self, client: OllamaClient):
        self.client = client

    async def run(self, req) -> Dict[str, Any]:
        # 1) 전략
        strategy_raw = await self.client.generate(build_strategy_prompt(req), system=SYSTEM)
        strategy = _safe_json_loads(strategy_raw)

        # 2) 후킹 후보
        hooks_raw = await self.client.generate(build_hooks_prompt(req, json.dumps(strategy, ensure_ascii=False)), system=SYSTEM)
        hooks = _safe_json_loads(hooks_raw).get("hooks", [])
        if not hooks:
            hooks = ["지금 겪는 불편, 의외로 간단히 해결할 수 있습니다."]

        # 3) 캠페인 생성 (채널별 x 시퀀스)
        campaign_items: List[Dict[str, Any]] = []
        for i in range(req.campaign_size):
            hook = hooks[i % len(hooks)]
            for ch in req.channels:
                post_raw = await self.client.generate(
                    build_post_prompt(req, json.dumps(strategy, ensure_ascii=False), hook, ch, i),
                    system=SYSTEM,
                    options={"temperature": 0.7}
                )
                post = _safe_json_loads(post_raw)
                joined_text = (post.get("title","") + "\n" + post.get("body","")).strip()
                flags = scan_risks(joined_text, req.banned_words)
                post["risk_flags"] = flags
                post["channel"] = ch
                campaign_items.append(post)

        return {
            "strategy": strategy,
            "campaign": campaign_items
        }
