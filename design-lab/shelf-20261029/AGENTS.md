# shelf-20261029 시안 디렉터리 규칙

상태(2026-10-29): 4개 시안 + 비교 갤러리 구현, 구현자(Claude) 브라우저 검증 통과, **Codex 독립 검증 대기, 운영 화면 미변경.** 설계·한계는 `DESIGN.md`.

- 이 디렉터리 안에서만 수정한다. 운영 `index.html`·`tokens.css`·`assets/`·`data/`·`collectors/`·`tests/`는 건드리지 않는다.
- 구성: `shared.js`(데이터·상태·항목 모델) · `controls.js`(공통 조작부) · `views.js`(시안별 화면) · `styles.css`(공통 + 4테마) · `gallery.*`.
- 판정(마감 제외·상태·정렬·건수)은 `../../assets/`를 재사용하고 새로 만들지 않는다. 가짜 데이터·fixture 금지.
- 출처 문자열은 `h()`/text node만. innerHTML 금지. 외부 링크는 `safeHttpsUrl` 통과분만.
- 검색 입력·선택 그룹은 재생성하지 않는다(포커스·캐럿 유지).
- HTTP(localhost)로만 연다(file:// 불가, 이유는 DESIGN.md).
