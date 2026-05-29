import html
import json
import re

from hf_daily.site_builder import SiteBuilder
from hf_daily.storage import ProjectPaths


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_generates_index_matrix_and_search_data_without_daily_pages(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "generated_at": "2026-05-28T10:00:00Z",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author", "B. Author"],
                    "published_at": "2026-05-27T00:00:00.000Z",
                    "upvotes": 7,
                    "num_comments": 2,
                    "one_sentence_summary": "A native VLM learns pixel-word alignment end to end.",
                    "institution_tag": "Existing University",
                    "topic_tag": "native vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": "https://example.com/project",
                    "github_repo": "https://github.com/example/native-vlm",
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    matrix = (paths.site_dir / "matrix.html").read_text(encoding="utf-8")
    styles = (paths.site_dir / "assets" / "styles.css").read_text(encoding="utf-8")
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    assert "Date Archive" in index
    assert "Institution Tags" in index
    assert "Topic Tags" in index
    assert "Native VLM" in index
    assert "A native VLM learns pixel-word alignment end to end." in index
    assert "native vision-language modeling" in index
    assert "Original abstract." in index
    assert "Institution x Topic" in matrix
    assert search["papers"][0]["id"] == "2605.00001"
    assert search["topic_tags"] == ["native vision-language modeling"]
    assert search["institution_tags"] == ["Existing University"]
    assert not (paths.site_dir / "daily").exists()
    assert "width: min(860px, 100%);" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "@media (max-width: 1200px)" in styles


def test_index_defaults_to_latest_date_and_renders_date_selectors(tmp_path):
    paths = ProjectPaths(tmp_path)
    base_paper = {
        "summary": "Original abstract.",
        "authors": ["A. Author"],
        "published_at": "2026-05-27T00:00:00.000Z",
        "upvotes": 1,
        "num_comments": 0,
        "one_sentence_summary": "中文一句话摘要。",
        "institution_tag": "Example University",
        "topic_tag": "LLM search",
        "hf_url": "https://huggingface.co/papers/2605.00001",
        "arxiv_url": "https://arxiv.org/abs/2605.00001",
        "project_page": None,
        "github_repo": None,
    }
    write_json(
        paths.daily_dir / "2026-05-27.json",
        {
            "date": "2026-05-27",
            "papers": [
                {
                    **base_paper,
                    "id": "2605.00001",
                    "daily_date": "2026-05-27",
                    "title": "Older Paper",
                }
            ],
        },
    )
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    **base_paper,
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Latest Paper",
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")

    assert "Latest Paper" in index
    assert "Older Paper" in index
    assert 'data-latest-date="2026-05-28"' in index
    assert '<select id="dateYear"' in index
    assert '<select id="dateMonth"' in index
    assert '<select id="dateDay"' in index
    assert "Open selected date" not in index
    assert 'id="dateStatus"' in index
    match = re.search(r'data-available-dates="([^"]+)"', index)
    assert match is not None
    assert json.loads(html.unescape(match.group(1))) == ["2026-05-28", "2026-05-27"]
    assert 'data-date="2026-05-28"' in index
    older_card = re.search(
        r'<article\s+class="([^"]*paper-card[^"]*)"\s+data-title="older paper"',
        index,
    )
    assert older_card is not None
    assert "is-hidden" in older_card.group(1)


def test_empty_daily_payloads_are_excluded_from_date_archive(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-27.json",
        {
            "date": "2026-05-27",
            "papers": [],
        },
    )
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Active Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "LLM search",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    match = re.search(r'data-available-dates="([^"]+)"', index)
    assert match is not None
    assert json.loads(html.unescape(match.group(1))) == ["2026-05-28"]
    assert 'data-latest-date="2026-05-28"' in index
    assert search["dates"] == ["2026-05-28"]
    assert not (paths.site_dir / "daily").exists()


def test_index_script_supports_in_place_date_and_all_history_tag_filtering(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-27.json",
        {
            "date": "2026-05-27",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-27",
                    "title": "Older RAG Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-27T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Older summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "RAG retrieval",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Latest Search Paper",
                    "summary": "Original abstract.",
                    "authors": ["B. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 2,
                    "num_comments": 0,
                    "one_sentence_summary": "Latest summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "LLM search",
                    "hf_url": "https://huggingface.co/papers/2605.00002",
                    "arxiv_url": "https://arxiv.org/abs/2605.00002",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert "selectedDate" in app
    assert "card.dataset.date === selectedDate" in app
    assert "currentFilter || hasSearchQuery || !layout ? true" in app
    assert "renderSelectedDate" in app


def test_index_script_searches_across_all_dates(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-27.json",
        {
            "date": "2026-05-27",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-27",
                    "title": "Older RAG Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-27T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Older summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "RAG retrieval",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Latest Search Paper",
                    "summary": "Original abstract.",
                    "authors": ["B. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 2,
                    "num_comments": 0,
                    "one_sentence_summary": "Latest summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "LLM search",
                    "hf_url": "https://huggingface.co/papers/2605.00002",
                    "arxiv_url": "https://arxiv.org/abs/2605.00002",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert "const hasSearchQuery = Boolean(query);" in app
    assert "currentFilter || hasSearchQuery || !layout ? true" in app


def test_index_renders_search_scope_selector(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")

    assert '<select id="searchScope" aria-label="Search field">' in index
    assert '<option value="all" selected>All fields</option>' in index
    assert '<option value="title">Title</option>' in index
    assert '<option value="summary">Summary</option>' in index
    assert '<option value="tag">Tags</option>' in index
    assert '<option value="topic">Topic</option>' in index
    assert '<option value="institution">Institution</option>' in index


def test_index_script_filters_search_by_selected_scope(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'const searchScope = document.getElementById("searchScope");' in app
    assert "const searchScopeValue = searchScope ? searchScope.value : \"all\";" in app
    assert "searchTextFor(card, searchScopeValue)" in app
    assert 'case "title":' in app
    assert 'case "summary":' in app
    assert 'case "tag":' in app
    assert 'case "topic":' in app
    assert 'case "institution":' in app
    assert 'searchScope.addEventListener("change", render);' in app


def test_index_renders_topic_trends_header_panel(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    styles = (paths.site_dir / "assets" / "styles.css").read_text(encoding="utf-8")

    assert '<div class="header-actions">' in index
    assert '<section class="trend-menu" id="topicTrendPanel" hidden>' in index
    assert '<button id="topicTrendToggle" class="trend-toggle" type="button" aria-expanded="false" aria-controls="topicTrendPanel">' in index
    assert '<select id="trendStartDate" aria-label="Trend start date"></select>' in index
    assert '<select id="trendEndDate" aria-label="Trend end date"></select>' in index
    assert '<select id="trendTopicSelect" aria-label="Topic trend selector" multiple></select>' in index
    assert '<svg id="topicTrendChart" class="trend-chart" role="img" aria-label="Topic trend chart"></svg>' in index
    assert 'id="topicTrendSummary"' in index
    assert '<section class="rising-topics">' in index
    assert '<h3>Rising topics</h3>' in index
    assert '<div id="risingTopicList" class="rising-topic-list"></div>' in index
    assert ".header-actions" in styles
    assert ".trend-menu" in styles
    assert ".trend-chart" in styles
    assert ".rising-topic-list" in styles


def test_index_renders_institution_topic_matrix_panel(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    matrix = (paths.site_dir / "matrix.html").read_text(encoding="utf-8")
    styles = (paths.site_dir / "assets" / "styles.css").read_text(encoding="utf-8")

    assert '<a class="trend-toggle" href="matrix.html">Matrix</a>' in index
    assert 'id="matrixPanel"' not in index
    assert "Institution x Topic" in matrix
    assert '<div id="institutionTopicMatrix" class="matrix-table"></div>' in matrix
    assert '<script id="matrixPapersData" type="application/json">' in matrix
    assert "2605.00001" in matrix
    assert '<a href="index.html">Index</a>' in matrix
    assert ".matrix-table" in styles
    assert ".matrix-cell" in styles
    assert "max-height: calc(100vh - 150px);" in styles


def test_index_script_calculates_and_renders_institution_topic_matrix(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Native VLM",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'const institutionTopicMatrix = document.getElementById("institutionTopicMatrix");' in app
    assert "setupInstitutionTopicMatrix();" in app
    assert "loadPapersForMatrix()" in app
    assert "function buildInstitutionTopicMatrix(" in app
    assert "function loadPapersForMatrix(" in app
    assert 'document.getElementById("matrixPapersData")' in app
    assert 'fetch("assets/papers.json")' in app
    assert "function localTopTopicsForInstitutions(" in app
    assert "function renderInstitutionTopicMatrix(" in app
    assert ".slice(0, 40)" in app
    assert ".slice(0, 20)" in app
    assert ".slice(0, 3)" in app
    assert "new Set([...globalTopics, ...localTopics])" in app
    assert 'strippedInstitution !== "unknown"' in app


def test_index_script_calculates_and_renders_topic_trends(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-27.json",
        {
            "date": "2026-05-27",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-27",
                    "title": "Older RAG Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-27T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "RAG retrieval",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Latest Agent Paper",
                    "summary": "Original abstract.",
                    "authors": ["B. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 2,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "multimodal agents",
                    "hf_url": "https://huggingface.co/papers/2605.00002",
                    "arxiv_url": "https://arxiv.org/abs/2605.00002",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'const topicTrendToggle = document.getElementById("topicTrendToggle");' in app
    assert 'const topicTrendChart = document.getElementById("topicTrendChart");' in app
    assert "setupTopicTrends();" in app
    assert "const defaultTrendDates = defaultTrendRangeDates();" in app
    assert "function buildTopicTrendSeries(" in app
    assert "function renderTopicTrendChart(" in app
    assert "function topTopicsForRange(" in app
    assert "function defaultTrendRangeDates(" in app
    assert ".slice(0, 15)" in app
    assert "function previousRangeFor(" in app
    assert "function buildRisingTopics(" in app
    assert "function renderRisingTopics(" in app
    assert ".slice(0, 5)" in app
    assert "currentCount - previousCount" in app
    assert 'trendTopicSelect.addEventListener("change", renderTopicTrends);' in app
    assert 'topicTrendReset.addEventListener("click", () => {' in app


def test_tag_sections_are_limited_to_top_20_sorted_by_count_desc(tmp_path):
    paths = ProjectPaths(tmp_path)
    papers = []
    for index in range(25):
        for repeat in range(25 - index):
            papers.append(
                {
                    "id": f"2605.{index:05d}{repeat:02d}",
                    "daily_date": "2026-05-28",
                    "title": f"Paper {index}-{repeat}",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": f"Institution {index:02d}",
                    "topic_tag": f"Topic {index:02d}",
                    "hf_url": f"https://huggingface.co/papers/2605.{index:05d}{repeat:02d}",
                    "arxiv_url": f"https://arxiv.org/abs/2605.{index:05d}{repeat:02d}",
                    "project_page": None,
                    "github_repo": None,
                }
            )
    write_json(paths.daily_dir / "2026-05-28.json", {"date": "2026-05-28", "papers": papers})

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    topic_matches = re.findall(
        r'data-filter-type="topic" data-filter-value="([^"]+)">[^<]+ <span>(\d+)</span>',
        index,
    )
    institution_matches = re.findall(
        r'data-filter-type="institution" data-filter-value="([^"]+)">[^<]+ <span>(\d+)</span>',
        index,
    )

    assert len(topic_matches) == 20
    assert len(institution_matches) == 20
    assert topic_matches[0] == ("Topic 00", "25")
    assert topic_matches[-1] == ("Topic 19", "6")
    assert "Topic 20" not in [name for name, _count in topic_matches]
    assert institution_matches[0] == ("Institution 00", "25")
    assert institution_matches[-1] == ("Institution 19", "6")
    assert search["topic_tags"][:3] == ["Topic 00", "Topic 01", "Topic 02"]
    assert len(search["topic_tags"]) == 20
    assert len(search["institution_tags"]) == 20


def test_unknown_institution_tags_are_excluded_from_tag_section(tmp_path):
    paths = ProjectPaths(tmp_path)
    papers = []
    for index, institution in enumerate(["Unknown", "unknown", "NVIDIA", "Tencent"]):
        for repeat in range(3):
            papers.append(
                {
                    "id": f"2605.9{index}{repeat}",
                    "daily_date": "2026-05-28",
                    "title": f"Paper {index}-{repeat}",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": institution,
                    "topic_tag": "LLM search",
                    "hf_url": f"https://huggingface.co/papers/2605.9{index}{repeat}",
                    "arxiv_url": f"https://arxiv.org/abs/2605.9{index}{repeat}",
                    "project_page": None,
                    "github_repo": None,
                }
            )
    write_json(paths.daily_dir / "2026-05-28.json", {"date": "2026-05-28", "papers": papers})

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    assert 'data-filter-type="institution" data-filter-value="Unknown"' not in index
    assert 'data-filter-type="institution" data-filter-value="unknown"' not in index
    assert 'data-filter-type="institution" data-filter-value="NVIDIA"' in index
    assert 'data-filter-type="institution" data-filter-value="Tencent"' in index
    assert search["institution_tags"] == ["NVIDIA", "Tencent"]


def test_topic_aliases_are_applied_to_built_site_without_rewriting_daily_data(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Agent Scaling",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "LLM agent test-time scaling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                },
                {
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Reasoning Scaling",
                    "summary": "Original abstract.",
                    "authors": ["B. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 2,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "LLM test-time scaling",
                    "hf_url": "https://huggingface.co/papers/2605.00002",
                    "arxiv_url": "https://arxiv.org/abs/2605.00002",
                    "project_page": None,
                    "github_repo": None,
                },
            ],
        },
    )
    write_json(
        paths.topic_aliases,
        {
            "aliases": {
                "LLM agent test-time scaling": "LLM test-time scaling",
            }
        },
    )

    SiteBuilder(paths).build()

    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))
    daily = json.loads((paths.daily_dir / "2026-05-28.json").read_text(encoding="utf-8"))

    assert [paper["topic_tag"] for paper in search["papers"]] == [
        "LLM test-time scaling",
        "LLM test-time scaling",
    ]
    assert search["topic_tags"] == ["LLM test-time scaling"]
    assert [paper["topic_tag"] for paper in daily["papers"]] == [
        "LLM agent test-time scaling",
        "LLM test-time scaling",
    ]


def test_institution_aliases_are_applied_to_built_site_without_rewriting_daily_data(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Alibaba System",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Alibaba",
                    "topic_tag": "LLM systems",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                },
                {
                    "id": "2605.00002",
                    "daily_date": "2026-05-28",
                    "title": "Alibaba Model",
                    "summary": "Original abstract.",
                    "authors": ["B. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 2,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "alibaba-inc",
                    "topic_tag": "LLM systems",
                    "hf_url": "https://huggingface.co/papers/2605.00002",
                    "arxiv_url": "https://arxiv.org/abs/2605.00002",
                    "project_page": None,
                    "github_repo": None,
                },
            ],
        },
    )
    write_json(
        paths.institution_aliases,
        {
            "aliases": {
                "Alibaba": "alibaba-inc",
            }
        },
    )

    SiteBuilder(paths).build()

    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))
    daily = json.loads((paths.daily_dir / "2026-05-28.json").read_text(encoding="utf-8"))

    assert [paper["institution_tag"] for paper in search["papers"]] == [
        "alibaba-inc",
        "alibaba-inc",
    ]
    assert search["papers"][0]["original_institution_tag"] == "Alibaba"
    assert search["institution_tags"] == ["alibaba-inc"]
    assert [paper["institution_tag"] for paper in daily["papers"]] == [
        "Alibaba",
        "alibaba-inc",
    ]


def test_tag_overrides_are_applied_to_built_site_without_rewriting_daily_data(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Corrected Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Wrong Lab",
                    "topic_tag": "wrong topic",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )
    write_json(
        paths.tag_overrides,
        {
            "paper_overrides": {
                "2605.00001": {
                    "institution_tag": "Correct Institute",
                    "topic_tag": "correct topic",
                }
            }
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))
    daily = json.loads((paths.daily_dir / "2026-05-28.json").read_text(encoding="utf-8"))

    assert search["papers"][0]["institution_tag"] == "Correct Institute"
    assert search["papers"][0]["topic_tag"] == "correct topic"
    assert search["papers"][0]["original_institution_tag"] == "Wrong Lab"
    assert search["papers"][0]["original_topic_tag"] == "wrong topic"
    assert search["institution_tags"] == ["Correct Institute"]
    assert search["topic_tags"] == ["correct topic"]
    assert "Correct Institute" in index
    assert "correct topic" in index
    assert daily["papers"][0]["institution_tag"] == "Wrong Lab"
    assert daily["papers"][0]["topic_tag"] == "wrong topic"


def test_pages_render_manual_tag_editor_and_export_controls(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Editable Paper",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Example University",
                    "topic_tag": "vision-language modeling",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    index = (paths.site_dir / "index.html").read_text(encoding="utf-8")
    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")
    styles = (paths.site_dir / "assets" / "styles.css").read_text(encoding="utf-8")

    assert 'data-paper-id="2605.00001"' in index
    assert 'data-original-institution="Example University"' in index
    assert 'data-original-topic="vision-language modeling"' in index
    assert 'data-tag-role="institution"' in index
    assert 'data-tag-role="topic"' in index
    assert '<button class="tag-edit-toggle secondary" type="button" aria-expanded="false">' in index
    assert re.search(
        r'<div class="tags">\s*'
        r'<span class="tag institution" data-tag-role="institution">Example University</span>\s*'
        r'<span class="tag topic" data-tag-role="topic">vision-language modeling</span>\s*'
        r'<button class="tag-edit-toggle secondary" type="button" aria-expanded="false">',
        index,
    )
    assert '<form class="tag-edit-form" hidden>' in index
    assert 'data-tag-field="institution_tag"' in index
    assert 'data-tag-field="topic_tag"' in index
    assert 'data-suggestion-list="institution_tag"' in index
    assert 'data-suggestion-list="topic_tag"' in index
    assert 'tag-edit-copy' in index
    assert 'tag-edit-export' in index
    assert '<script src="assets/app.js"></script>' in index
    assert not (paths.site_dir / "daily").exists()
    assert 'const tagOverrideStorageKey = "hf_daily_tag_overrides";' in app
    assert "setupTagEditors();" in app
    assert "function isAdminMode(" in app
    assert "function saveTagOverrideToAdmin(" in app
    assert "function overrideValuesForSave(" in app
    assert "hostname === \"127.0.0.1\" || hostname === \"localhost\"" in app
    assert 'fetch("/api/tag-overrides"' in app
    assert "Saved to data/tags/tag_overrides.json and rebuilt site." in app
    assert "const tagSuggestions = buildTagSuggestions();" in app
    assert "function buildTagSuggestions(" in app
    assert "loadGlobalTagSuggestions();" in app
    assert "function loadGlobalTagSuggestions(" in app
    assert "function papersJsonPath(" in app
    assert 'fetch(papersJsonPath())' in app
    assert "refreshOpenTagSuggestions();" in app
    assert "function refreshOpenTagSuggestions(" in app
    assert "function selectTagInputOnFocus(" in app
    assert "input.select();" in app
    assert "function setupTagAutocomplete(" in app
    assert "function renderTagSuggestions(" in app
    assert "function suggestionMatches(" in app
    assert "input.addEventListener(\"input\"" in app
    assert "function exportTagOverrides(" in app
    assert "function copyTagOverrides(" in app
    assert "localStorage.setItem(tagOverrideStorageKey" in app
    assert ".tag-editor" in styles
    assert ".tag-edit-form" in styles
    assert ".tag-suggestions" in styles
    assert ".tag-suggestion" in styles


def test_tag_autocomplete_trims_dom_suggestions_before_deduping(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "daily_date": "2026-05-28",
                    "title": "Trailing Tag",
                    "summary": "Original abstract.",
                    "authors": ["A. Author"],
                    "published_at": "2026-05-28T00:00:00.000Z",
                    "upvotes": 1,
                    "num_comments": 0,
                    "one_sentence_summary": "Summary.",
                    "institution_tag": "Shanghai AI Lab ",
                    "topic_tag": "vision-language modeling ",
                    "hf_url": "https://huggingface.co/papers/2605.00001",
                    "arxiv_url": "https://arxiv.org/abs/2605.00001",
                    "project_page": None,
                    "github_repo": None,
                }
            ],
        },
    )

    SiteBuilder(paths).build()

    app = (paths.site_dir / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'addTagSuggestionTo(suggestions, "institution_tag", card.dataset.institution);' in app
    assert 'addTagSuggestionTo(suggestions, "topic_tag", card.dataset.topic);' in app
    assert "function addTagSuggestionTo(suggestions, field, tag)" in app
    assert 'const value = String(tag || "").trim();' in app
    assert "suggestions.institution_tag.add(card.dataset.institution)" not in app
    assert "suggestions.topic_tag.add(card.dataset.topic)" not in app
