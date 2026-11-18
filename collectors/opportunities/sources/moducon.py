"""모두콘(MODUCON) 공식 사이트. 모두의연구소 행사 목록(biz.modulabs.co.kr)과 별도 도메인이라 따로 읽는다.
행사 정보는 head의 JSON-LD Event에서 읽고, 참가 신청 마감·참가비는 근거가 없어 '확인 필요'로 둔다."""
from .base import CollectResult
from .jsonld import raw_from_event, read_event

SOURCE_ID = "moducon"
SOURCE_NAME = "모두콘"
SOURCE_URL = "https://moducon.modulabs.co.kr/"
MAIN_URL = "https://moducon.modulabs.co.kr/"


def collect(fetcher, now, max_items=None):
    data = read_event(fetcher.get(MAIN_URL).text, SOURCE_NAME)
    raw = raw_from_event(
        data, SOURCE_NAME, MAIN_URL, ["AI", "컨퍼런스", "모두의연구소"],
        "참가 신청 마감·참가비는 공식 사이트 확인 필요",
        kind="event", organizer=data["organizer"] or "모두의연구소",
    )
    return CollectResult([raw], f"행사 {data['startDate']}~{data['endDate']} {data['venue']}")
