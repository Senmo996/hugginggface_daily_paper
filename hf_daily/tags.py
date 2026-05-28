from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .storage import ProjectPaths, read_json, write_json


class TagStore:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths
        self.paths.ensure_data_dirs()

    def topic_names(self) -> list[str]:
        return [topic["name"] for topic in self.load_topics()]

    def load_topics(self) -> list[dict[str, Any]]:
        payload = read_json(self.paths.topic_tags, {"topics": []})
        return payload.get("topics", [])

    def load_institutions(self) -> list[dict[str, Any]]:
        payload = read_json(self.paths.institution_tags, {"institutions": []})
        return payload.get("institutions", [])

    def reset_topics(self) -> None:
        write_json(self.paths.topic_tags, {"topics": []})

    def record_topic(
        self,
        name: str,
        description: str,
        paper_id: str,
        *,
        created_at: str | None = None,
    ) -> None:
        normalized = _normalize_tag(name)
        topics = self.load_topics()
        for topic in topics:
            if _normalize_tag(topic["name"]) == normalized:
                topic["usage_count"] = int(topic.get("usage_count", 0)) + 1
                examples = topic.setdefault("examples", [])
                if paper_id not in examples:
                    examples.append(paper_id)
                write_json(self.paths.topic_tags, {"topics": _sort_tags(topics)})
                return

        topics.append(
            {
                "name": name.strip(),
                "description": description.strip(),
                "created_at": created_at or _now(),
                "usage_count": 1,
                "examples": [paper_id],
            }
        )
        write_json(self.paths.topic_tags, {"topics": _sort_tags(topics)})

    def record_institution(self, name: str, paper_id: str) -> None:
        normalized = _normalize_tag(name)
        institutions = self.load_institutions()
        for institution in institutions:
            if _normalize_tag(institution["name"]) == normalized:
                institution["usage_count"] = int(institution.get("usage_count", 0)) + 1
                examples = institution.setdefault("examples", [])
                if paper_id not in examples:
                    examples.append(paper_id)
                write_json(
                    self.paths.institution_tags,
                    {"institutions": _sort_tags(institutions)},
                )
                return

        institutions.append(
            {
                "name": name.strip(),
                "created_at": _now(),
                "usage_count": 1,
                "examples": [paper_id],
            }
        )
        write_json(
            self.paths.institution_tags,
            {"institutions": _sort_tags(institutions)},
        )


def _sort_tags(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(tags, key=lambda tag: tag["name"].casefold())


def _normalize_tag(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
