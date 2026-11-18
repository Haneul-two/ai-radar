"""해외 대형 AI 학회 개최 일정. ccfddl/ccf-deadlines(MIT, 매일 갱신)의 학회별 YAML을 GitHub raw로 읽는다.

사용자가 해외는 '대형 컨퍼런스만' 받기로 했으므로 아래 CONFS 목록(주요 AI 학회)만 읽는다.
해외 현장 행사를 받는 유일한 출처이며 그 예외는 rules.GLOBAL_OFFLINE_SOURCES에 둔다.
YAML 라이브러리 없이 필요한 스칼라 줄(title·description·year·link·date·place)만 읽는다.
논문 제출 마감은 참가 신청 마감이 아니므로 deadline에 쓰지 않는다.
"""
import re
from datetime import date, timedelta

from .. import rules
from ..errors import FetchError, StructureError
from ..urlsafe import is_safe_https_url
from .base import CollectResult, fail_if_every_fetch_failed

SOURCE_ID = "majorconf"
SOURCE_NAME = "주요 AI 학회(ccfddl)"
SOURCE_URL = "https://ccfddl.com/"
RAW = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main/conference/{path}.yml"
PAGE = "https://github.com/ccfddl/ccf-deadlines/blob/main/conference/{path}.yml"
CONFS = ("AI/nips", "AI/icml", "AI/iclr", "AI/cvpr", "AI/iccv", "AI/eccv", "AI/aaai", "AI/ijcai", "AI/acl", "AI/emnlp", "AI/naacl")
HORIZON_DAYS = 400  # 1년여 뒤까지만(다음 해 회차 링크가 미리 올라와도 너무 먼 것은 뺀다)

_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_RANGE_RE = re.compile(_MONTH + r"\s+(\d{1,2})(?:\s*[-–—~]\s*(?:" + _MONTH + r"\s+)?(\d{1,2}))?", re.I)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_KOREA_RE = re.compile(r"korea|seoul|busan|대한민국|서울|부산", re.I)
_VIRTUAL_RE = re.compile(r"virtual|online", re.I)


def _scalar(line):
    value = line.split(":", 1)[1].strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"" else value


def parse_conf_file(text):
    """YAML → (title, description, [{year, link, date, place}])."""
    title = description = None
    blocks, current = [], None
    for line in text.splitlines():
        if line.startswith("- title:"):
            title = _scalar(line)
        elif line.startswith("  description:"):
            description = _scalar(line)
        elif re.match(r"^\s+- year:", line):
            current = {"year": _scalar(line)}
            blocks.append(current)
        elif current is not None:
            match = re.match(r"^\s+(link|date|place):", line)
            if match:
                current[match.group(1)] = _scalar(line)
    if not title or not blocks:
        raise StructureError("학회 일정 파일 구조 확인 불가(title·confs 없음)")
    return title, description, blocks


def parse_period(text, fallback_year):
    """'December 8-10 (Sydney), December 9-11 (Atlanta), 2026' → (가장 이른 날, 가장 늦은 날). 못 읽으면 None."""
    years = set(_YEAR_RE.findall(text or ""))
    if len(years) > 1 or (years and int(years.pop()) != fallback_year):
        return None  # 연도가 여럿이거나 회차 연도와 다르면 어느 해인지 추측하지 않는다
    year = fallback_year
    days = []
    for m1, d1, m2, d2 in _RANGE_RE.findall(text or ""):
        first_month = _MONTHS[m1[:3].lower()]
        last_month = _MONTHS[m2[:3].lower()] if m2 else first_month
        try:
            start, end = date(year, first_month, int(d1)), date(year, last_month, int(d2 or d1))
        except ValueError:
            return None
        if end < start:
            return None  # 연도를 넘는 표기는 추측하지 않는다
        days += [start, end]
    return (min(days), max(days)) if days else None


def build_raw(path, title, description, block, today):
    try:
        year = int(block["year"])
    except (KeyError, ValueError):
        return None
    period = parse_period(block.get("date"), year)
    link, place = block.get("link"), (block.get("place") or "").strip()
    if period is None or not is_safe_https_url(link) or period[1] < today or period[0] > today + timedelta(days=HORIZON_DAYS):
        return None
    korea = bool(_KOREA_RE.search(place))
    mode = "online" if _VIRTUAL_RE.search(place) else ("offline" if place else "unknown")
    where = "국내 오프라인" if korea else ("온라인" if mode == "online" else "해외 현장")
    return {
        "kind": "event", "title": f"{title} {year}", "organizer": title,
        "description": description or title, "tags": ["AI", "학회", "해외" if not korea else "국내"],
        "mode": mode, "region": f"{where} · {place}" if place else where, "country": "KR" if korea else "GLOBAL",
        "startDate": period[0].isoformat(), "endDate": period[1].isoformat(),
        "registrationStartDate": None, "deadlineDate": None, "deadlineAt": None,
        "eligibility": rules.UNKNOWN_TEXT, "eligibilityVerified": False, "fee": rules.UNKNOWN_TEXT, "prize": None,
        # 공식 링크를 여러 회차가 같이 쓸 수 있어 id는 파일+회차 연도로 만든다(sourceUrl 기준).
        "url": link, "sourceUrl": f"{PAGE.format(path=path)}?edition={year}", "sourceName": SOURCE_NAME, "sourceStatus": "unknown",
        "dateNote": f"개최 {block.get('date')} (현지 날짜, ccfddl 학회 일정 기준). 참가 등록 마감·참가비는 공식 사이트 확인",
    }


def collect(fetcher, now, max_items=None):
    today = now.astimezone(rules.SEOUL).date()
    items, failures, skipped = [], [], 0
    for path in CONFS:
        try:
            title, description, blocks = parse_conf_file(fetcher.get(RAW.format(path=path)).text)
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        for block in blocks:
            raw = build_raw(path, title, description, block, today)
            if raw:
                items.append(raw)
            elif block.get("date") and block.get("year", "").isdigit() and parse_period(block["date"], int(block["year"])) is None:
                skipped += 1
    fail_if_every_fetch_failed(len(CONFS), failures, SOURCE_NAME)
    if max_items is not None:
        items = items[:max(0, max_items)]
    return CollectResult(items, f"학회 {len(CONFS)}곳 중 {len(CONFS) - len(failures)}곳 확인, 예정 회차 {len(items)}건, 날짜 표기 해석 불가 {skipped}건")
