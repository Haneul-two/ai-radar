# AI Radar

> 국내 전체와 한국에서 참가할 수 있는 해외 온라인 **AI 행사 · 공모전 · 해커톤** 중 **아직 신청할 수 있는 것**을 마감일 기준으로 비교하고 저장하는 개인용 보드. 화면 이름은 AI Radar(브라우저 제목 포함)이다. 폴더·저장소·공개 URL 이름도 `ai-radar`로 **변경을 마쳤다**(2026-10-14). 새 주소의 Pages 빌드와 공개 화면 검증도 마쳤다(아래 배포 참고).

> 상태: 재설계(AI Radar)·신청 마감 제외·10출처 수집 확장은 **2026-10-12 운영 반영 완료**(PR #3~#5)이며 10출처 모두 정상이다. 데이터 건수는 갱신마다 달라지므로 `docs/HISTORY.md`의 시점별 기록을 본다. 이름 변경(`ai-data-storage` → `ai-radar`)은 활성 폴더·GitHub 저장소·origin 모두 완료됐고, **새 주소(`/ai-radar/`)의 Pages 빌드(PR #6 병합 2cc8744, built)와 공개 브라우저 검증(2026-10-14)도 통과**했다.

정적 HTML + ES modules + JSON 구조라 서버 없이 GitHub Pages에서 동작합니다. 데이터는 `collectors/opportunities/`(Python)가 만들고, 화면은 `data/opportunities.json`과 `data/ingest-status.json`만 읽습니다.

이전의 5개 카테고리(행사·뉴스·논문·채용·도구) 다크 대시보드는 전면 개편으로 대체되었습니다. `ai-events.html`과 `data/events.json` 외 카테고리 JSON, `collectors/collect_{news,papers,jobs,tools}.py`는 **보관만 하고 새 화면·자동 수집에서는 쓰지 않습니다**.

---

## 화면 기능

- 신청이 끝난 항목(마감·종료)은 목록·검색·유형 건수·저장·달력·마감 임박·상세 진입 어디에도 나오지 않는다. 마감 필터도 없다. 원본/보관 데이터는 지우지 않는다. 옛 `status=closed` URL·저장 설정은 전체로 바뀐다.
- 상단에 제목 "AI 공모전·해커톤·행사 모아보기"와 요약 3종(참가 가능한 기회 · 7일 내 마감 · 데이터 갱신). 왼쪽 열에 검색·유형·진행 상태·참가 방식(1279 이하에서는 검색·유형은 항상 보이고 나머지만 접힘).
- 유형 탭(전체·행사·공모전·해커톤, 실제 건수), 검색(제목·주최·태그·설명), 진행 상태(모집중·예정·진행중·일정 미정)·참가 방식 필터, 정렬(마감 / 개최일 / 최근 확인). 데스크톱은 열 머리글이 있는 비교 목록, 모바일은 한 행에 마감·개최·참가·저장을 모두 보인다
- 목록 ↔ 월별 달력. 달력은 마감(●)과 개최 시작(◆)을 따로 표시하고 일요일 시작. 일정 미정 항목은 건수만 안내하고 목록에서 확인
- 상세 패널(네이티브 `<dialog>`): 마감·개최·자격·참가비·상금·마지막 확인·출처 링크. Esc/닫기 후 원래 위치로 포커스 복귀
- 내 저장(브라우저 localStorage). 데이터에서 사라진 저장 id는 지우지 않고 건수와 안내를 표시
- 마감 임박(최대 5건)·출처 상태(성공/확인 실패/접근 제한 + 마지막 성공 확인 시각)는 필터 하단 접이식 영역
- 필터는 URL query 우선 → localStorage → 기본값. 잘못된 값은 기본값으로 복구
- 수집 출처 12곳: 기존 7곳(Devpost · DACON · 위비티 · AI Summit Seoul · 서초 AI 페스타 · NVIDIA AI Day Seoul · AI FESTA) + 콘테스트코리아 · Dev-Event · AI EXPO KOREA + 2026-10-28 추가 LOTTE AX CHALLENGE(공식) · 링커리어(기업 챌린지가 일찍 올라오는 공모전 모음). 제목의 `AX`(AI 전환)도 AI 관련으로 본다. 공식 행사 출처는 지정한 사이트만 매일 다시 확인하며 웹 전체 행사 발견을 보장하지 않습니다. 출처별 한도·한계는 `docs/sources.md`, 검토 후 반려한 후보와 사유는 [`docs/evidence/radar-source-audit.md`](docs/evidence/radar-source-audit.md). 운영 중 AI API 호출·토큰 사용은 없습니다.
- AI Summit 응답 진단: `python tools/diagnose_aisummit.py`. 기존 robots/호스트/2.5MB 제한으로 읽고 크기·본문 위치·날짜 파싱 결과만 출력합니다. `Test` workflow를 수동 실행하면 같은 진단을 GitHub runner에서도 수행합니다.
- AI EXPO는 공식 사이트 조회 실패 시 접근이 허용된 SHOWALA 공개 행사 기록으로 동일 행사인지 검증해 갱신합니다. 실제 확인 출처를 표시하며 기존 행사 ID를 유지합니다. `python tools/diagnose_aiexpo.py`와 `Test` 수동 실행으로 기본·대체 경로를 진단할 수 있습니다.

### 날짜·상태 규칙

기준 시간대는 Asia/Seoul. 마감이 확정되어 지난 항목(현재 한국 시각 기준)은 보이지 않고, 마감 미확정 미래 항목은 '확인 필요'로 남는다. 정확한 `deadlineAt`은 절대 시각으로 비교하고 서울 날짜로 환산해 표시합니다(예: 10/26 17:00 EDT → 10/27 06:00 KST). 날짜만 있는 마감은 서울 당일 끝까지 보이며 "마감 시간 확인 필요"를 붙입니다. 판정 순서는 `docs/spec.md` §3, 구현은 `assets/status.mjs`. 마감일을 모르는 행사가 개최 전이면 "모집중"이 아니라 "예정"입니다.

---

## 설치

실행 기준은 Node 24, Python 3.11입니다. 화면(`index.html`)은 의존성이 없고, Python은 수집기와 테스트에만 씁니다.

```powershell
# Windows PowerShell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

```bash
# POSIX (macOS/Linux)
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

이하 명령은 Windows 기준(`.venv/Scripts/python.exe`)이며, POSIX에서는 `.venv/bin/python`으로 바꿉니다.

## 로컬 실행

`fetch()`와 ES modules는 `file://`에서 동작하지 않으므로 HTTP 서버가 필요합니다.

```bash
.venv/Scripts/python.exe -m http.server 8012 --bind 127.0.0.1
# 브라우저: http://127.0.0.1:8012/
```

검증용 query (**localhost / 127.0.0.1에서만** 작동, GitHub Pages 등 다른 호스트에서는 무시하고 '검증 모드' 배너를 띄우지 않음):

| query | 효과 |
|---|---|
| `?debug=loading` / `error` / `empty` | 로딩·오류·빈 데이터 상태에서 멈춤 |
| `?now=2026-10-02T03:00:00Z` | 현재 시각 고정 |

localhost에서는 `window.__boardDebug`(상태·항목 읽기, `setPhase()`)도 노출됩니다. 비밀값은 담지 않습니다.

## 테스트

```bash
node --test tests/*.test.mjs                                  # 날짜·상태·노출(visibility)·필터·정렬·달력·저장·데이터 로더·알림 (의존성 없음)
.venv/Scripts/python.exe -m unittest discover -s tests -v     # 수집 파이프라인
.venv/Scripts/python.exe collectors/collect_events.py --offline   # 네트워크 없이 기존 JSON·curated 계약만 검증
.venv/Scripts/python.exe collectors/collect_events.py --dry-run   # 실제 조회, 파일은 쓰지 않음
```

### 브라우저 검사(선택)

실제 화면 동작(필터·상세 모달 포커스·달력·반응형·로딩/오류/빈 상태)을 확인하는 Playwright 스크립트입니다. 필수 의존성이 아니라서 `requirements.txt`에는 없으며, **설치된 Microsoft Edge**가 필요합니다(Playwright 브라우저 다운로드 없음, 매번 새 headless profile 사용). 위 HTTP 서버(8012)가 떠 있어야 합니다.

```bash
.venv/Scripts/python.exe -m pip install playwright==1.63.0
.venv/Scripts/python.exe tools/browser_check.py     # POSIX: python tools/browser_check.py
```

캡처는 `docs/evidence/*.png`, 결과는 `docs/evidence/browser-check.json`에 저장됩니다.

AI Radar 화면 전용 검사는 `tools/check_radar_ui.py`(같은 전제: Edge, 서버 8012)입니다. 마감 경계 시각, 폭 320~1440 가로 넘침과 제목 최소 폭, 검색 포커스·저장·상세·달력, 로딩/오류/빈 상태를 확인하며 결과는 `docs/evidence/radar-frontend-checks.txt`입니다.

---

## 구조

```
index.html            진입 HTML (마크업 골격만)
tokens.css            색·글꼴·간격·반경·모션 토큰 (유일한 값 원천)
assets/styles/*.css   base · layout · components · rows · calendar · detail
assets/*.mjs          순수 로직(브라우저·Node 공용): time, status, visibility, filters, calendar, storage, data, notices, format, safe-url, debug
assets/*.js           DOM 모듈: app(진입), render, view-list/calendar/urgent/detail/controls, item-parts, dom, icons
tests/*.test.mjs      node:test 회귀 테스트 (+ helpers.mjs 합성 데이터)
design-lab/           디자인 비교 시안과 토큰 조절판 (메인에서 링크하지 않는 개발 자료)
data/opportunities.json, data/ingest-status.json   수집기가 쓰는 화면용 데이터
collectors/opportunities/   수집 파이프라인
```

보안 원칙: 외부 문자열은 `textContent`/text node로만 넣고 HTML 문자열을 주입하지 않습니다. 외부 링크는 userinfo 없는 `https`만 허용하며 `target="_blank" rel="noopener noreferrer"`로 엽니다.

## 자동 업데이트

`.github/workflows/update.yml`은 하루 1회(09:00 KST, cron `0 0 * * *`) 실행되며(수집 step 제한 18분·job 25분), 저장소 변수 `ENABLE_OPPORTUNITY_UPDATES == 'true'`일 때만 동작합니다. 이 변수는 실제로 `true`로 설정돼 활성화됐고, 첫 실행은 수동 `workflow_dispatch`(run 38190817956, 성공)였습니다. 예약(`schedule`) 실행은 run 38352906516(2026-10-13T05:44:01Z)과 38508066853(2026-10-14T03:47:32Z)이 success로 확인됐습니다. cron 설정은 UTC 00:00(KST 09:00)이지만 실제 실행 시각은 위와 같이 지연되므로 정시 실행이라고 단정하지 않습니다. 수집기가 전부 실패(종료 코드 1)해도 tests 통과 후 `ingest-status.json`의 실패 상태를 commit하고 마지막에 workflow를 실패로 표시합니다. 기존 데이터 손상(종료 코드 2)은 commit하지 않습니다.

`GITHUB_TOKEN`으로 push한 commit은 branch 기반 Pages build를 자동으로 실행하지 않습니다. 그래서 commit 직후 `pages: write` 권한으로 Pages API(`POST /repos/{owner}/{repo}/pages/builds`)를 호출해 최신 master의 재빌드를 명시적으로 요청합니다(종료 코드 2에서는 실행하지 않음). 첫 수동 실행에서 이 API 재빌드가 실제로 작동했고 Pages 최신 빌드가 데이터 커밋 2427883과 일치했습니다.

## 배포

공개 URL: https://haneul-two.github.io/ai-radar/ (저장소 `Haneul-two/ai-radar`, 기존 저장소의 이름 변경). GitHub Pages API의 주소와 source(master/root)를 새 이름으로 확인했고, PR #6 병합 2cc8744의 Pages 빌드가 built임을 확인했다. 2026-10-14T07:59:28Z `tools/check_naming_public.py` 실행에서 공개 JSON이 로컬 배포본과 일치하고(보관 175건·노출 118건, 10출처 모두 ok) Edge 1440/390 화면(제목·브랜드 AI Radar, 알림 없음, 가로 넘침 0, pageerror·requestfailed 0)이 통과했다 — 이 실제 검증 범위 안에서만 새 주소가 정상 서비스 중이라고 쓴다(증거 `docs/evidence/naming-production.json`). 이전 주소 https://haneul-two.github.io/ai-data-storage/ 는 GitHub이 자동으로 연결해 주지 않는 과거 URL이므로, 북마크는 직접 새 주소로 바꿔야 한다. GitHub Pages(Deploy from a branch, root). `design-lab/`도 root에 포함되므로 "배포 제외"가 아닙니다 — 링크하지 않을 뿐입니다. 완전히 제외하려면 이후 Pages artifact workflow가 필요합니다.
