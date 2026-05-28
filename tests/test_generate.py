import json

from hf_daily.generator import DailyGenerator
from hf_daily.llm import LLMGeneration
from hf_daily.storage import ProjectPaths


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate_metadata(self, paper, existing_topics, known_institution):
        self.calls.append(
            {
                "paper_id": paper["id"],
                "existing_topics": list(existing_topics),
                "known_institution": known_institution,
            }
        )
        if paper["id"] == "2605.00001":
            return LLMGeneration(
                one_sentence_summary="A native VLM learns pixel-word alignment end to end.",
                institution_tag="Should Not Override",
                topic_tag="native vision-language modeling",
                topic_description="End-to-end multimodal models that learn visual and textual alignment natively.",
                topic_is_new=False,
            )
        return LLMGeneration(
            one_sentence_summary="A retrieval method improves tool-use reasoning.",
            institution_tag="Example AI Lab",
            topic_tag="affordance-grounded tool use",
            topic_description="Multimodal reasoning about object affordances for physical tool use.",
            topic_is_new=True,
        )


class OnPolicyLLMClient:
    def __init__(self):
        self.calls = []

    def generate_metadata(self, paper, existing_topics, known_institution):
        self.calls.append(list(existing_topics))
        return LLMGeneration(
            one_sentence_summary="The paper improves on-policy distillation with early rollout stopping.",
            institution_tag=known_institution or "Example AI Lab",
            topic_tag="on-policy distillation",
            topic_description="Policy distillation methods that train student models from on-policy rollouts.",
            topic_is_new=True,
        )


class CheckpointLLMClient:
    def __init__(self, paths):
        self.paths = paths
        self.calls = 0

    def generate_metadata(self, paper, existing_topics, known_institution):
        self.calls += 1
        if self.calls == 2:
            daily_payload = json.loads(
                (self.paths.daily_dir / "2026-05-28.json").read_text(encoding="utf-8")
            )
            assert daily_payload["status"] == "partial"
            assert [paper["id"] for paper in daily_payload["papers"]] == ["2605.00001"]
        return LLMGeneration(
            one_sentence_summary=f"Summary for {paper['id']}.",
            institution_tag=known_institution or "Example AI Lab",
            topic_tag="native vision-language modeling",
            topic_description="End-to-end multimodal models that learn visual and textual alignment natively.",
            topic_is_new=False,
        )


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_generate_reuses_existing_topic_and_preserves_hf_institution(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
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
    write_json(
        paths.topic_tags,
        {
            "topics": [
                {
                    "name": "native vision-language modeling",
                    "description": "Existing topic.",
                    "created_at": "2026-05-01T00:00:00Z",
                    "usage_count": 3,
                    "examples": ["2505.00000"],
                }
            ]
        },
    )

    generator = DailyGenerator(paths=paths, llm_client=FakeLLMClient())
    result = generator.generate("2026-05-28")

    paper = result["papers"][0]
    assert paper["one_sentence_summary"] == "A native VLM learns pixel-word alignment end to end."
    assert paper["institution_tag"] == "Existing University"
    assert paper["topic_tag"] == "native vision-language modeling"

    topics = json.loads(paths.topic_tags.read_text(encoding="utf-8"))["topics"]
    assert topics[0]["usage_count"] == 4
    assert topics[0]["examples"] == ["2505.00000", "2605.00001"]


def test_generate_uses_llm_for_missing_institution_and_creates_topic(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
            {
                "paper": {
                    "id": "2605.00002",
                    "title": "Creative Tool Use",
                    "summary": "A benchmark for creative physical intelligence.",
                    "authors": [{"name": "B. Author"}],
                }
            }
        ],
    )

    llm = FakeLLMClient()
    generator = DailyGenerator(paths=paths, llm_client=llm)
    result = generator.generate("2026-05-28")

    paper = result["papers"][0]
    assert paper["institution_tag"] == "Example AI Lab"
    assert paper["topic_tag"] == "affordance-grounded tool use"
    assert llm.calls[0]["known_institution"] is None

    topics = json.loads(paths.topic_tags.read_text(encoding="utf-8"))["topics"]
    assert topics == [
        {
            "name": "affordance-grounded tool use",
            "description": "Multimodal reasoning about object affordances for physical tool use.",
            "created_at": topics[0]["created_at"],
            "usage_count": 1,
            "examples": ["2605.00002"],
        }
    ]


def test_generate_skips_existing_papers_unless_forced(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
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
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "one_sentence_summary": "Existing summary.",
                    "institution_tag": "Existing University",
                    "topic_tag": "native vision-language modeling",
                }
            ],
        },
    )

    llm = FakeLLMClient()
    generator = DailyGenerator(paths=paths, llm_client=llm)
    result = generator.generate("2026-05-28")

    assert result["papers"][0]["one_sentence_summary"] == "Existing summary."
    assert llm.calls == []


def test_generate_reports_progress_and_writes_partial_checkpoint(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
            {
                "paper": {
                    "id": "2605.00001",
                    "title": "Native VLM",
                    "summary": "A native one-vision model.",
                    "authors": [{"name": "A. Author"}],
                    "organization": {"fullname": "Existing University"},
                }
            },
            {
                "paper": {
                    "id": "2605.00002",
                    "title": "Another Native VLM",
                    "summary": "Another native one-vision model.",
                    "authors": [{"name": "B. Author"}],
                    "organization": {"fullname": "Existing University"},
                }
            },
        ],
    )
    messages = []

    generator = DailyGenerator(paths=paths, llm_client=CheckpointLLMClient(paths))
    result = generator.generate("2026-05-28", progress=messages.append)

    assert result["status"] == "complete"
    assert result["paper_count"] == 2
    assert messages == [
        "Generating 1/2: 2605.00001 - Native VLM",
        "Generating 2/2: 2605.00002 - Another Native VLM",
    ]


def test_generate_reports_skipped_existing_papers(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
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
    write_json(
        paths.daily_dir / "2026-05-28.json",
        {
            "date": "2026-05-28",
            "papers": [
                {
                    "id": "2605.00001",
                    "title": "Native VLM",
                    "one_sentence_summary": "Existing summary.",
                    "institution_tag": "Existing University",
                    "topic_tag": "native vision-language modeling",
                }
            ],
        },
    )
    messages = []

    DailyGenerator(paths=paths, llm_client=FakeLLMClient()).generate(
        "2026-05-28",
        progress=messages.append,
    )

    assert messages == ["Skipping existing 1/1: 2605.00001 - Native VLM"]


def test_generate_can_reset_over_specific_topic_tags_before_regeneration(tmp_path):
    paths = ProjectPaths(tmp_path)
    write_json(
        paths.raw_dir / "2026-05-28.json",
        [
            {
                "paper": {
                    "id": "2605.27028",
                    "title": "Less is More: Early Stopping Rollout for On-Policy Distillation",
                    "summary": "A method for on-policy distillation.",
                    "authors": [{"name": "A. Author"}],
                    "organization": {"fullname": "Example University"},
                }
            }
        ],
    )
    write_json(
        paths.topic_tags,
        {
            "topics": [
                {
                    "name": "Early-Stopped On-Policy LLM Distillation",
                    "description": "Too specific.",
                    "created_at": "2026-05-28T00:00:00Z",
                    "usage_count": 1,
                    "examples": ["2605.27028"],
                }
            ]
        },
    )

    llm = OnPolicyLLMClient()
    result = DailyGenerator(paths=paths, llm_client=llm).generate(
        "2026-05-28",
        force=True,
        reset_topic_tags=True,
    )

    assert llm.calls == [[]]
    assert result["papers"][0]["topic_tag"] == "on-policy distillation"
    topics = json.loads(paths.topic_tags.read_text(encoding="utf-8"))["topics"]
    assert [topic["name"] for topic in topics] == ["on-policy distillation"]
