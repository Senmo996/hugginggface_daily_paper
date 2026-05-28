import http.client
import json
import threading

from hf_daily.admin_server import create_admin_server
from hf_daily.site_builder import SiteBuilder
from hf_daily.storage import ProjectPaths


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_daily_fixture(paths):
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


def test_admin_server_saves_tag_override_and_rebuilds_site(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_daily_fixture(paths)
    SiteBuilder(paths).build()
    server = create_admin_server(paths, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        body = json.dumps(
            {
                "paper_id": "2605.00001",
                "institution_tag": "Correct Institute",
                "topic_tag": "correct topic",
            }
        )
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/tag-overrides",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    overrides = json.loads(paths.tag_overrides.read_text(encoding="utf-8"))
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    assert response.status == 200
    assert payload["status"] == "saved"
    assert overrides["paper_overrides"]["2605.00001"] == {
        "institution_tag": "Correct Institute",
        "topic_tag": "correct topic",
    }
    assert search["papers"][0]["institution_tag"] == "Correct Institute"
    assert search["papers"][0]["topic_tag"] == "correct topic"


def test_admin_server_deletes_override_when_no_tags_are_sent(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_daily_fixture(paths)
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
    server = create_admin_server(paths, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/api/tag-overrides",
            body=json.dumps({"paper_id": "2605.00001"}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    overrides = json.loads(paths.tag_overrides.read_text(encoding="utf-8"))
    search = json.loads((paths.site_dir / "assets" / "papers.json").read_text(encoding="utf-8"))

    assert response.status == 200
    assert payload["status"] == "saved"
    assert overrides["paper_overrides"] == {}
    assert search["papers"][0]["institution_tag"] == "Wrong Lab"
    assert search["papers"][0]["topic_tag"] == "wrong topic"


def test_admin_server_disables_browser_cache_for_static_assets(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_daily_fixture(paths)
    SiteBuilder(paths).build()
    server = create_admin_server(paths, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request("GET", "/assets/app.js")
        response = connection.getresponse()
        response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status == 200
    assert response.getheader("Cache-Control") == "no-store"
