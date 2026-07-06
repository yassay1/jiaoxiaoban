"""Community service HTTP client.

Phase 5 / P8: real community service HTTP client with retry, timeout,
and proper error handling. Supports the full CRUD interface needed by
the community agent subgraph.
"""

import logging
from dataclasses import dataclass, field

import httpx
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# ── Data models (duplicated here to avoid circular imports with adapter) ──


@dataclass
class HelpTaskSearchQuery:
    keyword: str = ""
    status: str | None = None
    category: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass
class HelpTaskItem:
    task_id: str
    title: str
    description: str = ""
    category: str | None = None
    external_user_id: str = ""
    status: str = "published"
    created_at: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class PublishHelpTaskResult:
    task_id: str
    status: str = "published"


@dataclass
class DeleteHelpTaskResult:
    task_id: str
    status: str = "deleted"


class CommunityServiceError(Exception):
    """Raised when the community service returns an error or is unreachable."""
    pass


class CommunityClient:
    """社区系统 API Client — Phase 5 P8: real HTTP adapter.

    Calls the external community service REST API.
    Supports retry on transient errors and structured error handling.
    """

    def __init__(self, max_retries: int = 2):
        settings = get_settings()
        self.base_url = settings.community_service_base_url.rstrip("/")
        self.api_key = settings.community_service_api_key
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make an HTTP request with retry logic."""
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json_data,
                    params=params,
                )
                response.raise_for_status()
                return response.json() if response.content else {}
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    "Community service connection failed (attempt %d/%d): %s",
                    attempt + 1, self.max_retries + 1, e,
                )
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(0.5 * (attempt + 1))
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors
                if 400 <= e.response.status_code < 500:
                    raise CommunityServiceError(
                        f"Community service returned {e.response.status_code}: {e.response.text[:200]}"
                    ) from e
                last_error = e
                logger.warning(
                    "Community service error (attempt %d/%d): %s",
                    attempt + 1, self.max_retries + 1, e,
                )
            except Exception as e:
                last_error = e
                logger.warning("Community request failed: %s", e)
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(0.5 * (attempt + 1))

        raise CommunityServiceError(
            f"Community service unreachable after {self.max_retries + 1} attempts: {last_error}"
        )

    # ── Task CRUD ──

    async def create_task(self, task_data: dict) -> dict:
        """POST /tasks — create a help task."""
        return await self._request("POST", "/tasks", json_data=task_data)

    async def search_tasks(self, query: HelpTaskSearchQuery) -> list[dict]:
        """GET /tasks — search help tasks."""
        params: dict[str, str | int] = {}
        if query.keyword:
            params["keyword"] = query.keyword
        if query.status:
            params["status"] = query.status
        if query.category:
            params["category"] = query.category
        params["limit"] = query.limit
        params["offset"] = query.offset
        result = await self._request("GET", "/tasks", params=params)
        return result.get("tasks", result.get("data", []))

    async def get_task(self, task_id: str) -> dict:
        """GET /tasks/{id} — get task detail."""
        return await self._request("GET", f"/tasks/{task_id}")

    async def delete_task(self, task_id: str, external_user_id: str) -> dict:
        """DELETE /tasks/{id} — delete a task."""
        return await self._request(
            "DELETE", f"/tasks/{task_id}",
            params={"external_user_id": external_user_id},
        )

    async def get_my_tasks(
        self, external_user_id: str, status: str | None = None
    ) -> list[dict]:
        """GET /users/{id}/tasks — get user's own tasks."""
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        result = await self._request(
            "GET", f"/users/{external_user_id}/tasks", params=params,
        )
        return result.get("tasks", result.get("data", []))

    # ── Post operations ──

    async def get_post(self, post_id: str) -> dict:
        """GET /posts/{id} — get post detail."""
        return await self._request("GET", f"/posts/{post_id}")

    async def get_user_info(self, external_user_id: str) -> dict:
        """GET /users/{id} — get user profile."""
        return await self._request("GET", f"/users/{external_user_id}")

    # ── Health ──

    async def health_check(self) -> bool:
        """Check if the community service is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/health")
            return resp.status_code < 500
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


community_client = CommunityClient()





