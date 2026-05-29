from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .storage import ProjectPaths, read_json, write_json


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATES_DIR = PACKAGE_DIR / "default_templates"
DEFAULT_STATIC_DIR = PACKAGE_DIR / "default_static"
TAG_LIMIT = 20


class SiteBuilder:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths
        self.env = Environment(
            loader=FileSystemLoader(
                [str(paths.templates_dir), str(DEFAULT_TEMPLATES_DIR)]
            ),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["author_list"] = author_list

    def build(self) -> None:
        daily_payloads = self._load_daily_payloads()
        topic_aliases = self._load_topic_aliases()
        institution_aliases = self._load_institution_aliases()
        tag_overrides = self._load_tag_overrides()
        papers = [
            _apply_tag_overrides(
                _apply_institution_alias(
                    _apply_topic_alias(paper, topic_aliases),
                    institution_aliases,
                ),
                tag_overrides,
            )
            for payload in daily_payloads
            for paper in payload.get("papers", [])
        ]
        dates = [payload["date"] for payload in daily_payloads]
        latest_payload = daily_payloads[0] if daily_payloads else {"date": None, "papers": []}
        topic_counts = Counter(paper.get("topic_tag") for paper in papers if paper.get("topic_tag"))
        institution_counts = Counter(
            paper.get("institution_tag")
            for paper in papers
            if _is_public_institution_tag(paper.get("institution_tag"))
        )
        topic_tags = _top_tags(topic_counts)
        institution_tags = _top_tags(institution_counts)

        if self.paths.site_dir.exists():
            shutil.rmtree(self.paths.site_dir)
        (self.paths.site_dir / "assets").mkdir(parents=True, exist_ok=True)

        self._copy_static_assets()

        index_template = self.env.get_template("index.html")
        matrix_template = self.env.get_template("matrix.html")
        topics_template = self.env.get_template("topics.html")
        all_topics = [
            {"name": tag, "count": count}
            for tag, count in sorted(
                topic_counts.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ]

        (self.paths.site_dir / "index.html").write_text(
            index_template.render(
                dates=dates,
                papers=papers,
                all_papers=papers,
                latest_date=latest_payload.get("date"),
                topic_tags=topic_tags,
                institution_tags=institution_tags,
                counts={
                    "topics": topic_counts,
                    "institutions": institution_counts,
                },
            ),
            encoding="utf-8",
        )

        (self.paths.site_dir / "matrix.html").write_text(
            matrix_template.render(
                dates=dates,
                papers=papers,
            ),
            encoding="utf-8",
        )

        (self.paths.site_dir / "topics.html").write_text(
            topics_template.render(
                dates=dates,
                papers=papers,
                topics=all_topics,
            ),
            encoding="utf-8",
        )

        write_json(
            self.paths.site_dir / "assets" / "papers.json",
            {
                "papers": papers,
                "dates": dates,
                "topic_tags": topic_tags,
                "institution_tags": institution_tags,
            },
        )

    def _load_daily_payloads(self) -> list[dict[str, Any]]:
        if not self.paths.daily_dir.exists():
            return []
        payloads = []
        for path in sorted(self.paths.daily_dir.glob("*.json"), reverse=True):
            payload = read_json(path)
            if payload and payload.get("papers"):
                payloads.append(payload)
        return payloads

    def _copy_static_assets(self) -> None:
        for static_dir in [DEFAULT_STATIC_DIR, self.paths.root / "static"]:
            if not static_dir.exists():
                continue
            for source in static_dir.iterdir():
                target = self.paths.site_dir / "assets" / source.name
                if source.is_file():
                    shutil.copy2(source, target)

    def _load_topic_aliases(self) -> dict[str, str]:
        payload = read_json(self.paths.topic_aliases, {"aliases": {}})
        aliases = payload.get("aliases", {})
        if not isinstance(aliases, dict):
            return {}
        return {
            _normalize_topic(source): str(target).strip()
            for source, target in aliases.items()
            if str(source).strip() and str(target).strip()
        }

    def _load_institution_aliases(self) -> dict[str, str]:
        payload = read_json(self.paths.institution_aliases, {"aliases": {}})
        aliases = payload.get("aliases", {})
        if not isinstance(aliases, dict):
            return {}
        return {
            _normalize_topic(source): str(target).strip()
            for source, target in aliases.items()
            if str(source).strip() and str(target).strip()
        }

    def _load_tag_overrides(self) -> dict[str, dict[str, str]]:
        payload = read_json(self.paths.tag_overrides, {"paper_overrides": {}})
        overrides = payload.get("paper_overrides", {})
        if not isinstance(overrides, dict):
            return {}
        normalized: dict[str, dict[str, str]] = {}
        for paper_id, fields in overrides.items():
            if not str(paper_id).strip() or not isinstance(fields, dict):
                continue
            clean_fields = {
                field: str(fields[field]).strip()
                for field in ["institution_tag", "topic_tag"]
                if str(fields.get(field, "")).strip()
            }
            if clean_fields:
                normalized[str(paper_id).strip()] = clean_fields
        return normalized


def author_list(authors: list[str], limit: int = 3) -> str:
    if not authors:
        return "Unknown authors"
    if len(authors) <= limit:
        return ", ".join(authors)
    return f"{', '.join(authors[:limit])}, +{len(authors) - limit} more"


def _top_tags(counts: Counter[str]) -> list[str]:
    return [
        tag
        for tag, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )[:TAG_LIMIT]
    ]


def _is_public_institution_tag(tag: Any) -> bool:
    return bool(tag) and str(tag).strip().casefold() != "unknown"


def _apply_topic_alias(paper: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    topic = paper.get("topic_tag")
    canonical = aliases.get(_normalize_topic(topic))
    if not canonical:
        return dict(paper)
    return {
        **paper,
        "topic_tag": canonical,
        "original_topic_tag": topic,
    }


def _apply_institution_alias(paper: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    institution = paper.get("institution_tag")
    canonical = aliases.get(_normalize_topic(institution))
    if not canonical:
        return dict(paper)
    return {
        **paper,
        "institution_tag": canonical,
        "original_institution_tag": institution,
    }


def _apply_tag_overrides(
    paper: dict[str, Any],
    overrides: dict[str, dict[str, str]],
) -> dict[str, Any]:
    paper_id = str(paper.get("id", "")).strip()
    override = overrides.get(paper_id)
    if not override:
        return dict(paper)

    updated = dict(paper)
    if "institution_tag" in override and override["institution_tag"] != paper.get("institution_tag"):
        updated["original_institution_tag"] = paper.get("institution_tag")
        updated["institution_tag"] = override["institution_tag"]
    if "topic_tag" in override and override["topic_tag"] != paper.get("topic_tag"):
        updated.setdefault("original_topic_tag", paper.get("topic_tag"))
        updated["topic_tag"] = override["topic_tag"]
    return updated


def _normalize_topic(topic: Any) -> str:
    return " ".join(str(topic or "").strip().casefold().split())
