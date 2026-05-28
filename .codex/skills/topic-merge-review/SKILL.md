---
name: topic-merge-review
description: Use when reviewing, proposing, approving, or applying topic tag merges, topic aliases, canonical topic names, duplicate topic cleanup, similar topic consolidation, or changes to data/tags/topic_aliases.json in this huggingface_daily project.
---

# Topic Merge Review

## Core Rule

Topic merges are two-phase only:

1. Produce a review packet with candidate merges and evidence.
2. Write aliases only after the user explicitly approves exact alias-to-canonical pairs.

Never write `data/tags/topic_aliases.json`, rewrite `data/daily/*.json`, or change canonical topic output during phase 1.

## Phase 1: Review Packet Only

When asked to merge or clean similar topics:

1. Inspect current topics, counts, and representative paper titles.
2. Group candidates conservatively.
3. For each candidate, include:
   - alias topic
   - proposed canonical topic
   - confidence: high, medium, or low
   - evidence for merging
   - evidence against merging
   - representative paper titles from both sides
4. Recommend only high-confidence merges for approval.
5. End with a clear approval request. Do not write files.

Use the helper script from the repository root to generate a starting report:

```powershell
python .codex\skills\topic-merge-review\scripts\suggest_topic_merges.py --root .
```

## Phase 2: Apply Only Approved Merges

Before writing anything, verify the user approved exact alias-to-canonical pairs in the current conversation. Acceptable approval looks like:

```text
Approve:
- Old topic A -> Canonical topic A
- Old topic B -> Canonical topic B
```

If approval is vague, partial, or refers to "your suggestions" without listing pairs, stop and ask for exact approval.

When approved:

1. Write or update only `data/tags/topic_aliases.json`.
2. Do not rewrite `data/daily/*.json`.
3. Rebuild generated site outputs if the project uses them.
4. Report applied pairs and any skipped pairs.

## Merge Criteria

Prefer merging when all are true:

- Same medium-granularity research direction.
- Alias is mostly naming variation, narrower benchmark wording, or redundant modality prefix.
- Representative paper titles support the same concept.
- No clear semantic boundary would be lost.

Keep separate when any are true:

- One topic is a subfield with distinct methods or evaluation goals.
- Terms share words but differ in object: image vs video, retrieval vs distillation, safety evaluation vs safety alignment.
- One is an infrastructure/benchmark topic and the other is a modeling method.
- Evidence is mostly string similarity.

## Output Format

Use this format for review packets:

```markdown
## Candidate Topic Merges

### High Confidence
- `alias` -> `canonical`
  Evidence for: ...
  Evidence against: ...
  Representative titles: ...

### Needs Human Judgment
- ...

### Keep Separate
- ...

Reply with exact approved pairs before I write `data/tags/topic_aliases.json`.
```

## Red Flags

Stop before writing if you are thinking:

- "This is obviously safe, I can write aliases now."
- "The user said merge topics, so approval is implied."
- "I can apply high-confidence pairs and ask about the rest later."
- "I'll rewrite daily JSON so the data looks clean."

All of these violate the skill. Produce or update the review packet instead.
