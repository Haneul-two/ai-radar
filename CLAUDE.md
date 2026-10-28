# AI 기회 보드 — Claude Code 개발 가이드 (현재 상태·규칙)

경과·검증·사고 기록은 `docs/HISTORY.md`, 사양은 `docs/spec*.md`, 작업 규칙 요약은 `AGENTS.md`.
현재 상태(2026-10-12, AI Radar): **로컬 재설계·신청 마감 제외·10출처 수집 확장 구현·검증 완료(Python 214 OK · Node 118 pass · `tools/check_radar_ui.py` 98/98 pageerror 0), 원격 재설계 배포 대기.** 최종 실수집은 root가 진행 중이라 현재 데이터 건수는 최종 수집 후 `docs/HISTORY.md`에 기록한다(예전 dry 164/183건을 현재 데이터로 쓰지 않는다). 기존 운영 승인은 유지되며 원격 반영은 그 범위에서 하되 배포 완료는 확인 전까지 단정하지 않는다. 예약 cron 자동 첫 실행 미검증. 기획 `docs/ai-radar-spec.md`.
이전 상태(운영 시작, 역사): **운영 시작됨.** PR #1 병합(master d01cbf3), 첫 운영 수집(수동 workflow_dispatch run 38190817956) 성공, Pages 최신 빌드가 데이터 커밋 2427883과 동일, 공개 사이트 https://haneul-two.github.io/ai-data-storage/ 정상. 매일 09:00 KST 갱신 활성화(`ENABLE_OPPORTUNITY_UPDATES=true`)·교차 리뷰 반영 완료. 단, **예약 시각에 자동 발생한 첫 실행은 아직 없어 통과로 쓰지 않는다.** 원격 master의 자동 데이터 갱신 3건(ee68ae6→aa04b7e)은 보존 병합했다. `docs/tasks/`·`tools/run_claude.py`는 내부용이라 git 제외(로컬 보관). 증거·run·commit은 `docs/HISTORY.md`.
확장 운영 반영(2026-10-12): PR #2 병합(구현 e82b77e, CI 38208056185 success; merge 04a31cd, Test 38208115198·Pages 38208115264 success). 운영 수동 update run 38208115725 success, 수집 2026-10-12T05:29:11Z, data commit 5b822b9. 운영 데이터 110건 / 7출처(devpost 6 · dacon 10 · wevity 90 · aisummit 1 · seocho 1 · nvidia 1 · aifesta 1), **6출처 ok + aisummit error** — 원인: 응답 크기 2.5MB 상한 초과, 이전 항목 1건과 검증 시각 보존. 7출처 모두 성공이라고 쓰지 않는다. 위비티는 새 조회 89건 + 사라진 기존 항목 stale 보존 = 90건. 새 공식 3출처(seocho·nvidia·aifesta)는 모두 정상. 공개 보드 실Edge 1440/390 8검사 통과·pageErrors 0(`docs/evidence/expanded-public.json`·png), AI FESTA 26은 status closed 1건·open 0건. data commit 5b822b9의 Pages built 확인됨(builds/latest built, 공개 JSON updatedAt 2026-10-12T05:29:11Z·110건이 로컬 운영 최신과 일치, 공개 browser 8검사 재통과·pageErrors 0; `docs/evidence/expanded-deployment.json`). **예약 시각 자동 실행은 아직 미검증.** 과거 로컬 109건 성공 기록은 `docs/HISTORY.md`에 보존.
이전 상태(역사, 운영 시작 전): 로컬 구현·검증 완료(데이터 전체33 = 활성23 + 종료9 + 마감1), 원격(push·workflow·Pages·예약) 미실행. 증거는 `docs/evidence/final-checks.txt`, 통과표는 `docs/verification.md`.

최신 상태(2026-10-14, 이름 변경 완료): 폴더 `C:/Users/caring/Projects/ai-radar`, 저장소 `Haneul-two/ai-radar`(기존 저장소 이름 변경), 공개 URL https://haneul-two.github.io/ai-radar/. 위 본문의 옛 폴더·저장소·`ai-data-storage` URL과 "원격 배포 대기" 서술은 당시 기록이다. 새 주소는 PR #6 병합 2cc8744의 Pages built, 2026-10-14T07:59:28Z `tools/check_naming_public.py` 실검증(공개 JSON이 로컬 배포본과 일치, 보관 175·노출 118·10출처 ok, Edge 1440/390 통과·pageerror 0)이 확인된 범위에서만 정상 서비스로 쓴다. 예약 cron은 schedule 실행 2회 success가 확인됐다. 출처: `AGENTS.override.md`·`README.md`·`docs/HISTORY.md`, 증거 `docs/evidence/naming-production.json`. `.claude/rules/ai-radar-state.md`의 2026-10-13 준비 문구는 과거 기록이다.

## 프로젝트 개요

국내 + 한국 참가 가능 해외 온라인 AI 행사·공모전·해커톤 탐색 보드(개인용). 정적 `index.html` + ES modules가 `data/opportunities.json`(+`data/ingest-status.json` overlay)을 fetch해 렌더링한다. 서버 없음, GitHub Pages 동작. 이전 5탭 대시보드(`ai-events.html`, 카테고리 JSON, 뉴스/논문/채용/도구 수집기)는 보관만 하고 쓰지 않는다.

## 아키텍처

```
index.html ─ tokens.css + assets/styles/*.css
           └ assets/app.js ─ render.js ─ view-*.js ─ item-parts.js ─ dom.js/icons.js
                     └ 순수 로직(.mjs, Node 테스트 대상): time · status · visibility · filters · calendar · storage · data · notices · format · safe-url · debug
data/opportunities.json, ingest-status.json  ←  collectors/opportunities/ (백엔드 영역)
```

- 신청 마감(closed/ended) 제외 판정은 `assets/visibility.mjs` 한 곳에서 한다(한국 현재 시각 기준, dateOnly는 한국 당일 끝까지). 화면 코드에 따로 거르지 않는다 — 목록·검색·건수·저장·달력·임박·상세가 어긋나지 않게 하기 위해서다.
- 로직(`.mjs`)은 DOM을 만지지 않고 `now`를 인자로 받는다. DOM 코드(`.js`)에는 판정 로직을 넣지 않는다.
- 화면 갱신: 선택 그룹·검색 입력·헤더 버튼은 한 번 만들고 값만 바꾼다(포커스·캐럿 유지). 결과 영역만 다시 그린다.

## 작업 규칙

- 한 파일에 몰아넣지 않는다. 새 기능은 해당 모듈에 넣거나 새 모듈로 분리한다. (design-lab 시안만 1파일 HTML 예외)
- 색·글꼴·간격·반경은 `tokens.css` 토큰만 쓴다. 컴포넌트 CSS에 리터럴 색을 쓰지 않는다.
- **외부/출처 문자열은 `h()`(text node)·`textContent`로만 넣는다. `innerHTML`·`insertAdjacentHTML` 금지** — 출처 콘텐츠가 스크립트를 실행하지 못하게 하기 위해서다.
- 외부 링크는 `safeHttpsUrl()`을 통과한 https만, `target="_blank" rel="noopener noreferrer"`. 집계 사이트 URL을 '공식 신청'이라 부르지 않는다('안내 페이지 열기', '출처 확인').
- 확인하지 않은 날짜·참가비·자격을 만들지 않는다. 없으면 '미확인'/'확인 필요'로 쓴다. 마감 날짜와 개최 날짜를 섞지 않는다.
- 사용자에게 API·스키마·오류 원문을 보이지 않는다(출처, 마지막 확인, 수집 지연만).
- 저장 기록 쓰기가 실패하면 저장됐다고 말하지 않는다(세션 한정 안내). 저장 id는 데이터에서 사라져도 지우지 않는다.
- `?debug`/`?now`와 `window.__boardDebug`는 localhost/127.0.0.1에서만. production에서 무시.
- `data/*.json`은 수집기 산출물이다. 화면 작업 중 수동 수정·가짜 데이터 작성 금지. 화면 검증은 repo 밖 합성 데이터로 한다.
- `fetch()` URL은 `data/` 하위 상대 경로로 고정.
- 문서 3종(README/CLAUDE/design)은 구현과 함께 갱신한다.

## 사고에서 얻은 규칙

- 읽기가 끝나지 않은 로딩/오류 중에 '아직 수집된 기회가 없어요'를 띄운 적이 있다 → 데이터 상태 알림(미수집·지연·출처)은 `phase === 'ready'`에서만, 브라우저 저장 경고는 항상.
- root가 소유한 서버(8012)는 소유하지 않은 구현자가 끝내지 않는다 → 이전에 종료돼 브라우저 연결이 끊겼다.
- 수집기 전체 실패(종료 코드 1)도 `ingest-status.json`을 commit해야 사이트에 실패가 전달된다 → workflow는 collector를 `continue-on-error`로 두고 tests 뒤 commit, 마지막에 실패 표시. 종료 코드 2(손상)는 commit하지 않는다.
- 표준 예외 문구는 괄호 안 실제 국가명이 있어야 한국 참가로 승인한다(`(see rules)`는 거부). curated·신선 결과·저장 항목 모두 `rules.meets_contract`를 거친다.

- 위비티를 1페이지·소스당 20건으로만 읽다 2페이지 10번째의 고용24 해커톤을 놓쳤다 → 위비티는 전용 한도(최대 6페이지·100건)를 쓰고, 이후 페이지 오류는 부분 성공으로 숨기지 않고 소스 실패로 처리한다.
- 공식 행사 페이지의 서브 프로그램 오픈예정·마감을 행사 전체 상태로 읽을 위험이 있다 → 서초 AI 페스타처럼 근거 없는 접수 상태는 `sourceStatus: unknown`, 마감 null로 두고 NVIDIA는 연도 포함 hero 한 줄만 기간으로 읽는다.
- 목록 재렌더가 검색 입력을 다시 만들면 포커스·캐럿이 사라진다 → 입력과 필터 버튼은 재생성하지 않는다.
- 저장 토글이 목록 전체를 다시 그리면 키보드 포커스를 잃는다 → 버튼 상태만 동기화하고, 저장 보기에서만 다시 그린 뒤 포커스를 복원한다.
- 좁은 화면의 달력 칸은 마커 버튼이 44px을 못 만든다 → 칸에는 점만, 클릭은 월 일정 목록(agenda)에서 받는다.
- 모바일 보조 버튼(`calc(--control - …)`)이 36px로 줄어든 적이 있다 → 터치 목표는 `--control`(모바일 44px) 미만으로 줄이지 않는다.
- 가로 overflow 0만 보고 통과시키면 태블릿 첫 제목이 30px이어도 놓친다 → 폭별 제목 최소 폭을 실측한다(상세는 AGENTS.md).
- 목록 현재 페이지가 closed뿐이라 뒷페이지가 없다고 판정하면 활성 항목을 놓친다 → 위비티·콘테스트코리아는 빈/반복 페이지와 상한에서만 멈춘다.
- 위비티 본문에서 '구글폼 신청'만 보고 오프라인 해커톤을 온라인으로 읽을 뻔했다 → 신청 방법은 진행 방식이 아니다. 온라인 접수만으로 온라인 판정은 작품 제출이 곧 참가인 공모전에만(`sources/wevity_body.py`).
- NVIDIA hero가 `M월 D~D일, YYYY`에서 `YYYY년 M월 D~D일`로 바뀌어 4일간 갱신 실패했다 → 공식 페이지 파서는 같은 정보의 표기 순서 변형을 함께 받고, 변경 시 실페이지 문구로 재현 테스트를 추가한다.
- NVIDIA 수정을 로컬 브랜치에 커밋만 하고 push하지 않아 공개 보드 실패 알림이 이틀 더 남았다 → 출처 수정은 PR 병합·수동 수집·공개 JSON 확인까지 해야 끝난 것이다.
- 'LOTTE AX CHALLENGE'가 제목에 AI 단어가 없어 모음 사이트에 올라와도 걸러질 상황이었다 → AI 판정 단어에 `AX`를 두고, 새 표현은 실제 제목으로 `AxKeywordTest`에 추가한다.
- 검증할 때 브라우저 대기 조건을 `.opp`만 쓰면 달력 화면에서 시간초과가 난다 → `.opp, .state, .cal`.

## 명령

```bash
.venv/Scripts/python.exe -m http.server 8012 --bind 127.0.0.1
node --test tests/*.test.mjs
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe collectors/collect_events.py --dry-run
.venv/Scripts/python.exe collectors/collect_events.py --offline
.venv/Scripts/python.exe tools/browser_check.py   # 선택: playwright==1.63.0 + installed Edge, 서버 8012 필요
.venv/Scripts/python.exe tools/check_radar_ui.py  # AI Radar 화면 검사(폭 320~1440, 제목 최소 폭 포함), 서버 8012 필요
```

예약 수집(`update.yml`)은 변수 `ENABLE_OPPORTUNITY_UPDATES=true`가 있어야만 동작한다. 켜는 것은 사용자 승인 사항.

## 디자인

`design.md`와 `tokens.css` 참고. 탐색 시안과 조절판은 `design-lab/`(메인에서 링크하지 않음).
