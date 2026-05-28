from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    def __init__(self, root: str | Path = ".") -> None:
        object.__setattr__(self, "root", Path(root).resolve())

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def daily_dir(self) -> Path:
        return self.data_dir / "daily"

    @property
    def tags_dir(self) -> Path:
        return self.data_dir / "tags"

    @property
    def topic_tags(self) -> Path:
        return self.tags_dir / "topics.json"

    @property
    def institution_tags(self) -> Path:
        return self.tags_dir / "institutions.json"

    @property
    def topic_aliases(self) -> Path:
        return self.tags_dir / "topic_aliases.json"

    @property
    def institution_aliases(self) -> Path:
        return self.tags_dir / "institution_aliases.json"

    @property
    def tag_overrides(self) -> Path:
        return self.tags_dir / "tag_overrides.json"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def site_dir(self) -> Path:
        return self.root / "site"

    def ensure_data_dirs(self) -> None:
        for path in [self.raw_dir, self.daily_dir, self.tags_dir]:
            path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
