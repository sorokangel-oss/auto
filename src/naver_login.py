"""네이버 로그인 및 세션(storage_state) 관리.

네이버는 자동화된 로그인 폼 제출을 캡차/2단계 인증으로 막는 경우가 많다.
따라서 로그인은 "화면이 보이는(headed) 브라우저"에서 아이디/비밀번호만 자동
입력해두고, 캡차 통과나 최종 로그인 버튼 클릭은 사람이 직접 하도록 설계했다.
한 번 로그인에 성공하면 세션 쿠키를 storage/naver_storage_state.json 에 저장해
이후에는 재로그인 없이 재사용한다.
"""

from __future__ import annotations

import time

from playwright.sync_api import BrowserContext, Page, Playwright

from .config import STORAGE_DIR, STORAGE_STATE_PATH

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
LOGIN_CHECK_URL = "https://www.naver.com"
LOGIN_WAIT_TIMEOUT_SEC = 600  # 사람이 캡차/2단계 인증을 풀 시간 (최대 10분)


def _fill_login_form(page: Page, naver_id: str, naver_pw: str) -> None:
    """아이디/비밀번호 입력만 자동화한다. 로그인 버튼 클릭은 사용자가 한다."""
    page.wait_for_selector("#id", timeout=15000)
    page.click("#id")
    page.keyboard.type(naver_id, delay=80)
    page.click("#pw")
    page.keyboard.type(naver_pw, delay=80)


def _is_logged_in(context: BrowserContext) -> bool:
    cookies = context.cookies(LOGIN_CHECK_URL)
    return any(c["name"] == "NID_AUT" for c in cookies)


def interactive_login(playwright: Playwright, naver_id: str, naver_pw: str) -> None:
    """headed 브라우저를 열어 로그인하고 세션을 저장한다."""
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(locale="ko-KR")
    page = context.new_page()
    page.goto(NAVER_LOGIN_URL)

    if naver_id and naver_pw:
        try:
            _fill_login_form(page, naver_id, naver_pw)
            print("아이디/비밀번호를 입력했습니다. 캡차가 나오면 직접 풀고 로그인 버튼을 눌러주세요.")
        except Exception as e:  # noqa: BLE001 - 자동 입력 실패는 치명적이지 않음
            print(f"자동 입력에 실패했습니다 ({e}). 브라우저에서 직접 로그인해주세요.")
    else:
        print(".env에 NAVER_ID/NAVER_PW가 없습니다. 브라우저에서 직접 로그인해주세요.")

    print("로그인 완료를 기다리는 중... (최대 10분)")
    deadline = time.time() + LOGIN_WAIT_TIMEOUT_SEC
    while time.time() < deadline:
        if _is_logged_in(context):
            print("로그인 성공을 확인했습니다. 세션을 저장합니다.")
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(STORAGE_STATE_PATH))
            browser.close()
            return
        time.sleep(2)

    browser.close()
    raise TimeoutError(
        "로그인 완료를 확인하지 못했습니다. 다시 `login` 명령을 실행해주세요."
    )


def open_authenticated_context(
    playwright: Playwright, headless: bool = True
) -> tuple:
    """저장된 세션으로 브라우저 컨텍스트를 연다. 세션이 없으면 예외를 던진다."""
    if not STORAGE_STATE_PATH.exists():
        raise FileNotFoundError(
            "저장된 로그인 세션이 없습니다. 먼저 `python main.py login`을 실행하세요."
        )
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        storage_state=str(STORAGE_STATE_PATH), locale="ko-KR"
    )
    if not _is_logged_in(context):
        browser.close()
        raise PermissionError(
            "저장된 세션이 만료되었습니다. `python main.py login`을 다시 실행하세요."
        )
    return browser, context
