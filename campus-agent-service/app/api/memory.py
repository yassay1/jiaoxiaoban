"""Memory API — Phase 4 R5: long-term memory management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.session import get_db, AsyncSession
from app.services.long_term_memory_service import (
    save_user_memory,
    get_user_memories,
    delete_user_memory,
    format_memories_for_context,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryItem(BaseModel):
    id: str
    external_user_id: str
    memory_type: str
    content: str
    source: str | None = None
    importance: float = 0.5
    created_at: str | None = None
    updated_at: str | None = None


class MemoryListResponse(BaseModel):
    memories: list[MemoryItem]
    total: int
    context_text: str = ""


class MemoryCreateRequest(BaseModel):
    external_user_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    memory_type: str = "fact"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryDeleteResponse(BaseModel):
    deleted: bool
    memory_id: str


@router.get("/{external_user_id}", response_model=MemoryListResponse)
async def list_memories(
    external_user_id: str,
    memory_type: str = Query("", description="Filter by type: fact, preference, plan, note"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List user memories. Phase 4 R5."""
    mtype = memory_type if memory_type else None
    memories = await get_user_memories(db, external_user_id, memory_type=mtype, limit=limit)
    context_text = await format_memories_for_context(db, external_user_id, limit=limit)

    return MemoryListResponse(
        memories=[
            MemoryItem(
                id=m.id,
                external_user_id=m.external_user_id,
                memory_type=m.memory_type,
                content=m.content,
                source=m.source,
                importance=m.importance,
                created_at=m.created_at.isoformat() if m.created_at else None,
                updated_at=m.updated_at.isoformat() if m.updated_at else None,
            )
            for m in memories
        ],
        total=len(memories),
        context_text=context_text,
    )


@router.post("/", response_model=MemoryItem)
async def create_memory(req: MemoryCreateRequest, db: AsyncSession = Depends(get_db)):
    """Manually create a user memory. Phase 4 R5."""
    memory = await save_user_memory(
        db=db,
        external_user_id=req.external_user_id,
        content=req.content,
        memory_type=req.memory_type,
        importance=req.importance,
        source="manual",
    )
    return MemoryItem(
        id=memory.id,
        external_user_id=memory.external_user_id,
        memory_type=memory.memory_type,
        content=memory.content,
        source=memory.source,
        importance=memory.importance,
        created_at=memory.created_at.isoformat() if memory.created_at else None,
        updated_at=memory.updated_at.isoformat() if memory.updated_at else None,
    )


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def remove_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a user memory. Phase 4 R5."""
    deleted = await delete_user_memory(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryDeleteResponse(deleted=True, memory_id=memory_id)
