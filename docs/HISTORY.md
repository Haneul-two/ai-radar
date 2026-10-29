# HISTORY

## 2026-10-28 — NVIDIA 수정 배포 + AX 챌린지 수집(LOTTE AX CHALLENGE 공식·링커리어)

- 요청: 공개 보드 "일부 출처(NVIDIA AI Day Seoul) 갱신에 실패" 해결, https://lotteaxchallenge.com/ 추가, 앞으로 이런 기업 챌린지도 자동으로 넣기. 사용자 선택: AX 키워드 + 링커리어 출처, 검증 후 병합·수집까지 진행.
- NVIDIA: 10-26 수정(8e63368)이 로컬 브랜치 커밋만 되고 push되지 않아 10-27 운영 수집도 error였다. 2026-10-28 실페이지에서 수정 파서 정상(2026-11-09~10 코엑스) 확인 후 이번 PR로 배포.
- 롯데 AX 챌린지를 놓친 원인: ① 10-27 개설 사이트라 위비티·콘테스트코리아에 아직 없음 ② 제목에 'AI'가 없어 AI 판정(`is_ai_related('LOTTE AX CHALLENGE 2026')` = False)에서 걸러질 상황. → AI 판정에 `AX` 추가, 공식 사이트 `lotteax`와 링커리어 `linkareer` 출처 추가(상세 `docs/sources.md`).
- 롯데 일정: 화면은 이미지지만 `__NEXT_DATA__` 코드 섹션에 원문 — 온라인 예선 접수 10-28~11-04 23:59 KST, 오프라인 본선 11-24~25(롯데인재개발원 오산캠퍼스), 대상 'AI에 관심 있는 누구나', 총 상금 2천만원. 머리글 '2030년 12월 31일 마감'은 빌더 기본 문구라 무시.
- 교차 리뷰(Codex, read-only): P0/P1 없음. P2 2건·P3 1건 반영 — 링커리어 상세 status가 OPEN이 아니면 저장하지 않고 마감 전파에만 사용, 롯데 title 연도와 마감 연도 불일치는 오류, 링커리어 마감 밀리초 보존(23:59:59.999). 'AX' 의미적 오탐·`AX2026` 누락은 정책 위험으로 기록만.
- 검증: Python 281 OK, Node 118 pass. 실데이터 전체 dry-run(파일 미수정): 12출처 모두 ok, 전체 293건, 링커리어 AI 후보 82건(34페이지) 중 교차 출처 중복 제거 후 29건, lotteax 1건(링커리어의 같은 챌린지는 공식 출처 우선으로 제거).
- 한계: 링커리어와 위비티·콘테스트코리아 사이 제목 표기가 다른 같은 공모전 8건은 중복으로 남는다(기존 '누락보다 중복' 정책). 수집 요청이 약 120건 늘어 실행이 2~3분 길어진다(수집 step 18분 안).
- 배포: PR #8 병합(merge 938f7cc, CI node·python pass). 수동 update run 40645504322 success(7분 21초), 수집 2026-10-28T06:42:46Z, data commit d12ce7f, Pages 40646252345 success. 공개 `ingest-status.json` 12출처 모두 ok(nvidia 2026-11-09~10 코엑스, lotteax, linkareer AI 후보 84건·35페이지), 운영 데이터 294건, 공개 `opportunities.json`에 LOTTE AX CHALLENGE 2026(마감 2026-11-04T23:59:59+09:00) 노출 확인.

## 2026-10-26 — NVIDIA AI Day 갱신 실패 수정: hero 날짜 표기 변경

- 증상: 공개 보드에 "일부 출처(NVIDIA AI Day Seoul) 갱신에 실패했습니다". `ingest-status.json` nvidia status=error, message "hero의 연도 포함 기간 표기를 읽지 못함", lastSuccessAt 2026-10-22T03:33:45Z(그 뒤 매일 실패, 기존 항목 1건은 보존 노출).
- 원인: 공식 페이지 hero 표기가 `11월 9~10일, 2026 | 코엑스` → `2026년 11월 9~10일 | 코엑스`(연도가 앞)로 바뀌었다. 파서 정규식이 '연도가 뒤' 형식만 받았다.
- 수정: `sources/nvidia.py`가 두 형식을 모두 읽는다(여전히 h1 다음 hero 줄만, title 연도 대조 유지). 재현 테스트 `NvidiaTest.test_hero_year_first_format` 추가(수정 전 실패 확인).
- 참고: 실페이지에 '지금 등록하기' 버튼이 없어져 sourceStatus는 규칙대로 open → unknown이 된다(근거 없는 접수 상태를 만들지 않음).
- 검증: Python 263 OK. 2026-10-26 실페이지 HTML로 parse_main → 2026-11-09~2026-11-10 코엑스. 배포는 push 후 기록.

## 2026-10-16 — 위비티 '미확인' 줄이기: 상세 본문 전체 해석

- 요청: 보드에 미확인이 많다 → 위비티 안 링크까지 들어가서 정보를 가져올 수 없나. 사용자 확정 — 범위는 위비티 상세 본문 먼저(공식 홈페이지 fetch 안 함), 참가비 언급이 없으면 '확인 필요' 유지, 애매하면 비워 두기, 배포까지(push 전 재확인).
- 원인: 위비티 94건 중 참가비 94/94 '확인 필요'(코드가 항상 고정값), 방식 92/94 '미정'(제목만 보고 판정, 본문은 앞 4줄만 설명용으로 읽음), 마감 시각 94/94 없음. 본문에는 '이메일 접수', '10. 12.(월) 18:00까지' 같은 근거가 있었는데 버리고 있었다.
- 조사(20건 표본): 공식 홈페이지 링크는 16곳 중 9곳만 읽힘(인증서 오류·인스타그램·네이버 블로그·스크립트 렌더링). 근거 문구 빈도는 위비티 본문과 비슷해 외부 fetch의 이득이 작아 이번 범위에서 제외했다.
- 구현: `collectors/opportunities/sources/wevity_body.py` 신설(방식·마감 시각·참가비), `wevity.py`에서 제목 판정이 unknown일 때만 본문 방식 사용. 테스트 `tests/test_wevity_body.py` + `test_opportunities.py` 통합 1건.
- 실측(현재 활성 위비티 94건 본문, 1초 간격 조회): 방식 2→42건(온라인 37·혼합 4·오프라인 1), 마감 시각 0→38건(원문 줄과 38건 전부 대조 일치), 참가비 0→4건(모두 '무료' 명시).
- 실수 기록: 첫 규칙은 ① '과학관 방문, 축제 참여'(주제 설명)를 오프라인으로 ② '입상작을 오프라인 행사에 활용'을 근거로 혼합으로 ③ 신청만 구글폼인 오프라인 해커톤을 혼합/온라인으로 읽었다. → 단어·행동어 15자 근접, '방문'은 '방문 접수'만, 온라인 접수만으로 온라인 판정은 공모전에 한정하도록 고쳤다.
- Codex 교차 리뷰(HIGH 4·MEDIUM 2, 모두 재현 테스트 후 수정): 같은 날 발표·심사 시각을 마감으로 읽음 → 접수·마감 문맥(그 줄 또는 바로 위 제목 줄)만, 발표·심사·교육 줄 제외 / 본문의 다른 연도 날짜 → 연도가 다르면 배제 / `18:00~20:00`·`18:00 또는 23:59` → 애매하면 전체 버림 / `참가비 3만원 + 교육비 무료`·`무료(학생만)` → 무료로 단정하지 않음 / 오전 12시 → 00:00 / '비대면'을 '대면'(오프라인)으로 읽음 → 제외. 띄어 쓴 '접 수' 허용(실측 1건 복구).
- 검증: Python 262 OK · Node 118 pass. 실제 전체 수집을 임시 경로(`--output` scratchpad)로 1회 실행 — 10출처 모두 ok, 위비티 새 조회 활성 49건 중 방식 22건·마감 시각 18건·참가비 2건(나머지 47건은 마감된 기존 항목이라 다시 읽지 않고 보드에서도 제외). 저장소 `data/`는 수정하지 않았다(다음 예약 수집에서 반영). 화면 코드는 바꾸지 않았다.
- 배포(실측): push는 사용자가 직접 실행(안전 훅이 Claude의 push 차단). PR #7 CI python·node pass → 병합 78fcf90. 수동 update run 38860818670 success, data commit 7819134, Pages built=7819134. 공개 JSON updatedAt 2026-10-16T06:22:25Z·보관 187건·10출처 ok, 위비티 새 조회 49건 중 방식 22·마감 시각 18·참가비 2가 임시 경로 수집 결과와 일치. 공개 화면 브라우저 검사는 하지 않았다(화면 코드·필드 형식 변경 없음).

## 2026-10-14 — 이름 정리(ai-radar) 적용: 폴더·저장소·remote·새 주소 배포 검증 완료

- 승인: 사용자 `이어서진행해줘`로 root가 추천안을 적용했다. 이 항목은 그 결과를 상태 문서에 동기화한 기록이다(Claude 편집, Codex 독립 리뷰 예정).
- 폴더: 활성 폴더를 `C:/Users/caring/Projects/ai-radar`로 이동했다. 원본 `AI-DATA-STORAGE` checkout은 보호 유지.
- 환경: 기존 `.venv`는 이동 시 실행기 절대 경로가 달라지므로 `C:/Users/caring/Projects/_backups/ai-radar-venv-20261014`로 이동·보존(삭제 없음)하고, 새 폴더 `.venv`를 동일한 13개 버전으로 복구했다.
- 저장소: GitHub PATCH 성공 — `Haneul-two/ai-radar`, homepage https://haneul-two.github.io/ai-radar/, description `AI Radar 국내참가AI행사공모전해커톤탐색`. **기존 저장소의 이름 변경이며 새 저장소 생성이 아니다.** rename 전에 기존 원격의 최신 자동 데이터 갱신을 보존 병합했다.
- remote: origin을 `https://github.com/Haneul-two/ai-radar.git`로 변경, `git ls-remote` master 791a56c 성공. Pages API html_url은 새 주소이고 source는 master/root 그대로.
- 호환 검증(새 경로): Python 3.11.15/pip 24 CLI 동작, 전체 Python 241 OK · Node 118 pass, 현재 데이터 175건 `--offline` 계약 통과.
- 예약 실행 확인: run 38508066853(2026-10-14T03:47:32Z)과 38352906516(2026-10-13T05:44:01Z) 모두 event=schedule·conclusion=success. 이로써 "예약 cron 첫 실행 미검증"은 해소됐다. 단 cron 설정은 UTC 00:00(KST 09:00)이고 실제 실행은 위 시각이므로 정시에 실행됐다고 단정하지 않는다.
- **새 주소 배포 검증(완료, root 실측)**: PR #6 병합 2cc8744fe024d1f88c6eb94bc88ead6b4d48f1e3, 새 저장소 Test 38531497891·Pages 38531500212 success, Pages API built=2cc8744. 중복 Pages 38531498169는 cancelled라 통과에 세지 않는다. 2026-10-14T07:59:28Z `tools/check_naming_public.py` 실실행 통과 — https://haneul-two.github.io/ai-radar/ 공개 JSON이 로컬 배포본과 정확히 일치(datasetUpdatedAt 2026-10-14T03:47:46Z, 보관 175·노출 118, 10출처 모두 ok), Edge 1440/390 브랜드·title AI Radar, notice 없음, `AI EXPO` 검색 결과에 기존 ID aiexpo-119c9024b15a 1건, overflow 0, pageerror/requestfailed 0. 증거 `docs/evidence/naming-production.json`·`naming-public-1440.png`·`naming-public-390.png`. 정상 서비스 표현은 이 검증 범위에 한한다. 이전 주소는 자동 연결되지 않아 사용자가 북마크를 갱신해야 한다.
- 환경·설정: 새 경로 폴더/remote·GitHub homepage 완료, 원본 폴더 보호, 옛 venv 백업 `C:/Users/caring/Projects/_backups/ai-radar-venv-20261014/` 보존·동일 13개 복구. `ENABLE_OPPORTUNITY_UPDATES=true` 승계, schedule 실제 성공 2회는 위에 기록. 이름 변경 후 별도 전체 수집은 중복 실행하지 않고 현재 데이터·설정 호환성만 확인했다.
- 검증 도구 실수: `check_naming_public.py` 첫 실행이 실패했다. 원인은 앱이 아니라 검증 조건 — 첫 검색 결과를 AI EXPO라 단정했으나 `AI Summit Seoul & EXPO`도 검색에 맞는 정당한 결과였다. 앱 변경 없이 조건을 검색어 포함 + 지정 ID 포함으로 고쳐 통과시켰다.
- 편집 권한 기록: `.claude/rules/ai-radar-state.md`는 민감 파일 권한으로 편집이 거부돼 이번에 고치지 못했고 우회하지 않았다. 그 파일의 "2026-10-13 이름 정리 준비 … 검증 전" 문구는 과거 기록이며, 최신 사실은 `AGENTS.override.md`·`README.md`·이 HISTORY를 따른다.
- 보존: 아래 2026-10-13 준비 항목의 "미적용" 서술, 과거 URL, 증거 기록은 당시 사실이므로 바꾸지 않았다.

## 2026-10-13 — 이름 정리(ai-radar) 준비

- 요청: 화면 제목이 AI Radar이므로 폴더명·저장소명·사이트 주소도 맞추고 싶다는 요청. 목표 — 폴더 `ai-radar`, 저장소 `Haneul-two/ai-radar`, 공개 URL https://haneul-two.github.io/ai-radar/ .
- 준비 범위: README 소개·상태·운영 URL 문구, `tools/check_aisummit_public.py`·`check_aiexpo_public.py`의 BASE, AGENTS.override.md·`.claude/rules/ai-radar-state.md` 상태 기록. `index.html`의 상대 경로와 workflow의 `github.repository` 동적 참조는 이름 변경과 호환됨을 읽기로 확인했다. 수집 UA `ai-opportunity-board/1.0`, 가상환경, localStorage key, 데이터는 바꾸지 않았다.
- **미적용**: 폴더 이동, 저장소 rename, remote 변경, 커밋·푸시·배포, 새 주소 검증은 하지 않았다. 사용자 확인 후 root가 적용하며 새 주소 Pages 빌드 확인 전에는 새 URL을 운영 사실로 쓰지 않는다. 이전 기록·증거의 옛 URL은 역사로 보존한다.

## 2026-10-13 — AI EXPO 복구 최종 확인

- 01:04 UTC(10:04 KST) 공개 상태 재확인: 10개 출처 모두 ok, 마지막 수집 시각 2026-10-12T14:20:56Z. Edge 1440/390에서 실패 알림 없음·목록 정상 확인. 이전 검증 캡처·시각은 역사적 증거로 보존했다.
- 기록 저장 중 도구 연결 종료가 있었으나 문서·증거 쓰기는 적용돼 있었다. git 상태와 결과 파일을 먼저 확인해 완료된 전체 수집을 중복 실행하지 않았다.

## 2026-10-12 — AI EXPO 갱신 실패 후속 수정

- 원인: GitHub run 38225828342에서 robots.txt가 HTTP 202·179 bytes HTML challenge를 두 번 반환. 정상 정책을 확인할 수 없어 본문을 읽지 않고 차단했다. 로컬과 다른 GitHub 실행에서는 200이어서 실행 환경에 따라 반복되는 접근 확인임을 확인했다.
- 수정: 직접 사이트의 HTTP 조회 실패에 한해 독립 한국전시산업진흥회 SHOWALA 공개 행사 기록으로 동일 행사 검증·갱신. 공식 페이지의 구조 오류는 숨기지 않는다. 별도 robots·정확한 호스트·redirect·응답 상한 유지, 같은 상세 record의 최종 URL만 허용. 실제 읽은 출처와 직접 조회 실패를 기록하며 기존 ID/저장 기록 보존. 종료됐거나 다른 행사·연도·홈페이지·주최·기간의 기록은 거부한다.
- 실제 대체 경로: GitHub run 38261272189에서 SHOWALA robots/본문 조회·기간 파싱 성공(2027-04-14~16). 해당 실행에서는 원본 사이트도 200으로 정상 응답했으므로 실제 차단 회복과 독립 대체 경로 조회를 구분해서 기록한다.
- 검증: 신규 12개 회귀, 전체 Python 241·Node 118 통과. GPT-6 SOL 정적 교차 리뷰의 최종 URL 기록 개선 반영, Claude 정적 교차 리뷰 차단 이슈 없음. 두 리뷰 모두 테스트 직접 실행은 하지 않았고 root가 실행했다. GPT-6 Astra 리뷰는 사용량 한도로 실패했으며 통과로 기록하지 않는다.
- 보안/데이터: challenge 우회·UA 위장·robots/SSL 검증 약화 없음, 운영 LLM 호출 0. 원본 checkout/events.json 보존, 민감 연락처 없는 최소 fixture. 두 확인 경로가 모두 실패하면 이전 데이터 bytes와 verifiedAt 보존. `www.seoulmesse.com` 조사에서 TLS 검증 실패해 대체 경로로 채택하지 않았다.
- 운영: PR #5 병합 9c6a449, run 38262223254 성공. 데이터 0fa3c6eabe2e48a8aa3b7dc499c843c25ac09d1d Pages built 일치, 10개 출처 모두 ok. 이 실행에서는 AI EXPO 직접 사이트가 정상 응답했고, 별도 runner 진단으로 대체 경로도 조회/파싱되는 것을 확인했다. 이번 실행이 대체 경로로 복구된 것처럼 기록하지 않는다.
- 공개 검증: `tools/check_aiexpo_public.py --expected-at 2026-10-12T14:20:56Z` 통과. status의 checkedAt/lastSuccessAt와 항목 verifiedAt 모두 이번 run 시각과 일치, 기존 aiexpo-119c9024b15a ID 유지, 항목 1개. Edge 1440/390에서 모든 실패 알림 없음·목록 정상·overflow 없음·pageerror 0. 데이터 169건 오프라인 계약 통과, 공개 122건 확인. 증거 `docs/evidence/aiexpo-production.json`, `aiexpo-public-1440.png`, `aiexpo-public-390.png`.


## 2026-10-12 — AI Summit 갱신 오류 후속 수정

- 요청: 공개 보드의 AI Summit 갱신 실패 해결. Claude 한도 장애 보고 후 사용자 `너가 수정해줘`로 이번 오류의 Codex 직접 편집 승인.
- 원인 실측: GitHub 진단 run 38222377812. 앞 1MB에는 main이 없고 날짜 파싱 실패, 앞 2.5MB에는 main 문자열 위치 1,323,672와 2027-08-11~13 기간이 있어 파싱 성공. 로컬은 main 문자열 위치 212,176, 전체 590,217 bytes여서 기존 1MB 제한으로도 성공했다. 위치는 유니코드 문자 단위이며 읽기 제한은 바이트 단위다.
- 수정: AI Summit만 기존 MAX_BYTES(2.5MB)까지 읽고 멈춤. 전역 크기 제한·robots·허용 호스트·redirect·timeout 유지. 날짜를 찾지 못하면 기존처럼 오류·이전 데이터 보존. UI 경고를 강제로 숨기지 않는다.
- 검증: 실제 구조를 반영한 1.5MB 앞 padding 회귀 테스트가 수정 전 실패, 수정 후 성공. 2.6MB 뒤 행사 정보는 계속 오류. 전체 Python 229·Node 118 통과. 다른 모델(GPT-6 Astra) 독립 리뷰에서 차단 이슈 없음, 수집기 87개 테스트 직접 통과. 수정 후 GitHub runner run 38222751100도 동일 현상 재현과 2.5MB 날짜 파싱 성공. 운영 갱신·Pages 검증 결과는 아래에 기록한다.
- 운영 반영: PR #4 병합 8e1a7a4, 운영 수집 38223091709 성공, 데이터 d2cece2ec94cfd757a5998257dcbe5ce1e2e400d Pages built 확인. AI Summit status=ok, 기존 ID aisummit-57beffb6a815 보존, verifiedAt=lastSuccessAt=2026-10-12T08:21:49Z(이번 run 수집 시작 시각과 일치).
- 공개 검증: `tools/check_aisummit_public.py`로 1440/390 Edge 확인. AI Summit 실패 알림 없음, 목록 정상, 가로 넘침 없음, pageerror 0. 증거 `docs/evidence/aisummit-production.json`, `aisummit-public-1440.png`, `aisummit-public-390.png`. 독립 리뷰에서 지적한 최신성은 실제 run 시각과 별도로 대조했다.
- 별도 관측: 이번 전체 수집에서는 AI EXPO robots.txt가 HTTP 202를 반환해 blocked. 다른 9개 출처는 ok. 이 별도 차단을 우회하거나 성공으로 바꾸지 않았으며 기존 데이터를 보존한다. AI Summit 수정 완료와 전체 출처 모두 성공을 혼동하지 않는다.


## 2026-10-02 — AI 기회 보드 전면 개편

- 요청: AI 행사·공모전·해커톤만 탐색하도록 UI/UX와 수집 구조 전체 개편.
- 인테이크: 개인용, 국내+한국 참가 가능한 해외 온라인, 공개 무료/일1회/로그인 제외, 밝은 탐색 보드. 사용자 승인 `추천안으로 진행`.
- 기준: Haneul-two 저장소 최신 HEAD `ee68ae6442f3980fea6d55b2621d5e11c5c141bc`. 기존 bsky2327-oss checkout 및 CLAUDE.md 미커밋 변경은 보존. 새 checkout `C:/Users/caring/Projects/ai-data-storage-events`, branch `feat/ai-opportunity-board`.
- 조사: 기존 수집기는 유형/접수 마감이 없고 전체 소스 실패에도 updatedAt을 바꿈. workflow는 unrelated 카테고리 수집을 포함. 실제 테스트 workflow는 echo뿐.
- 환경: Node24.15.0, Python3.11.15, Claude Code2.1.287. Claude `READY` 호출 성공. 첫 shell 네트워크 차단은 읽기 호출 권한 확장으로 해결. 한글 stdin 깨짐은 UTF-8 파일 기반 인계로 예방한다.
- 출처 확인: Devpost robots 읽기 허용, 공개 목록 API 200 및 hackathons/meta 구조 확인. 위비티/데이콘 공개 목록·robots 200. 온오프믹스는 일반 수집 User-agent 차단으로 제외.
- 병렬 조사 에이전트는 사용량 제한으로 실패. 직접 조사로 전환.
- 문서: spec, UI/ingest 하위 사양서, implementation-plan 작성.

| 검증 | 상태 | 증거 |
|---|---|---|
| 최신 원격 HEAD | 통과 | git ls-remote: ee68ae6 |
| 별도 checkout/branch | 통과 | git clone, switch; 기존 checkout 보존 |
| Claude 응답 | 통과 | READY, exit0 |
| Devpost 공개 구조 | 통과 | HTTP200, hackathons/meta 및 2개 실제 항목 |
| 독립 사양서 점검 | 통과 | 6개 수정 반영(문서) |
| Python/Node 회귀 테스트 | 통과 | RED 후 GREEN. 최종 Python 97 OK · Node 106 pass (`docs/evidence/final-checks.txt`) |
| 실제 수집/실데이터 | 통과 | 4개 출처 ok(devpost 6·dacon 11·wevity 15·aisummit 1), 전체 33건. 최종 통합에서는 네트워크 재수집 안 함 |
| 화면/동작/반응형 | 통과 | `tools/browser_check.py` 35/35(Edge, 새 profile). 캡처 `docs/evidence/*-desktop.png`, `*-mobile.png` |
| 다른 모델 구현 교차 리뷰 | 통과 | Claude 구현 → Codex 독립 리뷰. 1차 7건·2차 4건 보완 |
| 원격 push/scheduled run/Pages 운영 | 미실행·미확인 | 통과로 쓰지 않음. 별도 사람 승인 필요 |

### 최종 통합 (2차 리뷰 4건 보완)

- 구현은 Claude, 독립 리뷰는 Codex. 1차 7건(`docs/tasks/review-fixes.md`) 보완 후 2차 4건 보완.
- 2차 4건: ① 로딩/오류 캡처에 '아직 수집된 기회가 없어요'가 보임 → `buildNotices`에 `phase` 전달, ready에서만 데이터 알림. ② `korea_allowed('... standard exceptions (see rules)')`가 True → 괄호 안 실제 국가명 목록일 때만 승인. ③ `load_curated`·신선 결과가 모양만 검증 → `meets_contract` 재사용. ④ 수집기 exit 1이면 workflow가 commit 전에 멈춰 실패 상태가 사이트에 안 나감 → `continue-on-error`+tests 후 commit+마지막 실패 step, exit 2는 commit 제외.
- 검사 수: Python 90→97, Node 103→106, 브라우저 35/35. 실제 결과는 `docs/evidence/final-checks.txt`.
- 캡처 위치: `docs/evidence/` (loading/error/empty/no-results/after/calendar/detail × desktop·mobile). 갱신 캡처 12개(after-desktop/mobile, detail-desktop, calendar-desktop/mobile, empty·error·loading-desktop/mobile, no-results-desktop)는 root가 직접 열어 확인을 마쳤다. 로딩·오류의 '미수집' 알림 제거도 확인.
- 현재 데이터: 전체 33 = 활성23(모집중21 + 예정2) + 종료9 + 마감1. 앞서 쓴 '종료일 기준 아직 끝나지 않음 24'는 화면 활성 수가 아니다(이전 단계의 역사 수치 34/24는 당시 결과로 유지).
- 교차 리뷰 완료: Claude 구현 → Codex 리뷰, Codex 보조도구(browser_check/run_claude) → Claude 읽기 리뷰. `tools/run_claude.py`의 `.cmd` 위험은 이 환경 비해당(`shutil.which`·`Get-Command` 모두 `claude.EXE`), 내부 전용·승인된 고정 명세만 전달.
- root 독립 재실행 완료: Python 97 OK, Node 106 exit0, offline 33/0 계약 통과, browser 35/35 오류0, 모든 항목 meets_contract True, 마스킹 누락 0, diff --check exit0. 기존 데이터 diff 없음, 기존 checkout CLAUDE.md 사용자 수정 보존.
- 로컬 성능 1회: navigation 436.8ms, 리소스 28·128432 bytes, DOM 897, 외부 리소스 0. 배포/실기기 성능은 미확인.
- 환경 브라우저 zoom 때문에 도구 CSS 너비와 캡처가 엇갈렸다 → 깨끗한 Edge profile로 실측해 해결.
- 브라우저 QA 스크립트: Python API `.first()` 오류와 중복 필터 버튼 locator 수정.
- 규칙집 추가 없음: 일반화할 규칙은 테스트와 최종 코드에 이미 드러나 별도 추가가 필요 없다.
- 한계: update.yml 변경은 YAML 텍스트 회귀로만 확인했고 Actions에서 실행한 적이 없다. 원격 scheduled run과 Pages 운영은 미확인.

## 2026-10-02 — 독립 사양서 리뷰 반영 (independent spec review completed)

- 독립 리뷰 결과를 문서에 반영(문서만 수정). `docs/implementation-plan.md`는 이미 존재했으므로 리뷰의 '계획 부재' 지적은 수정사항에서 제외.
- 수정 1: 전체 실패 시 opportunities.json 바이트 불변, 시도 상태는 `data/ingest-status.json`에 원자 기록 후 UI overlay. 부분 실패·archived·stale(90일) 규칙. 이유: 실패를 성공 갱신으로 오인 방지.
- 수정 2: `sourceStatus`/`stale` 추가, 상태 판정 우선순위와 필터(활성/모집중/예정/진행중/마감·종료/미정), date-only 당일 포함+시간 확인 필요. 이유: 마감 오판 방지.
- 수정 3: 한국 참가 허용 증거 기준과 국내/해외 eligibilityVerified 처리, 연령/학생 조건 보존.
- 수정 4: 허용 네트워크 호스트와 URL 검증(공인 HTTPS/443/userinfo 없음/redirect), 외부 apply URL 비fetch, 구조 미확인 소스는 error/blocked.
- 수정 5: 저장 id 소실 안내, URL 우선→localStorage→기본값, debug/now는 localhost/127.0.0.1 한정+테스트 배너.
- 수정 6: design-lab은 배포 root에 남는 기본 비노출 자료('미배포' 약속 금지), fixtures 최소 markup·출처 주석·연락처 마스킹.

## 2026-10-12 — 운영 활성화 승인 및 원격 반영 진행

- 승인: 사용자가 '원격 반영·Pages 배포·매일 09시 갱신 활성화'를 '이어서 진행'으로 승인했다. 추가 승인 질문은 없다.
- 권한: 원격 `Haneul-two/ai-data-storage`의 관리자·push 권한 확인. master/루트 legacy Pages 활성, URL https://haneul-two.github.io/ai-data-storage/.
- 원격 변경 보존: 원격 master가 ee68ae6에서 aa04b7e까지 자동 데이터 갱신 3건만 앞서 있다. 다른 변경을 되돌리지 않고 그대로 보존하며 병합한다.
- 내부 명세 로컬 보관: `docs/tasks/`(실행 명세)와 `tools/run_claude.py`(로컬 오케스트레이터)는 이번 작업의 내부 도구라 배포 저장소에 공개하지 않으려고 `.gitignore`에 추가했다. 파일은 삭제하지 않고 로컬에 둔다. `tools/browser_check.py`·테스트·검증 결과는 공개 검증 자료로 유지한다.
- 상태: 반영 진행 중이며 푸시·배포 완료는 아직 아니다.

### 2026-10-12 — 데이터 갱신 뒤 Pages 재빌드 누락 수정 (실행 검증 전)

- 발견한 운영 경계: `GITHUB_TOKEN`으로 push한 commit은 branch 기반(legacy) Pages build를 자동 실행하지 않는다. 현재 Pages는 master/루트 legacy라, 매일 갱신 commit이 생겨도 사이트가 갱신되지 않을 수 있었다.
- 수정(`.github/workflows/update.yml`): job `permissions`에 `pages: write` 추가(`contents: write` 유지). `Commit changes` 직후·마지막 실패 표시 step 이전에 `Request Pages rebuild` step 추가. `gh api --method POST "repos/${GH_REPO}/pages/builds"`, `GH_TOKEN`·`GH_REPO`는 env로 전달(토큰 값 저장·출력 없음). 종료 코드 2(데이터 손상)에서는 실행하지 않고, 정상/전체 실패(1)는 tests 성공 후 새 상태 JSON이 반영된 최신 master를 재빌드한다.
- 공식 근거: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site , https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build
- 상태: 실제 Actions runner에서 성공한 적 없다. 권한·재빌드 검증은 root가 실제 실행으로 한다. 작은 workflow 변경이라 YAML 텍스트 재현 테스트는 추가하지 않았다.

### 2026-10-12 — 운영 시작 (실제 배포·첫 수집·공개 사이트 검증 완료)

- 병합: PR https://github.com/Haneul-two/ai-data-storage/pull/1 MERGED(2026-10-12T01:09:52Z), master merge `d01cbf3f52424a7c5c6a39b9e215b6e02ec7bfba`. PR 최신 `0fb77d6`의 Python/Node GitHub 검사 모두 성공, 병합 master Test run 38190817171 success. 로컬 병합 후 Python 97 / Node 106 통과. 원격 최신 `aa04b7e`의 기존 데이터 갱신 3건은 그대로 보존 병합.
- 활성화: 저장소 변수 `ENABLE_OPPORTUNITY_UPDATES=true` 실제 설정. cron `0 0 * * *` = 매일 09:00 KST. **첫 실행은 수동 `workflow_dispatch`이며 예약 시각에 자동 발생한 실행이 아니다.**
- 첫 운영 수집: https://github.com/Haneul-two/ai-data-storage/actions/runs/38190817956 success. collect/tests/commit/Request Pages rebuild 전부 success. GitHub token `pages: write`로 Pages API 재빌드가 실제 작동함을 확인(이전 '실행 검증 전' 항목의 미확인 해소).
- 데이터 커밋: `24278837f43816a68e6f6a8912911bc8cdf45d05`. Pages latest status `built`, 동일 commit. 최신 배포 run 38190931779 success. 중복 Pages 실행 38190931297은 cancelled이며 최종 성공 빌드가 있으므로 오류가 아니다.
- 운영 화면: updatedAt 2026-10-12T01:10:08Z(10:10:08 KST). 전체 39건 / 활성 27(모집중 25 + 예정 2) / 종료 8 / 마감 4 / stale 5. Devpost 6 · DACON 10 · 위비티 22 · AI Summit 1, 네 출처 모두 ok. 출처 itemCount에는 보존된 예전 항목도 포함된다. stale 5는 화면에서 출처 재확인 표시로 보인다.
- 공개 사이트 검사: `docs/evidence/deployment-check.json` 10/10, 콘솔 오류 0. 최신 dataset timestamp·items가 remote master와 일치, production에서 debug/now 무시, 검색 포커스, 저장 후 재접속, 상세 HTTPS 링크·포커스 복귀, 달력, 모바일 390 가로 넘침 없음.
- 캡처: `docs/evidence/deployed-desktop.png`(1440×900), `deployed-mobile.png`(390×844)를 root가 직접 열어 확인.
- 루트 코드리뷰 Pages 보완: 데이터 갱신 commit 뒤 legacy Pages 자동 빌드가 없다는 점을 리뷰에서 짚어 workflow에 `pages: write`와 `Request Pages rebuild` step을 넣었고, 위 첫 실행으로 작동을 확인했다.
- 보존: 초기 `4dedda4`/`0fb77d6` PR 브랜치와 원본 checkout은 삭제하지 않았다. 로컬 `feat/ai-opportunity-board`는 master 운영 데이터까지 fast-forward 동기화했다. `docs/tasks/`·`tools/run_claude.py`는 gitignore로 로컬 보관, 공개 제외.
- 미확인: 예약 시각(cron)에 자동 발생한 첫 실행, 배포·실기기 성능 측정.
- 규칙집 추가 없음.

## 2026-10-12 — 공식 AI 행사 3종과 위비티 다중 페이지 수집 (로컬 구현, 원격 반영 전)

- 계기: 사용자가 "AI 행사 수집 범위가 너무 작다. 2026 서초 AI 페스타, 엔비디아 AI 데이 서울 2026 등 주요 행사도 수집해달라"고 요청. 조사 중 위비티 AI 검색 2페이지 10번째의 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤(ix111124)을 놓친 것도 확인(1페이지만 보고 소스당 20건 상한이라서).
- 구현(브랜치 feat/expanded-opportunity-sources, 기준 master cc4353f): 소스 `seocho`·`nvidia`·`aifesta` 추가와 공용 `sources/jsonld.py`(서초·AI Festa 2곳이 공유), `urlsafe` 허용 호스트 정확 일치 추가, `rules` 행사 정규식에 페스타·축제·festa·festival·AI Day 보완(해커톤>공모전>행사 우선과 강좌/채용 제외 유지), 위비티 최대 6페이지·상세 100건(`wevity.item_limit`/`page_url`). 기존 소스 우선순위는 그대로 두고 새 3종을 뒤에 등록.
- 기존 테스트 변경 1건: `test_opportunities.py`의 위비티 `collect` 테스트가 2페이지를 요청하게 되어 빈 2페이지 fixture(`wevity_empty.html`)를 추가.
- 검증: 새 `tests/test_expanded_sources.py` 43개를 먼저 작성해 RED(38 실패, `expanded-red.txt`) → 구현 후 Python 140 OK · Node 106 pass · `--offline` 통과(`expanded-green.txt`). 실제 수집 1회(약 4분): 7개 출처 모두 ok, 전체 39→109건(기존 39건 전부 보존). 위비티 89건(6페이지, 후보 89건, 상세 실패 0), 서초 AI 페스타(2026-10-17, 무료, 시민 누구나, 마감 null, sourceStatus unknown), NVIDIA AI Day Seoul 2026(2026-11-09~10 코엑스, 등록 CTA로 open, 마감·참가비 확인 필요), AI FESTA 26(2026-10-06~08, 종료), 고용24 해커톤(마감 2026-10-13) 모두 포함.
- 설계 선택 이유: 서브 프로그램 "오픈예정/마감"이 축제 전체 닫힘으로 읽히지 않게 sourceStatus unknown·deadline null. NVIDIA는 프로그램 탭의 11월 10일 시간이 아니라 연도 포함 hero 한 줄만 기간으로 읽고 title 연도와 대조. 이후 페이지 오류는 부분 성공으로 숨기지 않고 소스 실패로 처리해 기존 데이터를 보존. 사양 `docs/collection-expansion.md` 점검: 자격 근거는 FAQ 페이지가 아니라 메인 본문의 "시민 누구나" 문구를 쓴 것만 정정.
- 미실행(root 몫): 브라우저 검사, 원격 push·배포, Codex 독립 교차 리뷰. 이 항목은 완료로 기록하지 않았다.
- 규칙집 추가: CLAUDE.md '사고에서 얻은 규칙'에 2줄(위비티 전용 한도, 공식 행사 서브 프로그램 상태).

### 2026-10-12 — 확장 수집기 Codex 독립 리뷰 보완 (로컬, root 재리뷰·브라우저·배포 대기)

- Codex 읽기 리뷰 결과: 핵심 구현과 실수집 7개 출처는 정상. 좁은 보완 3건만 지적돼 Claude가 수정.
- ① 한국어 검색: NVIDIA 항목에 '엔비디아'·'데이'가 없어 "엔비디아 AI 데이 서울 2026"로 못 찾음 → 공식 영문 제목은 유지하고 tags에 `엔비디아`·`AI 데이`·`서울` 추가(총 6개). 회귀: `tests/filters.test.mjs`가 수집 데이터의 NVIDIA 항목을 실제 `applyFilters`(kind:event)로 검색.
- ② NVIDIA dateNote의 '공식 hero 표기'는 구현 용어라 '공식 안내의 개최 일정 기준'으로 교체(파서·함수명·코드 주석은 그대로).
- ③ 서초 fixture의 EventScheduled를 EventCancelled로 바꾸면 미래 취소 행사가 sourceStatus unknown(예정)으로 남던 문제 → `jsonld.read_event`가 schema `eventStatus`의 EventCancelled만 읽어 `closed` + dateNote '행사 취소'. EventPostponed 등 다른 값과 하위 프로그램 상태는 전체 행사에 적용하지 않음. RED(취소 회귀 1건·NVIDIA 문구 검사 실패 확인) 후 GREEN.
- 데이터 반영: 전체 재수집(90개 위비티 등)을 피하고 seocho·nvidia·aifesta 3개만 해당 수집 모듈로 다시 읽어 기존 문서에 병합(다른 4개 출처·항목·상태 보존, 해당 3개 출처 status/itemCount/checkedAt만 갱신, 원자적 쓰기). 결과 109건, sources 7개 유지, itemCount 합 109 = items 109. 서초 AI 페스타는 현재 취소 아님(unknown 유지).
- 검증: Python 142 OK · Node 107 pass · `--offline` 통과(`docs/evidence/expanded-green.txt`).
- 미실행(root 몫): 수정분 재리뷰, 브라우저 검증, 원격 반영·배포. → 브라우저 검증은 아래에서 완료.

### 2026-10-12 — 확장 로컬 브라우저 검증 및 Codex 독립 리뷰 기록 (원격 반영 전)

- Codex 최신 실측: Python 142 OK · Node 107 pass · `collectors/collect_events.py --offline` 109건 계약 통과.
- `tools/check_expanded_events.py`(Codex 작성): 실제 Edge, 데스크톱 1440·모바일 390 각 4검사(서초·NVIDIA 한국어 검색 1건, 가로 넘침 없음, 고용24 해커톤) = 8검사 통과, pageErrors 0. 증거 `docs/evidence/expanded-local.json`·`expanded-local-1440.png`·`expanded-local-390.png`. 도구는 Claude가 독립 리뷰했고 중대한 결함이 없어 수정하지 않았다.
- 원격 push·배포·공개 URL 검사는 아직 진행하지 않았다. 성공으로 기록하지 않는다.

## 2026-10-12 — 확장 PR #2 병합과 운영 반영 (실측)

- 병합: PR https://github.com/Haneul-two/ai-data-storage/pull/2 MERGED. 구현 `e82b77ed20d7d191f221a42ad4d85ad0a1b9d37c` CI run 38208056185 success. merge `04a31cd898be85fef74d81d1425a54d62e9f3da4` Test run 38208115198 success, Pages run 38208115264 success. 병합 커밋의 Pages built 확인됨.
- 운영 수동 update: run 38208115725 success, 수집 시각 2026-10-12T05:29:11Z, data commit `5b822b96069f121f4144944af46979be1c639988`.
- 운영 데이터: 110건 / 7출처 — devpost 6 · dacon 10 · wevity 90 · aisummit 1 · seocho 1 · nvidia 1 · aifesta 1. **6출처 ok, aisummit error**(원인: 응답 크기 2.5MB 상한 초과). aisummit은 이전 항목 1건과 검증 시각을 보존했다. 7출처 모두 성공이라고 쓰지 않는다. 위비티는 새 조회 89건 + 사라진 기존 항목 stale 보존으로 90건. 새 공식 3출처는 모두 정상.
- 공개 보드 검사: 실제 Edge 1440/390 총 8검사 통과, pageErrors 0(`docs/evidence/expanded-public.json`, `expanded-public-1440.png`, `expanded-public-390.png`). 별도 공개 검증에서 AI FESTA 26은 status closed 필터 1건(종료 표시), status open 0건.
- Codex 최종 실측: `gh` Pages builds/latest status built, commit `5b822b96069f121f4144944af46979be1c639988`. 공개 JSON updatedAt 2026-10-12T05:29:11Z·110건이 로컬 운영 최신과 일치. 공개 browser 8검사 재통과·pageErrors 0. 증거 `docs/evidence/expanded-deployment.json`.
- 미확인: 예약 시각(cron)에 자동 발생한 첫 실행, aisummit 크기 상한 초과 해소.
- 이전 '로컬 109건·7곳 ok' 기록은 로컬 수집 당시 사실이며 운영 수집 결과와 다르다(위 항목이 현재).

## 2026-10-12 — AI Radar 재설계·신청 마감 제외·수집 10출처 확장 (로컬 구현·검증 완료, 원격 배포 전)

- 요청과 확정 조건: AI 티가 나지 않는 전문가용 탐색 디자인(이름 AI Radar), 오늘 기준 신청 마감 제외, 수집 범위 확장. 사용자 확정 — 국내 + 한국 참가 해외 온라인, 공개 출처만·차단 우회 없음·운영 LLM 토큰 0, 한국 현재 시각에 확정 마감이 지난 항목은 탐색에서 제외, 시각 없는 마감(dateOnly)은 한국 당일 끝까지, 마감 미확정 미래 항목은 '확인 필요'로 유지. 사양 `docs/ai-radar-spec.md`, 디자인 `design.md`·`design-lab/radar/DESIGN.md`.
- 역할: GPT 6.1 SOL(max)가 웹 검색·설계·독립 캡처 리뷰, Claude가 기존 파일 구현, Codex가 독립 코드·실측 리뷰. 브랜치 `feat/ai-radar-redesign`.
- 화면: 비교 목록(데스크톱 열 머리글, 모바일 한 행에 마감·개최·참가·저장), 마감 임박·출처 상태는 필터 하단 접이식. 마감·종료는 `assets/visibility.mjs` 한 곳에서 판정해 목록·검색·건수·저장·달력·임박·상세 진입에서 제외한다(데이터 보관은 유지, 마감·종료 필터 삭제, 옛 `status=closed`는 all로 변환).
- 수집: 출처 7→10곳(콘테스트코리아·Dev-Event·AI EXPO KOREA). 위비티는 종료 행 상세를 읽지 않음(상세 약 89→53건), Devpost는 meta 기준 최대 5페이지·상세 20건, 교차 출처 중복 제거, aisummit은 앞 1MB 읽기. 한도·요청 수는 `docs/sources.md`. workflow 수집 step 18분·job 25분(기존 15분). 요청 수 해석: 소스별 상한 합계 약 250요청이지만 단정적 hard 상한은 아니고, 실측 1회가 robots·redirect 포함 257요청 약 4분 30초였다. 러너 지연을 요청당 3초로 가정해도 250요청 ≈ 12.5분이라 step 18분 안에 들게 잡았다.
- 사양 대비 독립 점검 6건(audit §0): 종료 행 상세 낭비, Devpost 14건 누락(1페이지만 읽음), 연도 포함 힌트 URL과 연도 하드코딩 금지 충돌, aisummit 2.5MB 로컬 미재현, 출처 간 중복, 개인 참가 판정 한계. 반려한 후보와 사유는 `docs/evidence/radar-source-audit.md` 참조(긴 목록은 여기 복제하지 않음).
- 검증(루트 독립 실행): Python **214 OK**, Node **118 pass**, 실제 Edge `tools/check_radar_ui.py` **98/98**·pageerror 0, 폭 320/375/390/414/768/1024/1280/1440 가로 넘침 0. 신규 `tests/test_radar_sources.py` RED 62건 중 56건 실패 → GREEN(`radar-backend-checks.txt`). 마감 직전/정각/직후, dateOnly 한국 날 경계, 옛 status=closed→all, 저장 id 보존, 달력·상세·임박·건수 일치, 열린 상세가 마감 시 닫힘, 키보드, 축소 모션, 오류/로딩/빈 상태 확인. 증거 `docs/evidence/radar-*.txt`·`radar-*.png`.
- 독립 리뷰 보완: wevity/contestkorea의 "현재 페이지가 전부 closed면 중단" 조기 중단 제거(등록순이라 뒷페이지에 활성이 있을 수 있음), 교차 출처 중복 키에서 의미 있는 `[Track1]` 같은 태그 보존(같은 날짜 Track1/Track2 보존), Dev-Event `sourceUrl`을 읽은 README 월 anchor로 고정·해외 오프라인 제외, Fetcher prefix 읽기 `1..maxBytes` 검증.
- 실수 기록:
  - 태블릿 폭 결함: 가로 넘침 0이었지만 768px에서 첫 행 제목 폭이 30px(저장 버튼 36px)이었다. 수정 후 768 **710px**, 모바일 390 160→**332px**. 폭별 제목 최소 폭을 실측하는 검사로 바꿨다(`radar-layout-red.txt` RED).
  - Windows 일회성 Python 결과 경로에 `/tmp/radar`를 써서 수집 검증 중 경로 오류가 1회 났다(작업 기록 기준, repo 로그에는 남지 않음). 실제 Windows Temp 절대 경로를 쓴다.
  - 온오프믹스 robots 선검증 누락 1회: 조사 중 robots 전문을 끝까지 읽기 전에 목록 페이지를 1회 요청했다. robots는 `Disallow: /`(우리 UA 비허용)였다. 그 응답은 폐기했고 저장·구현에 쓰지 않았으며 이후 요청·구현은 없다. 운영 Fetcher는 요청 전 robots 검사를 계속 강제한다.
- **미완료·미검증**: ① root의 최종 실수집(`data/opportunities.json` 갱신 1회)이 진행 중이다 — 완료 후 이 파일에 건수·출처별 상태를 추가한다. 예전 dry-run의 164건(이전 183건 표기 포함)은 현재 데이터가 아니다. ② 원격 재설계 배포는 아직 진행하지 않았다(이미 승인된 운영 업데이트 범위로 진행 예정, 배포 완료는 확인 전까지 단정하지 않음). ③ 예약 cron 자동 첫 실행 미검증. ④ 실제 10출처 모두 ok는 이전 dry-run 1회의 결과일 뿐이며 원격에서 모두 ok라는 보장은 없다. ⑤ aisummit 2.5MB 초과 해소 여부는 운영 수집으로만 확인된다.
- 규칙집 추가: `AGENTS.md`·`CLAUDE.md` '사고에서 얻은 규칙'에 제목 최소 폭 실측, 현재 페이지 closed만으로 중단 금지, Windows Temp 절대 경로(AGENTS만). 스킬 규칙 폴더는 수정하지 않았다(코드·회귀에 이미 반영된 교훈).

## 2026-10-29 — 디자인 비교 시안 4종 (검증 대기, 운영 화면 미변경)

- 사용자 요청 "하늘 창고 디자인 선반 참고해 개선"에서 "시안부터 비교"를 선택. 운영 파일 변경 없이 `design-lab/shelf-20261029/`에 시안 4종(01 포커스·02 에디토리얼·03 디스커버·04 플래너)과 비교 갤러리를 추가했다. 설계·한계 `design-lab/shelf-20261029/DESIGN.md`.
- 구현자(Claude) 실Edge 검증: 갤러리+시안 4종 폭 320/375/414/768/1440 가로 넘침 0·console/pageerror 0·조작 목표 44px 이상, 검색·유형·참가 방식·정렬·빈 결과 초기화·fetch 실패 재시도·reduced motion 확인(실제 데이터 159건 노출 기준).
- 미완료: Codex 독립 검증·교차 리뷰, 시안 선택, 운영 적용(저장·달력 등 기존 기능 보존 필요). 운영 화면은 그대로다.

## 2026-10-29 — 포커스 디자인 운영 소스 적용 (로컬 적용·검증 완료, 원격 미반영)

- 사용자가 시안 01 포커스를 선택하고 제목을 "AI 공모전·해커톤·행사 모아보기"로 확정. `index.html`·`tokens.css`·`assets/styles/{layout,components,rows}.css`·`assets/app.js`(요약 바인딩 3줄)·`assets/render.js`(요약 갱신)만 수정. data/·collectors/·.github/·순수 로직 `.mjs`·`tests/`는 건드리지 않았다.
- 설계: 눈에 보이는 h1(1440에서 30px) + 요약 3종. 검색·유형을 왼쪽 열(`.rail-main`)로 옮겨 1279 이하에서도 항상 보이게 하고 진행 상태·참가 방식만 기존 토글로 접는다. 유형은 1280 이상에서 세로 목록. 선택 상태는 연초록 바탕 + 짙은 초록 글자. 요약은 기존 `applyFilters(DEFAULT_FILTERS)` 노출 목록과 `getDeadline` 재사용(새 판정 없음).
- RED → GREEN: 새 `tools/check_focus_ui.py`를 먼저 작성해 기존 화면에서 실패(제목 불일치·요약 없음)를 확인한 뒤 적용.
- 실검증(로컬 8012, Edge): `check_focus_ui.py` 42/42(1440~320 폭, 로딩/오류/새로고침 실패 요약 포함), `check_radar_ui.py` 98/98 pageerror 0, Node 118 pass. Python 수집기 테스트·실수집은 UI 전용 작업이라 실행하지 않았다. 증거 `docs/evidence/focus-ui-checks.json`·`focus-{1440,768,390}.png`.
- 기존 검사 수정 1건: `check_radar_ui.py`의 검색어를 `items[0]`(이미 마감돼 목록에서 빠진 항목일 수 있음) 대신 `visible[0]`에서 고르도록 바꿨다 — 실데이터 갱신 후 0건으로 실패한 기존 취약점이며 디자인과 무관.
- **미완료**: Codex 독립 git diff·실Edge 캡처·기능 회귀 교차 리뷰 대기. commit·push·배포 없음(공개 사이트는 이전 디자인 그대로).
