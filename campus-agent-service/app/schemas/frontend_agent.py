from pydantic import BaseModel, Field


class FrontendAgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    conversationId: str | None = None
    userId: str | None = None
    imageUrls: list[str] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)


class FrontendAgentChatResponse(BaseModel):
    agentId: str
    reply: str
    actions: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class FrontendMessageListResponse(BaseModel):
    messages: list[dict]
    total: int
