"""공개 SSR의 최소 필드만 재구성. 연락처·주소·신청자 데이터는 보관하지 않는다."""
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from collectors.opportunities import rules
from collectors.opportunities.errors import FetchError, SourceError, StructureError
from collectors.opportunities.sources import modulabs
from test_opportunities import FakeFetcher

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)
# 2026-11-11 공개 /event 및 /event/571에서 확인한 최소 필드.
EVENT = {
    "seq": 571, "title": "Notion 당신의 생각을 현실로만드는 공간 (입문편)",
    "summary": "메모부터 할 일, 일정까지 한 곳에서 관리해요!",
    "keyword": "AI, 세미나, Notion, 노션", "type": "오프라인", "status": "모집중",
    "startDate": "2026-11-26T10:00:00.000Z", "endDate": "2026-11-26T12:00:00.000Z",
    "companyYn": 0, "showYn": 1, "useYn": 1,
}


def event(seq=571, **over):
    return {**EVENT, "seq": seq, **over}


def page(data, detail=False, split=False, extra_queries=()):
    key = ["event", {"seq": str(data["seq"])}] if detail else ["events", {"page": "1", "search": "", "status": ""}]
    query = {"queryKey": key, "state": {"data": data if detail else {"data": data, "count": len(data)}}}
    record = ["$", "$L13", None, {"state": {"mutations": [], "queries": [query, *extra_queries]}}]
    flight = "6:" + json.dumps(record, ensure_ascii=False) + "\n"
    # 실제 페이지처럼 JSON 중간에서 script가 분할된다.
    chunks = [flight[:len(flight) // 2], flight[len(flight) // 2:]] if split else [flight]
    return "<html>" + "".join("<script>self.__next_f.push(" + json.dumps([1, c], ensure_ascii=False) + ")</script>" for c in chunks) + "</html>"


def fetcher_for(rows, details=None):
    pages = {modulabs.SOURCE_URL: page(rows)}
    pages.update({modulabs.detail_url(r["seq"]): page(r, detail=True, split=True) for r in rows})
    if details:
        pages.update(details)
    return FakeFetcher(pages)


class ModulabsTest(unittest.TestCase):
    def test_real_minimal_detail_and_contract(self):
        result = modulabs.collect(fetcher_for([EVENT]), NOW)
        raw = result.items[0]
        self.assertEqual(raw["title"], EVENT["title"])
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-11-26", "2026-11-26"))
        self.assertEqual(raw["mode"], "offline")
        self.assertEqual(raw["sourceUrl"], "https://biz.modulabs.co.kr/event/571")
        self.assertEqual(raw["url"], raw["sourceUrl"])
        self.assertEqual(raw["sourceName"], "모두의연구소")
        self.assertIsNone(raw["deadlineAt"])
        self.assertIsNone(raw["deadlineDate"])
        self.assertIsNone(raw["registrationStartDate"])
        self.assertFalse(raw["eligibilityVerified"])
        self.assertEqual(raw["eligibility"], rules.UNKNOWN_TEXT)
        self.assertEqual(raw["fee"], rules.UNKNOWN_TEXT)
        self.assertEqual(raw["sourceStatus"], "open")
        self.assertIn("19:00", raw["dateNote"])
        normalized = rules.normalize_item(raw, modulabs.SOURCE_ID, NOW.isoformat())
        self.assertIsNotNone(normalized)
        rules.validate_item(normalized)
        self.assertTrue(rules.meets_contract(normalized))

    def test_detail_is_authoritative_and_kst_rollover(self):
        row = event(title="목록 AI 세미나")
        detail = event(title="확정 AI 세미나", startDate="2026-12-01T23:00:00Z", endDate="2026-12-02T01:00:00Z", status="모집완료")
        result = modulabs.collect(fetcher_for([row], {modulabs.detail_url(571): page(detail, detail=True)}), NOW)
        raw = result.items[0]
        self.assertEqual(raw["title"], "확정 AI 세미나")
        self.assertEqual(raw["startDate"], "2026-12-02")
        self.assertEqual(raw["sourceStatus"], "closed")

    def test_ai_filter_and_long_courses_jobs_excluded(self):
        rows = [event(1, title="사진전", keyword="사진", summary="사진 이야기"),
                event(2, title="AI 부트캠프 설명 세미나"), event(3, title="AI 강좌"),
                event(4, title="AI 채용 세미나"), event(5, title="AI 12주 과정"),
                event(6, title="AI 세미나", endDate="2026-12-26T12:00:00Z"),
                event(7, title="AI 세미나")]
        result = modulabs.collect(fetcher_for(rows), NOW)
        self.assertEqual([r["title"] for r in result.items], ["AI 세미나"])

    def test_detail_rechecks_relevance_and_visibility(self):
        for changed in (event(title="사진전", summary="사진", keyword="사진"), event(showYn=0), event(useYn=0), event(companyYn=1)):
            with self.subTest(changed=changed):
                result = modulabs.collect(fetcher_for([EVENT], {modulabs.detail_url(571): page(changed, detail=True)}), NOW)
                self.assertEqual(result.items, [])

    def test_missing_invalid_ambiguous_dates_fail_closed(self):
        for over in ({"startDate": None}, {"endDate": "미정"}, {"startDate": "2026-11-26"},
                     {"endDate": "2026-11-25T12:00:00Z"}, {"seq": 999}, {"title": None}):
            with self.subTest(over=over), self.assertRaises(SourceError):
                modulabs.collect(fetcher_for([EVENT], {modulabs.detail_url(571): page(event(**over), detail=True)}), NOW)

    def test_non_ai_detail_never_inherits_listing_ai_tag(self):
        d = event(title="사진 세미나", keyword="사진", summary="사진 이야기")
        result = modulabs.collect(fetcher_for([EVENT], {modulabs.detail_url(571): page(d, detail=True)}), NOW)
        self.assertEqual(result.items, [])

    def test_caps_zero_duplicates_and_no_pagination(self):
        rows = [event(n) for n in range(1, 31)]
        for cap, expected in ((None, 20), (999, 20), (3, 3), (0, 0), (-1, 0)):
            fetcher = fetcher_for(rows + rows)
            result = modulabs.collect(fetcher, NOW, cap)
            self.assertEqual(len(result.items), expected)
            self.assertEqual(len(fetcher.calls), expected + (1 if expected else 0))
            self.assertEqual(len(fetcher.calls), len(set(fetcher.calls)))

    def test_query_scope_ignores_unrelated_cache_and_external_links(self):
        unrelated = {"queryKey": ["advertisements"], "state": {"data": {"data": [event(999)]}}}
        html = page([EVENT], extra_queries=[unrelated]) + '<a href="https://evil.example/event/123">AI 세미나</a>'
        fetcher = fetcher_for([EVENT])
        fetcher.pages[modulabs.SOURCE_URL] = html
        self.assertEqual(len(modulabs.collect(fetcher, NOW).items), 1)
        self.assertEqual(fetcher.calls, [modulabs.SOURCE_URL, modulabs.detail_url(571)])

    def test_empty_confirmed_listing_ok_broken_structure_error(self):
        self.assertEqual(modulabs.collect(fetcher_for([]), NOW).items, [])
        for html in ("<html>점검중</html>", page(EVENT, detail=True), page([{"seq": "../../evil", "title": "AI"}])):
            with self.subTest(html=html), self.assertRaises(StructureError):
                modulabs.collect(FakeFetcher({modulabs.SOURCE_URL: html}), NOW)

    def test_fetch_failures_visible_and_all_fail_raise(self):
        fetcher = fetcher_for([EVENT, event(570)])
        fetcher.pages[modulabs.detail_url(571)] = FetchError("error", "503")
        result = modulabs.collect(fetcher, NOW)
        self.assertEqual(len(result.items), 1)
        self.assertIn("실패 1건", result.message)
        with self.assertRaises(SourceError):
            modulabs.collect(fetcher_for([EVENT], {modulabs.detail_url(571): FetchError("blocked", "robots")}), NOW)

    def test_unknown_status_and_mode_are_not_guessed(self):
        d = event(status="추후 안내", type="미정")
        raw = modulabs.collect(fetcher_for([d]), NOW).items[0]
        self.assertEqual(raw["mode"], "unknown")
        self.assertEqual(raw["sourceStatus"], "unknown")

    def test_unneeded_personal_fields_never_saved(self):
        d = copy.deepcopy(EVENT)
        d.update(location="PRIVATE_ADDRESS", locationSub="PRIVATE_ROOM", applicants=[{"userSeq": 123}],
                 desc="PRIVATE_BODY", question1="PRIVATE_QUESTION", speaker="PRIVATE_PERSON")
        result = modulabs.collect(fetcher_for([d]), NOW)
        self.assertNotIn("PRIVATE_", json.dumps(result.items))


if __name__ == "__main__":
    unittest.main()
