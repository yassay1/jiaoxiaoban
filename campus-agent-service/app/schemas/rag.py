from pydantic import BaseModel, Field
from typing import Optional


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048)
    agent_name: Optional[str] = Field(None, description="限定搜索的 Agent 知识库范围")
    top_k: int = Field(default=5, ge=1, le=20)


class RAGChunkResult(BaseModel):
    doc_id: str
    doc_title: str
    chunk_index: int
    content: str
    score: float
    source_url: str = ""
    section: str = ""
    agent_name: str = ""


class RAGSearchResponse(BaseModel):
    query: str
    results: list[RAGChunkResult]
    answer: Optional[str] = Field(None, description="LLM 基于检索结果生成的回答")
    total_results: int = 0


# ── Phase 4: Knowledge Management Schemas ──

class KnowledgeImportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    agent_name: Optional[str] = Field("", description="所属 Agent 知识域")
    source_url: Optional[str] = Field(None)
    source_type: Optional[str] = Field("manual")


class KnowledgeImportResponse(BaseModel):
    doc_id: str
    status: str


class KnowledgeDocItem(BaseModel):
    id: str
    title: str
    agent_name: Optional[str] = ""
    source_type: str
    source_url: Optional[str] = ""
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KnowledgeListResponse(BaseModel):
    docs: list[KnowledgeDocItem]
    total: int


class DomainStatsResponse(BaseModel):
    stats: dict = Field(default_factory=dict)
