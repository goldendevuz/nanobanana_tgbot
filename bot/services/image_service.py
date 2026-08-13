"""Async client for the Kie.ai image generation jobs API."""

import json
import logging
from typing import Any, Optional

import aiohttp
from django.conf import settings

logger = logging.getLogger(__name__)

API_CREATE = "https://api.kie.ai/api/v1/jobs/createTask"
API_STATUS = "https://api.kie.ai/api/v1/jobs/recordInfo"

_http_session: Optional[aiohttp.ClientSession] = None


async def get_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Authorization": f"Bearer {settings.KIE_API_KEY}"},
        )
    return _http_session


async def close_session() -> None:
    global _http_session
    if _http_session is not None and not _http_session.closed:
        await _http_session.close()
    _http_session = None


async def create_generation_task(prompt: str, image_size: str = "1:1") -> str:
    """Submit a generation job and return its task id."""
    if not settings.KIE_API_KEY:
        raise RuntimeError("KIE_API_KEY is not set")

    session = await get_session()
    payload = {
        "model": settings.KIE_MODEL,
        "callBackUrl": settings.KIE_CALLBACK_URL,
        "input": {
            "prompt": prompt,
            "output_format": "png",
            "image_size": image_size,
        },
    }

    async with session.post(API_CREATE, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200 or data.get("code") != 200:
            # Log the status only — the response can echo back the user's prompt.
            reason = data.get("msg") or f"HTTP {resp.status}"
            logger.error("createTask failed: code=%s msg=%s", data.get("code"), reason)
            raise RuntimeError(reason)
        return data["data"]["taskId"]


async def query_task_status(task_id: str) -> dict[str, Any]:
    """Fetch the current state of a generation job."""
    session = await get_session()
    async with session.get(API_STATUS, params={"taskId": task_id}) as resp:
        return await resp.json()


def extract_result_url(data: dict[str, Any]) -> str:
    """Pull the first result URL out of the API's stringified resultJson."""
    try:
        result_json = json.loads(data.get("resultJson") or "{}")
    except json.JSONDecodeError:
        logger.warning("Could not decode resultJson: %r", data.get("resultJson"))
        return ""
    urls = result_json.get("resultUrls") or []
    return urls[0] if urls else ""
