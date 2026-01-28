from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict
from typing import Optional

Channel = Literal["instagram", "thread", "blog", "linkedin"]
Goal = Literal["promo", "announce", "traffic", "engage", "recruit"]
Tone = Literal["casual", "formal", "humorous", "calm", "friendly"]

class BrandVoice(BaseModel):
    name: str = "default"
    rules: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

class PostRequest(BaseModel):
    product_name: str
    target: str
    pain_point: str
    solution: str
    differentiators: List[str] = Field(default_factory=list)
    proof: List[str] = Field(default_factory=list)  # 수치/후기/인증
    cta: str
    banned_words: List[str] = Field(default_factory=list)
    channels: List[Channel] = Field(default_factory=lambda: ["instagram", "thread", "blog", "linkedin"])
    goal: Goal = "promo"
    tone: Tone = "friendly"
    campaign_size: int = 10
    hook_variants: int = 10
    brand_voice: Optional[BrandVoice] = None
    model: Optional[str] = "gemma3:4b"

class PostItem(BaseModel):
    channel: Channel
    title: str
    body: str
    hashtags: List[str]
    story_captions: List[str]
    comment_prompts: List[str]
    risk_flags: List[str] = Field(default_factory=list)

class PostResponse(BaseModel):
    strategy: Dict[str, str]
    campaign: List[PostItem]
