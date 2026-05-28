from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Callable
from typing import Any, Protocol

from .llm import LLMGeneration
from .normalize import normalize_daily_response
from .storage import ProjectPaths, read_json, write_json
from .tags import TagStore


class LLMClient(Protocol):
    def generate_metadata(
        self,
        paper: dict[str, Any],
        existing_topics: list[str],
        known_institution: str | None,
    ) -> LLMGeneration:
        ...


class DailyGenerator:
    def __init__(self, paths: ProjectPaths, llm_client: LLMClient) -> None:
        self.paths = paths
        self.llm_client = llm_client
        self.tags = TagStore(paths)

    def generate(
        self,
        date: str,
        *,
        force: bool = False,
        reset_topic_tags: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        raw_path = self.paths.raw_dir / f"{date}.json"
        raw = read_json(raw_path)
        if raw is None:
            raise RuntimeError(f"Raw data not found for {date}. Run fetch first.")

        previous = read_json(self.paths.daily_dir / f"{date}.json", {"papers": []})
        previous_by_id = {paper["id"]: paper for paper in previous.get("papers", [])}
        generated_papers: list[dict[str, Any]] = []
        papers = normalize_daily_response(raw, daily_date=date)
        total = len(papers)
        if reset_topic_tags:
            self.tags.reset_topics()

        for index, paper in enumerate(papers, start=1):
            if not force and paper["id"] in previous_by_id:
                if progress:
                    progress(f"Skipping existing {index}/{total}: {paper['id']} - {paper['title']}")
                generated_papers.append(previous_by_id[paper["id"]])
                self._write_result(date, generated_papers, status="partial")
                continue

            if progress:
                progress(f"Generating {index}/{total}: {paper['id']} - {paper['title']}")
            known_institution = paper.get("institution")
            generation = self.llm_client.generate_metadata(
                paper,
                self.tags.topic_names(),
                known_institution,
            )
            institution_tag = known_institution or generation.institution_tag or "Unknown"
            topic_tag = generation.topic_tag
            enriched = {
                **paper,
                "one_sentence_summary": generation.one_sentence_summary,
                "institution_tag": institution_tag,
                "topic_tag": topic_tag,
                "model_metadata": {
                    "topic_is_new": generation.topic_is_new,
                    "generated_at": _now(),
                },
            }
            generated_papers.append(enriched)
            self.tags.record_institution(institution_tag, paper["id"])
            self.tags.record_topic(
                topic_tag,
                generation.topic_description,
                paper["id"],
            )
            self._write_result(date, generated_papers, status="partial")

        result = self._write_result(date, generated_papers, status="complete")
        return result

    def _write_result(
        self,
        date: str,
        papers: list[dict[str, Any]],
        *,
        status: str,
    ) -> dict[str, Any]:
        result = {
            "date": date,
            "generated_at": _now(),
            "status": status,
            "paper_count": len(papers),
            "papers": papers,
        }
        write_json(self.paths.daily_dir / f"{date}.json", result)
        return result


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
