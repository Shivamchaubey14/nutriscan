"""Async client for the inference microservice — non-blocking so a slow model
call never ties up the worker (SRS §7 async requirement)."""

from typing import Any

import httpx
from django.conf import settings


async def classify(image_bytes: bytes, filename: str, top_k: int = 3) -> dict[str, Any]:
    url = settings.INFERENCE_URL.rstrip("/") + "/predict"
    async with httpx.AsyncClient(timeout=settings.INFERENCE_TIMEOUT) as client:
        response = await client.post(
            url,
            files={"image": (filename, image_bytes, "application/octet-stream")},
            params={"top_k": top_k},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    return data
