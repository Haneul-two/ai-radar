# AI 기회 보드 — 전면 개편 사양서

> **AI Radar 갱신(2026-10-12)**: 화면 이름은 AI Radar. 신청이 끝난 항목은 탐색에서 제외한다(§3 갱신). 아래 본문의 '마감·종료 필터로 조회' 규칙은 이 갱신으로 대체된다. 기획 `docs/ai-radar-spec.md`, 출처 `docs/sources.md`. 원본/보관 데이터 계약(90일 보관 등)은 그대로다.

## 1. 목표와 근거

사용자 요청: `$make-it https://github.com/Haneul-two/ai-data-storage 이거 지금 내 환경에서의 최신 기준으로 개선하고 싶어. 이번엔 AI 행사와 공모전, 해커톤의 정보만 추릴 수 있도록. 아예 UI/UX부터 모든 걸 다 바꿔줘`.

착수 전 1라운드: 개인용 참가 기회 탐색 / 국내 + 한국에서 참가 가능한 해외 온라인 / 공개 무료 소스, 하루 1회, 로그인 수집 제외 / 밝은 탐색 보드. 사용자 답: `추천안으로 진행`.

목표는 실제 출처에서 AI 기회를 찾고, 마감과 참가 조건을 비교하고, 공식 안내로 이동하는 것이다. 규모 L: 웹 탐색 UI와 독립 실행 가능한 수집 파이프라인 두 하위 시스템. 이번 범위는 둘 다다. GitHub Pages에서 실행 가능한 정적 ES modules + Python 수집 구조를 유지한다.

## 2. 우선순위

| 단계 | 산출물 | 통과 조건 |
|---|---|---|
| P0 | AI 행사/공모전/해커톤 전용 화면 | 다른 카테고리 노출 없음, 실제 출처 링크, 검색·유형·상태·방식 필터, 마감/개최일 분리 |
| P0 | 수집 및 데이터 계약 | 실제 접근 가능한 국내 공개 소스와 Devpost, 관련성·지역·URL·날짜 검증, 중복 제거, 오류 시 기존 데이터 보존 |
| P0 | 품질·기록 | Python/Node 회귀 테스트, 모바일/데스크톱 UI 검증, 다른 모델 리뷰, 실행법·HISTORY |
| P1 | 참가 판단과 개인 정리 | 상세 패널, 로컬 저장, 월별 일정, 마감 임박 영역, 출처 갱신 상태 |
| P1 | 안전한 운영 준비 | 하루 1회 09:00 KST workflow 초안, 기본 비활성화 게이트, 검사 CI, 실제 수집 dry-run |
| P2 | 디자인 비교 자료 | design-lab의 경량 시안 3종과 토큰 조절 미리보기; 메인 화면에서 링크하지 않는 기본 비노출 개발 자료. Pages가 branch root 정적 구조라 design-lab은 배포 root에 남으며 '미배포'를 약속하지 않는다. 완전 배포 제외는 이후 Pages artifact workflow 도입 시 가능 |

P2를 제외해야 하면 완전히 제외하고 보고한다. 계정/서버 DB/자동 신청/외부 알림/유료 소스/실제 푸시·배포·예약 활성화는 이번 로컬 결과물에 포함하지 않는다.

## 3. 흐름과 상태

목록 로딩 → 검색·필터 → 상세 → 공식 안내 또는 저장. 저장은 브라우저 localStorage에만 유지한다. 목록/달력/저장 목록은 같은 필터와 데이터 계약을 사용한다. 상세 닫기·Esc 후 원래 포커스로 복귀한다. **AI Radar 갱신: 신청이 끝난 항목(closed/ended)은 어떤 필터로도 조회하지 않는다.** 데이터에는 남기되(보관) 목록·검색·건수·저장·달력·임박·상세 진입에서 제외한다.

**상태 판정 (위에서부터 첫 일치)**: ① 종료일이 서울 오늘보다 이전 → ended ② 출처가 명시 closed(`sourceStatus`) → closed ③ 정확한 deadlineAt이 now 이전 → closed ④ 국내 date-only deadlineDate가 서울 오늘보다 이전 → closed ⑤ 접수 시작일이 미래 → upcoming ⑥ sourceStatus open 또는 알려진 deadline이 미래 → open ⑦ 오늘이 개최 기간 → ongoing ⑧ startDate가 미래 → upcoming ⑨ 나머지 → unknown. 개최일만 있는 event는 모집중이라고 추측하지 않는다. date-only 마감은 당일을 포함하며 '시간 확인 필요'를 표시한다.

**노출 규칙(AI Radar)**: 위 판정 결과가 closed/ended면 숨긴다(`assets/visibility.mjs`, 한국 현재 시각 기준). exact 마감은 현재 시각 이상이면 노출·이후 제외, dateOnly는 한국 당일 끝까지 노출하고 '시간 확인 필요', 마감 미확정 미래 항목은 '확인 필요'로 남긴다(신청 가능 확정으로 표시하지 않음). 현재 시각이 바뀌면 다시 판정한다. 열린 상세는 마감 시각을 넘기면 닫는다. 옛 `status=closed` URL/저장 설정은 전체(all)로 바꾼다. 저장 id는 마감으로 사라져도 지우지 않는다.

**상태 필터**: 전체(all, 노출 가능한 항목) / 모집중(open) / 예정(upcoming) / 진행중(ongoing) / 미정(unknown). 마감·종료 필터는 없다.

**URL·저장 규칙**: 필터는 URL query가 있으면 URL 우선, 없으면 localStorage, 잘못된 값은 기본값. 저장 id가 데이터에서 사라져도 id는 보존하고 저장 목록에 사라진 건수와 안내를 표시한다. `?debug`와 `?now`는 localhost/127.0.0.1에서만 작동하고 테스트 모드 배너를 표시한다. GitHub Pages production은 이를 무시한다.

로딩 skeleton, 빈 목록의 필터 초기화, 오류의 재시도, 새로고침 중 disabled 버튼을 구현한다. 저장 실패 시 저장됐다고 주장하지 않고 해당 브라우저 제한을 안내한다. 데이터가 오래되었거나 소스가 실패했으면 그 상태를 숨기지 않는다.

## 4. 데이터 계약

`data/opportunities.json`: `{schemaVersion: 2, updatedAt: ISO|null, lastAttemptAt: ISO, sources: Source[], items: Opportunity[]}`.

`data/ingest-status.json`: `{lastAttemptAt: ISO, sources: Source[]}`. 매 시도의 상태를 원자적으로 기록하는 별도 파일이다. 전체 원격 수집 실패 시 opportunities.json은 바이트 단위로 불변이며 이 파일만 갱신된다. UI loader가 ingest-status.json의 sources를 opportunities.sources에 id 기준으로 overlay한다. 파일 삭제는 없다.

Source: `{id, name, url, status: 'ok'|'error'|'blocked', checkedAt, lastSuccessAt: ISO|null, itemCount, message}`. updatedAt은 하나 이상의 실제 수집 성공 때만 변경한다. HTTP 성공이지만 예상 목록 구조가 사라진 응답은 성공으로 간주하지 않는다.

Opportunity 필수 키:

```json
{
  "id": "source-stable-id",
  "kind": "event|contest|hackathon",
  "title": "확인한 제목",
  "organizer": "확인한 주최 또는 null",
  "description": "공개 안내의 짧은 요약",
  "tags": ["AI"],
  "mode": "online|offline|hybrid|unknown",
  "region": "국내 지역/해외 온라인/미정",
  "country": "KR|GLOBAL",
  "startDate": "YYYY-MM-DD 또는 null",
  "endDate": "YYYY-MM-DD 또는 null",
  "registrationStartDate": "YYYY-MM-DD 또는 null",
  "deadlineDate": "YYYY-MM-DD 또는 null",
  "deadlineAt": "시간대 포함 ISO datetime 또는 null",
  "eligibility": "확인한 참가 조건 또는 확인 필요",
  "eligibilityVerified": false,
  "fee": "확인한 참가비 또는 확인 필요",
  "prize": "확인한 상금 또는 null",
  "url": "안내/공식 신청용 https URL",
  "sourceUrl": "조회한 출처 https URL",
  "sourceId": "source-id",
  "sourceName": "출처 이름",
  "verifiedAt": "실제 조회 시각",
  "dateNote": "날짜만 제공/원문 시간대/미확정 안내 또는 null",
  "sourceStatus": "open|closed|unknown (선택)",
  "stale": false
}
```

`sourceStatus`는 선택, `stale`은 boolean이다. 성공 소스에서 사라진 활성 항목은 stale=true로 유지하고 '출처 재확인 필요'를 표시한다. 90일 지난 종료 항목만 결과에서 제외한다.

해외 온라인은 한국 참가 허용 증거가 있는 것만 포함한다. 증거: (a) 상세의 country 문구가 All countries/territories 또는 worldwide/open globally이면서 tooltip/본문의 제외 국가 목록이 South Korea/Republic of Korea/Korea(North Korea 제외)/KR을 금지하지 않는 경우, 또는 (b) 제한된 국가 목록이 한국/대한민국/South Korea/Republic of Korea를 명시 포함하는 경우. 국내 eligibilityVerified=false는 '참가 조건 확인 필요'로 보일 수 있으나 해외는 verified false를 자동 포함하지 않는다. 연령/학생 조건은 보존한다. 행사 개최일을 마감일로 대체하지 않는다. 날짜만 제공된 마감은 그 출처 기준 날짜임을 표시하고 시각을 만들어내지 않는다. deadlineAt이 있으면 서울 시간대로 마감과 D-day를 판단한다.

## 5. 품질과 검증

- `python -m unittest discover -s tests -v`: 필터 관련성(AI 단어 경계), 유형 우선순위, 지역·자격 제외, 날짜 경계, 소스 파싱, 중복, 부분/전체 실패 보존, robots 차단, unsafe URL, 연락처 마스킹.
- `node --test tests/*.test.mjs`: 날짜/상태/필터/정렬/캘린더/저장 로직. 테스트용 고정 시각을 함수 인자로 넘긴다.
- 실제 수집 `--dry-run`으로 소스별 상태/건수 확인 후 결과 저장; 실패 전후 파일 대조.
- UI 1440×900 및 390×844 직접 screenshot 확인. 추가 320/375/414/768px overflow 검사. 검색, 모든 유형, 종료, 저장 지속, 상세 키보드, 달력, 오류/빈/로딩 상태 확인. browser console error 0.
- 기존 데이터·소스 파일 무삭제, 원본 checkout의 미커밋 변경 보존, git diff --check.
- 사양서 독립 읽기 점검 1회 → 구현 → Claude 구현을 Codex가 독립 리뷰. 수정 후 필요한 테스트 재실행.

## 6. 분야 규칙과 이유

- 하나의 파일에 모든 기능을 넣지 않는다. 안 그러면 날짜/수집/화면 규칙을 독립 검증하기 어렵다. 출처: 사용자 AGENTS.md.
- 원본 데이터를 수정하거나 소스 실패 시 빈 파일로 덮어쓰지 않는다. 안 그러면 사용자가 관리한 정보와 마지막 정상 결과를 잃는다. 출처: backend-checklist, 기존 CLAUDE.md.
- 전화·이메일·키를 화면/로그/git에 저장하지 않는다. 안 그러면 공개 정적 배포에서 개인정보와 비밀값이 노출된다. 출처: backend-checklist.
- 데이터 수집과 렌더링에 HTML 문자열을 주입하지 않는다. 안 그러면 외부 출처 콘텐츠가 스크립트를 실행할 수 있다.
- UI의 로딩·빈·오류·작업 중 상태를 생략하지 않는다. 안 그러면 수집 실패를 데이터 없음 또는 성공으로 오인한다. 출처: frontend-checklist.
- 마감 날짜와 개최 날짜를 섞지 않는다. 안 그러면 행사 전인데 이미 접수가 마감된 기회를 신청 가능하다고 안내한다.
- 키보드 포커스·반응형·reduced motion을 생략하지 않는다. 안 그러면 모바일과 키보드 이용자가 신청 정보를 찾기 어렵다. 출처: DESIGN.md, hallmark.
- 확인하지 않은 날짜·상금·참가비·자격을 만들지 않는다. 안 그러면 사용자 참가 판단이 잘못된다. 출처: hallmark honest-copy.
- 실제 배포·예약 활성화·외부 알림을 실행하지 않는다. 안 그러면 사용자 승인 없이 원격 운영이 시작된다. 출처: make-it, 사용자 AGENTS.md.

3D/게임 효과 규칙 제외: 이 서비스는 정보 탐색 UI이며 해당 효과가 없다.

## 7. 운영 경계

공개 페이지를 소수 요청하고 robots를 존중한다. 현재 온오프믹스는 일반 User-agent 자동 수집을 금지하므로 자동 소스에서 제외한다. Devpost 공개 목록 API는 200과 구조를 실측했다. 국내 후보는 위비티와 데이콘 공개 목록이다. 구조를 확인하고 작동하는 parser만 연결한다(P0는 실제 국내 소스 1개 이상 + Devpost). parser 구조를 확인하지 못한 소스는 error/blocked로 기록한다. 로그인/차단 우회는 하지 않는다.

(AI Radar 갱신: 아래 호스트에 공식행사 adapter 호스트와 신규 `www.contestkorea.com`·`aiexpo.co.kr`·`raw.githubusercontent.com`이 정확한 이름으로 더해졌다. 상세 `docs/sources.md`.) 허용 네트워크 호스트: devpost.com 및 *.devpost.com, www.wevity.com/wevity.com, dacon.io/www.dacon.io, 공식행사 adapter 사용 시 www.aisummit.co.kr/aisummit.co.kr. 모든 URL은 공인 HTTPS hostname + port 443 + userinfo 없음을 검증하며 redirect에도 같은 정책을 적용한다. 외부 apply URL은 fetch하지 않고 HTTPS 안전 링크로만 보일 수 있다.

## 8. 가정과 조절값

- 정적 사이트 유지 — 서버 기능이 필요해지면 frontend의 data loader와 수집 출력 계약을 유지한 채 별도 API를 추가한다.
- 개인 저장은 브라우저별 — 공유/계정은 이번에 만들지 않는다.
- 새 브랜드 이름은 `AI 기회 보드`, 밝은 Cobalt 계열의 Workbench 구조 — tokens.css와 design.md에서 바꿀 수 있다.
- 기존 다크 대시보드는 전면 개편 승인에 따라 교체한다. 이전 카테고리 파일은 삭제하지 않는다.
- 기본 정렬은 마감 가까운 순. 마감이 없는 행사는 개최일(진행 중이면 오늘) 기준으로 사이에 두고, 개최일도 없으면 마지막(2026-11-18) — JS domain 모듈에서 변경.
- 수집은 소스별 상한 20개(위비티·콘테스트코리아·Dev-Event는 전용 한도, `docs/sources.md`), 타임아웃 15초, 요청 간격 1초, 하루 1회 09:00 KST — 수집 설정과 workflow에서 변경. 수집 step 18분·job 25분.
