import json

from hf_daily.llm import build_generation_messages


def test_generation_prompt_requests_medium_granularity_topic_tags():
    messages = build_generation_messages(
        paper={
            "id": "2605.27028",
            "title": "Less is More: Early Stopping Rollout for On-Policy Distillation",
            "summary": "A method for on-policy distillation.",
            "authors": ["A. Author"],
        },
        existing_topics=[
            "Early-Stopped On-Policy LLM Distillation",
            "MLLM retrieval",
        ],
        known_institution="Example University",
    )

    system_prompt = messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])

    assert "medium-granularity" in system_prompt
    assert "Do not create paper-specific" in system_prompt
    assert "on-policy distillation" in system_prompt
    assert "MLLM retrieval" in system_prompt
    assert user_payload["existing_topic_tags"] == [
        "Early-Stopped On-Policy LLM Distillation",
        "MLLM retrieval",
    ]


def test_generation_prompt_requests_chinese_one_sentence_summary():
    messages = build_generation_messages(
        paper={
            "id": "2605.28820",
            "title": "From Pixels to Words",
            "summary": "A native multimodal model.",
        },
        existing_topics=[],
        known_institution=None,
    )

    system_prompt = messages[0]["content"]

    assert "one_sentence_summary must be written in Simplified Chinese" in system_prompt
    assert "topic_tag must remain English" in system_prompt


def test_generation_prompt_instructs_model_not_to_reuse_over_specific_existing_tags():
    messages = build_generation_messages(
        paper={
            "id": "2605.27028",
            "title": "Less is More: Early Stopping Rollout for On-Policy Distillation",
            "summary": "A method for on-policy distillation.",
        },
        existing_topics=["Early-Stopped On-Policy LLM Distillation"],
        known_institution=None,
    )

    system_prompt = messages[0]["content"]

    assert "Do not reuse an existing tag if it is paper-specific" in system_prompt
    assert "rename it to a reusable method-family tag" in system_prompt
