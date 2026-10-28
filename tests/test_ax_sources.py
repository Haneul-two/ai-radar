"""AX 챌린지 수집 테스트 — AI 판정의 'AX', 롯데 AX 챌린지 공식 사이트, 링커리어 공모전 목록. 네트워크 없이 fixture만 쓴다."""
import json
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from collectors.opportunities import rules, urlsafe  # noqa: E402
from collectors.opportunities.errors import FetchError, SourceError, StructureError  # noqa: E402
from collectors.opportunities.sources import default_sources, linkareer, lotteax  # noqa: E402
from test_opportunities import FakeFetcher, fixture  # noqa: E402

NOW = datetime(2026, 10, 28, 3, 0, 0, tzinfo=timezone.utc)
NOW_ISO = "2026-10-28T03:00:00Z"


class AxKeywordTest(unittest.TestCase):
    def test_ax_counts_as_ai(self):
        for title in ("LOTTE AX CHALLENGE 2026", "2026 AX 아이디어 경진대회", "산업 AX 해커톤", "AX/DX 공모전"):
            self.assertTrue(rules.is_ai_related(title), title)

    def test_ax_inside_words_does_not(self):
        for title in ("TAX 절세 공모전", "MAXIM 영상 공모전", "AXE 챌린지", "Relax 사진전"):
            self.assertFalse(rules.is_ai_related(title), title)


class RegistryTest(unittest.TestCase):
    def test_new_sources_after_existing_ten_official_before_aggregator(self):
        ids = [s.id for s in default_sources()]
        self.assertEqual(ids[:10], ["devpost", "dacon", "wevity", "aisummit", "seocho", "nvidia", "aifesta", "contestkorea", "devevent", "aiexpo"])
        self.assertEqual(ids[10:], ["lotteax", "linkareer"])

    def test_exact_hosts_only(self):
        for ok in ("https://lotteaxchallenge.com/", "https://linkareer.com/list/contest", "https://linkareer.com/activity/360080"):
            self.assertTrue(urlsafe.is_fetch_allowed(ok), ok)
        for bad in ("https://www.linkareer.com/", "https://api.linkareer.com/", "https://evil.lotteaxchallenge.com/", "http://linkareer.com/"):
            self.assertFalse(urlsafe.is_fetch_allowed(bad), bad)


class LotteAxTest(unittest.TestCase):
    def collect(self, html=None):
        return lotteax.collect(FakeFetcher({lotteax.MAIN_URL: html or fixture("lotteax_main.html")}), NOW, 20)

    def test_item_from_page_schedule(self):
        raw = self.collect().items[0]
        self.assertEqual((raw["kind"], raw["title"], raw["organizer"], raw["country"]), ("contest", "LOTTE AX CHALLENGE 2026", "롯데", "KR"))
        self.assertEqual(raw["registrationStartDate"], "2026-10-28")
        self.assertEqual(raw["deadlineAt"], "2026-11-04T23:59:59+09:00")
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-11-24", "2026-11-25"))
        self.assertEqual(raw["mode"], "hybrid")
        self.assertIn("오산", raw["region"])
        self.assertIn("누구나", raw["eligibility"])
        self.assertTrue(raw["eligibilityVerified"])
        self.assertEqual(raw["prize"], "총 상금 2천만원")
        self.assertIn(rules.UNKNOWN_TEXT, raw["fee"])
        item = rules.normalize_item(raw, "lotteax", NOW_ISO)
        self.assertIsNotNone(item)
        self.assertEqual(item["deadlineDate"], "2026-11-04")
        self.assertTrue(rules.meets_contract(item))

    def test_reads_page_values_not_constants(self):
        html = fixture("lotteax_main.html").replace("2026-11-04T23:59:59+09:00", "2026-11-06T18:00:00+09:00").replace("11월 4일(수)", "11월 6일(금)")
        self.assertEqual(self.collect(html).items[0]["deadlineAt"], "2026-11-06T18:00:00+09:00")

    def test_missing_or_broken_schedule_is_error(self):
        base = fixture("lotteax_main.html")
        broken = {
            "deadline": base.replace("deadline:", "dueAt:"),
            "no timezone": base.replace("2026-11-04T23:59:59+09:00", "2026-11-04T23:59:59"),
            "prelim step": base.replace("온라인 예선", "온라인 접수"),
            "final step": base.replace("오프라인 본선(1박2일)", "오프라인 행사"),
            "prelim end mismatch": base.replace("11월 4일(수)", "11월 5일(목)"),
            "final before deadline": base.replace("11월 24일(화)~11월 25일(수)", "11월 2일(월)~11월 3일(화)"),
            "title year": base.replace("<title>LOTTE AX CHALLENGE 2026</title>", "<title>LOTTE AX CHALLENGE</title>"),
            "title year mismatch": base.replace("<title>LOTTE AX CHALLENGE 2026</title>", "<title>LOTTE AX CHALLENGE 2027</title>"),
            "no next data": "<html><title>LOTTE AX CHALLENGE 2026</title></html>",
        }
        for name, html in broken.items():
            with self.assertRaises(StructureError, msg=name):
                self.collect(html)


def listing_page(acts):
    """acts: [(id, title, close_ms)] → 링커리어 목록 HTML."""
    state = {f"Activity:{i}": {"__typename": "Activity", "id": i, "title": t, "organizationName": "주최", "recruitCloseAt": c} for i, t, c in acts}
    state["ROOT_QUERY"] = {"activities({})": {"totalCount": len(acts), "nodes": [{"__ref": f"Activity:{i}"} for i, _, _ in acts]}}
    blob = json.dumps({"props": {"pageProps": {"__APOLLO_STATE__": state}}}, ensure_ascii=False)
    return f'<html><script id="__NEXT_DATA__" type="application/json">{blob}</script></html>'


def detail_page(act_id, title, start_ms, close_ms, **extra):
    act = {"__typename": "Activity", "id": act_id, "title": title, "organizationName": "주최", "recruitStartAt": start_ms,
           "recruitCloseAt": close_ms, "status": "OPEN", "targets": [], "interests": [], "tenThousandUnitOfReward": None, "homepageURL": None, **extra}
    blob = json.dumps({"props": {"pageProps": {"__APOLLO_STATE__": {f"Activity:{act_id}": act}}}}, ensure_ascii=False)
    return f'<html><script id="__NEXT_DATA__" type="application/json">{blob}</script></html>'


CLOSE = 1793804399999  # 2026-11-04 23:59:59.999 KST
START = 1793113200000  # 2026-10-28 00:00 KST


class LinkareerTest(unittest.TestCase):
    def test_listing_reads_only_query_nodes(self):
        rows = linkareer.parse_listing(fixture("linkareer_listing.html"))
        self.assertEqual(len(rows), 20)  # 광고 Activity는 목록 노드가 아니므로 제외
        lotte = next(r for r in rows if r["id"] == "360080")
        self.assertEqual((lotte["title"], lotte["closeAt"]), ("LOTTE AX CHALLENGE 2026", CLOSE))

    def test_listing_without_next_data_is_error(self):
        with self.assertRaises(StructureError):
            linkareer.parse_listing("<html>점검 중</html>")

    def test_detail_fields(self):
        d = linkareer.parse_detail(fixture("linkareer_detail.html"), "360080")
        self.assertEqual(d["registrationStartDate"], "2026-10-28")
        self.assertEqual(d["deadlineAt"], "2026-11-04T23:59:59.999+09:00")  # 밀리초 보존(1초 일찍 숨기지 않음)
        self.assertEqual(d["organizer"], "롯데지주")
        self.assertEqual(d["eligibility"], "대상 제한 없음")
        self.assertEqual(d["prize"], "총 상금 2,000만원")
        self.assertIsNone(d["homepage"])

    def test_collect_ai_rows_only_with_paging_stop(self):
        pages = {
            linkareer.page_url(1): fixture("linkareer_listing.html"),
            linkareer.page_url(2): listing_page([("1", "2026 시민 AI영상 공모전", CLOSE), ("2", "감귤디저트대회", CLOSE)]),
            linkareer.page_url(3): listing_page([("1", "2026 시민 AI영상 공모전", CLOSE)]),  # 반복 페이지 → 중단
            linkareer.detail_url("360080"): fixture("linkareer_detail.html"),
            linkareer.detail_url("1"): detail_page("1", "2026 시민 AI영상 공모전", START, CLOSE),
        }
        for act_id in ("360253", "360109", "360055"):  # fixture 1페이지의 다른 AI 공모전
            pages[linkareer.detail_url(act_id)] = detail_page(act_id, "AI 공모전 " + act_id, START, None)
        fetcher = FakeFetcher(pages)
        result = linkareer.collect(fetcher, NOW, None)
        titles = {i["title"] for i in result.items}
        self.assertIn("LOTTE AX CHALLENGE 2026", titles)
        self.assertIn("2026 시민 AI영상 공모전", titles)
        self.assertNotIn("감귤디저트대회", titles)
        self.assertNotIn(linkareer.page_url(4), fetcher.calls)
        lotte = next(i for i in result.items if i["title"] == "LOTTE AX CHALLENGE 2026")
        self.assertEqual(lotte["sourceUrl"], "https://linkareer.com/activity/360080")
        self.assertEqual(lotte["url"], lotte["sourceUrl"])  # 홈페이지 링크가 없으면 링커리어 안내 페이지
        self.assertEqual(lotte["deadlineAt"], "2026-11-04T23:59:59.999+09:00")
        self.assertIsNotNone(rules.normalize_item(lotte, "linkareer", NOW_ISO))

    def test_detail_close_mismatch_counts_as_failure(self):
        pages = {
            linkareer.page_url(1): listing_page([("1", "AI 공모전 A", CLOSE), ("2", "AI 공모전 B", CLOSE)]),
            linkareer.page_url(2): listing_page([]),
            linkareer.detail_url("1"): detail_page("1", "AI 공모전 A", START, CLOSE + 86_400_000),
            linkareer.detail_url("2"): detail_page("2", "AI 공모전 B", START, CLOSE),
        }
        result = linkareer.collect(FakeFetcher(pages), NOW, None)
        self.assertEqual([i["title"] for i in result.items], ["AI 공모전 B"])
        self.assertIn("실패 1건", result.message)

    def test_detail_closed_early_is_not_saved_but_observed(self):
        pages = {
            linkareer.page_url(1): listing_page([("1", "AI 공모전 A", CLOSE), ("2", "AI 공모전 B", CLOSE)]),
            linkareer.page_url(2): listing_page([]),
            linkareer.detail_url("1"): detail_page("1", "AI 공모전 A", START, CLOSE, status="CLOSED"),
            linkareer.detail_url("2"): detail_page("2", "AI 공모전 B", START, CLOSE),
        }
        result = linkareer.collect(FakeFetcher(pages), NOW, None)
        self.assertEqual([i["title"] for i in result.items], ["AI 공모전 B"])
        self.assertEqual(result.closed_source_urls, [linkareer.detail_url("1")])
        self.assertIn("조기 마감 1건", result.message)

    def test_all_details_failing_is_source_error(self):
        pages = {linkareer.page_url(1): listing_page([("1", "AI 공모전 A", CLOSE)]), linkareer.page_url(2): listing_page([])}
        with self.assertRaises(SourceError):
            linkareer.collect(FakeFetcher(pages), NOW, None)

    def test_later_page_error_is_source_failure(self):
        pages = {linkareer.page_url(1): listing_page([("1", "AI 공모전 A", CLOSE)]), linkareer.page_url(2): FetchError("error", "503")}
        with self.assertRaises(FetchError):
            linkareer.collect(FakeFetcher(pages), NOW, None)

    def test_homepage_https_link_is_used(self):
        pages = {
            linkareer.page_url(1): listing_page([("1", "AI 해커톤", CLOSE)]), linkareer.page_url(2): listing_page([]),
            linkareer.detail_url("1"): detail_page("1", "AI 해커톤", START, CLOSE, homepageURL="https://example.org/ai"),
        }
        self.assertEqual(linkareer.collect(FakeFetcher(pages), NOW, None).items[0]["url"], "https://example.org/ai")

    def test_page_and_item_caps(self):
        pages = {linkareer.page_url(n): listing_page([(str(n), f"AI 공모전 {n}", CLOSE)]) for n in range(1, 100)}
        pages.update({linkareer.detail_url(str(n)): detail_page(str(n), f"AI 공모전 {n}", START, CLOSE) for n in range(1, 100)})
        fetcher = FakeFetcher(pages)
        linkareer.collect(fetcher, NOW, None)
        self.assertEqual(len([c for c in fetcher.calls if "/list/" in c]), linkareer.PAGE_LIMIT)
        fetcher = FakeFetcher(pages)
        self.assertEqual(len(linkareer.collect(fetcher, NOW, 3).items), 3)

    def test_fixtures_hold_no_manager_contacts(self):
        for name in ("linkareer_listing.html", "linkareer_detail.html"):
            self.assertIsNone(re.search(r"managerName|@[\w-]+\.", fixture(name)), name)


if __name__ == "__main__":
    unittest.main()
