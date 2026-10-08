from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import httpx


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 3) -> list[dict[str, str]]: ...


class WikipediaSearch:
    """Keyless web fallback using the public MediaWiki search API."""

    endpoint = "https://en.wikipedia.org/w/api.php"

    def search(self, query: str, limit: int = 3) -> list[dict[str, str]]:
        response = httpx.get(
            self.endpoint,
            params={"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json", "origin": "*"},
            headers={"User-Agent": "ai-tutor-agent/1.0 (educational project)"},
            timeout=5.0,
        )
        response.raise_for_status()
        return [
            {
                "title": item["title"],
                "snippet": item["snippet"].replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                "url": f'https://en.wikipedia.org/wiki/{item["title"].replace(" ", "_")}',
            }
            for item in response.json()["query"]["search"]
        ]


class FallbackAuditLogger:
    def __init__(self, path: Path | None = None):
        self.path = path or Path("logs/web_fallback.jsonl")

    def log(self, *, query: str, trace_id: str, status: str, result_count: int,
            error: str | None = None, provider: str = "wikipedia") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "query": query,
            "provider": provider,
            "status": status,
            "result_count": result_count,
            "error": error,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
