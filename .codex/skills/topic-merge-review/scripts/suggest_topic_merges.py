from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


STOPWORDS = {
    "llm",
    "model",
    "models",
    "multimodal",
    "evaluation",
    "benchmark",
    "agent",
    "agents",
    "diffusion",
    "language",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest topic merge candidates without writing files.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    papers = load_papers(args.root)
    counts = Counter(paper.get("topic_tag") for paper in papers if paper.get("topic_tag"))
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        topic = paper.get("topic_tag")
        if topic:
            by_topic[str(topic)].append(paper)

    print("# Candidate Topic Merge Review Packet")
    print()
    print(f"Topics: {len(counts)}")
    print(f"Papers: {len(papers)}")
    print()
    print("## Candidate Topic Merges")
    print()

    for score, total, left, right, jaccard, ratio in candidate_pairs(counts)[: args.limit]:
        print(f"### `{left}` <> `{right}`")
        print(f"- Counts: {counts[left]} + {counts[right]} = {total}")
        print(f"- Similarity: token={jaccard:.2f}, name={ratio:.2f}, max={score:.2f}")
        print("- Representative titles:")
        for title in titles(by_topic[left], 3):
            print(f"  - `{left}`: {title}")
        for title in titles(by_topic[right], 3):
            print(f"  - `{right}`: {title}")
        print("- Evidence for: inspect shared terms and paper intent.")
        print("- Evidence against: inspect whether one is a distinct subfield, benchmark, modality, or method.")
        print()

    print("Reply with exact approved pairs before writing data/tags/topic_aliases.json.")
    return 0


def load_papers(root: Path) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    for path in sorted((root / "data" / "daily").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        papers.extend(paper for paper in payload.get("papers", []) if isinstance(paper, dict))
    return papers


def candidate_pairs(counts: Counter[str]) -> list[tuple[float, int, str, str, float, float]]:
    topics = list(counts)
    pairs = []
    for index, left in enumerate(topics):
        for right in topics[index + 1 :]:
            jaccard = token_jaccard(left, right)
            ratio = SequenceMatcher(None, left.casefold(), right.casefold()).ratio()
            score = max(jaccard, ratio)
            if jaccard >= 0.45 or ratio >= 0.72:
                pairs.append((score, counts[left] + counts[right], left, right, jaccard, ratio))
    return sorted(pairs, reverse=True)


def token_jaccard(left: str, right: str) -> float:
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in STOPWORDS
    }


def titles(papers: list[dict[str, Any]], limit: int) -> list[str]:
    return [str(paper.get("title", "")).strip() for paper in papers[:limit] if paper.get("title")]


if __name__ == "__main__":
    raise SystemExit(main())
