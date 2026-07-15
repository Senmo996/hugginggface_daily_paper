# Static Site Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce generated matrix size, avoid eager global-index loading, and bound cross-date DOM rendering while preserving direct `file://` use.

**Architecture:** `SiteBuilder` will aggregate matrix data and group papers by date during its existing build pass. The browser will parse the compact matrix payload, load the global index only on demand, and render cross-date results in 100-card batches. Existing JSON-to-JavaScript fallback assets remain unchanged.

**Tech Stack:** Python 3.11, Jinja2, vanilla JavaScript, pytest

---

### Task 1: Precompute Matrix Data and Group Daily Papers Once

**Files:**
- Modify: `hf_daily/site_builder.py:52-183`
- Modify: `hf_daily/default_templates/matrix.html:15-27`
- Modify: `templates/matrix.html:15-27`
- Modify: `hf_daily/default_static/app.js:1831-1920`
- Test: `tests/test_site_builder.py:728-820`

- [ ] **Step 1: Write the failing matrix aggregation test**

Import `_build_institution_topic_matrix` and add a focused test with two public institutions and one ignored `Unknown` paper:

```python
from hf_daily.site_builder import SiteBuilder, _build_institution_topic_matrix


def test_build_institution_topic_matrix_returns_dense_ranked_payload():
    papers = [
        {"institution_tag": "Alpha Lab", "topic_tag": "topic-b"},
        {"institution_tag": "Alpha Lab", "topic_tag": "topic-b"},
        {"institution_tag": "Alpha Lab", "topic_tag": "local-topic"},
        {"institution_tag": "Beta Lab", "topic_tag": "topic-a"},
        {"institution_tag": "Beta Lab", "topic_tag": "topic-a"},
        {"institution_tag": "Unknown", "topic_tag": "ignored-topic"},
    ]

    assert _build_institution_topic_matrix(papers) == {
        "institutions": ["Alpha Lab", "Beta Lab"],
        "topics": ["topic-a", "topic-b", "local-topic"],
        "values": [[0, 2, 1], [2, 0, 0]],
    }
```

- [ ] **Step 2: Run the test and verify the RED state**

Run: `python -m pytest tests/test_site_builder.py::test_build_institution_topic_matrix_returns_dense_ranked_payload -q`

Expected: collection fails because `_build_institution_topic_matrix` does not exist.

- [ ] **Step 3: Implement the aggregation helper**

Add constants and a helper that preserves the current JavaScript ranking rules:

```python
MATRIX_INSTITUTION_LIMIT = 40
MATRIX_GLOBAL_TOPIC_LIMIT = 20
MATRIX_LOCAL_TOPIC_LIMIT = 3


def _ranked_keys(counts: Counter[str], limit: int) -> list[str]:
    return [
        key
        for key, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )[:limit]
    ]


def _build_institution_topic_matrix(papers: list[dict[str, Any]]) -> dict[str, Any]:
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
        for topic in _ranked_keys(local_counts[institution], MATRIX_LOCAL_TOPIC_LIMIT)
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
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `python -m pytest tests/test_site_builder.py::test_build_institution_topic_matrix_returns_dense_ranked_payload -q`

Expected: `1 passed`.

- [ ] **Step 5: Write failing build-output tests**

Update the existing matrix tests to require the compact payload and absence of complete paper content:

```python
match = re.search(
    r'<script id="matrixData" type="application/json">(.*?)</script>',
    matrix,
    re.DOTALL,
)
assert match is not None
matrix_data = json.loads(match.group(1))
assert matrix_data == {
    "institutions": ["Example University"],
    "topics": ["vision-language modeling"],
    "values": [[1]],
}
assert "2605.00001" not in matrix
assert "Original abstract." not in matrix
```

Replace old JavaScript-algorithm assertions with these browser contract assertions:

```python
assert 'document.getElementById("matrixData")' in app
assert "function loadInstitutionTopicMatrix(" in app
assert "function renderInstitutionTopicMatrix(" in app
assert "function buildInstitutionTopicMatrix(" not in app
assert 'fetch("assets/papers.json")' not in app
```

- [ ] **Step 6: Run matrix build tests and verify RED**

Run: `python -m pytest tests/test_site_builder.py::test_index_renders_institution_topic_matrix_panel tests/test_site_builder.py::test_index_script_calculates_and_renders_institution_topic_matrix -q`

Expected: failures because `matrixPapersData` still contains complete papers and the browser still aggregates them.

- [ ] **Step 7: Implement one-pass grouping and compact matrix rendering**

In `SiteBuilder.build()`, build `papers` and `papers_by_date` together, pass `matrix_data` and `total_papers` to the template, and use the mapping for daily assets:

```python
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
```

Render the matrix with:

```python
matrix_template.render(
    dates=dates,
    matrix_data=_build_institution_topic_matrix(papers),
    total_papers=len(papers),
    asset_version=asset_version,
)
```

Write each daily payload from `papers_by_date.get(date, [])`.

In both matrix templates, replace `papers|length` and `matrixPapersData` with:

```html
<span>{{ total_papers }} papers</span>
<script id="matrixData" type="application/json">{{ matrix_data|tojson }}</script>
```

Replace the browser-side paper loading and aggregation functions with a parser:

```javascript
function setupInstitutionTopicMatrix() {
  if (!institutionTopicMatrix) {
    return;
  }
  try {
    renderInstitutionTopicMatrix(loadInstitutionTopicMatrix());
  } catch (error) {
    institutionTopicMatrix.innerHTML = "";
    appendMatrixCell("Unable to load matrix data.", "matrix-head");
  }
}

function loadInstitutionTopicMatrix() {
  const embeddedData = document.getElementById("matrixData");
  if (!embeddedData || !embeddedData.textContent) {
    return { institutions: [], topics: [], values: [] };
  }
  return JSON.parse(embeddedData.textContent);
}
```

Update `renderInstitutionTopicMatrix` to read `matrix.values[rowIndex][columnIndex]` and compute the maximum from `matrix.values.flat()`.

- [ ] **Step 8: Run the site-builder suite and commit**

Run: `python -m pytest tests/test_site_builder.py -q`

Expected: all site-builder tests pass.

Commit:

```powershell
git add hf_daily/site_builder.py hf_daily/default_templates/matrix.html templates/matrix.html hf_daily/default_static/app.js tests/test_site_builder.py
git commit -m "perf: precompute static matrix data"
```

### Task 2: Lazy-Load Trend Topics

**Files:**
- Modify: `hf_daily/default_static/app.js:1580-1661`
- Test: `tests/test_site_builder.py:822-895`

- [ ] **Step 1: Write the failing lazy-load contract test**

Extend the trend test with blocks that distinguish initialization from first-open behavior:

```python
setup_start = app.index("function setupTopicTrends()")
listener_start = app.index('topicTrendToggle.addEventListener("click"', setup_start)
setup_prefix = app[setup_start:listener_start]
listener_end = app.index("trendStartDate.addEventListener", listener_start)
open_handler = app[listener_start:listener_end]

assert "populateTrendTopics();" not in setup_prefix
assert "populateTrendTopics().then(renderTopicTrends)" in open_handler
```

- [ ] **Step 2: Run the trend test and verify RED**

Run: `python -m pytest tests/test_site_builder.py::test_index_script_calculates_and_renders_topic_trends -q`

Expected: failure because `populateTrendTopics();` is called before the click listener.

- [ ] **Step 3: Move topic loading into the first-open path**

Remove the eager call and change the open handler to:

```javascript
if (isOpen) {
  populateTrendTopics()
    .then(renderTopicTrends)
    .catch(() => {});
}
```

Make `populateTrendTopics()` return the `loadSearchIndex()` promise after populating the selector. Existing `searchIndexPromise` caching prevents duplicate downloads.

- [ ] **Step 4: Run focused and full tests, then commit**

Run: `python -m pytest tests/test_site_builder.py::test_index_script_calculates_and_renders_topic_trends -q`

Expected: `1 passed`.

Run: `python -m pytest -q`

Expected: all tests pass.

Commit:

```powershell
git add hf_daily/default_static/app.js tests/test_site_builder.py
git commit -m "perf: defer global index until trends open"
```

### Task 3: Render Cross-Date Results in Batches

**Files:**
- Modify: `hf_daily/default_templates/index.html:144-163`
- Modify: `templates/index.html:144-163`
- Modify: `hf_daily/default_static/styles.css`
- Modify: `hf_daily/default_static/app.js:1-405`
- Test: `tests/test_site_builder.py:349-394`

- [ ] **Step 1: Write the failing pagination contract test**

Add a focused generated-asset test:

```python
def test_cross_date_results_are_rendered_in_batches(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(paths.daily_dir / "2026-05-28.json", {"date": "2026-05-28", "papers": []})

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert '<button id="loadMorePapers" class="secondary" type="button" hidden>Load more</button>' in index
    assert "const SEARCH_RESULT_BATCH_SIZE = 100;" in app
    assert "let visibleResultLimit = SEARCH_RESULT_BATCH_SIZE;" in app
    assert "papers.slice(0, visibleResultLimit)" in app
    assert "function resetVisibleResultLimit()" in app
    assert "function updateLoadMoreControl(" in app
    assert "visibleResultLimit += SEARCH_RESULT_BATCH_SIZE;" in app
```

- [ ] **Step 2: Run the pagination test and verify RED**

Run: `python -m pytest tests/test_site_builder.py::test_cross_date_results_are_rendered_in_batches -q`

Expected: failure because the control and batching state do not exist.

- [ ] **Step 3: Add the template control and styles**

Add after `paperList` in both index templates:

```html
<div class="load-more-row">
  <button id="loadMorePapers" class="secondary" type="button" hidden>Load more</button>
</div>
```

Add a centered layout rule to the package stylesheet:

```css
.load-more-row {
  display: flex;
  justify-content: center;
  padding-top: 16px;
}
```

- [ ] **Step 4: Implement bounded rendering state**

Add DOM/state declarations:

```javascript
const loadMorePapers = document.getElementById("loadMorePapers");
const SEARCH_RESULT_BATCH_SIZE = 100;
let visibleResultLimit = SEARCH_RESULT_BATCH_SIZE;
```

In `renderIndexPapers`, preserve the full filtered count but render only the prefix for global views:

```javascript
const isCrossDateView = Boolean(currentFilter || hasSearchQuery);
const visiblePapers = isCrossDateView ? papers.slice(0, visibleResultLimit) : papers;
renderPaperCards(visiblePapers, { compact: isCrossDateView });
updateIndexStatus(visiblePapers.length, papers.length);
updateLoadMoreControl(visiblePapers.length, papers.length, isCrossDateView);
```

Add helpers and the button handler:

```javascript
function resetVisibleResultLimit() {
  visibleResultLimit = SEARCH_RESULT_BATCH_SIZE;
}

function updateLoadMoreControl(visibleCount, totalCount, isCrossDateView) {
  if (!loadMorePapers) {
    return;
  }
  loadMorePapers.hidden = !isCrossDateView || visibleCount >= totalCount;
}

if (loadMorePapers) {
  loadMorePapers.addEventListener("click", () => {
    visibleResultLimit += SEARCH_RESULT_BATCH_SIZE;
    render();
  });
}
```

Call `resetVisibleResultLimit()` before rendering after tag-filter changes, search submission, filter clearing, and URL-topic application. Hide the button in the load failure path.

Change `updateIndexStatus` to accept visible and total counts and report both when they differ:

```javascript
const countLabel = visibleCount < totalCount ? `Showing ${visibleCount} of ${totalCount}` : String(totalCount);
```

- [ ] **Step 5: Run the pagination test and site-builder suite**

Run: `python -m pytest tests/test_site_builder.py::test_cross_date_results_are_rendered_in_batches -q`

Expected: `1 passed`.

Run: `python -m pytest tests/test_site_builder.py -q`

Expected: all site-builder tests pass.

- [ ] **Step 6: Commit the batching change**

```powershell
git add hf_daily/default_templates/index.html templates/index.html hf_daily/default_static/styles.css hf_daily/default_static/app.js tests/test_site_builder.py
git commit -m "perf: batch cross-date paper rendering"
```

### Task 4: Verify Generated Output and Browser Behavior

**Files:**
- Verify: `site/index.html`
- Verify: `site/matrix.html`
- Verify: `site/assets/app.js`

- [ ] **Step 1: Run the complete automated suite**

Run: `python -m pytest -q`

Expected: all tests pass with no warnings or failures.

- [ ] **Step 2: Rebuild the real static site**

Run: `python -m hf_daily build`

Expected: exit code 0 and `Done. Open ...\site\index.html`.

- [ ] **Step 3: Measure the optimized output**

Run:

```powershell
Get-Item site\matrix.html,site\assets\papers-index.json | Select-Object Name,Length
```

Expected: `matrix.html` is well below 1 MB and `papers-index.json` remains available for on-demand search and trends.

- [ ] **Step 4: Smoke-test HTTP behavior in a browser**

Start `python -m http.server 8000 --directory site`, open `http://127.0.0.1:8000/index.html`, and verify:

- the latest date renders without an eager `papers-index.json` request;
- opening Topic trends loads the index and renders the chart;
- searching `a` displays 100 cards and a visible Load more control;
- activating Load more displays 200 cards;
- `matrix.html` renders the same institution/topic grid from the compact payload.

- [ ] **Step 5: Smoke-test direct filesystem behavior**

Open `site/index.html` directly and verify the current day's JavaScript fallback loads. Submit a search and verify `papers-index.js` supplies results when JSON fetch is unavailable.

- [ ] **Step 6: Inspect repository state**

Run: `git status --short --branch` and `git diff --check`.

Expected: only intentional plan or implementation files are present, with no whitespace errors.
