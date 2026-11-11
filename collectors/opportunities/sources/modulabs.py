"""모두의연구소 공식 공개 행사 SSR 수집.

홈페이지 #main-seminar가 biz.modulabs.co.kr/event 상세로 연결된다.
목록 1페이지 + 상세 최대 20회. 페이지네이션·API·인증 조회는 하지 않는다.
HTTP/robots/1초 간격은 전달받은 공통 Fetcher가 적용한다.
모두모임 상세는 공개 HTML에 확정 일정이 없어 현재 수집하지 않는다.
"""
import json
import re
from datetime import timedelta

from bs4 import BeautifulSoup

from .. import rules
from ..errors import FetchError, StructureError
from .base import CollectResult, domestic_region, effective_limit, fail_if_every_fetch_failed

SOURCE_ID = "modulabs"
SOURCE_NAME = "모두의연구소"
SOURCE_URL = "https://biz.modulabs.co.kr/event"
PAGE_LIMIT = 1
ITEM_LIMIT = 20
_EXCLUDE = re.compile(r"부트캠프|boot\s?camp|강좌|채용|수강생|교육생|\d+\s*(?:주|개월)\s*(?:교육|과정)", re.I)
_MODES = {"온라인": "online", "오프라인": "offline", "온오프라인": "hybrid", "온·오프라인": "hybrid"}
_STATUSES = {"모집중": "open", "모집완료": "closed", "모집마감": "closed"}


def detail_url(seq):
    return f"https://biz.modulabs.co.kr/event/{seq}"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _query_data(text, query_name, seq=None):
    """실행 없이 Flight 문자열을 합치고 JSON 레코드의 queryKey만 선택한다.

    하나의 JSON 레코드가 여러 script로 나뉘므로 먼저 결합한다.
    T 레코드의 HTML·연락처·신청자 필드는 출력하거나 저장하지 않는다.
    """
    chunks = []
    for script in BeautifulSoup(text, "html.parser").find_all("script"):
        source = (script.string or "").strip()
        prefix = "self.__next_f.push("
        if not source.startswith(prefix):
            continue
        try:
            frame = json.loads(source[len(prefix):].rstrip(";").removesuffix(")"))
        except ValueError:
            continue
        if isinstance(frame, list) and len(frame) == 2 and frame[0] == 1 and isinstance(frame[1], str):
            chunks.append(frame[1])
    flight, matches = "".join(chunks), []
    for marker in re.finditer(r"(?:^|\n)[0-9a-f]+:", flight):
        try:
            record, _ = json.JSONDecoder().raw_decode(flight, marker.end())
        except ValueError:
            continue  # 모듈·텍스트 참조 레코드는 JSON이 아니다.
        for node in _walk(record):
            key = node.get("queryKey")
            if not isinstance(key, list) or len(key) != 2 or key[0] != query_name or not isinstance(key[1], dict):
                continue
            params = key[1]
            if seq is not None and str(params.get("seq")) != str(seq):
                continue
            if seq is None and (str(params.get("page")) != "1" or params.get("search") != "" or params.get("status") != ""):
                continue
            state = node.get("state")
            if isinstance(state, dict) and isinstance(state.get("data"), dict):
                matches.append(state["data"])
    if len(matches) != 1:
        raise StructureError("모두의연구소 공개 행사 데이터가 없거나 모호함")
    return matches[0]


def _identity(row):
    if not isinstance(row, dict):
        raise StructureError("모두의연구소 행사 항목 형식 오류")
    seq, title = row.get("seq"), row.get("title")
    if type(seq) is not int or seq <= 0 or not isinstance(title, str) or not title.strip() or title.startswith("$"):
        raise StructureError("모두의연구소 행사 번호 또는 제목 확인 불가")
    return seq


def parse_listing(text):
    data = _query_data(text, "events")
    rows = data.get("data")
    if not isinstance(rows, list):
        raise StructureError("모두의연구소 행사 목록 구조 확인 불가")
    for row in rows:
        _identity(row)
    return rows


def _candidate(row):
    title = row.get("title", "")
    summary = row.get("summary") if isinstance(row.get("summary"), str) else ""
    keyword = row.get("keyword") if isinstance(row.get("keyword"), str) else ""
    return (row.get("showYn") == 1 and row.get("useYn") == 1 and row.get("companyYn") == 0
            and not _EXCLUDE.search(title)
            and rules.is_ai_related(title, description=f"{keyword} {summary}"))


def parse_detail(text, seq):
    row = _query_data(text, "event", seq)
    if _identity(row) != seq:
        raise StructureError("모두의연구소 상세 행사 번호 불일치")
    start = rules.parse_iso_datetime(row.get("startDate"))
    end = rules.parse_iso_datetime(row.get("endDate"))
    if start is None or end is None or start > end:
        raise StructureError("모두의연구소 공식 개최 일정 확인 불가")
    return row, start.astimezone(rules.SEOUL), end.astimezone(rules.SEOUL)


def _build_raw(row, start, end):
    url = detail_url(row["seq"])
    title = rules.mask_contacts(rules.clean_text(row["title"]))
    mode = _MODES.get(row.get("type"), "unknown")
    return {
        "kind": "event", "title": title, "organizer": SOURCE_NAME,
        "description": title, "tags": ["AI"], "mode": mode,
        "region": domestic_region(mode), "country": "KR",
        "startDate": start.date().isoformat(), "endDate": end.date().isoformat(),
        "registrationStartDate": None, "deadlineDate": None, "deadlineAt": None,
        "eligibility": rules.UNKNOWN_TEXT, "eligibilityVerified": False,
        "fee": rules.UNKNOWN_TEXT, "prize": None, "url": url, "sourceUrl": url,
        "sourceName": SOURCE_NAME, "sourceStatus": _STATUSES.get(row.get("status"), "unknown"),
        "dateNote": f"공식 개최 {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M} (한국 시각). 접수 마감·참가 조건 확인 필요",
    }


def collect(fetcher, now, max_items=None):
    limit = effective_limit(max_items)
    if not limit:
        return CollectResult([], "목록 0페이지·상세 0건 확인")
    rows, seen = [], set()
    for row in parse_listing(fetcher.get(SOURCE_URL).text):
        seq = row["seq"]
        if seq not in seen and _candidate(row):
            rows.append(row)
            seen.add(seq)
        if len(rows) >= limit:
            break
    items, failures, excluded = [], [], 0
    for candidate in rows:
        try:
            row, start, end = parse_detail(fetcher.get(detail_url(candidate["seq"])).text, candidate["seq"])
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        if not _candidate(row) or end - start > timedelta(days=7):
            excluded += 1
            continue
        items.append(_build_raw(row, start, end))
    fail_if_every_fetch_failed(len(rows), failures, SOURCE_NAME)
    return CollectResult(items, f"목록 1페이지·상세 {len(rows)}건 확인, {len(items)}건 사용, 제외 {excluded}건, 실패 {len(failures)}건 (목록 최대 {PAGE_LIMIT}페이지·상세 최대 {ITEM_LIMIT}건)")
