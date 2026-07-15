from __future__ import annotations

import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .storage import ProjectPaths, read_json, write_json


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATES_DIR = PACKAGE_DIR / "default_templates"
DEFAULT_STATIC_DIR = PACKAGE_DIR / "default_static"
TAG_LIMIT = 20
MATRIX_INSTITUTION_LIMIT = 40
MATRIX_GLOBAL_TOPIC_LIMIT = 20
MATRIX_LOCAL_TOPIC_LIMIT = 3
INDEX_FIELDS = [
    "id",
    "daily_date",
    "title",
    "authors",
    "one_sentence_summary",
    "institution_tag",
    "topic_tag",
    "original_institution_tag",
    "original_topic_tag",
    "hf_url",
    "arxiv_url",
    "project_page",
    "github_repo",
    "upvotes",
    "num_comments",
]


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
        self.env.filters["url_quote"] = lambda value: quote(str(value), safe="")

    def build(self) -> None:
        asset_version = _asset_version()
        daily_payloads = self._load_daily_payloads()
        topic_aliases = self._load_topic_aliases()
        institution_aliases = self._load_institution_aliases()
        tag_overrides = self._load_tag_overrides()
        priority_topics = self._load_priority_topics()
        papers: list[dict[str, Any]] = []
        papers_by_date: dict[str, list[dict[str, Any]]] = {}
        for payload in daily_payloads:
            for source_paper in payload.get("papers", []):
                paper = _apply_tag_overrides(
                    _apply_institution_alias(
                        _apply_topic_alias(source_paper, topic_aliases),
                        institution_aliases,
                    ),
                    tag_overrides,
                )
                papers.append(paper)
                paper_date = str(paper.get("daily_date") or "").strip()
                if paper_date:
                    papers_by_date.setdefault(paper_date, []).append(paper)
        dates = [payload["date"] for payload in daily_payloads]
        latest_payload = daily_payloads[0] if daily_payloads else {"date": None, "papers": []}
        latest_papers = papers_by_date.get(latest_payload.get("date"), [])
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
        (self.paths.site_dir / "assets" / "daily").mkdir(parents=True, exist_ok=True)

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
                papers=latest_papers,
                all_papers=papers,
                latest_date=latest_payload.get("date"),
                total_papers=len(papers),
                asset_version=asset_version,
                priority_topics=priority_topics,
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
                matrix_data=_build_institution_topic_matrix(papers),
                total_papers=len(papers),
                asset_version=asset_version,
            ),
            encoding="utf-8",
        )

        (self.paths.site_dir / "topics.html").write_text(
            topics_template.render(
                dates=dates,
                papers=papers,
                topics=all_topics,
                asset_version=asset_version,
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
        self._write_json_asset(
            self.paths.site_dir / "assets" / "papers-index",
            {
                "papers": [_paper_index_entry(paper) for paper in papers],
                "dates": dates,
                "topic_tags": topic_tags,
                "institution_tags": institution_tags,
            },
        )
        self._write_json_asset(
            self.paths.site_dir / "assets" / "tag-suggestions",
            {
                "institution_tag": self._load_tag_names(
                    self.paths.institution_tags,
                    "institutions",
                ),
                "topic_tag": self._load_tag_names(self.paths.topic_tags, "topics"),
            },
        )
        for payload in daily_payloads:
            date = str(payload.get("date", "")).strip()
            if not date:
                continue
            self._write_json_asset(
                self.paths.site_dir / "assets" / "daily" / date,
                {
                    "date": date,
                    "papers": papers_by_date.get(date, []),
                    "asset_version": asset_version,
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

    def _write_json_asset(self, base_path: Path, payload: dict[str, Any]) -> None:
        write_json(base_path.with_suffix(".json"), payload)
        js_payload = _json_to_js_payload(payload, base_path.name)
        base_path.with_suffix(".js").write_text(
            f"window.HFDailyData = window.HFDailyData || {{}};\n"
            f"window.HFDailyData[{js_payload['key']}] = {js_payload['value']};\n",
            encoding="utf-8",
        )

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

    def _load_priority_topics(self) -> list[str]:
        payload = read_json(self.paths.priority_topics, {"topics": []})
        topics = payload.get("topics", [])
        if not isinstance(topics, list):
            return []
        return _unique_clean_strings(topics)

    def _load_tag_names(self, path: Path, key: str) -> list[str]:
        payload = read_json(path, {key: []})
        values = payload.get(key, [])
        if not isinstance(values, list):
            return []
        names = [
            item.get("name") if isinstance(item, dict) else item
            for item in values
        ]
        return sorted(_unique_clean_strings(names), key=str.casefold)


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


def _ranked_keys(counts: Counter[str], limit: int) -> list[str]:
    return [
        key
        for key, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )[:limit]
    ]


def _build_institution_topic_matrix(
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    institution_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    local_counts: dict[str, Counter[str]] = {}

    for paper in papers:
        institution = str(paper.get("institution_tag") or "").strip()
        topic = str(paper.get("topic_tag") or "").strip()
        if not _is_public_institution_tag(institution) or not topic:
            continue
        institution_counts[institution] += 1
        topic_counts[topic] += 1
        local_counts.setdefault(institution, Counter())[topic] += 1

    institutions = _ranked_keys(institution_counts, MATRIX_INSTITUTION_LIMIT)
    topics = _ranked_keys(topic_counts, MATRIX_GLOBAL_TOPIC_LIMIT)
    topics.extend(
        topic
        for institution in institutions
        for topic in _ranked_keys(
            local_counts[institution],
            MATRIX_LOCAL_TOPIC_LIMIT,
        )
        if topic not in topics
    )
    return {
        "institutions": institutions,
        "topics": topics,
        "values": [
            [local_counts[institution].get(topic, 0) for topic in topics]
            for institution in institutions
        ],
    }


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


def _unique_clean_strings(values: list[Any]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        topic = str(value or "").strip()
        key = topic.casefold()
        if not topic or key in seen:
            continue
        cleaned.append(topic)
        seen.add(key)
    return cleaned


def _paper_index_entry(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        field: paper.get(field)
        for field in INDEX_FIELDS
        if paper.get(field) not in [None, ""]
    }


def _json_to_js_payload(payload: dict[str, Any], fallback_key: str) -> dict[str, str]:
    import json

    return {
        "key": json.dumps(str(payload.get("date") or fallback_key), ensure_ascii=False),
        "value": json.dumps(payload, ensure_ascii=False),
    }


def _asset_version() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")
