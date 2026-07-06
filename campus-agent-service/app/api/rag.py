import logging

from fastapi import APIRouter, Depends, Query

from app.db.session import get_db, AsyncSession
from app.schemas.rag import (
    RAGSearchRequest,
    RAGSearchResponse,
    RAGChunkResult,
    KnowledgeImportRequest,
    KnowledgeImportResponse,
    KnowledgeListResponse,
    KnowledgeDocItem,
    DomainStatsResponse,
)
from app.services.rag_service import (
    search_knowledge,
    import_knowledge_doc,
    import_knowledge_batch,
    import_seed_knowledge,
    list_knowledge_docs,
    get_domain_stats,
)
from app.chains.rag_answer_chain import generate_rag_answer
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=RAGSearchResponse)
async def rag_search(req: RAGSearchRequest, db: AsyncSession = Depends(get_db)):
    """Phase 4: enhanced search with source_url, section, and agent_name in results."""
    chunks = await search_knowledge(
        db=db,
        query=req.query,
        agent_name=req.agent_name or "",
        top_k=req.top_k,
    )

    results = [
        RAGChunkResult(
            doc_id=c["doc_id"],
            doc_title=c["doc_title"],
            chunk_index=c["chunk_index"],
            content=c["content"],
            score=c["score"],
            source_url=c.get("source_url", ""),
            section=c.get("section", ""),
            agent_name=c.get("agent_name", ""),
        )
        for c in chunks
    ]

    answer = None
    try:
        answer = await generate_rag_answer(
            query=req.query,
            context_chunks=[c["content"] for c in chunks],
        )
    except LLMNotConfiguredError:
        answer = LLM_NOT_CONFIGURED_MSG

    return RAGSearchResponse(
        query=req.query,
        results=results,
        answer=answer,
        total_results=len(results),
    )


# ── Phase 4: Knowledge Management APIs ──

@router.post("/import", response_model=KnowledgeImportResponse)
async def import_knowledge(req: KnowledgeImportRequest, db: AsyncSession = Depends(get_db)):
    """Import a single knowledge document."""
    doc_id = await import_knowledge_doc(
        db=db,
        title=req.title,
        content=req.content,
        agent_name=req.agent_name or "",
        source_url=req.source_url,
        source_type=req.source_type or "manual",
    )
    return KnowledgeImportResponse(doc_id=doc_id, status="imported")


@router.post("/import-batch", response_model=KnowledgeImportResponse)
async def import_knowledge_batch_api(req: list[KnowledgeImportRequest], db: AsyncSession = Depends(get_db)):
    """Batch import knowledge documents. Phase 4."""
    docs = [
        {
            "title": d.title,
            "content": d.content,
            "agent_name": d.agent_name or "",
            "source_url": d.source_url,
            "source_type": d.source_type or "bulk_import",
        }
        for d in req
    ]
    doc_ids = await import_knowledge_batch(db, docs)
    return KnowledgeImportResponse(
        doc_id=",".join(doc_ids),
        status=f"imported {len(doc_ids)} docs",
    )


@router.post("/seed", response_model=KnowledgeImportResponse)
async def seed_knowledge(
    agent_names: str = Query("", description="Comma-separated agent names, empty for all"),
    db: AsyncSession = Depends(get_db),
):
    """Import seed knowledge for agents. Phase 4.

    Example: POST /api/rag/seed?agent_names=teaching_agent,life_agent
    """
    names = [n.strip() for n in agent_names.split(",") if n.strip()] if agent_names else None
    result = await import_seed_knowledge(db, agent_names=names)
    total = sum(len(ids) for ids in result.values())
    return KnowledgeImportResponse(
        doc_id=str(result),
        status=f"seeded {total} docs across {len(result)} domains",
    )


@router.get("/docs", response_model=KnowledgeListResponse)
async def list_docs(
    agent_name: str = Query("", description="Filter by agent name"),
    db: AsyncSession = Depends(get_db),
):
    """List knowledge documents. Phase 4."""
    docs = await list_knowledge_docs(db, agent_name=agent_name)
    return KnowledgeListResponse(
        docs=[KnowledgeDocItem(**d) for d in docs],
        total=len(docs),
    )


@router.get("/stats", response_model=DomainStatsResponse)
async def domain_stats(db: AsyncSession = Depends(get_db)):
    """Get knowledge domain statistics. Phase 4."""
    stats = await get_domain_stats(db)
    return DomainStatsResponse(stats=stats)
