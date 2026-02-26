import logging
import os
from typing import List, Optional
import aiohttp

logger = logging.getLogger(__name__)

API_CREATE = "https://api.kie.ai/api/v1/jobs/createTask"
API_STATUS = "https://api.kie.ai/api/v1/jobs/recordInfo"

KIE_API_KEY = os.getenv("KIE_API_KEY")

if not KIE_API_KEY:
    raise RuntimeError("KIE_API_KEY is not set")

KIE_MODEL = os.getenv("KIE_MODEL", "google/nano-banana")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://example.com/api/callback")

http_session: Optional[aiohttp.ClientSession] = None

async def _session() -> aiohttp.ClientSession:
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()
    return http_session


async def create_generation_task(prompt: str, image_size: str = "1:1") -> str:
    s = await _session()
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KIE_API_KEY}"
    }

    payload = {
        "model": KIE_MODEL,
        "callBackUrl": CALLBACK_URL,
        "input": {
            "prompt": prompt,
            "output_format": "png",
            "image_size": image_size
        }
    }

    async with s.post(API_CREATE, headers=headers, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200 or data.get("code") != 200:
            logger.error("CreateTask error %s", data)
            raise RuntimeError(f"CreateTask error: {data}")
        return data["data"]["taskId"]
    

async def query_task_status(task_id: str) -> dict:
    s = await _session()
    headers = {"Authorization": f"Bearer {KIE_API_KEY}"}
    params = {"taskId": task_id}
    async with s.get(API_STATUS, headers=headers, params=params) as resp:
        return await resp.json()
