from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


GENERIC_WORDS = {
    "ai",
    "artificial",
    "center",
    "centre",
    "computer",
    "department",
    "for",
    "group",
    "inc",
    "institute",
    "intelligence",
    "lab",
    "laboratory",
    "learning",
    "machine",
    "of",
    "research",
    "school",
    "team",
    "the",
    "university",
}

SUBUNIT_WORDS = {
    "center",
    "centre",
    "department",
    "group",
    "lab",
    "laboratory",
    "research",
    "school",
    "team",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest institution merge candidates without writing files.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    papers = load_papers(args.root)
    counts = Counter(
        str(paper.get("institution_tag")).strip()
        for paper in papers
        if is_candidate_tag(paper.get("institution_tag"))
    )
    by_institution: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        institution = paper.get("institution_tag")
        if is_candidate_tag(institution):
            by_institution[str(institution).strip()].append(paper)

    print("# Candidate Institution Merge Review Packet")
    print()
    print(f"Institutions: {len(counts)}")
    print(f"Papers: {len(papers)}")
    print()
    print("## Candidate Institution Merges")
    print()

    for candidate in candidate_pairs(counts)[: args.limit]:
        score, total, left, right, jaccard, ratio, normalized_match, parent_subunit = candidate
        confidence = confidence_hint(score, normalized_match, parent_subunit)
        print(f"### `{left}` <> `{right}`")
        print(f"- Confidence hint: {confidence}")
        print(f"- Counts: {counts[left]} + {counts[right]} = {total}")
        print(f"- Similarity: token={jaccard:.2f}, name={ratio:.2f}, max={score:.2f}")
        print("- Representative titles:")
        for title in titles(by_institution[left], 3):
            print(f"  - `{left}`: {title}")
        for title in titles(by_institution[right], 3):
            print(f"  - `{right}`: {title}")
        print("- Evidence for: inspect whether these are naming variants of the same organization.")
        print("- Evidence against: inspect parent/lab, campus, department, and acronym ambiguity.")
        print()

    print("Reply with exact approved pairs before writing data/tags/institution_aliases.json.")
    return 0


def load_papers(root: Path) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    for path in sorted((root / "data" / "daily").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        papers.extend(paper for paper in payload.get("papers", []) if isinstance(paper, dict))
    return papers


def candidate_pairs(counts: Counter[str]) -> list[tuple[float, int, str, str, float, float, bool, bool]]:
    institutions = list(counts)
    pairs = []
    for index, left in enumerate(institutions):
        for right in institutions[index + 1 :]:
            normalized_match = normalize_name(left) == normalize_name(right)
            jaccard = token_jaccard(left, right)
            ratio = SequenceMatcher(None, comparable_name(left), comparable_name(right)).ratio()
            score = max(jaccard, ratio)
            parent_subunit = is_parent_subunit_pair(left, right)
            if normalized_match or jaccard >= 0.55 or ratio >= 0.78:
                pairs.append(
                    (
                        score,
                        counts[left] + counts[right],
                        left,
                        right,
                        jaccard,
                        ratio,
                        normalized_match,
                        parent_subunit,
                    )
                )
    return sorted(pairs, reverse=True)


def is_candidate_tag(value: Any) -> bool:
    tag = str(value or "").strip()
    return bool(tag) and tag.casefold() != "unknown"


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
        if token not in GENERIC_WORDS
    }


def comparable_name(value: str) -> str:
    token_list = re.findall(r"[a-z0-9]+", value.casefold())
    return " ".join(token for token in token_list if token not in {"the", "of", "for"})


def normalize_name(value: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", value.casefold()))


def is_parent_subunit_pair(left: str, right: str) -> bool:
    left_tokens = set(re.findall(r"[a-z0-9]+", left.casefold()))
    right_tokens = set(re.findall(r"[a-z0-9]+", right.casefold()))
    if not left_tokens or not right_tokens:
        return False
    shared = left_tokens & right_tokens
    if not shared:
        return False
    left_has_subunit = bool(left_tokens & SUBUNIT_WORDS)
    right_has_subunit = bool(right_tokens & SUBUNIT_WORDS)
    return left_has_subunit != right_has_subunit


def confidence_hint(score: float, normalized_match: bool, parent_subunit: bool) -> str:
    if parent_subunit:
        return "needs human judgment"
    if normalized_match or score >= 0.92:
        return "high"
    return "medium"


def titles(papers: list[dict[str, Any]], limit: int) -> list[str]:
    return [str(paper.get("title", "")).strip() for paper in papers[:limit] if paper.get("title")]


if __name__ == "__main__":
    raise SystemExit(main())
