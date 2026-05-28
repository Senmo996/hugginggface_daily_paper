from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


@dataclass(frozen=True)
class LLMGeneration:
    one_sentence_summary: str
    institution_tag: str
    topic_tag: str
    topic_description: str
    topic_is_new: bool


class OpenAICompatibleClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required")
        model = os.getenv("OPENAI_MODEL")
        if not model:
            raise RuntimeError("OPENAI_MODEL is required")
        return cls(
            api_key=api_key,
            model=model,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )

    def generate_metadata(
        self,
        paper: dict[str, Any],
        existing_topics: list[str],
        known_institution: str | None,
    ) -> LLMGeneration:
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=build_generation_messages(paper, existing_topics, known_institution),
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return LLMGeneration(
            one_sentence_summary=str(data["one_sentence_summary"]).strip(),
            institution_tag=str(data.get("institution_tag") or known_institution or "Unknown").strip(),
            topic_tag=str(data["topic_tag"]).strip(),
            topic_description=str(data.get("topic_description") or data["topic_tag"]).strip(),
            topic_is_new=bool(data.get("topic_is_new", False)),
        )


def build_generation_messages(
    paper: dict[str, Any],
    existing_topics: list[str],
    known_institution: str | None,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You classify AI research papers for a local archive. "
                "Return strict JSON only. "
                "one_sentence_summary must be written in Simplified Chinese as one sentence "
                "describing the paper direction and method. "
                "topic_tag must remain English. "
                "Topic tags must be English medium-granularity method or research-direction tags, "
                "not paper titles and not one-off method names. "
                "Use reusable method-family labels such as on-policy distillation, "
                "MLLM retrieval, RAG retrieval, multimodal agents, video diffusion, "
                "LLM memory, world models, PEFT, or benchmark evaluation. "
                "Do not create paper-specific tags like an exact system name, benchmark name, "
                "or title phrase unless it is already a broadly used field term. "
                "Prefer an existing topic tag when it is a reusable medium-granularity match. "
                "Do not reuse an existing tag if it is paper-specific or too narrow; "
                "rename it to a reusable method-family tag instead. "
                "Create a new topic tag only when no reusable existing tag fits."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "paper": {
                        "id": paper.get("id"),
                        "title": paper.get("title"),
                        "abstract": paper.get("summary"),
                        "authors": paper.get("authors", []),
                        "keywords": paper.get("ai_keywords", []),
                        "project_page": paper.get("project_page"),
                        "github_repo": paper.get("github_repo"),
                        "known_institution": known_institution,
                    },
                    "existing_topic_tags": existing_topics,
                    "required_json_schema": {
                        "one_sentence_summary": "string",
                        "institution_tag": "string",
                        "topic_tag": "string",
                        "topic_description": "string",
                        "topic_is_new": "boolean",
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
