"""네이버 블로그 자동 포스팅 프로그램 CLI.

사용 예시:
    python main.py login                       # 최초 1회, 네이버 로그인 및 세션 저장
    python main.py post-now --topic "가을 등산 코스 추천"
    python main.py post-now --topic "..." --dry-run   # 발행 전 입력만 테스트
    python main.py run-scheduler                # config.yaml 스케줄대로 자동 실행
"""

from __future__ import annotations

import argparse
import sys

from playwright.sync_api import sync_playwright

from src.config import Config
from src.content_generator import ContentGenerator
from src.naver_login import interactive_login, open_authenticated_context
from src.naver_poster import post_to_blog
from src.scheduler import run_scheduler


def cmd_login(_args: argparse.Namespace) -> None:
    config = Config.load()
    with sync_playwright() as playwright:
        interactive_login(playwright, config.naver_id, config.naver_pw)
    print("로그인 세션 저장이 완료되었습니다. 이제 post-now / run-scheduler를 사용할 수 있습니다.")


def cmd_post_now(args: argparse.Namespace) -> None:
    config = Config.load()

    generator = ContentGenerator(config.anthropic_api_key, config.anthropic_model)
    print(f"'{args.topic}' 주제로 글을 생성하는 중...")
    post = generator.generate(
        topic=args.topic,
        tone=config.content.tone,
        min_length=config.content.min_length,
    )
    print(f"제목: {post.title}")
    print(f"태그: {', '.join(post.tags)}")
    print(f"본문 미리보기:\n{post.body_text[:300]}...\n")

    with sync_playwright() as playwright:
        browser, context = open_authenticated_context(playwright, headless=config.headless and not args.show_browser)
        try:
            page = context.new_page()
            result = post_to_blog(
                page=page,
                blog_id=config.naver_blog_id,
                title=post.title,
                paragraphs=post.paragraphs,
                tags=post.tags,
                dry_run=args.dry_run,
            )
            print(result.message)
            if result.screenshot_path:
                print(f"스크린샷 저장: {result.screenshot_path}")
            if not result.success:
                sys.exit(1)
        finally:
            browser.close()


def cmd_run_scheduler(_args: argparse.Namespace) -> None:
    config = Config.load()
    run_scheduler(config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="네이버 블로그 자동 포스팅 프로그램")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="네이버 로그인 후 세션 저장")
    login_parser.set_defaults(func=cmd_login)

    post_parser = subparsers.add_parser("post-now", help="지금 바로 글 1개 생성 및 발행")
    post_parser.add_argument("--topic", required=True, help="글 주제")
    post_parser.add_argument(
        "--dry-run", action="store_true", help="발행 없이 입력까지만 테스트"
    )
    post_parser.add_argument(
        "--show-browser",
        action="store_true",
        help="브라우저 창을 띄워서 실행 (디버깅용)",
    )
    post_parser.set_defaults(func=cmd_post_now)

    scheduler_parser = subparsers.add_parser(
        "run-scheduler", help="config.yaml의 스케줄대로 자동 포스팅 시작"
    )
    scheduler_parser.set_defaults(func=cmd_run_scheduler)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
