from __future__ import annotations

from typing import Any


def normalize_daily_response(raw: Any, daily_date: str) -> list[dict[str, Any]]:
    items = _extract_items(raw)
    papers: list[dict[str, Any]] = []
    for item in items:
        paper = item.get("paper", item)
        paper_id = str(paper.get("id", "")).strip()
        if not paper_id:
            continue
        organization = paper.get("organization") or item.get("organization") or {}
        institution = organization.get("fullname") or organization.get("name") or None
        papers.append(
            {
                "id": paper_id,
                "daily_date": daily_date,
                "title": paper.get("title", ""),
                "summary": paper.get("summary", ""),
                "authors": _author_names(paper.get("authors") or []),
                "published_at": paper.get("publishedAt") or item.get("publishedAt"),
                "submitted_on_daily_at": paper.get("submittedOnDailyAt"),
                "upvotes": paper.get("upvotes") or item.get("upvotes") or 0,
                "num_comments": item.get("numComments") or paper.get("numComments") or 0,
                "ai_keywords": paper.get("ai_keywords") or item.get("ai_keywords") or [],
                "institution": institution,
                "hf_url": f"https://huggingface.co/papers/{paper_id}",
                "arxiv_url": f"https://arxiv.org/abs/{paper_id}",
                "project_page": paper.get("projectPage") or item.get("projectPage"),
                "github_repo": paper.get("githubRepo") or item.get("githubRepo"),
                "thumbnail": item.get("thumbnail") or paper.get("thumbnail"),
            }
        )
    return papers


def _extract_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        value = raw.get("value")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _author_names(authors: list[dict[str, Any]]) -> list[str]:
    names = []
    for author in authors:
        name = author.get("name")
        if name:
            names.append(str(name))
    return names
