"""LOTTE AX CHALLENGE 공식 사이트(커리어링크 빌더, Next.js). 일정은 화면에선 이미지·스크립트로 그려지고,
__NEXT_DATA__ 디자인 데이터 안 코드 섹션의 STEPS(단계별 날짜)와 CONFIG.deadline(예선 마감 일시)에 원문이 있다.
머리글의 '2030년 12월 31일 접수 마감'은 빌더 기본 문구라 쓰지 않는다."""
import json
import re

from bs4 import BeautifulSoup

from .. import rules
from ..errors import StructureError
from .base import CollectResult

SOURCE_ID = "lotteax"
SOURCE_NAME = "LOTTE AX CHALLENGE"
SOURCE_URL = "https://lotteaxchallenge.com/"
MAIN_URL = "https://lotteaxchallenge.com/"
_TITLE_RE = re.compile(r"LOTTE AX CHALLENGE (20\d\d)")
_DEADLINE_RE = re.compile(r'deadline:\s*"([^"]+)"')
_STEP_RE = re.compile(r'\{\s*date:\s*"([^"]*)",\s*title:\s*"([^"]*)",\s*desc:\s*"([^"]*)"')
_RANGE_RE = re.compile(r"(\d{1,2})월\s*(\d{1,2})일[^~]*~\s*(\d{1,2})월\s*(\d{1,2})일")
_TARGET_RE = re.compile(r'\["대상",\s*"([^"]+)"\]')
_PRIZE_RE = re.compile(r"총 상금 [\d,]+[천만억]*원")


def _strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)
    elif isinstance(node, str):
        yield node


def _range(text, year):
    m = _RANGE_RE.search(text)
    if not m:
        raise StructureError(f"LOTTE AX 일정 '{text}'에서 기간을 읽지 못함")
    start, end = rules.parse_date(f"{year}-{m[1]}-{m[2]}"), rules.parse_date(f"{year}-{m[3]}-{m[4]}")
    if not start or not end or start > end:
        raise StructureError(f"LOTTE AX 일정 '{text}' 날짜가 올바르지 않음")
    return start, end


def parse_main(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    year = _TITLE_RE.search(title.get_text()) if title else None
    script = soup.find("script", id="__NEXT_DATA__")
    if not year or script is None:
        raise StructureError("LOTTE AX 페이지 title 연도나 __NEXT_DATA__가 없음")
    try:
        texts = list(_strings(json.loads(script.string or "")))
    except ValueError as exc:
        raise StructureError(f"LOTTE AX __NEXT_DATA__ 파싱 실패: {exc}") from exc
    code = "\n".join(t for t in texts if "STEPS" in t or "deadline:" in t)
    deadline = _DEADLINE_RE.search(code)
    deadline_at = deadline[1] if deadline and rules.parse_iso_datetime(deadline[1]) else None
    if deadline_at is None:
        raise StructureError("LOTTE AX 예선 마감 일시(시간대 포함)를 읽지 못함")
    steps = _STEP_RE.findall(code)  # (날짜, 단계명, 설명)
    prelim = next((s for s in steps if "예선" in s[1]), None)
    final = next((s for s in steps if "본선" in s[1]), None)
    if prelim is None or final is None:
        raise StructureError("LOTTE AX 일정에서 예선·본선 단계를 찾지 못함")
    deadline_day = rules.seoul_date_from_iso(deadline_at)
    reg_start, reg_end = _range(prelim[0], deadline_day[:4])
    if reg_end != deadline_day:
        raise StructureError(f"LOTTE AX 예선 일정 끝({reg_end})과 마감 일시({deadline_day})가 다름")
    start, end = _range(final[0], deadline_day[:4])
    if start <= deadline_day:
        raise StructureError("LOTTE AX 본선이 예선 마감보다 앞섬")
    target, prize, venue = _TARGET_RE.search(code), _PRIZE_RE.search("\n".join(texts)), re.search(r"\(([^()]+)\)", final[2])
    online, offline = "온라인" in prelim[1], "오프라인" in final[1]
    return {
        "title": f"LOTTE AX CHALLENGE {year[1]}", "registrationStartDate": reg_start, "deadlineAt": deadline_at,
        "startDate": start, "endDate": end, "eligibility": rules.clean_text(target[1].replace("\\n", " ")) if target else None,
        "prize": prize[0] if prize else None, "venue": venue[1] if venue else None,
        "mode": "hybrid" if online and offline else "offline" if offline else "online" if online else "unknown",
    }


def collect(fetcher, now, max_items=None):
    data = parse_main(fetcher.get(MAIN_URL).text)
    raw = {
        "kind": "contest", "title": data["title"], "organizer": "롯데",
        "description": "롯데 계열사 현업 과제를 AI 에이전트로 해결하는 실전형 챌린지. 온라인 예선 후 오프라인 본선, 수상자 채용 전환형 인턴십 연계",
        "tags": ["AI", "AX", "AI 에이전트", "챌린지", "롯데", "채용 연계"], "mode": data["mode"],
        "region": f"온라인 예선 · 오프라인 본선({data['venue'] or '장소 확인 필요'})", "country": "KR",
        "startDate": data["startDate"], "endDate": data["endDate"], "registrationStartDate": data["registrationStartDate"],
        "deadlineDate": None, "deadlineAt": data["deadlineAt"],
        "eligibility": data["eligibility"] or rules.UNKNOWN_TEXT, "eligibilityVerified": bool(data["eligibility"]),
        "fee": rules.UNKNOWN_TEXT, "prize": data["prize"], "url": MAIN_URL, "sourceUrl": MAIN_URL, "sourceName": SOURCE_NAME,
        "dateNote": "마감은 온라인 예선 접수 마감. 행사 기간은 오프라인 본선(1박 2일, 예선 통과자)",
        "sourceStatus": "unknown",
    }
    return CollectResult([raw], f"예선 {data['registrationStartDate']}~{data['deadlineAt']}, 본선 {data['startDate']}~{data['endDate']}")
