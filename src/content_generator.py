"""Claude API를 이용해 네이버 블로그용 글(제목/본문/태그)을 생성한다."""

from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "클릭을 유도하는 매력적인 블로그 제목 (30자 내외)",
        },
        "paragraphs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "본문을 문단 단위로 나눈 배열. 각 문단은 2~5문장.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "네이버 블로그 태그로 쓸 키워드 5~10개 (# 없이)",
        },
    },
    "required": ["title", "paragraphs", "tags"],
    "additionalProperties": False,
}


@dataclass
class GeneratedPost:
    title: str
    paragraphs: list[str]
    tags: list[str]

    @property
    def body_text(self) -> str:
        return "\n\n".join(self.paragraphs)


class ContentGenerator:
    def __init__(self, api_key: str, model: str = "claude-opus-5"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, topic: str, tone: str, min_length: int) -> GeneratedPost:
        prompt = (
            f"너는 네이버 블로그 전문 작가야. 아래 조건에 맞는 블로그 글을 작성해줘.\n\n"
            f"- 주제: {topic}\n"
            f"- 톤앤매너: {tone}\n"
            f"- 전체 분량: 최소 {min_length}자 이상 (공백 포함)\n"
            f"- 문단은 읽기 쉽게 여러 개로 나눌 것 (문단당 2~5문장)\n"
            f"- 과장되거나 확인되지 않은 사실(의학적 효능, 통계 등)은 쓰지 말 것\n"
            f"- 광고 문구나 홍보성 어투 대신 정보 전달과 경험 공유 위주로 작성할 것\n"
            f"- 결과는 지정된 JSON 스키마 형식으로만 반환할 것"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            messages=[{"role": "user", "content": prompt}],
        )

        text = next(block.text for block in response.content if block.type == "text")
        data = json.loads(text)

        return GeneratedPost(
            title=data["title"].strip(),
            paragraphs=[p.strip() for p in data["paragraphs"] if p.strip()],
            tags=[t.strip() for t in data["tags"] if t.strip()],
        )
