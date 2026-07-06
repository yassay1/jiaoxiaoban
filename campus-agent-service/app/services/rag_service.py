"""Real RAG service using pgvector + OpenAI embeddings.

Phase 4: improved chunking, batch import, source citation, and anti-fabrication.
"""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.config.settings import get_settings
from app.services.llm_service import check_llm_configured, _should_trust_env

logger = logging.getLogger(__name__)


async def _get_embedding(text: str) -> list[float]:
    """使用 OpenAI embeddings 获取文本向量。"""
    import httpx
    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        http_client=httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds,
            trust_env=_should_trust_env(settings),
        ),
    )
    resp = await client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


# ── Smart Chunking ──

def _smart_chunk_text(content: str, max_chunk_size: int = 800, overlap_lines: int = 1) -> list[dict]:
    """Split document content into overlapping chunks by section headers and paragraphs.

    Returns list of {content, section_title, chunk_index}.
    """
    lines = content.strip().split("\n")
    chunks: list[dict] = []
    current_section = ""
    current_chunk_lines: list[str] = []
    current_len = 0
    idx = 0

    section_re = re.compile(r"^#{1,3}\s+(.+)$|^(.+)[：:]\s*$|^\d+[\.\、\)]\s*(.+)$")

    def flush_chunk():
        nonlocal idx
        if current_chunk_lines:
            chunk_text = "\n".join(current_chunk_lines).strip()
            if len(chunk_text) >= 20:  # Accept shorter but non-empty chunks
                chunks.append({
                    "content": chunk_text,
                    "section_title": current_section,
                    "chunk_index": idx,
                })
                idx += 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_len > 0:
                current_chunk_lines.append("")
                current_len += 1
            continue

        # Detect section headers
        section_match = section_re.match(stripped)
        if section_match and len(stripped) < 80 and not stripped.startswith("-"):
            flush_chunk()
            current_section = stripped.rstrip("：:")
            current_chunk_lines = []
            current_len = 0
            continue

        current_chunk_lines.append(stripped)
        current_len += len(stripped)

        if current_len >= max_chunk_size:
            flush_chunk()
            # Overlap: keep last N lines for context continuity
            overlap = current_chunk_lines[-overlap_lines:] if overlap_lines > 0 and len(current_chunk_lines) > overlap_lines else []
            current_chunk_lines = list(overlap)
            current_len = sum(len(l) for l in current_chunk_lines)

    flush_chunk()
    return chunks


# ── Search ──

async def search_knowledge(
    db: AsyncSession,
    query: str,
    agent_name: str = "",
    top_k: int = 5,
    min_score: float = 0.5,
) -> list[dict]:
    """向量检索知识库，按 agent_name 过滤。

    Phase 4: lower min_score threshold and return richer metadata with source_url.
    """
    if not check_llm_configured():
        logger.warning("LLM not configured, RAG search skipped")
        return []

    try:
        embedding = await _get_embedding(query)
    except Exception as e:
        logger.error("Failed to get embedding: %s", e)
        return []

    try:
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
        stmt = text("""
            SELECT
                kc.id,
                kc.content,
                kc.chunk_index,
                kd.title AS doc_title,
                kd.source_url,
                kd.source_type,
                kd.agent_name,
                kc.metadata,
                1 - (kc.embedding <=> CAST(:vec AS vector)) AS similarity
            FROM knowledge_chunks kc
            JOIN knowledge_docs kd ON kc.doc_id = kd.id
            WHERE (:agent = '' OR kd.agent_name = :agent)
              AND kd.status = 'active'
            ORDER BY kc.embedding <=> CAST(:vec2 AS vector)
            LIMIT :limit
        """)
        result = await db.execute(stmt, {
            "vec": vector_str,
            "vec2": vector_str,
            "agent": agent_name,
            "limit": top_k,
        })
        rows = result.fetchall()

        return [
            {
                "doc_id": row.id,
                "doc_title": row.doc_title,
                "source_url": row.source_url,
                "source_type": row.source_type,
                "agent_name": row.agent_name,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "section": (row.metadata.get("section_title") if row.metadata else None) or "",
                "score": round(float(row.similarity), 4),
            }
            for row in rows
            if row.similarity is not None and float(row.similarity) > min_score
        ]
    except Exception as e:
        logger.error("RAG search failed: %s", e)
        return []


# ── Import ──

async def import_knowledge_doc(
    db: AsyncSession,
    title: str,
    content: str,
    agent_name: str = "",
    source_url: str | None = None,
    source_type: str = "manual",
    generate_embeddings: bool = True,
) -> str:
    """导入知识文档并使用智能分块（Phase 4: section-aware chunking）。"""
    import uuid
    from app.db.models import KnowledgeDoc, KnowledgeChunk

    doc_id = str(uuid.uuid4())
    doc = KnowledgeDoc(
        id=doc_id,
        title=title,
        source_type=source_type,
        source_url=source_url,
        agent_name=agent_name,
        status="active",
    )
    db.add(doc)

    # Phase 4: use smart chunking instead of simple paragraph split
    chunks_data = _smart_chunk_text(content)
    if not chunks_data:
        # Fallback: simple paragraph split
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunks_data = [
            {"content": p, "section_title": "", "chunk_index": i}
            for i, p in enumerate(paragraphs)
        ]

    for cdata in chunks_data:
        chunk = KnowledgeChunk(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            chunk_index=cdata["chunk_index"],
            content=cdata["content"],
            metadata_={"section_title": cdata.get("section_title", "")},
        )
        db.add(chunk)

        if generate_embeddings and check_llm_configured():
            try:
                chunk.embedding = await _get_embedding(cdata["content"])
            except Exception as e:
                logger.warning("Embedding generation failed for chunk %d: %s", cdata["chunk_index"], e)

    await db.flush()
    logger.info("Imported doc '%s' with %d chunks (agent=%s)", title, len(chunks_data), agent_name)
    return doc_id


async def import_knowledge_batch(
    db: AsyncSession,
    docs: list[dict],
    generate_embeddings: bool = True,
) -> list[str]:
    """批量导入知识文档。Phase 4: batch import for seed data.

    Each doc dict: {title, content, agent_name, source_url?, source_type?}
    """
    doc_ids: list[str] = []
    for doc_data in docs:
        doc_id = await import_knowledge_doc(
            db=db,
            title=doc_data["title"],
            content=doc_data["content"],
            agent_name=doc_data.get("agent_name", ""),
            source_url=doc_data.get("source_url"),
            source_type=doc_data.get("source_type", "bulk_import"),
            generate_embeddings=generate_embeddings,
        )
        doc_ids.append(doc_id)
    logger.info("Batch imported %d docs", len(doc_ids))
    return doc_ids


async def import_seed_knowledge(
    db: AsyncSession,
    agent_names: list[str] | None = None,
    generate_embeddings: bool = True,
) -> dict[str, list[str]]:
    """Import seed knowledge for specified agents (or all if None). Phase 4."""
    from app.db.seed_data.knowledge_seeds import ALL_SEEDS

    result: dict[str, list[str]] = {}
    targets = agent_names or list(ALL_SEEDS.keys())

    for agent_name in targets:
        seeds = ALL_SEEDS.get(agent_name, [])
        if not seeds:
            result[agent_name] = []
            continue
        doc_ids = await import_knowledge_batch(db, [
            {**s, "agent_name": agent_name} for s in seeds
        ], generate_embeddings=generate_embeddings)
        result[agent_name] = doc_ids

    return result


# ── Document Management ──

async def list_knowledge_docs(
    db: AsyncSession,
    agent_name: str = "",
    status: str = "active",
) -> list[dict]:
    """列出知识文档。Phase 4: document management."""
    from app.db.models import KnowledgeDoc

    stmt = select(KnowledgeDoc).where(KnowledgeDoc.status == status)
    if agent_name:
        stmt = stmt.where(KnowledgeDoc.agent_name == agent_name)
    stmt = stmt.order_by(KnowledgeDoc.updated_at.desc()).limit(100)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "agent_name": doc.agent_name,
            "source_type": doc.source_type,
            "source_url": doc.source_url,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }
        for doc in docs
    ]


async def get_domain_stats(db: AsyncSession) -> dict:
    """Get knowledge domain statistics. Phase 4."""
    from app.db.models import KnowledgeDoc
    from sqlalchemy import func

    stmt = (
        select(KnowledgeDoc.agent_name, func.count().label("count"))
        .where(KnowledgeDoc.status == "active")
        .group_by(KnowledgeDoc.agent_name)
    )
    result = await db.execute(stmt)
    stats = {row.agent_name: row.count for row in result.fetchall()}
    stats["_total"] = sum(stats.values())
    return stats

