"""환경 변수(.env)와 config.yaml을 읽어 하나의 설정 객체로 제공한다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT_DIR / "storage"
STORAGE_STATE_PATH = STORAGE_DIR / "naver_storage_state.json"

load_dotenv(ROOT_DIR / ".env")

# .env에 ANTHROPIC_API_KEY= 처럼 빈 값으로 남아있으면 os.environ에는 빈 문자열로
# "설정된" 상태가 되어버린다. 그 상태로 두면 Anthropic SDK가 "키가 비어있음"으로
# 판단해 ant auth login/Claude Code 구독 인증으로 넘어가지 못할 수 있으므로,
# 비어있는 값은 아예 없는 것처럼 제거한다.
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ.pop("ANTHROPIC_API_KEY", None)


@dataclass
class ScheduleConfig:
    times: list[str] = field(default_factory=lambda: ["09:00"])
    timezone: str = "Asia/Seoul"


@dataclass
class ContentConfig:
    language: str = "ko"
    min_length: int = 800
    tone: str = "친근하고 정보 전달이 명확한 블로그 톤"


@dataclass
class Config:
    naver_id: str
    naver_pw: str
    naver_blog_id: str
    anthropic_api_key: str
    anthropic_model: str
    topics: list[str]
    category: str
    schedule: ScheduleConfig
    content: ContentConfig
    headless: bool = True

    @classmethod
    def load(cls, config_path: str | Path = ROOT_DIR / "config.yaml") -> "Config":
        config_path = Path(config_path)
        raw: dict = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

        schedule_raw = raw.get("schedule", {}) or {}
        content_raw = raw.get("content", {}) or {}

        naver_id = os.environ.get("NAVER_ID", "")
        naver_pw = os.environ.get("NAVER_PW", "")
        naver_blog_id = os.environ.get("NAVER_BLOG_ID") or raw.get("blog_id", "")
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

        if not naver_blog_id:
            raise ValueError(
                "네이버 블로그 아이디가 없습니다. .env의 NAVER_BLOG_ID 또는 "
                "config.yaml의 blog_id를 설정하세요."
            )

        return cls(
            naver_id=naver_id,
            naver_pw=naver_pw,
            naver_blog_id=naver_blog_id,
            anthropic_api_key=anthropic_api_key,
            anthropic_model=anthropic_model,
            topics=raw.get("topics", []) or [],
            category=raw.get("category", "") or "",
            schedule=ScheduleConfig(
                times=schedule_raw.get("times", ["09:00"]),
                timezone=schedule_raw.get("timezone", "Asia/Seoul"),
            ),
            content=ContentConfig(
                language=content_raw.get("language", "ko"),
                min_length=content_raw.get("min_length", 800),
                tone=content_raw.get("tone", "친근하고 정보 전달이 명확한 블로그 톤"),
            ),
            headless=raw.get("headless", True),
        )
