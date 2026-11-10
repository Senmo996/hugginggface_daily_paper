import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hf_daily.llm import OpenAICompatibleClient


VALID_METADATA = {
    "one_sentence_summary": "该论文通过低秩适配器实现多目标偏好优化。",
    "institution_tag": "Example Lab",
    "topic_tag": "preference optimization",
    "topic_description": "Methods for optimizing preferences.",
    "topic_is_new": False,
}


def response(content, finish_reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content), finish_reason=finish_reason,
    )])


def client_with_responses(*responses):
    client = OpenAICompatibleClient.__new__(OpenAICompatibleClient)
    client.model = "test-model"
    client.client = Mock()
    client.client.chat.completions.create.side_effect = responses
    return client


def generate(client, known_institution=None):
    return client.generate_metadata(
        {"id": "2611.09634", "title": "Test paper", "summary": "Test abstract"},
        ["preference optimization"],
        known_institution,
    )


def test_valid_metadata_needs_one_request():
    client = client_with_responses(response(json.dumps(VALID_METADATA)))
    result = generate(client)
    assert result.one_sentence_summary == VALID_METADATA["one_sentence_summary"]
    assert result.topic_tag == VALID_METADATA["topic_tag"]
    assert result.topic_is_new is False
    assert client.client.chat.completions.create.call_count == 1


@pytest.mark.parametrize("bad_response", [
    response('{"topic_tag":"preference optimization"}'),
    response('{"one_sentence_summary":"summary"}'),
    response(json.dumps({"metadata": VALID_METADATA})),
    response("{}"),
    response(None),
    response("   "),
    response("not JSON"),
    response("[]"),
    response('{"one_sentence_summary":'),
    response(json.dumps(VALID_METADATA), "length"),
    SimpleNamespace(choices=[]),
])
def test_invalid_response_is_retried_with_validation_feedback(bad_response, caplog):
    client = client_with_responses(bad_response, response(json.dumps(VALID_METADATA)))
    assert generate(client).one_sentence_summary == VALID_METADATA["one_sentence_summary"]
    calls = client.client.chat.completions.create.call_args_list
    assert len(calls) == 2
    assert "failed validation" in calls[1].kwargs["messages"][-1]["content"]
    assert "2611.09634" in caplog.text
    assert "attempt 1/3" in caplog.text


@pytest.mark.parametrize("field,value", [
    ("one_sentence_summary", None),
    ("one_sentence_summary", "  "),
    ("one_sentence_summary", ["summary"]),
    ("topic_tag", 42),
    ("topic_tag", ""),
    ("institution_tag", {"name": "lab"}),
    ("topic_description", ["description"]),
    ("topic_is_new", "false"),
    ("topic_is_new", 1),
])
def test_wrong_field_types_are_retried(field, value):
    client = client_with_responses(
        response(json.dumps({**VALID_METADATA, field: value})),
        response(json.dumps(VALID_METADATA)),
    )
    assert generate(client).topic_is_new is False
    assert client.client.chat.completions.create.call_count == 2


def test_repeated_invalid_metadata_raises_contextual_error():
    client = client_with_responses(*[
        response('{"topic_tag":"preference optimization"}') for _ in range(3)
    ])
    with pytest.raises(RuntimeError) as caught:
        generate(client)
    error = str(caught.value)
    assert "2611.09634" in error
    assert "attempt 3/3" in error
    assert "finish_reason=stop" in error
    assert "keys=['topic_tag']" in error
    assert "one_sentence_summary must be a non-empty string" in error
    assert client.client.chat.completions.create.call_count == 3


def test_optional_defaults_and_whitespace_are_preserved():
    client = client_with_responses(response(json.dumps({
        "one_sentence_summary": " summary ", "topic_tag": " PEFT ",
        "institution_tag": " ", "topic_description": None,
    })))
    result = generate(client, known_institution="Known Lab")
    assert result.one_sentence_summary == "summary"
    assert result.institution_tag == "Known Lab"
    assert result.topic_tag == result.topic_description == "PEFT"
    assert result.topic_is_new is False


def test_api_errors_are_not_retried_by_metadata_validation():
    client = client_with_responses(RuntimeError("API unavailable"))
    with pytest.raises(RuntimeError, match="API unavailable"):
        generate(client)
    assert client.client.chat.completions.create.call_count == 1
