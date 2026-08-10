"""설정된 시각에 맞춰 자동으로 글을 생성하고 포스팅하는 스케줄러."""

from __future__ import annotations

import logging
import random

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from playwright.sync_api import sync_playwright

from .config import Config
from .content_generator import ContentGenerator
from .naver_login import open_authenticated_context
from .naver_poster import post_to_blog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler")


def run_post_job(config: Config, topic: str | None = None) -> None:
    topic = topic or (random.choice(config.topics) if config.topics else None)
    if not topic:
        logger.error("config.yaml의 topics가 비어 있어 글 주제를 정할 수 없습니다.")
        return

    logger.info("주제 '%s'로 글 생성을 시작합니다.", topic)
    generator = ContentGenerator(config.anthropic_api_key, config.anthropic_model)
    post = generator.generate(
        topic=topic,
        tone=config.content.tone,
        min_length=config.content.min_length,
    )
    logger.info("글 생성 완료: %s (%d개 문단)", post.title, len(post.paragraphs))

    with sync_playwright() as playwright:
        browser, context = open_authenticated_context(playwright, headless=config.headless)
        try:
            page = context.new_page()
            result = post_to_blog(
                page=page,
                blog_id=config.naver_blog_id,
                title=post.title,
                paragraphs=post.paragraphs,
                tags=post.tags,
            )
            if result.success:
                logger.info("포스팅 성공: %s", result.message)
            else:
                logger.error("포스팅 실패: %s", result.message)
        finally:
            browser.close()


def run_scheduler(config: Config) -> None:
    scheduler = BlockingScheduler(timezone=config.schedule.timezone)

    for time_str in config.schedule.times:
        hour, minute = time_str.split(":")
        scheduler.add_job(
            run_post_job,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            args=[config],
            id=f"naver-blog-post-{time_str}",
            misfire_grace_time=3600,
        )
        logger.info("스케줄 등록: 매일 %s (%s)", time_str, config.schedule.timezone)

    logger.info("스케줄러를 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러를 종료합니다.")
