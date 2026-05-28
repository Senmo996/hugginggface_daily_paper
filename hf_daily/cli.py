from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .admin_server import create_admin_server
from .fetcher import DailyFetcher, build_http_client
from .generator import DailyGenerator
from .llm import OpenAICompatibleClient
from .site_builder import SiteBuilder
from .storage import ProjectPaths


def build_llm_client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient.from_env()


def main(argv: list[str] | None = None) -> int:
    _configure_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = ProjectPaths(args.root)

    try:
        if args.command == "fetch":
            print(f"Fetching Hugging Face Daily Papers for {args.date}", flush=True)
            DailyFetcher(paths, client=build_http_client()).fetch(args.date)
            print("Fetch complete", flush=True)
        elif args.command == "generate":
            if args.reset_topic_tags:
                print("Resetting topic tag library", flush=True)
            DailyGenerator(paths, build_llm_client()).generate(
                args.date,
                force=args.force,
                reset_topic_tags=args.reset_topic_tags,
                progress=_print_progress,
            )
            print("Generation complete", flush=True)
        elif args.command == "build":
            print("Building static site", flush=True)
            SiteBuilder(paths).build()
            print(f"Done. Open {paths.site_dir / 'index.html'}", flush=True)
        elif args.command == "admin":
            print("Building static site", flush=True)
            SiteBuilder(paths).build()
            server = create_admin_server(paths, args.host, args.port)
            print(
                f"Local admin ready at http://{args.host}:{server.server_port}/index.html",
                flush=True,
            )
            print("Press Ctrl+C to stop.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "run":
            print(f"Fetching Hugging Face Daily Papers for {args.date}", flush=True)
            DailyFetcher(paths, client=build_http_client()).fetch(args.date)
            print("Fetch complete", flush=True)
            if args.reset_topic_tags:
                print("Resetting topic tag library", flush=True)
            DailyGenerator(paths, build_llm_client()).generate(
                args.date,
                force=args.force,
                reset_topic_tags=args.reset_topic_tags,
                progress=_print_progress,
            )
            print("Generation complete", flush=True)
            print("Building static site", flush=True)
            SiteBuilder(paths).build()
            print(f"Done. Open {paths.site_dir / 'index.html'}", flush=True)
        else:
            parser.print_help()
            return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hf_daily",
        description="Fetch Hugging Face Daily Papers and build a static archive.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch daily papers from Hugging Face.")
    fetch.add_argument("--date", default=today(), help="Date in YYYY-MM-DD format.")

    generate = subparsers.add_parser("generate", help="Generate summaries and tags.")
    generate.add_argument("--date", default=today(), help="Date in YYYY-MM-DD format.")
    generate.add_argument("--force", action="store_true", help="Regenerate existing papers.")
    generate.add_argument(
        "--reset-topic-tags",
        action="store_true",
        help="Clear the local topic tag library before generation.",
    )

    subparsers.add_parser("build", help="Build the static site.")

    admin = subparsers.add_parser("admin", help="Start the local tag editing admin site.")
    admin.add_argument("--host", default="127.0.0.1", help="Local bind host.")
    admin.add_argument("--port", type=int, default=8765, help="Local admin port.")

    run = subparsers.add_parser("run", help="Fetch, generate, and build.")
    run.add_argument("--date", default=today(), help="Date in YYYY-MM-DD format.")
    run.add_argument("--force", action="store_true", help="Regenerate existing papers.")
    run.add_argument(
        "--reset-topic-tags",
        action="store_true",
        help="Clear the local topic tag library before generation.",
    )
    return parser


def today() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def _print_progress(message: str) -> None:
    print(message, flush=True)


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
