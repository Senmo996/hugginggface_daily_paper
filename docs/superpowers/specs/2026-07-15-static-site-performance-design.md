# Static Site Performance Design

## Goal

Reduce initial browser work and generated-site size without changing the archive's visible behavior or removing the ability to open `site/index.html` directly from the filesystem.

The first optimization batch covers matrix data, homepage index loading, bounded result rendering, and one-pass daily grouping. LLM generation, tag-store caching, and incremental site rebuilds are separate follow-up projects.

## Constraints

- Opening `site/index.html` through `file://` must continue to work.
- Daily paper assets and the global search index retain the current JSON-first, JavaScript-fallback loading mechanism.
- Search, tag filters, topic trends, paper selection, tag editing, and downloads keep their current behavior.
- Root-level templates override package defaults, so matching template files must stay synchronized.
- The source files under `data/daily/` are read-only inputs to the site build.

## Build Architecture

`SiteBuilder.build()` will make one pass over normalized papers and build both:

- the flat `papers` list needed by the global index;
- a `papers_by_date` mapping used to write each daily asset.

This replaces the current full-paper scan for every date. Empty daily payloads remain excluded exactly as they are now.

The builder will also produce the institution-topic matrix in Python. The result has this JSON-compatible shape:

```json
{
  "institutions": ["Institution A"],
  "topics": ["topic-a"],
  "values": [[3]]
}
```

The aggregation preserves the current browser algorithm:

1. Ignore missing institutions and the `Unknown` institution, case-insensitively.
2. Count only papers that have both a public institution and a topic.
3. Select the top 40 institutions and global top 20 topics by descending paper count, breaking ties alphabetically.
4. Add each selected institution's top three local topics, preserving first occurrence and removing duplicates.
5. Emit a dense row-major value matrix aligned with `institutions` and `topics`.

The compact aggregate will be embedded in `matrix.html`. This avoids an additional request, works under `file://`, and removes the complete paper corpus from the page.

## Browser Data Flow

The homepage continues to request only the selected day's JSON/JavaScript asset for its default view.

The global search index is loaded only when one of these actions needs it:

- the user submits a non-empty search;
- the user activates a cross-date tag filter;
- a topic filter is supplied in the page URL;
- the user opens the topic-trend panel for the first time.

Topic-trend options are populated on that first panel opening, not during application startup. The existing cached promise ensures later searches and trend renders reuse the same index request. Fetch failures continue to fall back to the JavaScript asset for direct filesystem use.

The matrix page parses the embedded aggregate and renders it directly. It no longer loads or reconstructs a matrix from full paper records.

## Bounded Result Rendering

Cross-date search and tag-filter results will render in batches of 100. The complete match count remains available for status text, but only the current visible prefix is converted into paper-card DOM nodes.

An initially hidden `Load more` button appears when more matches exist. Each activation increases the visible limit by 100 and rerenders the bounded prefix. Starting a new search, changing or clearing a tag filter, or applying a URL topic filter resets the limit to 100. Changing priority topics preserves the current result limit.

Normal single-date views are not capped because the current maximum is 50 papers per day. Selection state remains stored independently from rendered cards, so selected papers survive rerenders.

Status text distinguishes the visible and total counts, for example `Showing 100 of 7,179 search results across all dates`. The button is hidden for empty results, single-date views, and fully rendered result sets.

## Error Handling

- An archive with no eligible matrix data produces empty arrays and the existing empty matrix shell rather than raising an exception.
- Malformed or unavailable global index assets follow the existing error path and display the current load failure message.
- Failure while loading trend topics does not prevent daily browsing or search controls from working.
- Matrix payload parsing failure shows the existing matrix load error state.

## Testing

Tests will be added before production changes and must fail for the missing behavior.

Builder tests will verify:

- exact institution order, topic order, and matrix values for a deterministic fixture;
- `matrix.html` contains the aggregate but excludes full titles, abstracts, and paper URLs;
- daily assets still contain the correct date-specific papers after one-pass grouping;
- direct-open JavaScript fallback assets are still generated.

Frontend contract tests will verify:

- the index template contains the `Load more` control;
- application startup no longer populates trend topics eagerly;
- opening trends triggers topic population and global-index loading;
- search/filter rendering uses a 100-result limit and exposes the total count;
- new searches and filters reset the result limit.

The full pytest suite must pass. A generated-site size check will confirm that `matrix.html` no longer scales with complete paper-record size, and a local browser smoke test will cover daily loading, search pagination, trends, and matrix rendering.

## Non-Goals

- Removing JSON/JavaScript duplicate assets.
- Adding a database, service worker, or third-party search library.
- Parallelizing LLM calls or changing prompts.
- Caching tag stores in memory.
- Implementing incremental rebuilds.
