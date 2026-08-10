# 네이버 블로그 자동 포스팅 프로그램

Claude API로 블로그 글(제목/본문/태그)을 생성하고, Playwright로 네이버 블로그에
자동으로 로그인·발행하는 파이썬 프로그램입니다. 매일 정해진 시각에 자동으로
포스팅하는 스케줄러도 포함되어 있습니다.

## ⚠️ 먼저 읽어주세요

- 네이버는 공식적으로 개인 개발자에게 블로그 글쓰기 API를 제공하지 않습니다.
  이 프로그램은 **브라우저 자동화(Playwright)** 로 실제 에디터를 조작하는
  방식이라, 네이버가 에디터 UI를 바꾸면 선택자가 깨져 동작하지 않을 수 있습니다.
- 자동화된 로그인은 캡차/2단계 인증으로 막히는 경우가 많습니다. 그래서
  `login` 명령은 브라우저 창을 띄워 **아이디/비밀번호까지만 자동 입력**하고,
  캡차 통과와 로그인 버튼 클릭은 사람이 직접 하도록 설계했습니다. 한 번
  로그인해두면 세션이 저장되어 이후에는 재로그인 없이 자동 포스팅이 가능합니다.
- 과도한 자동 포스팅은 네이버 이용약관 위반 및 계정 제재로 이어질 수 있습니다.
  발행 주기(하루 1~2회 이하 권장)와 콘텐츠 품질에 유의하세요.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 설정

1. `.env.example`을 `.env`로 복사하고 값을 채웁니다.

   ```bash
   cp .env.example .env
   ```

   - `NAVER_ID` / `NAVER_PW`: 네이버 로그인 정보
   - `NAVER_BLOG_ID`: `blog.naver.com/여기` 에 들어가는 아이디
   - `ANTHROPIC_API_KEY`: [console.anthropic.com](https://console.anthropic.com)에서 발급

2. `config.yaml`에서 포스팅 주제 목록, 발행 시각, 글 톤 등을 원하는 대로 수정합니다.

## 사용법

### 1. 최초 로그인 (최초 1회 필수)

```bash
python main.py login
```

브라우저 창이 뜨면 아이디/비밀번호가 자동 입력됩니다. 캡차가 나오면 직접 풀고
로그인 버튼을 눌러주세요. 로그인이 확인되면 `storage/naver_storage_state.json`에
세션이 저장되고 프로그램이 자동으로 종료됩니다.

> 세션은 시간이 지나면 만료될 수 있습니다. `post-now`/`run-scheduler`가
> "세션이 만료되었습니다"라는 오류를 내면 `login`을 다시 실행하세요.

### 2. 글 1개 즉시 생성 + 발행

```bash
python main.py post-now --topic "가을 등산 코스 추천"
```

발행 전에 입력만 테스트하려면:

```bash
python main.py post-now --topic "가을 등산 코스 추천" --dry-run --show-browser
```

### 3. 스케줄러로 자동 반복 실행

```bash
python main.py run-scheduler
```

`config.yaml`의 `schedule.times`에 지정된 시각마다 `topics` 중 하나를 무작위로
골라 자동으로 글을 생성하고 발행합니다. 서버/PC에서 계속 실행 중이어야 합니다
(예: `tmux`, `systemd`, `pm2`, cron으로 감싸서 실행 등).

## 문제 해결

- **선택자를 찾지 못했다는 오류**: 네이버 에디터 구조가 바뀐 것입니다.
  `--dry-run --show-browser`로 실행해 `storage/last_attempt.png` 스크린샷과
  실제 브라우저 화면을 보고, `src/naver_poster.py`의 `TITLE_SELECTORS` /
  `BODY_SELECTORS` 등에 새 선택자를 추가하세요.
- **로그인 세션이 자꾸 만료됨**: 네이버 보안 정책상 오래 방치된 세션은
  풀립니다. `login`을 다시 실행하세요.
- **글이 너무 짧게/이상하게 생성됨**: `config.yaml`의 `content.tone`,
  `content.min_length`를 조정하거나 `topics`를 더 구체적으로 작성하세요.

## 폴더 구조

```
main.py                 # CLI 진입점 (login / post-now / run-scheduler)
config.yaml              # 주제, 발행 시각, 글 톤 설정
.env                      # 로그인 정보 및 API 키 (git에 올리지 마세요)
src/
  config.py               # 설정 로더
  content_generator.py    # Claude API로 글 생성
  naver_login.py          # 네이버 로그인 및 세션 저장/재사용
  naver_poster.py         # SmartEditor 자동 입력/발행
  scheduler.py             # APScheduler 기반 자동 실행
storage/
  naver_storage_state.json  # 저장된 로그인 세션 (git에 올리지 마세요)
```
