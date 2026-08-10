"""네이버 블로그 SmartEditor ONE 자동 글쓰기.

주의: 이 모듈은 네이버 블로그 에디터의 DOM 구조에 의존한다. 네이버가 에디터를
업데이트하면 선택자(selector)가 바뀌어 동작하지 않을 수 있다. 그런 경우
`--dry-run`으로 실행해 storage/last_attempt.png 스크린샷을 확인하고,
아래 *_SELECTORS 목록에 새 선택자를 추가해서 고치면 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import FrameLocator, Page, TimeoutError as PWTimeoutError

from .config import STORAGE_DIR

WRITE_URL_TMPL = "https://blog.naver.com/{blog_id}?Redirect=Write&"

TITLE_SELECTORS = [
    ".se-section-documentTitle .se-text-paragraph",
    ".se-documentTitle .se-text-paragraph",
]

BODY_SELECTORS = [
    ".se-main-container .se-component-content .se-text-paragraph",
    ".se-main-container .se-text-paragraph",
]

CONTINUE_POPUP_CANCEL_TEXT = "취소"
PUBLISH_BUTTON_TEXT = "발행"
TAG_INPUT_PLACEHOLDER = "태그를 입력해 주세요"


@dataclass
class PostResult:
    success: bool
    message: str
    screenshot_path: str | None = None


def _get_editor_frame(page: Page) -> FrameLocator:
    return page.frame_locator("iframe#mainFrame")


def _dismiss_continue_popup(frame: FrameLocator) -> None:
    """'이어서 작성하시겠습니까?' 팝업이 뜨면 취소(새 글 작성)를 누른다."""
    try:
        cancel_btn = frame.get_by_role("button", name=CONTINUE_POPUP_CANCEL_TEXT)
        cancel_btn.wait_for(state="visible", timeout=3000)
        cancel_btn.click()
    except PWTimeoutError:
        pass  # 팝업이 없으면 그대로 진행


def _click_first_visible(frame: FrameLocator, selectors: list[str], timeout: int = 8000):
    last_error: Exception | None = None
    for selector in selectors:
        try:
            locator = frame.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return locator
        except PWTimeoutError as e:  # noqa: PERF203
            last_error = e
            continue
    raise RuntimeError(
        f"선택자를 찾지 못했습니다 (시도: {selectors}). 네이버 에디터 구조가 "
        f"변경되었을 수 있습니다."
    ) from last_error


def _type_body(page: Page, frame: FrameLocator, paragraphs: list[str]) -> None:
    _click_first_visible(frame, BODY_SELECTORS)
    for i, paragraph in enumerate(paragraphs):
        page.keyboard.type(paragraph, delay=10)
        if i != len(paragraphs) - 1:
            page.keyboard.press("Enter")


def _type_title_text(page: Page, frame: FrameLocator, title: str) -> None:
    _click_first_visible(frame, TITLE_SELECTORS)
    page.keyboard.type(title, delay=20)


def _apply_tags(page: Page, frame: FrameLocator, tags: list[str]) -> None:
    if not tags:
        return
    try:
        tag_input = frame.get_by_placeholder(TAG_INPUT_PLACEHOLDER)
        tag_input.wait_for(state="visible", timeout=5000)
        for tag in tags:
            tag_input.click()
            page.keyboard.type(tag, delay=20)
            page.keyboard.press("Enter")
    except PWTimeoutError:
        pass  # 태그 입력 UI를 찾지 못해도 발행은 계속 진행한다


def post_to_blog(
    page: Page,
    blog_id: str,
    title: str,
    paragraphs: list[str],
    tags: list[str] | None = None,
    dry_run: bool = False,
) -> PostResult:
    tags = tags or []
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = str(STORAGE_DIR / "last_attempt.png")

    try:
        page.goto(WRITE_URL_TMPL.format(blog_id=blog_id), wait_until="domcontentloaded")
        frame = _get_editor_frame(page)
        _dismiss_continue_popup(frame)

        _type_title_text(page, frame, title)
        _type_body(page, frame, paragraphs)

        page.screenshot(path=screenshot_path, full_page=True)

        if dry_run:
            return PostResult(
                success=True,
                message="dry-run: 제목/본문 입력까지 완료했고 발행은 하지 않았습니다.",
                screenshot_path=screenshot_path,
            )

        publish_open_btn = frame.get_by_role("button", name=PUBLISH_BUTTON_TEXT).first
        publish_open_btn.click()

        _apply_tags(page, frame, tags)

        # 발행 패널의 최종 확인 버튼. 상단 버튼과 텍스트가 같으므로 마지막 것을 클릭한다.
        confirm_btn = frame.get_by_role("button", name=PUBLISH_BUTTON_TEXT).last
        confirm_btn.wait_for(state="visible", timeout=8000)
        confirm_btn.click()

        page.wait_for_timeout(3000)
        page.screenshot(path=screenshot_path, full_page=True)

        return PostResult(
            success=True,
            message="포스팅을 발행했습니다.",
            screenshot_path=screenshot_path,
        )

    except Exception as e:  # noqa: BLE001
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:  # noqa: BLE001
            screenshot_path = None
        return PostResult(
            success=False,
            message=f"포스팅 중 오류가 발생했습니다: {e}",
            screenshot_path=screenshot_path,
        )
