from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from hf_daily.fetcher import DailyFetcher, build_http_client
from hf_daily.generator import DailyGenerator
from hf_daily.llm import OpenAICompatibleClient
from hf_daily.site_builder import SiteBuilder
from hf_daily.storage import ProjectPaths


DEFAULT_PROXY = "http://127.0.0.1:7900"


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    paths = ProjectPaths(root)

    configure_output()
    configure_proxy(args.proxy)

    latest = latest_completed_non_empty_date(paths)
    start = args.start or ((latest + timedelta(days=1)) if latest else date.today())
    end = args.end or date.today()

    if start > end:
        print(f"Already up to date through {latest.isoformat() if latest else 'no local data'}.")
        return 0

    fetcher = DailyFetcher(paths, client=build_http_client(), retries=args.retries)
    generator = DailyGenerator(paths, OpenAICompatibleClient.from_env())
    processed: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    current = start
    while current <= end:
        day = current.isoformat()
        print(f"Checking {day}", flush=True)

        try:
            payload = fetcher.fetch(day)
        except RuntimeError as exc:
            print(f"Skipping unavailable {day}: {exc}", flush=True)
            skipped.append(day)
            current += timedelta(days=1)
            continue

        if not payload:
            print(f"Skipping empty {day}", flush=True)
            remove_empty_daily_file(paths, day)
            skipped.append(day)
            current += timedelta(days=1)
            continue

        try:
            generator.generate(day, progress=lambda message: print(message, flush=True))
            processed.append(day)
        except Exception as exc:
            failed.append((day, str(exc)))
            print(f"Failed generating {day}: {exc}", flush=True)
            raise

        current += timedelta(days=1)

    if processed:
        print("Building static site", flush=True)
        SiteBuilder(paths).build()
    else:
        print("No non-empty dates processed; static site rebuild skipped.", flush=True)

    print(f"Processed dates: {processed}")
    print(f"Skipped empty or unavailable dates: {skipped}")
    print(f"Errors: {failed}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch latest Hugging Face Daily Papers and rebuild the static site.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--start", type=parse_date, help="Optional start date, YYYY-MM-DD.")
    parser.add_argument("--end", type=parse_date, help="Optional end date, YYYY-MM-DD.")
    parser.add_argument("--proxy", default=DEFAULT_PROXY, help="HTTP proxy URL.")
    parser.add_argument("--retries", type=int, default=5, help="Fetch retry count per date.")
    return parser.parse_args()


def configure_output() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def configure_proxy(proxy: str) -> None:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ[key] = proxy
    print(f"Using proxy: {proxy}", flush=True)


def latest_completed_non_empty_date(paths: ProjectPaths) -> date | None:
    latest: date | None = None
    for path in paths.daily_dir.glob("*.json"):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        papers = data.get("papers") or []
        if data.get("status") != "complete" or not papers:
            continue
        day = date.fromisoformat(path.stem)
        if latest is None or day > latest:
            latest = day
    return latest


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def remove_empty_daily_file(paths: ProjectPaths, day: str) -> None:
    daily_path = paths.daily_dir / f"{day}.json"
    if daily_path.exists():
        daily_path.unlink()


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
