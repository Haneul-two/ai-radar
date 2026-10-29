# AI Radar 디자인 비교 시안 — 최종 독립 검증

- 일자: 2026-10-29 KST
- 요청: 하늘 창고 디자인 선반 참고한 AI Radar 개선. 사용자 후속 선택: **시안부터 비교**.
- 구현: Claude Code. 독립 검토·최종 실측: Codex.
- 상태: 시안 4종·비교 갤러리 완성, 사용자 선택 대기. 운영 적용·원격 push·배포 없음.

## 최종 검증

Claude의 마지막 모바일/CSS 보완 완료 후 Codex가 `.venv/Scripts/python.exe -X utf8 docs/tasks/check_shelf_design_20261029.py`를 독립 재실행했다.

- 실제 Edge **107/107**, pageerror **0**. 전체 결과: `checks.json`.
- 시안 4종과 갤러리 각각 320/375/414/768/1440px 가로 넘침 없음.
- 제목 폭·버튼 높이, 검색 포커스 유지, 빈 결과/초기화, 유형/참가 방식 필터, fetch 실패/재시도, reduced motion 확인.
- 안전한 HTTPS 안내 링크와 noopener/noreferrer 확인.
- 운영 필터·마감 제외 Node 검사 `node --test tests/filters.test.mjs tests/visibility.test.mjs` **29/29**.
- 원본 운영 index.html, tokens.css, assets/, data/, collectors/, tests/ 변경 없음. 기존 추적 파일 변경은 이번 작업 기록을 추가한 AGENTS.override.md와 docs/HISTORY.md뿐.

## 캡처 직접 검토

- `gallery.png`: 네 구조 차이와 2열 비교 확인.
- 01 데스크톱: 필터·목록 열 정렬과 제목 폭 확인.
- 02 모바일: '129건' 숫자/단위 한 줄 확인. 요약 1열 적용.
- 03 모바일: 카드 단일 열, 제목/참가/마감 정보 확인.
- 04 모바일: 중복 일정 사이드바 숨김으로 날짜 목록이 첫 화면에 진입함을 확인.
- 데스크톱 플래너 CSS의 잘못 중첩된 규칙도 Claude가 보완했으며 최종 1440px 재검증·캡처에 포함됨.

## 참고와 경계

하늘 창고 `data/refs.json`의 디자인 분류를 확인하고 Kombai Gallery, v0 templates, 21st.dev를 Codex가 실제 방문했다. 구조/타이포/선택 상태만 참고하며 외부 코드·이미지·폰트를 복제하지 않았다. Motion Prompt는 등록 자료로만 참고했다.

시안은 실제 로컬 데이터와 기존 마감·필터 판정을 사용한다. 검색·유형·참가 방식·정렬·안내 링크만 동작한다. 저장·상세 드로어·달력·상태 필터·URL 상태는 시안에 구현하지 않았으며 선택 후 운영 적용 단계에서 보존할 대상이다. 백엔드 수집·자동화 변경은 없다. 외부 자산이 없는 읽기 전용 시안이므로 추가 캐시/서버/전송 기능은 생략했다.

Hallmark 자체 평가(5점): 철학 4 / 위계 4 / 구현 4 / 구체성 4 / 절제 4 / 구조 다양성 5. 최종 운영 화면에 대한 접근성 인증이나 전체 기능 회귀 완료를 뜻하지 않는다.
