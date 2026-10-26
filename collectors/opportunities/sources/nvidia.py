"""NVIDIA AI Day Seoul 공식 안내 페이지. 상단 hero의 '월 일~일, 연도 | 장소' 한 줄에서 기간을 읽는다.
프로그램별 세션·워크숍 시간(예: 11월 10일 오후)은 행사 전체 기간이 아니므로 hero 밖 날짜는 쓰지 않는다.
페이지는 약 0.5MB라 h1 이후 일부 텍스트만 훑는다."""
import re
import unicodedata

from bs4 import BeautifulSoup

from .. import rules
from ..errors import StructureError
from .base import CollectResult

SOURCE_ID = "nvidia"
SOURCE_NAME = "NVIDIA AI Day Seoul"
SOURCE_URL = "https://www.nvidia.com/ko-kr/ai-days/"
MAIN_URL = "https://www.nvidia.com/ko-kr/ai-days/"
HERO_TEXT_NODES = 12  # h1 다음에서 hero 줄을 찾는 텍스트 노드 수
_TITLE_RE = re.compile(r"AI Day Seoul\s+(20\d\d)")
_RANGE = r"(?P<month>\d{1,2})월\s*(?P<first>\d{1,2})\s*[~\-–]\s*(?P<last>\d{1,2})일"
_VENUE = r"\s*\|\s*(?P<venue>[^|\s]+)"
_HERO_RES = (  # '11월 9~10일, 2026 | 코엑스'와 '2026년 11월 9~10일 | 코엑스'
    re.compile(_RANGE + r",?\s*(?P<year>20\d\d)" + _VENUE),
    re.compile(r"(?P<year>20\d\d)년\s*" + _RANGE + _VENUE),
)
_CTA_TEXT = "지금 등록하기"


def _norm(text):
    """전각 물결·en space·nbsp 같은 표기 차이를 맞춘다."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def parse_main(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    title_match = _TITLE_RE.search(_norm(title.get_text())) if title else None
    if not title_match:
        raise StructureError("NVIDIA AI Day 페이지 title에서 'AI Day Seoul 연도'를 읽지 못함")
    h1 = soup.find("h1")
    if h1 is None or _norm(h1.get_text()) != "AI Day Seoul":
        raise StructureError("NVIDIA AI Day 페이지 h1이 'AI Day Seoul'이 아님")
    hero = _norm(" ".join(h1.find_all_next(string=True, limit=HERO_TEXT_NODES)))
    m = next((m for m in (r.search(hero) for r in _HERO_RES) if m), None)
    if not m:
        raise StructureError("NVIDIA AI Day hero의 연도 포함 기간 표기를 읽지 못함")
    month, first, last, year, venue = int(m["month"]), m["first"], m["last"], m["year"], m["venue"]
    if year != title_match[1]:
        raise StructureError(f"NVIDIA AI Day title 연도({title_match[1]})와 hero 연도({year})가 다름")
    start = rules.parse_date(f"{year}-{month}-{first}")
    end = rules.parse_date(f"{year}-{month}-{last}")
    if not start or not end or start > end:
        raise StructureError("NVIDIA AI Day hero 기간 날짜가 올바르지 않음")
    description = soup.find("meta", attrs={"name": "description"})
    register_open = any(
        _norm(a.get_text()) == _CTA_TEXT and a.get("href", "").startswith("https://")
        for a in soup.select("a.brand-cta")
    )
    return {
        "year": year, "startDate": start, "endDate": end, "venue": venue, "registerOpen": register_open,
        "description": rules.shorten(_norm(description.get("content", "")), 160) if description else "",
    }


def collect(fetcher, now, max_items=None):
    data = parse_main(fetcher.get(MAIN_URL).text)
    title = f"NVIDIA AI Day Seoul {data['year']}"
    raw = {
        "kind": "event", "title": title, "organizer": "NVIDIA", "description": data["description"] or title,
        "tags": ["AI", "워크숍", "NVIDIA", "엔비디아", "AI 데이", "서울"], "mode": "offline", "region": f"서울 {data['venue']}", "country": "KR",
        "startDate": data["startDate"], "endDate": data["endDate"], "registrationStartDate": None,
        "deadlineDate": None, "deadlineAt": None, "eligibility": rules.UNKNOWN_TEXT, "eligibilityVerified": False,
        "fee": f"{rules.UNKNOWN_TEXT}(프로그램별로 다름)", "prize": None, "url": MAIN_URL, "sourceUrl": MAIN_URL,
        "sourceName": SOURCE_NAME,
        "dateNote": "공식 안내의 개최 일정 기준 행사 기간. 세션·워크숍 시간은 프로그램별로 다르고 등록 마감과 참가비는 공식 페이지에서 확인 필요",
        "sourceStatus": "open" if data["registerOpen"] else "unknown",
    }
    return CollectResult([raw], f"행사 {data['startDate']}~{data['endDate']} {data['venue']}, 등록 버튼 {'있음' if data['registerOpen'] else '없음'}")
