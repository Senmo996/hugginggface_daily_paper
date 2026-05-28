from __future__ import annotations

import time
from typing import Any

import httpx

from .storage import ProjectPaths, write_json


HF_BASE_URL = "https://huggingface.co"


def build_http_client() -> httpx.Client:
    return httpx.Client(base_url=HF_BASE_URL, timeout=30.0)


class DailyFetcher:
    def __init__(
        self,
        paths: ProjectPaths,
        client: httpx.Client | None = None,
        *,
        retries: int = 3,
    ) -> None:
        self.paths = paths
        self.client = client or build_http_client()
        self.retries = retries

    def fetch(self, date: str) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.client.get("/api/daily_papers", params={"date": date})
                response.raise_for_status()
                payload = response.json()
                write_json(self.paths.raw_dir / f"{date}.json", payload)
                return payload
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == self.retries:
                    break
                time.sleep(0.5 * attempt)
        raise RuntimeError(f"Failed to fetch Hugging Face daily papers for {date}: {last_error}")
