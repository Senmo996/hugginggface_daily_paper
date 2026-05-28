import json

import httpx

from hf_daily.cli import main


class FakeLLMClient:
    def generate_metadata(self, paper, existing_topics, known_institution):
        from hf_daily.llm import LLMGeneration

        return LLMGeneration(
            one_sentence_summary="A native VLM learns pixel-word alignment end to end.",
            institution_tag="Fallback Lab",
            topic_tag="native vision-language modeling",
            topic_description="End-to-end multimodal vision-language model training.",
            topic_is_new=True,
        )


def test_cli_run_fetches_generates_and_builds(tmp_path, monkeypatch):
    def handler(request):
        assert request.url.path == "/api/daily_papers"
        assert request.url.params["date"] == "2026-05-28"
        return httpx.Response(
            200,
            json=[
                {
                    "paper": {
                        "id": "2605.00001",
                        "title": "Native VLM",
                        "summary": "A native one-vision model.",
                        "authors": [{"name": "A. Author"}],
                        "organization": {"fullname": "Existing University"},
                    }
                }
            ],
        )

    import hf_daily.cli as cli_module

    monkeypatch.setattr(cli_module, "build_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr(
        cli_module,
        "build_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler), base_url="https://huggingface.co"),
    )

    exit_code = main(["--root", str(tmp_path), "run", "--date", "2026-05-28"])

    assert exit_code == 0
    assert json.loads((tmp_path / "data" / "raw" / "2026-05-28.json").read_text())[
        0
    ]["paper"]["id"] == "2605.00001"
    assert (tmp_path / "data" / "daily" / "2026-05-28.json").exists()
    assert (tmp_path / "site" / "index.html").exists()


def test_cli_run_prints_progress(tmp_path, monkeypatch, capsys):
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "paper": {
                        "id": "2605.00001",
                        "title": "Native VLM",
                        "summary": "A native one-vision model.",
                        "authors": [{"name": "A. Author"}],
                    }
                }
            ],
        )

    import hf_daily.cli as cli_module

    monkeypatch.setattr(cli_module, "build_llm_client", lambda: FakeLLMClient())
    monkeypatch.setattr(
        cli_module,
        "build_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler), base_url="https://huggingface.co"),
    )

    assert main(["--root", str(tmp_path), "run", "--date", "2026-05-28"]) == 0

    output = capsys.readouterr().out
    assert "Fetching Hugging Face Daily Papers for 2026-05-28" in output
    assert "Generating 1/1: 2605.00001 - Native VLM" in output
    assert "Building static site" in output
    assert "Done. Open" in output


def test_cli_generate_without_api_key_exits_cleanly(tmp_path, monkeypatch, capsys):
    import hf_daily.cli as cli_module

    monkeypatch.setattr(cli_module, "build_llm_client", lambda: (_ for _ in ()).throw(RuntimeError("OPENAI_API_KEY is required")))

    exit_code = main(["--root", str(tmp_path), "generate", "--date", "2026-05-28"])

    assert exit_code == 2
    assert "OPENAI_API_KEY is required" in capsys.readouterr().err


def test_cli_admin_builds_site_and_starts_local_server(tmp_path, monkeypatch, capsys):
    import hf_daily.cli as cli_module

    started = {}

    class FakeAdminServer:
        server_port = 8765

        def serve_forever(self):
            started["served"] = True
            raise KeyboardInterrupt

        def server_close(self):
            started["closed"] = True

    monkeypatch.setattr(
        cli_module,
        "create_admin_server",
        lambda paths, host, port: started.update(
            {"root": paths.root, "host": host, "port": port}
        )
        or FakeAdminServer(),
    )

    exit_code = main(["--root", str(tmp_path), "admin", "--port", "8765"])

    assert exit_code == 0
    assert started == {
        "root": tmp_path.resolve(),
        "host": "127.0.0.1",
        "port": 8765,
        "served": True,
        "closed": True,
    }
    output = capsys.readouterr().out
    assert "Building static site" in output
    assert "Local admin ready at http://127.0.0.1:8765/index.html" in output
