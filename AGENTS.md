# AI 기회 보드 — 작업 규칙과 현재 상태

- 현재 상태(2026-10-12, AI Radar): **로컬 재설계·신청 마감 제외·수집 10출처 확장 구현과 검증 완료, 원격 재설계 배포 대기.** 운영 사이트는 이전 화면이다. 최종 실수집은 root가 진행 중이라 **현재 데이터 건수는 최종 수집 후 `docs/HISTORY.md`에 기록**한다(예전 dry-run 164/183건을 현재 데이터로 쓰지 않는다). 원격 반영은 이미 승인된 운영 업데이트 범위로 root가 하며, 배포 완료는 확인 전까지 단정하지 않는다. 예약 cron 자동 첫 실행도 미검증. 기획: `docs/ai-radar-spec.md`, 출처 감사: `docs/evidence/radar-source-audit.md`.
- 이전 상태(2026-10-12 운영 시작, 역사): **운영 시작됨.** PR #1 병합(master d01cbf3), 첫 운영 수집(수동 workflow_dispatch run 38190817956) 성공, Pages 최신 빌드가 데이터 커밋 2427883과 동일, 공개 사이트 https://haneul-two.github.io/ai-data-storage/ 정상. 매일 09:00 KST 갱신 활성화(`ENABLE_OPPORTUNITY_UPDATES=true`)·교차 리뷰 반영 완료. 단, **예약 시각에 자동 발생한 첫 실행은 아직 없어 통과로 쓰지 않는다.** 원격 master의 자동 데이터 갱신 3건(ee68ae6→aa04b7e)은 보존 병합했다. `docs/tasks/`·`tools/run_claude.py`는 내부용이라 git 제외(로컬 보관). 증거·run·commit은 `docs/HISTORY.md`. 확장 운영 반영: PR #2 병합(merge 04a31cd), 수동 update run 38208115725 success(data commit 5b822b9, Pages built·공개 JSON 최신 일치 확인, 증거 `docs/evidence/expanded-deployment.json`), 110건·6출처 ok + aisummit error(응답 2.5MB 상한 초과, 7출처 모두 성공 아님). 예약 자동 실행은 아직 미검증.
- 아래는 운영 시작 전 로컬 검사 기록(역사): 2026-10-02 **로컬 구현·검증 완료, 원격 미실행**(push·workflow 실행·Pages 운영·예약 활성화 없음). 기준 저장소 `Haneul-two/ai-data-storage`, 기준 HEAD `ee68ae6442f3980fea6d55b2621d5e11c5c141bc`, 브랜치 `feat/ai-opportunity-board`.
- 사용자 승인: 개인 참가 기회 탐색, 국내 전체 + 한국에서 참가 가능한 해외 온라인, 공개 무료 소스, 하루 1회, 밝은 탐색 보드. UI와 수집 파이프라인 전체 구현. 추가 방향 질문 없이 진행한다.
- 기존 `C:/Users/caring/Projects/ai-data-storage`의 사용자 변경은 손대지 않는다. 이번 작업은 이 별도 checkout에서만 진행한다.
- 기존 파일 편집은 Claude Code가 수행한다. Codex는 새 문서 작성, 조사, 실행 검증 및 Claude 구현 교차 리뷰를 수행한다.
- 사양서: `docs/spec.md`, `docs/spec-ui.md`, `docs/spec-ingest.md`. 구현 계획: `docs/implementation-plan.md`. 경과·검증·리뷰: `docs/HISTORY.md`.
- 기존 뉴스/논문/채용/도구 파일은 보존하지만 신규 화면과 자동 수집 경로에서 사용하지 않는다. 파일·브랜치 삭제, 푸시·배포·예약 활성화는 별도 승인 대상이다.
- 원본 `data/events.json`은 읽기 전용으로 보존한다. 신규 데이터는 `data/opportunities.json`, 수동 입력은 `data/curated.json`으로 분리한다.
- 공개 URL과 날짜는 확인한 값만 사용한다. 미확정 참가비·마감일·참가 자격을 추측하지 않는다.
- 크롤러는 robots 정책·도메인 허용목록·타임아웃·요청 한도를 실행 시 적용한다. 로그인, 우회, 유료 API, 자동 참가 신청은 구현하지 않는다.
- 화면·중간 JSON·로그에는 전화·이메일 등 연락처를 저장하지 않는다. 외부 HTML을 실행하거나 innerHTML에 주입하지 않는다.
- 수집 전체 실패 시 `data/opportunities.json`은 바이트 단위 불변이다. 매 시도 상태는 `data/ingest-status.json`(`{lastAttemptAt, sources: Source[]}`)에 원자적으로 기록하고 UI loader가 opportunities.sources에 id 기준 overlay한다. 일부 실패 시 성공 소스만 교체하고 실패 소스의 항목/verifiedAt은 보존한다. 성공 소스에서 사라진 활성 항목은 stale=true, 90일 지난 종료 항목만 제외한다. 파일 삭제는 없다.
- 네트워크 허용 호스트는 devpost.com(*.devpost.com), wevity.com, dacon.io, 공식행사 adapter용 aisummit.co.kr·seochoai.kr·www.nvidia.com·aifesta.kr, 신규 www.contestkorea.com·aiexpo.co.kr·www.showala.com·raw.githubusercontent.com, 2026-10-28 lotteaxchallenge.com·linkareer.com(각 정확한 호스트)뿐이며 공인 HTTPS 443·userinfo 없음·redirect 동일 검증. `?debug`/`?now`는 localhost/127.0.0.1에서만 작동한다.
- 로컬 실행: `.venv/Scripts/python.exe -m http.server 8012 --bind 127.0.0.1`.
- 검사 명령(2026-10-02 결과): `.venv/Scripts/python.exe -m unittest discover -s tests -v`(AI Radar 로컬 214 OK — 이전 142) · `node --test tests/*.test.mjs`(118 pass — 이전 107) · `.venv/Scripts/python.exe collectors/collect_events.py --offline`(통과) · `.venv/Scripts/python.exe tools/browser_check.py`(35/35, Playwright 1.63.0 + installed Edge) · `.venv/Scripts/python.exe tools/check_radar_ui.py`(AI Radar 화면 98/98, pageerror 0, 서버 8012 필요, `docs/evidence/radar-frontend-checks.txt`). 증거 `docs/evidence/final-checks.txt`.
- 현재 데이터는 로컬 최종 수집 후 기록 대기. 마지막으로 확인된 운영 데이터(2026-10-12 운영 수동 수집 5b822b9): 전체 110건, 6출처 ok + aisummit error(응답 2.5MB 상한 초과, 이전 1건·검증 시각 보존). devpost 6 · dacon 10 · wevity 90(새 89 + stale 보존) · aisummit 1 · seocho 1 · nvidia 1 · aifesta 1. 과거 로컬 109건(7곳 ok) 기록은 HISTORY. 이전 기준(2026-10-02): 전체 33건, 출처 4곳.
- 한계: 위비티는 AI 검색 최대 6페이지·상세 100건(종료 라벨 행의 상세는 읽지 않음), Devpost는 meta 기준 최대 5페이지·상세 20건, 콘테스트코리아 'AI' 12+'인공지능' 3페이지·상세 60건, Dev-Event README 1회·항목 100 상한, DACON은 1페이지·20건이다(`--max-items`는 목록형 소스의 상한). aisummit은 기존 안전 상한인 앞 2.5MB까지 읽고 기간을 못 찾으면 오류, 응답 전체 2.5MB cap은 유지. 공식 행사 3곳은 지정한 사이트만 본다(웹 전체 발견 아님). 자격·일정은 원문 문구 기준이라 불확실할 수 있으며(DACON 자격 `확인 필요`, 위비티 마감은 날짜만) 화면이 그대로 '확인 필요'로 표시한다. 수동 실행 1회와 Pages 운영은 확인했으나 예약 시각에 자동 발생한 첫 실행은 아직 확인하지 않았다.
- archived: 종료 후 90일이 지난 항목만 출력에서 뺀다(그 전에는 보존). 병합 때 저장 항목에도 관련성·지역·자격·초대 전용 계약을 다시 검사해 위반분은 출력에서 제외한다(예전 규칙으로 들어온 항목이 영구 보존되지 않게 하려는 것).
- 기존 `C:/Users/caring/Projects/ai-data-storage` checkout은 그대로 보존했다.

## 사고에서 얻은 규칙

- 도구 연결 종료는 실행 취소를 뜻하지 않았다 → 재개 시 git 상태·결과 파일부터 확인해 이미 완료된 수집을 중복 실행하지 않는다.

- 가로 overflow가 0이어도 태블릿(768px)에서 첫 행 제목 폭이 30px이었다 → 폭별로 제목의 최소 폭(실측)을 함께 검사한다. 수정 후 768에서 710px, 모바일 390에서 160→332px.
- 목록 현재 페이지가 closed뿐이라고 뒷페이지에 활성이 없다고 판정하면 놓친다(위비티는 등록순이라 마감이 단조롭지 않다) → 빈/반복 페이지와 상한에서만 멈춘다.
- Windows 일회성 Python 결과 경로에 `/tmp/radar`를 써서 수집 검증 중 경로 오류가 1회 났다 → 실제 Windows Temp 절대 경로(`$env:TEMP`)를 쓴다.
- 실패한 조회를 성공 갱신으로 기록하지 않는다. 기존 수집기는 소스 실패에도 updatedAt을 바꿔 데이터 신선도를 오인하게 했다.
- root가 소유한 서버(8012)는 소유하지 않은 구현자가 끝내지 않는다. 실제 frontend 작업이 root 8012까지 종료해 브라우저 연결이 끊겼고 root가 재시작했다.
- 에이전트 호출 프롬프트는 UTF-8 파일로 전달한다. PowerShell에서 Python stdin으로 한글 코드를 전달하면 문자열이 물음표로 바뀔 수 있다.
