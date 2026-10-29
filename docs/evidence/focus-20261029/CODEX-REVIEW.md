# 포커스 디자인 적용 — Codex 최종 교차 리뷰

- 날짜: 2026-10-29 KST
- 구현: Claude Code. 검토/최종 독립 실행: Codex.
- 사용자 확정: 시안 01 포커스, 화면 제목 **AI 공모전·해커톤·행사 모아보기**.
- 상태: 로컬 운영 소스 적용 및 검증 완료. 원격 push/merge/배포 미실행. 공개 화면은 아직 이전 버전.

## 코드 검토

index.html의 기존 ID/조작을 보존하면서 검색·유형을 좌측 상시 노출 영역으로 옮겼다. 추가 필터만 좁은 화면에서 접는다. 기존 검색 debounce/URL/localStorage/저장/상세/달력의 연결은 변경하지 않았다. 새 요약은 기존 DEFAULT_FILTERS 노출 목록과 getDeadline을 재사용하며 검색·유형·저장 필터와 무관하다. 로딩/오류는 가짜 건수 없이 표시하고 새로고침 실패는 기존 데이터와 요약을 유지한다. 색/상태 토큰과 CSS 변경은 선택된 시안 범위다.

검토상 차단할 결함 없음. Node 순수 로직, data/, collectors/, .github/, tests/ 변경 없음 확인. git diff --check 통과. README/design/지시파일/이력의 로컬 적용·원격 미반영 설명 확인.

## 최종 독립 실행

| 명령 | 결과 |
|---|---|
| node --test tests/*.test.mjs | 118/118 |
| .venv/Scripts/python.exe -X utf8 tools/check_radar_ui.py | 98/98, page/console error 0 |
| .venv/Scripts/python.exe -X utf8 tools/check_focus_ui.py | 42/42, 의도한 요청 중단 이외 page/console error 0 |
| .venv/Scripts/python.exe -X utf8 docs/tasks/focus-final-review-20261029.py | 320/375/414/768/1280/1440px, 가로 넘침 0, 제목 폭 >=200px, pageerror 0 |

새 브라우저 컨텍스트에서 첫 화면 캡처를 직접 검토했다. `focus-1440.png`에서 제목·요약·좌측 필터·비교 목록 정렬, `focus-375.png`에서 검색·유형 상시노출과 세로 행/저장 버튼을 확인했다. 전체 폭 실측은 independent-layout.json.

기능 회귀는 검색 포커스/URL, 저장 지속, 상세 열기/닫기/키보드 포커스, 달력 월이동/상세, 로딩/빈결과/오류, 마감시각 경과 후 제외, reduced-motion까지 포함한다.

브라우저 검사 병렬 실행 중 로컬 서버에 1회 연결 거부가 발생해 해당 focus 검사를 단독 재실행했고 42/42 통과했다. 코드 변경은 필요하지 않았다. 수집기·실수집은 UI 변경 범위가 아니므로 실행하지 않았다.

## 전송 경계

프로젝트 AGENTS.md 및 사용자 전역 지침의 원격 push·배포 별도 승인 규칙을 따른다. 검증된 로컬 결과를 보여준 뒤 원격 반영 승인을 받는다. 이전 시안/기록과 파일은 보존했다.
