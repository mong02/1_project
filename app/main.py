from fastapi import FastAPI
from app.schemas import PostRequest, PostResponse
from app.llm.ollama_client import OllamaClient
from app.agents.orchestrator import SocialAgent

app = FastAPI(title="Social Media Auto Generator Agent")

client = OllamaClient(default_model="gemma3:4b")
agent = SocialAgent(client)

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/generate", response_model=PostResponse)
async def generate(req: PostRequest):
    result = await agent.run(req)
    return result
