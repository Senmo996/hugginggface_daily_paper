---
name: institution-merge-review
description: Use when reviewing, proposing, approving, or applying institution tag merges, institute tag merges, institution aliases, canonical institution names, duplicate institution cleanup, similar institution consolidation, or changes to data/tags/institution_aliases.json in this huggingface_daily project.
---

# Institution Merge Review

## Core Rule

Institution merges are two-phase only:

1. Produce a review packet with candidate merges and evidence.
2. Write aliases only after the user explicitly approves exact alias-to-canonical pairs.

Never write `data/tags/institution_aliases.json`, rewrite `data/daily/*.json`, or change canonical institution output during phase 1.

## Phase 1: Review Packet Only

When asked to merge or clean similar institution tags:

1. Inspect current institution tags, counts, examples, and representative paper titles.
2. Group candidates conservatively.
3. For each candidate, include:
   - alias institution
   - proposed canonical institution
   - confidence: high, medium, or low
   - evidence for merging
   - evidence against merging
   - representative paper titles from both sides
4. Recommend only high-confidence merges for approval.
5. End with a clear approval request. Do not write files.

Use the helper script from the repository root to generate a starting report:

```powershell
python .codex\skills\institution-merge-review\scripts\suggest_institution_merges.py --root .
```

## Phase 2: Apply Only Approved Merges

Before writing anything, verify the user approved exact alias-to-canonical pairs in the current conversation. Acceptable approval looks like:

```text
Approve:
- Old Institute A -> Canonical Institute A
- Old Institute B -> Canonical Institute B
```

If approval is vague, partial, or refers to "your suggestions" without listing pairs, stop and ask for exact approval.

When approved:

1. Write or update only `data/tags/institution_aliases.json`.
2. Do not rewrite `data/daily/*.json`.
3. Rebuild generated site outputs if the project uses them.
4. Report applied pairs and any skipped pairs.

## Merge Criteria

Prefer merging when all are true:

- Tags refer to the same institution, lab, company, or clearly equivalent organization name.
- Difference is casing, punctuation, abbreviation expansion, spelling variant, or a known alias.
- Representative paper titles or examples do not indicate different organizations.
- The canonical name is the clearest stable display name already used by the project.

Keep separate when any are true:

- Parent company and lab/sub-organization distinction matters, such as `ByteDance` vs `ByteDance Seed`.
- Campus, school, lab, or department identity is meaningfully different, such as `University of Toronto` vs `University of Toronto CSSLab`.
- Acronym is ambiguous without supporting evidence, such as `CUHK` vs a specific CUHK lab.
- Similarity is only string overlap, spelling proximity, or shared geography.
- One tag is `Unknown` or `unknown`; do not merge unknowns into real institutions through aliases.

## Output Format

Use this format for review packets:

```markdown
## Candidate Institution Merges

### High Confidence
- `alias` -> `canonical`
  Evidence for: ...
  Evidence against: ...
  Representative titles: ...

### Needs Human Judgment
- ...

### Keep Separate
- ...

Reply with exact approved pairs before I write `data/tags/institution_aliases.json`.
```

## Red Flags

Stop before writing if you are thinking:

- "The names look close enough, I can write aliases now."
- "The user said merge institutions, so approval is implied."
- "I can apply high-confidence pairs and ask about the rest later."
- "I'll rewrite daily JSON so the data looks clean."
- "I'll merge parent organizations and labs to simplify the dashboard."

All of these violate the skill. Produce or update the review packet instead.
