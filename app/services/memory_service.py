import json
from typing import Optional
import redis.asyncio as aioredis

from app.config.settings import get_settings


class MemoryService:
    """Redis 会话状态管理服务。

    存储会话临时状态、任务草稿缓存，预留异步任务和限流能力。
    """

    def __init__(self):
        settings = get_settings()
        self._redis: aioredis.Redis | None = None
        self._redis_url = settings.redis_url

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def set_session_state(self, session_id: str, key: str, value: dict, ttl: int = 3600) -> None:
        redis = await self._get_redis()
        full_key = f"session:{session_id}:{key}"
        await redis.set(full_key, json.dumps(value, ensure_ascii=False), ex=ttl)

    async def get_session_state(self, session_id: str, key: str) -> Optional[dict]:
        redis = await self._get_redis()
        full_key = f"session:{session_id}:{key}"
        data = await redis.get(full_key)
        return json.loads(data) if data else None

    async def delete_session(self, session_id: str) -> None:
        redis = await self._get_redis()
        pattern = f"session:{session_id}:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

    async def cache_task_draft(self, draft_id: str, draft_data: dict, ttl: int = 7200) -> None:
        redis = await self._get_redis()
        key = f"task_draft:{draft_id}"
        await redis.set(key, json.dumps(draft_data, ensure_ascii=False), ex=ttl)

    async def get_task_draft(self, draft_id: str) -> Optional[dict]:
        redis = await self._get_redis()
        key = f"task_draft:{draft_id}"
        data = await redis.get(key)
        return json.loads(data) if data else None

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None


memory_service = MemoryService()
