"""루마(Luma) 공식 달력 구독(iCal) 피드 수집.

루마 약관은 공식 지원 인터페이스 밖의 접근을 금지하므로 웹 페이지·내부 API가 아니라
루마가 구독용으로 공개하는 iCal 주소(api.lu.ma/ics/get)만 읽는다.
서울 탐색 피드는 인기 행사 일부만 주므로 AI 주최자 캘린더를 함께 구독한다.
한국 위치가 확인된 행사만 쓰고(GEO 좌표 또는 주소 문구), 설명 본문은 AI 판정에만 쓰고 저장하지 않는다.
주최자 추가는 CALENDARS에 한 줄.
"""
import re
from datetime import timedelta

from .. import rules
from ..errors import FetchError, StructureError
from ..urlsafe import is_safe_https_url
from .base import CollectResult, domestic_region, fail_if_every_fetch_failed
from .ical import is_date_value, parse_events, parse_moment

SOURCE_ID = "luma"
SOURCE_NAME = "루마(Luma)"
SOURCE_URL = "https://luma.com/seoul"
ITEM_LIMIT = 80
ICS = "https://api.lu.ma/ics/get?entity={entity}&id={id}"
SEOUL_FEED = ("discover", "discplace-eQieweHXBFCWbCj", "What's Happening in Seoul")
# 2026-11-18 루마 행사 페이지에서 확인한 국내 AI 행사 주최 캘린더(개인 캘린더 제외).
# 세 번째 값 True = AI 전용 캘린더라 제목·설명에 'AI'가 없어도 AI 행사로 본다(예: Upstage Open Stage).
CALENDARS = (
    ("cal-qfWAAeoGm9Ftyn1", "Upstage AI Events", True),
    ("cal-63UOFcweB97l2gc", "Codex Community Events", True),
    ("cal-XmhPL0FrRSClpvX", "c0mpiled", True),
    ("cal-pL7vbzvCovkJ2gP", "Beyond the Vibes Community", True),
    ("cal-Md9x0T9gv5euc9v", "Notion Korea", False),
    ("cal-ylx8HtmmzipNDX6", "Hashed Events", False),
    ("cal-K68VPyn9J6fifMT", "Team.Human", False),
    ("cal-AnCgGC7F1FV6z5Z", "Dev Korea", False),
    ("cal-w5PsR14bCTbwI7f", "Layergg", False),
)
_KOREA_RE = re.compile(r"south korea|republic of korea|대한민국|\bkorea\b|seoul|서울|경기|인천|부산|대전|대구|광주|성남|판교", re.I)
_OFFICIAL_LINK_RE = re.compile(r"^Get up-to-date information at: (https://(?:luma\.com|lu\.ma)/[A-Za-z0-9/_-]+)")
_MAX_DAYS = 7  # 일주일을 넘는 일정은 행사가 아니라 상시 모집·과정으로 본다


def feeds():
    """[(피드 URL, 주최 캘린더 이름 또는 None, AI 전용 여부)]. 서울 피드는 주최자를 알 수 없어 None."""
    return [(ICS.format(entity=SEOUL_FEED[0], id=SEOUL_FEED[1]), None, False)] + [(ICS.format(entity="calendar", id=c), name, ai) for c, name, ai in CALENDARS]


def _value(event, name):
    return (event.get(name) or ("", {}))[0].strip()


def _place_text(event):
    """주소로 쓸 글자만: LOCATION(링크 제외) + 설명의 'Address:' 문단(빈 줄 전까지). 본문 문구는 섞지 않는다."""
    location = _value(event, "LOCATION")
    body = _value(event, "DESCRIPTION")
    address = body.split("Address:", 1)[1].strip().split("\n\n", 1)[0] if "Address:" in body else ""
    return f"{'' if location.startswith('https://') else location} {address}"


def _in_korea(event):
    geo = _value(event, "GEO")
    if geo:
        try:
            lat, lon = (float(x) for x in geo.split(";"))
        except ValueError:
            lat = lon = None
        if lat is not None:
            north_of_dmz_west = lat > 37.9 and lon < 127.1  # 개성 등 군사분계선 북쪽 서부
            return 33.0 <= lat <= 38.7 and 124.5 <= lon <= 131.0 and not north_of_dmz_west
    return bool(_KOREA_RE.search(_place_text(event)))


def _event_url(event):
    match = _OFFICIAL_LINK_RE.search(_value(event, "DESCRIPTION"))  # 루마가 첫 줄에 넣는 공식 안내 링크만(본문 속 다른 행사 링크 제외)
    if match and is_safe_https_url(match.group(1)):
        return match.group(1)
    uid = _value(event, "UID").split("@", 1)[0]
    if re.fullmatch(r"evt-[A-Za-z0-9]+", uid):
        return f"https://luma.com/event/{uid}"
    return None


def _city(event):
    text = _place_text(event)
    for pattern, name in ((r"seoul|서울", "서울"), (r"seongnam|성남|판교|pangyo", "경기 성남"), (r"busan|부산", "부산"), (r"incheon|인천", "인천")):
        if re.search(pattern, text, re.I):
            return name
    return None


def build_raw(event, now, calendar_name=None, ai_calendar=False):
    """VEVENT → 원시 항목. 대상이 아니면 None, 구조가 깨졌으면 StructureError."""
    title = rules.mask_contacts(rules.clean_text(_value(event, "SUMMARY")))
    if not title:
        raise StructureError("루마 일정 제목 없음")
    start = parse_moment(*event.get("DTSTART", ("", {})))
    end_value, end_params = event.get("DTEND", ("", {}))
    end = parse_moment(end_value, end_params) if end_value else start  # DTEND가 있는데 못 읽으면 추측하지 않는다
    if start is None or end is None or end < start:
        raise StructureError("루마 일정 시각 확인 불가")
    all_day = is_date_value(event.get("DTSTART", ("", {}))[1])
    if all_day and end_value and end > start:
        end -= timedelta(days=1)  # 종일 일정의 DTEND는 다음 날(배타적)이다
    if end < now or end - start > timedelta(days=_MAX_DAYS):
        return None
    body = rules.clean_text(_value(event, "DESCRIPTION"))
    if rules.is_excluded_title(title) or rules.is_invite_only_title(title):
        return None  # 정규화에서 빠질 일정이 같은 UID를 먼저 차지하지 않게 여기서 거른다
    if not _in_korea(event) or not (ai_calendar or rules.is_ai_related(title, description=body)):
        return None
    url = _event_url(event)
    if url is None:
        raise StructureError("루마 일정 링크 확인 불가")
    city = _city(event)
    return {
        "kind": rules.classify_kind(title, "event") or "event", "title": title,
        "organizer": calendar_name,  # iCal ORGANIZER는 개인 호스트 이름이라 저장하지 않는다
        "description": title, "tags": ["AI", "루마"], "mode": "offline",
        "region": f"국내 오프라인 · {city}" if city else domestic_region("offline"), "country": "KR",
        "startDate": start.date().isoformat(), "endDate": end.date().isoformat(),
        "registrationStartDate": None, "deadlineDate": None, "deadlineAt": None,
        "eligibility": rules.UNKNOWN_TEXT, "eligibilityVerified": False, "fee": rules.UNKNOWN_TEXT, "prize": None,
        "url": url, "sourceUrl": url, "sourceName": SOURCE_NAME,
        "sourceStatus": "closed" if _value(event, "STATUS").upper() == "CANCELLED" else "unknown",
        "dateNote": f"개최 {start:%Y-%m-%d}{'' if all_day else f' {start:%H:%M}'} ~ {end:%Y-%m-%d}{'' if all_day else f' {end:%H:%M}'} (한국 시각, 루마 일정 기준). 신청 마감·참가 조건은 루마 페이지 확인",
    }


def collect(fetcher, now, max_items=None):
    limit = ITEM_LIMIT if max_items is None else max(0, min(max_items, ITEM_LIMIT))
    if not limit:
        return CollectResult([], "피드 0개 확인")
    now = now.astimezone(rules.SEOUL)
    urls = feeds()
    items, seen, failures, broken = [], set(), [], 0
    for url, calendar_name, ai_calendar in urls:
        try:
            events = parse_events(fetcher.get(url).text)
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        for event in events:
            uid = _value(event, "UID")
            if not uid or uid in seen:
                continue
            try:
                raw = build_raw(event, now, calendar_name, ai_calendar)
            except StructureError:
                broken += 1
                continue
            if raw:  # 채택한 일정만 기록: 서울 피드에서 빠진 일정도 뒤의 AI 전용 캘린더에서 받을 수 있게
                seen.add(uid)
                items.append(raw)
    fail_if_every_fetch_failed(len(urls), failures, SOURCE_NAME)
    items.sort(key=lambda r: (r["startDate"], r["title"]))
    used = items[:limit]
    return CollectResult(used, f"피드 {len(urls)}개 중 {len(urls) - len(failures)}개 확인, 국내 AI 일정 {len(items)}건 중 {len(used)}건 사용, 형식 오류 {broken}건 (상한 {ITEM_LIMIT}건)")
