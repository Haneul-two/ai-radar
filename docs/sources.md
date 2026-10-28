# 수집 소스 사실과 한계

> **AI Radar(2026-10-12, 로컬 구현)**: 출처 10곳(기존 7 + 콘테스트코리아·Dev-Event·AI EXPO KOREA). 이 문서 아래 본문 중 7곳 기준 서술(허용 호스트·위비티·Devpost·aisummit·우선순위·한계)은 '## AI Radar 변경(2026-10-12)'가 우선한다. 반려한 후보와 사유는 [`evidence/radar-source-audit.md`](evidence/radar-source-audit.md)(여기에 긴 목록을 복제하지 않는다). 현재 데이터 건수·출처별 ok는 최종 수집 후 `HISTORY.md`에 기록한다. **원격 재설계 배포 전**이며 원격에서 10출처 모두 ok라는 보장은 없다.

기준일 2026-10-02 실측(공식 행사 3종·위비티 다중 페이지는 2026-10-12 추가). 구현: `collectors/opportunities/sources/`. 실행: `.venv/Scripts/python.exe collectors/collect_events.py [--dry-run|--offline] [--output PATH] [--max-items N]`.

## 공통 정책

- User-Agent `ai-opportunity-board/1.0`. 위비티는 URL이 들어간 긴 UA를 403으로 거절한다(브라우저 흉내는 쓰지 않는다).
- 허용 호스트: devpost.com(*.devpost.com), wevity.com, dacon.io, aisummit.co.kr(각 www 포함), seochoai.kr(www 포함), www.nvidia.com, aifesta.kr(www 포함) — 새 호스트는 정확한 이름만 허용(하위 도메인 아님). 모든 요청과 redirect는 HTTPS 443·userinfo 없음·허용목록을 재검증한다. redirect 3회, 응답 2.5MB, 요청 timeout 15초, 요청 간 1초.
- robots.txt는 호스트별로 실행 중 캐시한다. 404/410만 "규칙 없음"이고 timeout·403·5xx는 `blocked`다(허용으로 보지 않는다). 와일드카드(`*`, `$`)와 최장 일치를 직접 해석한다.
- 소스당 최대 20건(Devpost 기본 10건, 위비티 예외 아래 참고). 외부 신청 링크(위비티 홈페이지 필드)는 fetch하지 않고 안전한 HTTPS 링크로만 저장한다.
- 설명은 200자 이내 요약, 이메일·전화는 `[연락처 생략]`으로 치환한다. 연락처 섹션은 추출하지 않는다.

## Devpost (`devpost`)

- 목록 `https://devpost.com/api/hackathons?search=AI&status[]=open&challenge_type[]=online&page=1` → `{hackathons, meta}`. 구조가 다르면 오류, `hackathons: []`는 정상 0건.
- 필터: `themes`에 Machine Learning/AI, 위치 Online, `open_state=open`, `invite_only=false`. 통과분만 상세 1회 조회.
- 상세: `#eligibility-list`(연령·학생 조건 + 국가 문구, 제외 국가는 `span[title]` tooltip), `[data-iso-date]` 정확한 마감 시각, `meta[name=description]` 한 줄 소개.
- 한국 참가 근거(`rules.korea_allowed`): 전세계 문구 + 제외 목록이 South Korea/Republic of Korea/Korea/KR/한국을 금지하지 않음, 또는 제한 목록이 한국을 명시 포함. **North Korea 제외는 한국 제외가 아니다.** "excluding standard exceptions"만 있고 목록을 알 수 없으면 제외한다.
- 마감: 원문 시각(예 `2026-10-26T17:00:00-04:00`)을 `deadlineAt`에 그대로 두고 `deadlineDate`/`endDate`는 서울 날짜(10-27). `dateNote`에 원문 시간대 표기. 시작일은 목록 `submission_period_dates`.
- 참가비는 출처에서 확인하지 않아 `확인 필요`. 상금 `$0`은 null.

## DACON (`dacon`)

- `https://dacon.io/competitions`(SSR)의 `.official-comp` 안 `a[href*="/competitions/official/"]`, 제목 `.name`, 태그 `.keyword`, 상태 `.dday`(참가신청중→open, 마감→closed, 그 외(연습 등)→unknown).
- AI 관련 제목/태그만 최대 20건(open → unknown → closed 순, 목록의 최신순 유지). 각 `/overview/` 상세 조회.
- 상세 inline script `window.__NUXT__=(function...` 은 **실행하지 않고** `competitionDetail` 이후의 따옴표 문자열 필드(`period_start`, `period_end`, `submission_end`, `prize_info`)만 정규식+JSON 문자열 디코드로 읽는다. 변수 참조(`description:k` 등)는 읽을 수 없어 설명은 키워드 요약으로 대체.
- `submission_end`(제출 마감) → `deadlineAt` `+09:00`. `merge_deadline`은 팀 병합 마감이라 쓰지 않는다. `period_start/end`는 대회 기간이며 접수 시작일로 추정하지 않는다. `submission_end`가 시작일보다 앞서는 원문 모순(실제 관측: SW부문 2025-07-15)은 마감으로 쓰지 않고 null.
- 참가 자격은 확인 불가 → `확인 필요`(verified=false). 방식: 제목의 오프라인/온라인, 키워드 `코드 제출`이면 online, 나머지 unknown. `채용` 태그만으로 해커톤을 제외하지 않는다(제목 기준 부트캠프·강의·채용공고만 제외).

## 위비티 (`wevity`)

- 검색은 반드시 `sp=name`(또는 `sp=contents`)이 있어야 필터가 적용된다: `https://www.wevity.com/?c=find&s=1&gub=1&sp=name&sw=AI`. 행 `.list li`(헤더 `li.top`), 제목 `.tit a[href*="gbn=view"]`, `.organ`, `.day .dday`.
- 목록은 `gp=2..6`으로 최대 6페이지(15개씩, 후보 최대 90)까지 읽고 상세는 최대 100건이다. `--max-items`를 주면 그 값(100 이하)이 한도이며 한도를 채우면 다음 페이지를 읽지 않는다. 같은 `ix`는 한 번만 보고, 빈 페이지나 이미 본 페이지가 오면 멈춘다. 2페이지 이후의 HTTP·구조 오류는 소스 오류가 되어 기존 데이터를 보존한다(부분 결과를 성공으로 쓰지 않음).
- 제목을 로컬에서 다시 AI 단어 경계로 걸러 상세 `?c=find&s=1&gub=1&gbn=view&ix=ID`를 조회한다. 상세 `ul.cd-info-list`: 응모대상, 주최/주관, 접수기간(`시작 ~ 마감`), 총 상금/1등 상금, 홈페이지.
- 접수기간 마감은 날짜만 제공 → 상세 본문(`#viewContents`)에서 **마감 날짜 바로 뒤에 붙은 시각**이 하나로 정해질 때만 `deadlineAt`(KST)을 채운다(24:00·밤 12시는 그날 23:59:59). 없거나 서로 다른 시각이 섞이면 null, `dateNote`에 날짜만 제공 명시. 개최일은 제공되지 않아 start/endDate null. 응모대상이 있으면 그대로 저장(원문 표기, "기타"·"제한없음" 포함).
- 방식(2026-10-16~): 제목에 온라인/오프라인이 없으면 본문 접수·진행 문장으로 판정한다(`sources/wevity_body.py`). 근거는 단어와 행동어가 15자 안에 있는 줄만, 문의처 줄 제외. 온라인 접수·제출(이메일·구글폼·홈페이지)만으로 온라인이라 보는 건 공모전뿐(해커톤·행사는 '온라인 진행' 문구 필요). 온라인 접수 + 오프라인 진행은 오프라인, 온라인 진행·재택 + 오프라인은 혼합.
- 참가비: 본문에 `참가비/참가료/교육비 … 무료·없음` 또는 `참가비: N원`이 명시된 경우만 채우고, 없으면 '확인 필요'(공모전은 대부분 무료라 언급 자체가 드물다 — 실측 94건 중 4건).
- 한계: 다수가 AI 영상/이미지 공모전이다(제목에 AI 포함). 2026-10-16 실측 94건 중 방식 42건·마감 시각 38건 판정, 나머지는 근거 문구가 없어 미정. 외부 홈페이지 링크는 여전히 fetch하지 않는다(실측 16곳 중 7곳이 인증서 오류·SNS·스크립트 렌더링이라 읽히지 않음).

## AI Summit Seoul (`aisummit`)

- 공식 행사 단일 페이지 어댑터. 현재 페이지는 **2027.8.11(수) - 8.13(금)** 을 노출하지만 `<title>`은 2026 표기다. 본문 `YYYY.M.D(요일) - M.D` 표기와 `컨퍼런스/EXPO YYYY년 M월 D-D일` 표기만 신뢰하고, 서로 연도가 다르거나 읽지 못하면 오류. 제목 연도가 다르면 소스 메시지에 경고.
- 컨퍼런스 8/11-12, EXPO 8/11-13, 코엑스, 주최 DMK Global/COEX/KITA. 마감·참가비·자격은 확인 필요(추측하지 않음). 푸터/연락처 텍스트는 저장하지 않고 설명은 구조화 필드로 합성.
- `aisummit.co.kr/robots.txt`는 `/api/`, `/search`, `?format=` 계열 등을 막지만 `/`는 허용한다.

## 서초 AI 페스타 (`seocho`)

- `https://seochoai.kr/` 한 장. head의 JSON-LD `Event`(공용 `sources/jsonld.py`가 읽음)에서 명칭·시작/종료(서울 날짜+개최 시각)·장소명·주최·무료 여부를 읽는다. 값은 코드에 고정하지 않고 페이지 값을 쓴다. `eventStatus`가 EventCancelled일 때만 `sourceStatus: closed`·dateNote에 `행사 취소`(다른 값·하위 프로그램 상태는 무시).
- `offers.validFrom`은 행사 접수 시작이라는 근거가 없어 쓰지 않는다. 일부 프로그램의 사전예약 오픈예정·마감은 축제 전체 상태가 아니므로 `sourceStatus: unknown`, 마감 null, `dateNote`에 개최 시각과 "프로그램별 신청은 공식 사이트 확인"을 둔다.
- 참가비 `무료`는 `isAccessibleForFree`/`price 0` 근거가 있을 때만(서로 어긋나면 `확인 필요`). 자격 `시민 누구나`는 본문에 그 문구가 있을 때만 verified. 도로명 주소는 저장하지 않고 장소명만 쓴다.

## NVIDIA AI Day Seoul (`nvidia`)

- `https://www.nvidia.com/ko-kr/ai-days/`(약 0.5MB). `<title>`의 `AI Day Seoul 연도`, h1 `AI Day Seoul`, h1 뒤 hero 한 줄 `M월 D～D일, 연도 | 장소`(전각 물결·en space는 NFKC로 정규화)에서만 기간을 읽는다. title 연도와 hero 연도가 다르거나 날짜가 잘못되면 오류. 프로그램 탭의 `11월 10일` 같은 세션 시간은 기간으로 쓰지 않는다.
- 이름은 읽은 연도로 `NVIDIA AI Day Seoul {연도}`. 등록 마감은 null, 참가비는 프로그램별이라 `확인 필요(프로그램별로 다름)`. `sourceStatus: open`은 헤더의 `지금 등록하기` CTA가 https 링크로 있을 때만. 등록 링크(register.nvidia.com)는 허용 호스트가 아니라 저장하지 않고 공식 안내 페이지 URL을 쓴다. 한국어 검색을 위해 tags에 `엔비디아`·`AI 데이`·`서울`을 둔다.

## AI FESTA (`aifesta`)

- `https://www.aifesta.kr/`. 본문은 JS 앱(`#root`)이라 비어 있고 head의 JSON-LD `@graph` 안 `Event`를 읽는다(WebSite·Organization은 무시). 참가비·신청 마감·자격은 제공되지 않아 `확인 필요`. 종료한 행사도 90일 정책으로 저장되고 화면 기본(활성) 목록에서는 빠진다.

## AI Radar 변경(2026-10-12, 로컬)

- 허용 호스트 추가(정확한 이름만): `www.contestkorea.com`, `aiexpo.co.kr`(www는 301 이동이라 허용 안 함), `raw.githubusercontent.com`. 우선순위는 기존 7곳 뒤에 contestkorea > devevent > aiexpo.
- **위비티**: 종료 라벨 행은 상세를 읽지 않는다. 목록이 등록순이라 마감이 단조롭지 않으므로, 한 페이지가 전부 종료여도 멈추지 않고 빈 페이지·반복 페이지·상한(6페이지·상세 100건)에서만 멈춘다. 상세 요청 약 89→53건(실측).
- **Devpost**: 목록 meta 총 건수 기준으로 최대 5페이지, 상세 기본 20건(실측 총 23건=3페이지). 한도를 채우면 다음 페이지를 읽지 않고, 이후 페이지 오류는 소스 실패.
- **콘테스트코리아(`contestkorea`)**: 서버 렌더링 GET. 제목 검색 'AI' 최대 12페이지 + '인공지능' 최대 3페이지, 상세 최대 60건. 접수기간은 상세의 연도 포함 `YYYY.MM.DD ~ YYYY.MM.DD`만 쓰고 날짜만 제공(`deadlineAt` null). 목록 마감과 상세 마감이 다르거나 접수중인데 마감이 지났으면 그 항목을 실패로 센다. 심사기간은 개최일이 아니라 `startDate/endDate` null. 현재 페이지가 전부 마감이어도 뒷페이지가 없다고 판정하지 않는다.
- **Dev-Event(`devevent`)**: GitHub raw README 1회(약 120KB), 항목 100 상한. 접수 범위는 날짜만, 원문 시각은 `dateNote`. 일반 세미나는 제목에도 AI 단어가 있어야 하고 해커톤·대회는 AI 태그로 인정. 해외 지명 오프라인(온라인 병행 포함)은 한국 참가 확인 불가라 제외. 행사 landing 링크는 읽지 않고 저장만. `sourceUrl`은 읽은 README의 월 anchor, landing은 `url`. 디렉터리 표기라 날짜·참가비는 원문 확인 필요.
- **AI EXPO KOREA(`aiexpo`)**: `/전시회-개요/` 표에서 행사명·기간·장소·주최를 읽는다. HTTP/robots 조회 실패 시 독립 한국전시산업진흥회 SHOWALA 공개 행사 기록(`www.showala.com/ex/ex_detail.php?idx=4273`)으로 확인한다. 별도 robots/허용 호스트/redirect/2.5MB 제한 유지. 행사명·연도·공식 홈페이지·주최·기간·최종 응답 URL이 일치해야 하고 종료된 기록은 대체 갱신에 쓰지 않는다. 실제 확인 URL은 sourceUrl, 사용자 행사 링크는 기존 url이며 기존 ID는 유지한다. 마감·참가비·자격은 확인 필요. SHOWALA의 다른 회차 등록 경로는 변경 시 재검토해야 한다.
- **AI Summit Seoul(`aisummit`)**: 기존 안전 상한인 앞 2.5MB까지 읽고 멈춘다. GitHub runner의 앞 1MB에는 행사 본문이 없어 날짜를 찾지 못하고, 앞 2.5MB에서는 정상 파싱되는 현상을 재현했다(run 38222377812). 상한 내 연도 포함 기간을 못 찾으면 추측하지 않고 오류로 둔다. 전역 응답 크기·robots·redirect 제한은 그대로 유지한다.
- **교차 출처 중복**: 제목(공백·기호 정규화)+마감일(없으면 개최 시작일)이 같은 다른 출처 항목은 먼저 등록된 출처 하나만 남긴다. 앞 `[..]`는 그 항목의 주최명과 정확히 같을 때만 뗀다(`[Track1]`·`[Seoul]`은 보존 — 누락보다 중복 몇 건이 안전). 날짜가 없으면 합치지 않는다. 같은 날짜의 Track1/Track2는 보존.
- `Fetcher.get(prefix_bytes)`는 `1 <= prefix_bytes <= max_bytes`가 아니면 요청 전에 `ValueError`.
- `--max-items`는 목록형 소스(위비티·Devpost·콘테스트코리아·Dev-Event)의 상세/항목 수 상한.
- **요청 수와 시간**: 소스별 하드 상한 합계는 약 250요청(robots 제외)이라고 보지만 이는 단정할 수 있는 절대 상한이 아니다. 실측 1회(2026-10-12)는 robots·redirect를 포함해 257요청, 약 4분 30초(요청 간격 1초, 요청당 평균 약 1.05초)였다. GitHub 러너는 지연이 클 수 있어 요청당 3초로 가정하면 250요청 ≈ 12.5분이라, workflow는 수집 step `timeout-minutes: 18`, job `25`(기존 15)로 두어 step이 초과해도 tests·commit·실패 표시가 남게 했다.
- 정확한 요청 URL과 소스별 목록/상세 요청 최대치는 audit 문서 §3·§4.

## AX 챌린지 출처 추가(2026-10-28)

- AI 판정 단어에 `AX`(AI 전환, 단어 경계)를 더했다. 기업 챌린지가 제목에 'AI' 없이 `LOTTE AX CHALLENGE`처럼 올라와 걸러졌기 때문이다. `TAX`·`MAXIM`·`AXE`는 해당 없음.
- 허용 호스트 추가(정확한 이름만): `lotteaxchallenge.com`, `linkareer.com`(www·api 하위 도메인 아님). 우선순위는 aiexpo 뒤에 lotteax > linkareer — 같은 챌린지면 공식 출처가 남는다(제목+마감일 중복 키).
- **LOTTE AX CHALLENGE(`lotteax`)**: `https://lotteaxchallenge.com/` 1회(약 0.6MB). 커리어링크 빌더(Next.js)라 일정이 이미지·스크립트로 그려지며, `__NEXT_DATA__` 디자인 데이터의 코드 섹션 원문 `STEPS`(단계별 날짜)와 `CONFIG.deadline`(시간대 포함 예선 마감)을 읽는다. 예선 단계 날짜 끝 = 마감일, 본선 > 마감이어야 하고 아니면 오류. 연도는 마감 일시에서 가져온다(하드코딩 없음). 머리글 '2030년 12월 31일 접수 마감'은 빌더 기본 문구라 쓰지 않는다. 마감 = 온라인 예선 접수 마감, 개최 기간 = 오프라인 본선. 참가비는 미표기라 `확인 필요`.
- **링커리어(`linkareer`)**: 접수중(OPEN) 공모전 목록 최신 등록순 `page=N`(20건/페이지) 최대 40페이지, 빈/반복 페이지에서 멈춤. 목록·상세 모두 `__NEXT_DATA__` Apollo 캐시이며 광고 Activity는 `activities(...)` 쿼리 노드가 아니라 제외. 제목 AI 판정(`AI`/`AX`/인공지능 등) 후보만 상세 최대 120건. 상세의 접수 시작·마감(epoch ms → KST, 마감 23:59:59)·대상·총 상금·주최를 쓴다. 목록 마감과 상세 마감이 다르면 그 항목 실패, 후보 전부 실패면 소스 오류, 이후 페이지 오류도 소스 실패. 홈페이지가 https면 그 링크, 없으면 링커리어 안내 페이지. 담당자 이름·연락처는 읽지 않는다. 2026-10-28 실측: AI 후보 80건(상한 80 당시 30페이지), 상세 실패 0.

## 저장·병합 규칙

- 전체 원격 실패 시 `data/opportunities.json`은 바이트 불변이고 `data/ingest-status.json`만 갱신된다. 부분 실패는 성공 소스만 교체하고 실패 소스 행·`verifiedAt`·`lastSuccessAt`을 보존한다.
- 성공 소스에서 사라진 활성 항목은 `stale=true`(verifiedAt 유지), 종료 후 90일이 지난 항목만 제외한다. 날짜가 없는 항목은 verifiedAt 기준.
- id = `소스id-sha1(canonical sourceUrl)[:12]`. 서로 다른 소스가 같은 canonical `url`을 가리키면 소스 우선순위(devpost > dacon > wevity > aisummit > seocho > nvidia > aifesta > contestkorea > devevent > aiexpo)로 한 건만 남긴다.
- 기존 JSON이 손상됐거나 계약을 어기면 종료 코드 2로 중단하고 어떤 파일도 쓰지 않는다. 종료 코드 1은 모든 소스 실패.
- `data/curated.json`(수동 입력, `schemaVersion: 2`, 전체 항목 계약)은 현재 비어 있다. 값이 있으면 검증 후 병합하며 자동 재확인은 하지 않는다(각 항목의 `verifiedAt`이 입력 시점). 기존 `data/events.json`은 건드리지 않는다.

## 파이프라인 계약(2차 리뷰 보완 포함)

- 모든 신선한 소스 결과와 `curated.json` 항목은 같은 계약(`rules.meets_contract`)을 통과해야 한다: AI 관련성, 지역(KR 또는 GLOBAL+online), 자격 확인(GLOBAL은 `eligibilityVerified`와 한국 참가 증거), 초대 전용 제외. 신선한 결과는 위반 항목만 건너뛰고 메시지에 "계약 위반으로 N건 제외"를 남기며, curated 위반은 `ExistingDataError`로 중단(원본 보존). curated 파일이 없거나 비어 있으면 정상이다.
- 저장된 stale 항목도 병합 때 같은 계약을 다시 검사해 위반분은 출력에서 뺀다(예: 나중에 추가된 internal 대회 규칙).
- "excluding standard exceptions"는 **괄호 안에 실제 국가명 목록**(예: Brazil, Crimea, Cuba, Iran, North Korea, Quebec, Russia)이 있을 때만 승인한다. `(see rules)`·TBD·빈 괄호는 거부한다.
- Fetcher는 redirect 대상의 robots.txt를 **요청 전에** 검사한다(중간 redirect 포함).
- DACON은 목록 **1페이지만** 본다. 위비티는 AI 검색 최대 6페이지(위 참고).
- Devpost 상세 한국 참가 문구와 위비티 응모대상은 원문을 그대로 보여주며, 원문이 바뀌면 안전하게 제외 쪽으로 동작한다.
- workflow Actions 버전은 2026-10-02에 직접 조회한 최신 릴리스 기준이다: [actions/checkout v7.0.1](https://github.com/actions/checkout/releases), [actions/setup-python v7.0.0](https://github.com/actions/setup-python/releases), [actions/setup-node v7.0.0](https://github.com/actions/setup-node/releases) (workflow에는 major `@v7`로 고정).

## 알려진 한계

- DACON은 1페이지(14건 수준)만 본다. 위비티는 6페이지·후보 90건 상한이라 그 뒤 항목은 누락될 수 있고, 한 번의 수집에 약 4분(요청 간격 1초)이 든다.
- 콘테스트코리아·위비티의 응모 대상은 원문 표기이며 개인/팀/기업 구분은 하지 않는다. Dev-Event는 커뮤니티 큐레이션이라 제목에 AI 단어가 없는 일반 세미나는 놓칠 수 있다.
- 공식 행사 3곳은 지정한 사이트만 매일 확인한다. 웹 전체의 다른 행사는 발견하지 못하며, 사이트 마크업이 바뀌면 오류로 표시되고 이전 데이터가 보존된다.
- 위비티는 종료·마감 항목(2026-10-12 수집 기준 37건)도 목록에 있어 보드의 마감·종료 필터에 쌓인다.
- AI Summit의 이전 1MB 읽기 제한 오류는 PR #4로 해결했다. AI EXPO의 환경별 HTTP 202 차단은 PR #5로 독립 전시포털 확인 경로를 추가했다. 최신 운영 run 38262223254에서는 10개 출처가 모두 정상 갱신됐다. 기본·대체 경로에서 확인할 수 없는 경우에는 계속 오류와 이전 데이터 보존 정책을 적용한다.
- Devpost 한국 참가 판정은 상세 페이지의 문구 휴리스틱이다. 문구가 바뀌면 안전하게 제외 쪽으로 동작한다.
- 온오프믹스는 일반 UA 자동 수집을 금지해 제외했다(robots `Disallow: /`).
