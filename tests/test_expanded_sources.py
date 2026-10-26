"""공식 AI 행사 3종(서초·NVIDIA·AI Festa)과 위비티 다중 페이지 수집 테스트 — 네트워크 없이 fixture만 쓴다."""
import importlib
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from collectors.opportunities import pipeline, rules, urlsafe  # noqa: E402
from collectors.opportunities.errors import FetchError, StructureError  # noqa: E402
from collectors.opportunities.sources import default_sources, wevity  # noqa: E402
from collectors.opportunities.sources.base import SourceSpec  # noqa: E402
from test_opportunities import NOW, NOW_ISO, OK_ROBOTS, FakeFetcher, FakeResp, fixture, make_fetcher  # noqa: E402

TODAY = date(2026, 10, 12)


def source(name):
    """모듈이 아직 없으면 그 테스트만 실패하도록 지연 import 한다."""
    return importlib.import_module(f"collectors.opportunities.sources.{name}")


def listing(ixs, prefix="AI 해커톤"):
    rows = "".join(
        f'<li><div class="tit"><a href="?c=find&amp;gbn=view&amp;ix={ix}">{prefix} {ix}</a></div>'
        f'<div class="organ">주최</div><div class="day">D-3<span class="dday ing">접수중</span></div></li>'
        for ix in ixs
    )
    return f'<div class="list"><ul class="list"><li class="top"><div class="tit">공모전명</div></li>{rows}</ul></div>'


def wevity_pages(page_ixs):
    """page_ixs: 페이지별 ix 목록. 상세는 모든 ix에 같은 fixture를 돌려준다."""
    pages = {}
    for n, ixs in enumerate(page_ixs, start=1):
        pages[wevity.LISTING_URL if n == 1 else f"{wevity.LISTING_URL}&gp={n}"] = listing(ixs)
    for ixs in page_ixs:
        for ix in ixs:
            pages[wevity.detail_url(str(ix))] = fixture("wevity_detail.html")
    return pages


def detail_calls(fetcher):
    return [c for c in fetcher.calls if "gbn=view" in c]


class KindRulesTest(unittest.TestCase):
    def test_festival_words_are_events(self):
        for title in ("2026 서초 AI 페스타", "NVIDIA AI Day Seoul", "AI Festival 2026", "AI FESTA 26", "AI 축제 한마당"):
            self.assertEqual(rules.classify_kind(title), "event", title)

    def test_contest_and_hackathon_win_over_festival(self):
        self.assertEqual(rules.classify_kind("서초 AI 페스타 캐릭터 공모전"), "contest")
        self.assertEqual(rules.classify_kind("AI 페스타 해커톤"), "hackathon")

    def test_course_and_job_exclusions_stay(self):
        self.assertIsNone(rules.classify_kind("AI 개발자 부트캠프 수강생 모집"))
        self.assertIsNone(rules.classify_kind("AI 엔지니어 신입 채용 공고"))
        self.assertIsNone(rules.classify_kind("Email Day 안내"))


class AllowListTest(unittest.TestCase):
    def test_new_exact_hosts_only(self):
        for ok in ("https://seochoai.kr/", "https://www.nvidia.com/ko-kr/ai-days/", "https://www.aifesta.kr/", "https://aifesta.kr/"):
            self.assertTrue(urlsafe.is_fetch_allowed(ok), ok)
        for bad in ("https://evil.seochoai.kr/", "https://nvidia.com/ko-kr/ai-days/", "https://developer.nvidia.com/", "https://register.nvidia.com/", "http://seochoai.kr/"):
            self.assertFalse(urlsafe.is_fetch_allowed(bad), bad)


class RegistryTest(unittest.TestCase):
    def test_existing_seven_sources_keep_priority_first(self):
        self.assertEqual([s.id for s in default_sources()][:7], ["devpost", "dacon", "wevity", "aisummit", "seocho", "nvidia", "aifesta"])


class JsonLdTest(unittest.TestCase):
    def wrap(self, payload):
        return f'<html><head><script type="application/ld+json">{json.dumps(payload)}</script></head></html>'

    EVENT = {"@type": "Event", "name": "AI 테스트 행사", "startDate": "2026-12-01T10:00:00+09:00", "endDate": "2026-12-02T18:00:00+09:00",
             "location": {"name": "코엑스", "address": {"addressCountry": "KR", "addressRegion": "서울"}}}

    def read(self, html):
        return source("jsonld").read_event(html, "테스트")

    def test_single_list_and_graph_shapes(self):
        for payload in (self.EVENT, [{"@type": "WebSite"}, self.EVENT], {"@graph": [{"@type": "Organization"}, self.EVENT]},
                        {"@type": ["Thing", "Event"], **{k: v for k, v in self.EVENT.items() if k != "@type"}}):
            data = self.read(self.wrap(payload))
            self.assertEqual((data["name"], data["startDate"], data["endDate"]), ("AI 테스트 행사", "2026-12-01", "2026-12-02"))
            self.assertEqual(data["venue"], "코엑스")

    def test_dates_use_seoul_calendar_day(self):
        event = dict(self.EVENT, startDate="2026-11-30T20:00:00-05:00", endDate="2026-12-02T09:00:00+09:00")
        self.assertEqual(self.read(self.wrap(event))["startDate"], "2026-12-01")

    def test_no_event_or_bad_json_is_error_not_empty(self):
        for html in ("<html></html>", self.wrap({"@type": "WebSite"}),
                     '<script type="application/ld+json">{not json</script>', self.wrap({"@graph": []})):
            with self.assertRaises(StructureError):
                self.read(html)

    def test_ambiguous_two_events_is_error(self):
        with self.assertRaises(StructureError):
            self.read(self.wrap([self.EVENT, dict(self.EVENT, name="다른 행사")]))

    def test_invalid_dates_are_errors(self):
        for patch in ({"startDate": "내일"}, {"startDate": "2026-12-01T10:00:00"}, {"startDate": None}, {"endDate": "2026-13-40T10:00:00+09:00"},
                      {"startDate": "2026-12-05T10:00:00+09:00"}, {"name": ""}):
            with self.assertRaises(StructureError, msg=patch):
                self.read(self.wrap(dict(self.EVENT, **patch)))

    def test_non_korea_location_is_error(self):
        event = dict(self.EVENT, location={"name": "Moscone", "address": {"addressCountry": "US"}})
        with self.assertRaises(StructureError):
            self.read(self.wrap(event))


class SeochoTest(unittest.TestCase):
    def collect(self, html=None):
        seocho = source("seocho")
        return seocho.collect(FakeFetcher({seocho.MAIN_URL: html or fixture("seocho_main.html")}), NOW, 20)

    def test_item_from_official_jsonld(self):
        result = self.collect()
        self.assertEqual(len(result.items), 1)
        raw = result.items[0]
        self.assertEqual((raw["kind"], raw["title"], raw["mode"], raw["country"]), ("event", "2026 서초 AI 페스타", "offline", "KR"))
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-10-17", "2026-10-17"))
        self.assertEqual(raw["organizer"], "서초구")
        self.assertIn("서초문화예술공원", raw["region"])
        self.assertEqual(raw["fee"], "무료")
        self.assertEqual((raw["eligibility"], raw["eligibilityVerified"]), ("시민 누구나", True))
        self.assertIn("10:00", raw["dateNote"])
        self.assertIn("18:00", raw["dateNote"])

    def test_sub_program_states_do_not_close_the_festival(self):
        raw = self.collect().items[0]
        self.assertEqual(raw["sourceStatus"], "unknown")
        self.assertIsNone(raw["deadlineDate"])
        self.assertIsNone(raw["deadlineAt"])
        item = rules.normalize_item(raw, "seocho", NOW_ISO)
        self.assertIsNotNone(item)
        self.assertFalse(rules.is_archived(item, TODAY))

    def test_cancelled_event_status_closes_the_festival(self):
        html = fixture("seocho_main.html").replace("schema.org/EventScheduled", "schema.org/EventCancelled")
        raw = self.collect(html).items[0]
        self.assertEqual(raw["sourceStatus"], "closed")
        self.assertIn("행사 취소", raw["dateNote"])

    def test_postponed_or_scheduled_status_is_not_cancellation(self):
        for status in ("EventScheduled", "EventPostponed"):
            html = fixture("seocho_main.html").replace("schema.org/EventScheduled", f"schema.org/{status}")
            self.assertEqual(self.collect(html).items[0]["sourceStatus"], "unknown", status)

    def test_offer_valid_from_is_not_registration_start(self):
        raw = self.collect().items[0]
        self.assertIsNone(raw["registrationStartDate"])
        self.assertNotIn("2026-09-15", json.dumps(raw, ensure_ascii=False))

    def test_reads_page_values_not_constants(self):
        html = fixture("seocho_main.html").replace("2026-10-17", "2027-03-05").replace("2026 서초 AI 페스타", "2027 서초 AI 페스타")
        raw = self.collect(html).items[0]
        self.assertEqual((raw["title"], raw["startDate"], raw["endDate"]), ("2027 서초 AI 페스타", "2027-03-05", "2027-03-05"))

    def test_fee_and_eligibility_stay_unknown_without_evidence(self):
        html = fixture("seocho_main.html").replace('"isAccessibleForFree": true,', "").replace('"price": "0"', '"price": "5000"')
        html = html.replace("시민 누구나", "참가 희망자")
        raw = self.collect(html).items[0]
        self.assertEqual(raw["fee"], rules.UNKNOWN_TEXT)
        self.assertEqual((raw["eligibility"], raw["eligibilityVerified"]), (rules.UNKNOWN_TEXT, False))

    def test_street_address_and_contacts_are_not_stored(self):
        blob = json.dumps(rules.normalize_item(self.collect().items[0], "seocho", NOW_ISO), ensure_ascii=False)
        self.assertNotIn("바우뫼로", blob)

    def test_missing_jsonld_is_structure_error(self):
        with self.assertRaises(StructureError):
            self.collect("<html><body>점검 중</body></html>")


class AiFestaTest(unittest.TestCase):
    def collect(self, html=None):
        aifesta = source("aifesta")
        return aifesta.collect(FakeFetcher({aifesta.MAIN_URL: html or fixture("aifesta_main.html")}), NOW, 20)

    def test_event_from_graph(self):
        raw = self.collect().items[0]
        self.assertEqual((raw["kind"], raw["title"], raw["mode"], raw["country"]), ("event", "AI FESTA 26", "offline", "KR"))
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-10-06", "2026-10-08"))
        self.assertEqual(raw["organizer"], "AI Festa 사무국")
        self.assertIn("코엑스 C홀", raw["region"])

    def test_unprovided_fee_eligibility_and_deadline_stay_unknown(self):
        raw = self.collect().items[0]
        self.assertEqual((raw["fee"], raw["eligibility"]), (rules.UNKNOWN_TEXT, rules.UNKNOWN_TEXT))
        self.assertFalse(raw["eligibilityVerified"])
        self.assertIsNone(raw["deadlineDate"])
        self.assertEqual(raw["sourceStatus"], "unknown")

    def test_ended_event_is_kept_as_archived_not_active(self):
        item = rules.normalize_item(self.collect().items[0], "aifesta", NOW_ISO)
        self.assertIsNotNone(item)
        self.assertTrue(rules.is_archived(item, TODAY))
        self.assertFalse(rules.is_expired_archive(item, TODAY))

    def test_graph_without_event_is_error(self):
        html = fixture("aifesta_main.html").replace('"@type": "Event"', '"@type": "Thing"')
        with self.assertRaises(StructureError):
            self.collect(html)


class NvidiaTest(unittest.TestCase):
    def collect(self, html=None):
        nvidia = source("nvidia")
        return nvidia.collect(FakeFetcher({nvidia.MAIN_URL: html or fixture("nvidia_ai_day.html")}), NOW, 20)

    def test_hero_year_and_range(self):
        data = source("nvidia").parse_main(fixture("nvidia_ai_day.html"))
        self.assertEqual((data["startDate"], data["endDate"]), ("2026-11-09", "2026-11-10"))
        self.assertEqual(data["venue"], "코엑스")

    def test_hero_year_first_format(self):
        # 2026-10 공식 페이지가 '2026년 11월 9~10일 | 코엑스'로 표기를 바꿨다.
        html = fixture("nvidia_ai_day.html").replace("11월 9&#xFF5E;10일, 2026", "2026년 11월 9~10일")
        data = source("nvidia").parse_main(html)
        self.assertEqual((data["year"], data["startDate"], data["endDate"], data["venue"]), ("2026", "2026-11-09", "2026-11-10", "코엑스"))

    def test_item(self):
        raw = self.collect().items[0]
        self.assertEqual((raw["kind"], raw["title"], raw["mode"], raw["country"]), ("event", "NVIDIA AI Day Seoul 2026", "offline", "KR"))
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-11-09", "2026-11-10"))
        self.assertEqual(raw["organizer"], "NVIDIA")
        self.assertIn("코엑스", raw["region"])
        self.assertIsNone(raw["deadlineDate"])
        self.assertIsNone(raw["deadlineAt"])
        self.assertIn(rules.UNKNOWN_TEXT, raw["fee"])
        self.assertEqual(raw["sourceStatus"], "open")
        self.assertIsNotNone(rules.normalize_item(raw, "nvidia", NOW_ISO))
        self.assertNotIn("hero", raw["dateNote"])
        for alias in ("엔비디아", "AI 데이", "서울"):
            self.assertIn(alias, raw["tags"])

    def test_program_session_times_do_not_shrink_the_period(self):
        # fixture에는 11월 10일 오후 워크숍 시간 줄이 있다. 기간은 hero 표기 전체여야 한다.
        raw = self.collect().items[0]
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-11-09", "2026-11-10"))

    def test_reads_page_year_not_constant(self):
        html = fixture("nvidia_ai_day.html").replace("2026", "2027")
        raw = self.collect(html).items[0]
        self.assertEqual((raw["title"], raw["startDate"], raw["endDate"]), ("NVIDIA AI Day Seoul 2027", "2027-11-09", "2027-11-10"))

    def test_title_year_must_match_hero_year(self):
        html = fixture("nvidia_ai_day.html").replace("<title>AI Day Seoul 2026:", "<title>AI Day Seoul 2025:")
        with self.assertRaises(StructureError):
            self.collect(html)

    def test_missing_pieces_are_errors(self):
        base = fixture("nvidia_ai_day.html")
        broken = {
            "hero": base.replace("11월 9&#xFF5E;10일, 2026", "곧 공개"),
            "title": base.replace("AI Day Seoul 2026: 핸즈온", "핸즈온"),
            "h1": base.replace('<h1 class="title ">AI Day <span style="font-weight: normal;">Seoul</span></h1>', "<h2>AI Day</h2>"),
            "bad month/day": base.replace("11월 9&#xFF5E;10일", "2월 30&#xFF5E;31일"),
            "reversed": base.replace("11월 9&#xFF5E;10일", "11월 10&#xFF5E;9일"),
        }
        for name, html in broken.items():
            with self.assertRaises(StructureError, msg=name):
                self.collect(html)

    def test_status_open_only_with_register_cta(self):
        html = fixture("nvidia_ai_day.html").replace("지금 등록하기", "곧 공개")
        self.assertEqual(self.collect(html).items[0]["sourceStatus"], "unknown")

    def test_ascii_tilde_and_nbsp_variants(self):
        html = fixture("nvidia_ai_day.html").replace("9&#xFF5E;10일, 2026&ensp;|&ensp;코엑스", "9~10일,&nbsp;2026&nbsp;|&nbsp;코엑스")
        raw = self.collect(html).items[0]
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2026-11-09", "2026-11-10"))


class OfficialFetchPathTest(unittest.TestCase):
    """새 소스도 허용목록·robots·redirect 검증을 실제 Fetcher로 통과한다."""

    def routes(self):
        return {
            "https://seochoai.kr/robots.txt": OK_ROBOTS, "https://seochoai.kr/": FakeResp(200, fixture("seocho_main.html").encode("utf-8")),
            "https://www.aifesta.kr/robots.txt": OK_ROBOTS, "https://www.aifesta.kr/": FakeResp(200, fixture("aifesta_main.html").encode("utf-8")),
            "https://www.nvidia.com/robots.txt": OK_ROBOTS, "https://www.nvidia.com/ko-kr/ai-days/": FakeResp(200, fixture("nvidia_ai_day.html").encode("utf-8")),
        }

    def test_all_three_collect_through_fetcher(self):
        fetcher, _, _ = make_fetcher(self.routes())
        for spec in default_sources():
            if spec.id in ("seocho", "nvidia", "aifesta"):
                self.assertEqual(len(spec.collect(fetcher, NOW, 20).items), 1, spec.id)

    def test_robots_disallow_blocks_official_source(self):
        routes = self.routes()
        routes["https://seochoai.kr/robots.txt"] = FakeResp(200, b"User-agent: *\nDisallow: /\n")
        fetcher, session, _ = make_fetcher(routes)
        with self.assertRaises(FetchError) as cm:
            source("seocho").collect(fetcher, NOW, 20)
        self.assertEqual(cm.exception.status, "blocked")
        self.assertNotIn("https://seochoai.kr/", session.calls)

    def test_redirect_to_other_host_is_blocked(self):
        routes = self.routes()
        routes["https://www.aifesta.kr/"] = FakeResp(302, b"", {"Location": "https://evil.example/"})
        fetcher, session, _ = make_fetcher(routes)
        with self.assertRaises(FetchError) as cm:
            source("aifesta").collect(fetcher, NOW, 20)
        self.assertEqual(cm.exception.status, "blocked")
        self.assertNotIn("https://evil.example/", session.calls)


class WevityPagingTest(unittest.TestCase):
    def test_second_page_target_is_collected(self):
        pages = {
            wevity.LISTING_URL: fixture("wevity_listing.html"),
            f"{wevity.LISTING_URL}&gp=2": fixture("wevity_listing_page2.html"),
            f"{wevity.LISTING_URL}&gp=3": fixture("wevity_empty.html"),
            **{wevity.detail_url(ix): fixture("wevity_detail.html") for ix in ("111322", "111124", "999101")},
        }
        fetcher = FakeFetcher(pages)
        result = wevity.collect(fetcher, NOW, None)
        by_ix = {r["sourceUrl"].rsplit("ix=", 1)[1]: r for r in result.items}
        self.assertEqual(sorted(by_ix), ["111124", "111322", "999101"])
        self.assertEqual(by_ix["111124"]["title"], "2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤")
        self.assertEqual(by_ix["111124"]["kind"], "hackathon")
        self.assertEqual(by_ix["999101"]["kind"], "contest")
        self.assertEqual(len([c for c in detail_calls(fetcher) if c.endswith("ix=111322")]), 1)  # 페이지 간 중복 ix는 한 번만 조회

    def test_default_limit_is_not_cut_back_to_twenty(self):
        pages = wevity_pages([range(1, 16), range(16, 31), []])
        fetcher = FakeFetcher(pages)
        result = wevity.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 30)
        self.assertEqual(len(detail_calls(fetcher)), 30)

    def test_page_and_item_caps(self):
        pages = wevity_pages([range(n * 15 + 1, n * 15 + 16) for n in range(8)])
        fetcher = FakeFetcher(pages)
        result = wevity.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 90)
        self.assertFalse([c for c in fetcher.calls if "gp=7" in c or "gp=8" in c])
        self.assertLessEqual(len(detail_calls(fetcher)), 100)

    def test_item_limit_function(self):
        self.assertEqual(wevity.item_limit(None), 100)
        self.assertEqual(wevity.item_limit(7), 7)
        self.assertEqual(wevity.item_limit(500), 100)
        self.assertEqual(wevity.item_limit(0), 0)

    def test_explicit_max_items_bounds_detail_fetches_and_paging(self):
        fetcher = FakeFetcher(wevity_pages([range(1, 16), range(16, 31)]))
        result = wevity.collect(fetcher, NOW, 5)
        self.assertEqual(len(result.items), 5)
        self.assertEqual(len(detail_calls(fetcher)), 5)
        self.assertFalse([c for c in fetcher.calls if "gp=2" in c])
        fetcher = FakeFetcher(wevity_pages([range(1, 16), range(16, 31)]))
        self.assertEqual(len(wevity.collect(fetcher, NOW, 20).items), 20)
        self.assertEqual(len(detail_calls(fetcher)), 20)

    def test_repeated_or_empty_page_stops(self):
        pages = wevity_pages([range(1, 16), range(1, 16), range(16, 31)])
        fetcher = FakeFetcher(pages)
        self.assertEqual(len(wevity.collect(fetcher, NOW, None).items), 15)
        self.assertFalse([c for c in fetcher.calls if "gp=3" in c])
        fetcher = FakeFetcher(wevity_pages([range(1, 16), []]))
        self.assertEqual(len(wevity.collect(fetcher, NOW, None).items), 15)

    def test_later_page_http_error_fails_the_source(self):
        pages = wevity_pages([range(1, 16)])
        pages[f"{wevity.LISTING_URL}&gp=2"] = FetchError("error", "HTTP 503")
        with self.assertRaises(FetchError):
            wevity.collect(FakeFetcher(pages), NOW, None)

    def test_later_page_structure_error_fails_the_source(self):
        pages = wevity_pages([range(1, 16)])
        pages[f"{wevity.LISTING_URL}&gp=2"] = "<html><body>forbidden</body></html>"
        with self.assertRaises(StructureError):
            wevity.collect(FakeFetcher(pages), NOW, None)

    def test_first_page_structure_checks_are_kept(self):
        with self.assertRaises(StructureError):
            wevity.collect(FakeFetcher({wevity.LISTING_URL: "<html>x</html>"}), NOW, None)
        self.assertEqual(wevity.collect(FakeFetcher({wevity.LISTING_URL: fixture("wevity_empty.html")}), NOW, None).items, [])

    def test_later_page_failure_preserves_previous_data(self):
        import tempfile
        pages = wevity_pages([range(1, 4), []])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "opportunities.json"
            spec = SourceSpec("wevity", "위비티", wevity.SOURCE_URL, wevity.collect)
            pipeline.run(out, curated_path=None, fetcher=FakeFetcher(pages), sources=[spec], now=NOW)
            before = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(before["items"]), 3)
            pages[f"{wevity.LISTING_URL}&gp=2"] = FetchError("error", "HTTP 503")
            report = pipeline.run(out, curated_path=None, fetcher=FakeFetcher(pages), sources=[spec], now=NOW)
            self.assertEqual(report["sources"][0]["status"], "error")
            after = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(after["items"], before["items"])


if __name__ == "__main__":
    unittest.main()
