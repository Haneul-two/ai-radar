"""AI Radar 수집 확장 테스트 — 콘테스트코리아·Dev-Event·AI EXPO, Devpost/위비티 목록 깊이, aisummit 큰 응답, 교차 출처 중복.
네트워크 없이 최소 fixture만 쓴다(실제 페이지에서 표·행만 발췌, 연락처 없음)."""
import importlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from collectors.opportunities import pipeline, rules, urlsafe  # noqa: E402
from collectors.opportunities.errors import FetchError, SourceError, StructureError  # noqa: E402
from collectors.opportunities.http import Fetcher  # noqa: E402
from collectors.opportunities.sources import aisummit, default_sources, devpost, wevity  # noqa: E402
from collectors.opportunities.sources.base import SourceSpec  # noqa: E402
from test_opportunities import FakeFetcher, FakeResp, OK_ROBOTS, fixture, make_fetcher, make_item  # noqa: E402

NOW = datetime(2026, 10, 12, 6, 0, 0, tzinfo=timezone.utc)  # 한국시간 2026-10-12 15:00
NOW_ISO = "2026-10-12T06:00:00Z"


def source(name):
    """모듈이 아직 없으면 그 테스트만 실패하도록 지연 import 한다."""
    return importlib.import_module(f"collectors.opportunities.sources.{name}")


def detail_calls(fetcher, marker="str_no="):
    return [c for c in fetcher.calls if marker in c and "list.php" not in c]


class AllowListTest(unittest.TestCase):
    def test_new_exact_hosts_only(self):
        for ok in ("https://www.contestkorea.com/sub/list.php?int_gbn=1", "https://aiexpo.co.kr/",
                   "https://raw.githubusercontent.com/brave-people/Dev-Event/master/README.md"):
            self.assertTrue(urlsafe.is_fetch_allowed(ok), ok)
        for bad in ("https://contestkorea.com/", "https://evil.contestkorea.com/", "https://www.aiexpo.co.kr/", "https://sub.aiexpo.co.kr/",
                    "https://evil.raw.githubusercontent.com/x", "https://github.com/brave-people/Dev-Event", "https://gist.githubusercontent.com/x",
                    "http://aiexpo.co.kr/", "https://thinkcontest.com/", "https://onoffmix.com/", "https://daker.ai/"):
            self.assertFalse(urlsafe.is_fetch_allowed(bad), bad)


class RegistryTest(unittest.TestCase):
    def test_ten_sources_existing_priority_first(self):
        self.assertEqual([s.id for s in default_sources()][:10],  # 이후 추가 출처는 test_ax_sources
                         ["devpost", "dacon", "wevity", "aisummit", "seocho", "nvidia", "aifesta", "contestkorea", "devevent", "aiexpo"])


# ---------------------------------------------------------------- ContestKorea

def ck_row(no, title, status, period="09.30~10.25", bcode="030310001"):
    return (f'<li><div class="title"><a href="view.php?int_gbn=1&amp;Txt_bcode={bcode}&amp;str_no={no}"><span class="category">학문</span>'
            f'<span class="txt">{title}</span></a></div><ul class="host"><li class="icon_1"><strong>주최</strong> . 주최</li>'
            f'<li class="icon_2"><strong>대상</strong> . 일반인</li></ul><div class="date"><div class="date-detail"><span class="step-1"><em>접수</em> {period}</span></div></div>'
            f'<div class="d-day"><span class="condition">{status}</span></div></li>')


def ck_page(*rows):
    return f'<html><body><div class="list_style_2"><ul>{"".join(rows)}</ul></div></body></html>'


class ContestKoreaParseTest(unittest.TestCase):
    def test_listing_rows_and_status_mapping(self):
        rows = source("contestkorea").parse_listing(fixture("contestkorea_listing.html"))
        by_title = {r["title"]: r for r in rows}
        self.assertEqual(len(rows), 5)
        self.assertEqual(by_title["2026 AI 플랫폼 구축 경진대회"]["sourceStatus"], "open")
        self.assertEqual(by_title["2026 AI 플랫폼 구축 경진대회"]["strNo"], "202610110007")
        self.assertEqual(by_title["제2회 AI전자그림책 공모전 'AI 이야기 숲'"]["sourceStatus"], "unknown")  # 접수예정
        self.assertEqual(by_title["2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤"]["sourceStatus"], "open")  # 마감임박
        self.assertEqual(by_title["생명안전 AI숏폼 공모전"]["sourceStatus"], "closed")  # 심사중

    def test_listing_structure_errors_and_legit_empty(self):
        mod = source("contestkorea")
        with self.assertRaises(StructureError):
            mod.parse_listing("<html><body>점검중</body></html>")
        with self.assertRaises(StructureError):
            mod.parse_listing('<div class="list_style_2"><ul><li><div class="title">제목 링크 없음</div></li></ul></div>')
        self.assertEqual(mod.parse_listing('<div class="list_style_2"><ul></ul></div>'), [])

    def test_detail_fields(self):
        detail = source("contestkorea").parse_detail(fixture("contestkorea_detail.html"))
        self.assertEqual(detail["period"], ("2026-09-30", "2026-10-25"))
        self.assertIn("대학생", detail["target"])
        self.assertEqual(detail["region"], "온라인")
        self.assertEqual(detail["apply_url"], "https://daker.ai/public/hackathons/ai-platform-build-challenge-prelims")
        self.assertIn("100만원", detail["prize"])
        self.assertEqual(detail["fee"], "무료 접수")

    def test_detail_without_table_is_structure_error(self):
        with self.assertRaises(StructureError):
            source("contestkorea").parse_detail("<html><body>삭제된 게시물입니다</body></html>")

    def test_invalid_or_reversed_period_is_none_not_guessed(self):
        mod = source("contestkorea")
        for bad in ("2026.13.45 ~ 2026.10.25", "2026.10.25 ~ 2026.09.30", "10.01 ~ 10.25", "상시 접수"):
            html = fixture("contestkorea_detail.html").replace("2026.09.30 ~ 2026.10.25", bad)
            self.assertIsNone(mod.parse_detail(html)["period"], bad)

    def test_non_https_or_script_apply_link_is_not_used(self):
        mod = source("contestkorea")
        html = fixture("contestkorea_detail.html").replace("https://daker.ai/public", "http://daker.ai/public")
        self.assertIsNone(mod.parse_detail(html)["apply_url"])


class ContestKoreaCollectTest(unittest.TestCase):
    def pages(self, **over):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): fixture("contestkorea_listing.html"), mod.page_url("AI", 2): ck_page(ck_row("1", "마감 AI 대회", "캠페인마감")),
                 mod.page_url("인공지능", 1): ck_page()}
        for no in ("202610110007", "202610090001", "202610060001"):
            pages[mod.detail_url("031210001", no)] = fixture("contestkorea_detail.html")
        pages.update(over)
        return pages

    def test_only_active_ai_candidates_are_fetched(self):
        mod = source("contestkorea")
        listing = mod.parse_listing(fixture("contestkorea_listing.html"))
        pages = {mod.page_url("AI", 1): fixture("contestkorea_listing.html"), mod.page_url("AI", 2): ck_page(), mod.page_url("인공지능", 1): ck_page()}
        for row in listing:  # 상세의 접수 마감은 목록의 마감일(MM.DD)과 같아야 한다
            month, day = row["listEnd"]
            pages[mod.detail_url(row["bcode"], row["strNo"])] = fixture("contestkorea_detail.html").replace(
                "2026.09.30 ~ 2026.10.25", f"2026.{month}.{day} ~ 2026.{month}.{day}")
        fetcher = FakeFetcher(pages)
        result = mod.collect(fetcher, NOW, None)
        fetched = {c.rsplit("str_no=", 1)[1] for c in detail_calls(fetcher)}
        closed_no = next(r["strNo"] for r in listing if r["title"].startswith("생명안전"))
        non_ai_no = next(r["strNo"] for r in listing if r["title"].startswith("LAIKA"))
        self.assertNotIn(closed_no, fetched)  # 심사중(종료) 행은 상세를 읽지 않는다
        self.assertNotIn(non_ai_no, fetched)  # 제목에 AI 단어가 없는 행(LAIKA)도 읽지 않는다
        self.assertEqual(len(fetched), 3)
        self.assertEqual(len(result.items), 3)

    def test_all_closed_page_does_not_stop_later_pages(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(ck_row("1", "마감 AI 대회", "심사중")), mod.page_url("AI", 2): ck_page(ck_row("202610110007", "열린 AI 대회", "접수중", "10.01~10.25")),
                 mod.page_url("AI", 3): ck_page(), mod.page_url("인공지능", 1): ck_page(),
                 mod.detail_url("030310001", "202610110007"): fixture("contestkorea_detail.html")}
        fetcher = FakeFetcher(pages)
        result = mod.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 1)
        self.assertIn(mod.page_url("AI", 3), fetcher.calls)  # 빈 페이지에서 멈춘다

    def test_item_values_from_detail_not_listing(self):
        mod = source("contestkorea")
        row = mod.parse_listing(fixture("contestkorea_listing.html"))[0]
        raw = mod.build_raw(row, mod.parse_detail(fixture("contestkorea_detail.html")))
        self.assertEqual((raw["registrationStartDate"], raw["deadlineDate"], raw["deadlineAt"]), ("2026-09-30", "2026-10-25", None))
        self.assertEqual((raw["startDate"], raw["endDate"]), (None, None))  # 심사기간은 개최일이 아니다
        self.assertEqual((raw["kind"], raw["mode"], raw["country"], raw["sourceStatus"]), ("contest", "online", "KR", "open"))
        self.assertEqual(raw["url"], "https://daker.ai/public/hackathons/ai-platform-build-challenge-prelims")
        self.assertTrue(raw["sourceUrl"].startswith("https://www.contestkorea.com/sub/view.php?"))
        self.assertIn("날짜만", raw["dateNote"])
        self.assertTrue(raw["eligibilityVerified"])
        self.assertEqual(raw["fee"], "무료")
        item = rules.normalize_item(raw, "contestkorea", NOW_ISO)
        self.assertIsNotNone(item)
        self.assertTrue(rules.meets_contract(item))

    def test_upcoming_keeps_registration_start_and_is_not_open(self):
        mod = source("contestkorea")
        row = next(r for r in mod.parse_listing(fixture("contestkorea_listing.html")) if r["title"].startswith("제2회 AI전자그림책"))
        html = fixture("contestkorea_detail.html").replace("2026.09.30 ~ 2026.10.25", "2026.11.02 ~ 2026.11.16")
        raw = mod.build_raw(row, mod.parse_detail(html))
        self.assertEqual((raw["sourceStatus"], raw["registrationStartDate"], raw["deadlineDate"]), ("unknown", "2026-11-02", "2026-11-16"))

    def test_no_apply_link_falls_back_to_detail_page(self):
        mod = source("contestkorea")
        row = mod.parse_listing(fixture("contestkorea_listing.html"))[0]
        html = fixture("contestkorea_detail.html").replace("https://daker.ai/public", "javascript:void(0)//")
        raw = mod.build_raw(row, mod.parse_detail(html))
        self.assertEqual(raw["url"], raw["sourceUrl"])

    def test_spaced_region_names_are_compacted(self):
        mod = source("contestkorea")
        html = fixture("contestkorea_detail.html").replace("<td> 온라인 </td>", "<td> 서 울 </td>")
        self.assertEqual(mod.parse_detail(html)["region"], "서울")
        html = fixture("contestkorea_detail.html").replace("<td> 온라인 </td>", "<td> 서울 강남구 </td>")
        self.assertEqual(mod.parse_detail(html)["region"], "서울 강남구")

    def test_unspecified_target_stays_unverified(self):
        mod = source("contestkorea")
        row = mod.parse_listing(fixture("contestkorea_listing.html"))[0]
        html = fixture("contestkorea_detail.html").replace("누구나 , 유치원 , 초등학생 , 중학생 , 고등학생 , 대학생 , 대학원생 , 일반인 , 외국인", "해당자 ▶")
        raw = mod.build_raw(row, mod.parse_detail(html))
        self.assertEqual((raw["eligibility"], raw["eligibilityVerified"]), ("확인 필요", False))

    def test_detail_year_conflicting_with_listing_is_skipped_not_trusted(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(ck_row("202610110007", "2026 AI 플랫폼 구축 경진대회", "접수중", "09.30~10.25")),
                 mod.page_url("AI", 2): ck_page(), mod.page_url("인공지능", 1): ck_page()}
        bad = fixture("contestkorea_detail.html").replace("2026.09.30 ~ 2026.10.25", "2025.09.30 ~ 2025.10.25")
        pages[mod.detail_url("030310001", "202610110007")] = bad
        with self.assertRaises(SourceError):  # 후보 1건이 전부 거부되면 완전 성공으로 숨기지 않는다
            mod.collect(FakeFetcher(pages), NOW, None)

    def test_paging_continues_past_closed_only_pages_and_dedupes_keywords(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(ck_row("1", "AI 챌린지 하나", "접수중"), ck_row("2", "AI 챌린지 둘", "캠페인마감")),
                 mod.page_url("AI", 2): ck_page(ck_row("3", "AI 챌린지 셋", "발표보기")),
                 mod.page_url("AI", 3): ck_page(ck_row("4", "AI 챌린지 넷", "접수중")), mod.page_url("AI", 4): ck_page(),
                 mod.page_url("인공지능", 1): ck_page(ck_row("1", "AI 챌린지 하나", "접수중")), mod.page_url("인공지능", 2): ck_page()}
        pages[mod.detail_url("030310001", "1")] = fixture("contestkorea_detail.html")
        pages[mod.detail_url("030310001", "4")] = fixture("contestkorea_detail.html")
        fetcher = FakeFetcher(pages)
        result = mod.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 2)
        self.assertTrue([c for c in fetcher.calls if "page=3" in c and "Txt_word=AI" in c])  # 종료만 있던 2페이지 뒤 3페이지의 활성 항목도 읽음
        self.assertEqual(len(detail_calls(fetcher)), 2)  # 두 키워드에 모두 나온 항목은 한 번만 조회

    def test_page_and_detail_hard_caps(self):
        mod = source("contestkorea")
        pages = {}
        for p in range(1, 40):
            pages[mod.page_url("AI", p)] = ck_page(*[ck_row(f"{p:02d}{n:02d}", f"AI 대회 {p}-{n}", "접수중") for n in range(12)])
        pages[mod.page_url("인공지능", 1)] = ck_page()
        for p in range(1, 40):
            for n in range(12):
                pages[mod.detail_url("030310001", f"{p:02d}{n:02d}")] = fixture("contestkorea_detail.html")
        fetcher = FakeFetcher(pages)
        mod.collect(fetcher, NOW, None)
        listing_calls = [c for c in fetcher.calls if "list.php" in c]
        self.assertLessEqual(len(listing_calls), mod.PAGE_LIMIT + mod.PAGE_LIMIT_SECONDARY)
        self.assertLessEqual(len(detail_calls(fetcher)), mod.ITEM_LIMIT)

    def test_max_items_bounds_detail_requests(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(*[ck_row(f"{n:04d}", f"AI 대회 {n}", "접수중") for n in range(12)]),
                 mod.page_url("AI", 2): ck_page(), mod.page_url("인공지능", 1): ck_page()}
        for n in range(12):
            pages[mod.detail_url("030310001", f"{n:04d}")] = fixture("contestkorea_detail.html")
        fetcher = FakeFetcher(pages)
        self.assertEqual(len(mod.collect(fetcher, NOW, 4).items), 4)
        self.assertEqual(len(detail_calls(fetcher)), 4)

    def test_later_page_http_or_structure_error_fails_source(self):
        mod = source("contestkorea")
        base = {mod.page_url("AI", 1): ck_page(ck_row("1", "AI 챌린지", "접수중")), mod.detail_url("030310001", "1"): fixture("contestkorea_detail.html"),
                mod.page_url("인공지능", 1): ck_page()}
        with self.assertRaises(FetchError):
            mod.collect(FakeFetcher({**base, mod.page_url("AI", 2): FetchError("error", "HTTP 503")}), NOW, None)
        with self.assertRaises(StructureError):
            mod.collect(FakeFetcher({**base, mod.page_url("AI", 2): "<html>forbidden</html>"}), NOW, None)

    def test_all_detail_failures_are_source_error(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(ck_row("1", "AI 챌린지", "접수중")), mod.page_url("AI", 2): ck_page(),
                 mod.page_url("인공지능", 1): ck_page(), mod.detail_url("030310001", "1"): FetchError("error", "boom")}
        with self.assertRaises(SourceError):
            mod.collect(FakeFetcher(pages), NOW, None)

    def test_listing_end_date_conflicting_with_detail_is_skipped(self):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(ck_row("1", "AI 챌린지", "접수중", "09.30~10.31"), ck_row("2", "AI 챌린지 둘", "접수중")),
                 mod.page_url("AI", 2): ck_page(), mod.page_url("인공지능", 1): ck_page(),
                 mod.detail_url("030310001", "1"): fixture("contestkorea_detail.html"), mod.detail_url("030310001", "2"): fixture("contestkorea_detail.html")}
        result = mod.collect(FakeFetcher(pages), NOW, None)
        self.assertEqual([r["title"] for r in result.items], ["AI 챌린지 둘"])  # 목록 마감 10.31 ≠ 상세 10.25

    def test_through_real_fetcher_robots_and_redirect_guard(self):
        mod = source("contestkorea")
        routes = {"https://www.contestkorea.com/robots.txt": FakeResp(200, b"User-agent: *\nDisallow: /sub/\n")}
        fetcher, session, _ = make_fetcher(routes)
        with self.assertRaises(FetchError) as cm:
            mod.collect(fetcher, NOW, None)
        self.assertEqual(cm.exception.status, "blocked")
        self.assertFalse([c for c in session.calls if "list.php" in c])
        routes = {"https://www.contestkorea.com/robots.txt": OK_ROBOTS,
                  mod.page_url("AI", 1): FakeResp(302, b"", {"Location": "https://evil.example/x"})}
        fetcher, session, _ = make_fetcher(routes)
        with self.assertRaises(FetchError):
            mod.collect(fetcher, NOW, None)
        self.assertNotIn("https://evil.example/x", session.calls)


# ---------------------------------------------------------------- Dev-Event

class DevEventTest(unittest.TestCase):
    def collect(self, text=None, now=NOW):
        mod = source("devevent")
        return mod.collect(FakeFetcher({mod.README_URL: text if text is not None else fixture("devevent_readme.md")}), now, None)

    def by_title(self, result):
        return {r["title"]: r for r in result.items}

    def test_only_future_ai_items_from_monthly_sections(self):
        titles = set(self.by_title(self.collect()))
        self.assertEqual(titles, {
            "2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤", "[Seoul] Google Agentic AI Night", "Intel AI Summit Seoul 2026",
            "NVIDIA AI Day Seoul 2026", "항만 문제해결을 위한 AI 기술 공모전", "연말 AI 해커톤 (연도 넘김 접수)", "Cursor Hackathon Seoul 4th",
        })

    def test_excluded_reasons(self):
        titles = set(self.by_title(self.collect()))
        self.assertNotIn("AI 공격 대응 : 위협 인텔리전스 실전 활용 전략", titles)  # 접수 마감 10-08 < 오늘
        self.assertNotIn("지난 AI 밋업", titles)
        self.assertNotIn("2026 ELECCON", titles)  # AI 분류/제목 아님
        self.assertNotIn("AI 개발자 일정 미정 세미나", titles)  # 날짜 없음은 만들지 않는다
        self.assertNotIn("AI 부트캠프 수강생 모집", titles)
        self.assertNotIn("클라우드 운영 사례 세미나", titles)  # AI 태그만 있고 제목에 AI 단어가 없는 일반 세미나
        self.assertNotIn("비HTTPS AI 세미나", titles)
        self.assertNotIn("과거 기록 AI 행사", titles)  # 지난 행사 기록 섹션
        self.assertNotIn("AI 동아리 모집", titles)  # 월별 섹션이 아님

    def test_deadline_is_date_only_and_year_from_section(self):
        items = self.by_title(self.collect())
        hack = items["2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤"]
        self.assertEqual((hack["registrationStartDate"], hack["deadlineDate"], hack["deadlineAt"]), ("2026-09-21", "2026-10-13", None))
        self.assertEqual((hack["kind"], hack["mode"], hack["fee"]), ("hackathon", "hybrid", "무료"))
        self.assertIn("17:00", hack["dateNote"])  # 원문 시각은 근거로만 남기고 마감 시각으로 단정하지 않는다
        self.assertEqual(hack["sourceStatus"], "open")

    def test_year_wrap_for_registration_crossing_new_year(self):
        wrap = self.by_title(self.collect())["연말 AI 해커톤 (연도 넘김 접수)"]
        self.assertEqual((wrap["registrationStartDate"], wrap["deadlineDate"]), ("2026-12-20", "2027-01-05"))

    def test_event_date_items_have_no_deadline(self):
        night = self.by_title(self.collect())["[Seoul] Google Agentic AI Night"]
        self.assertEqual((night["startDate"], night["endDate"], night["deadlineDate"]), ("2026-10-22", "2026-10-22", None))
        self.assertEqual((night["kind"], night["mode"], night["sourceStatus"]), ("event", "offline", "unknown"))
        self.assertEqual(night["region"], "서울 강남구")
        nv = self.by_title(self.collect())["NVIDIA AI Day Seoul 2026"]
        self.assertEqual((nv["startDate"], nv["endDate"]), ("2026-11-09", "2026-11-10"))

    def test_upcoming_registration_is_not_open(self):
        intel = self.by_title(self.collect())["Intel AI Summit Seoul 2026"]
        self.assertEqual((intel["fee"], intel["sourceStatus"]), ("유료", "open"))
        later = self.collect(now=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(self.by_title(later)["Intel AI Summit Seoul 2026"]["sourceStatus"], "unknown")  # 접수 시작(09-12) 전

    def test_deadline_today_is_kept(self):
        same_day = datetime(2026, 10, 13, 14, 59, tzinfo=timezone.utc)  # 한국시간 10-13 23:59
        self.assertIn("2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤", self.by_title(self.collect(now=same_day)))
        next_day = datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc)  # 한국시간 10-14 00:00
        self.assertNotIn("2026 고용24 국민참여 AI 고용서비스 발굴 온라인 해커톤", self.by_title(self.collect(now=next_day)))

    def test_ai_tagged_hackathon_without_ai_word_in_title_is_kept(self):
        cursor = self.by_title(self.collect())["Cursor Hackathon Seoul 4th"]
        self.assertEqual((cursor["kind"], cursor["startDate"], cursor["tags"][0]), ("hackathon", "2026-10-24", "AI"))

    def test_contest_kind_and_contract(self):
        items = self.by_title(self.collect())
        self.assertEqual(items["항만 문제해결을 위한 AI 기술 공모전"]["kind"], "contest")
        for raw in items.values():
            item = rules.normalize_item(raw, "devevent", NOW_ISO)
            self.assertIsNotNone(item, raw["title"])
            self.assertEqual((raw["eligibility"], raw["eligibilityVerified"]), ("확인 필요", False))

    def test_source_url_is_the_read_readme_anchor_not_event_landing(self):
        for raw in self.collect().items:
            self.assertTrue(raw["sourceUrl"].startswith("https://github.com/brave-people/Dev-Event#"), raw["sourceUrl"])
            self.assertNotEqual(raw["sourceUrl"], raw["url"])
        self.assertEqual(self.by_title(self.collect())["Intel AI Summit Seoul 2026"]["sourceUrl"], "https://github.com/brave-people/Dev-Event#26년-11월")

    def test_explicit_foreign_offline_events_are_excluded_not_labelled_kr(self):
        self.assertNotIn("AI Builders Summit San Francisco", self.by_title(self.collect()))
        hybrid = fixture("devevent_readme.md").replace("`오프라인(미국 샌프란시스코)`", "`온라인`, `오프라인(일본 도쿄)`")
        self.assertNotIn("AI Builders Summit San Francisco", self.by_title(self.collect(hybrid)))

    def test_links_are_event_pages_not_fetched(self):
        mod = source("devevent")
        fetcher = FakeFetcher({mod.README_URL: fixture("devevent_readme.md")})
        mod.collect(fetcher, NOW, None)
        self.assertEqual(fetcher.calls, [mod.README_URL])  # 외부 행사 페이지는 읽지 않는다

    def test_structure_errors_are_not_empty_success(self):
        for bad in ("# 다른 문서\n- 항목\n", "", "<html>blocked</html>"):
            with self.assertRaises(StructureError):
                self.collect(bad)
        broken = fixture("devevent_readme.md").replace("접수:", "기간:").replace("일시:", "때:")
        with self.assertRaises(StructureError):  # 모든 항목의 날짜 줄을 못 읽으면 형식 변경이다
            self.collect(broken)

    def test_invalid_calendar_dates_are_skipped(self):
        text = fixture("devevent_readme.md").replace("10. 22(목) 14:00 ~ 10. 22(목) 16:00", "13. 45(목) 14:00 ~ 13. 45(목) 16:00")
        self.assertNotIn("[Seoul] Google Agentic AI Night", self.by_title(self.collect(text)))

    def test_real_fetcher_uses_allowlisted_host_and_respects_robots(self):
        mod = source("devevent")
        routes = {"https://raw.githubusercontent.com/robots.txt": OK_ROBOTS,
                  mod.README_URL: FakeResp(200, fixture("devevent_readme.md").encode("utf-8"))}
        fetcher, _, _ = make_fetcher(routes)
        self.assertGreater(len(mod.collect(fetcher, NOW, None).items), 3)
        routes["https://raw.githubusercontent.com/robots.txt"] = FakeResp(200, b"User-agent: *\nDisallow: /\n")
        fetcher, _, _ = make_fetcher(routes)
        with self.assertRaises(FetchError) as cm:
            mod.collect(fetcher, NOW, None)
        self.assertEqual(cm.exception.status, "blocked")


# ---------------------------------------------------------------- AI EXPO

class AiExpoTest(unittest.TestCase):
    def test_item_from_overview_table(self):
        mod = source("aiexpo")
        result = mod.collect(FakeFetcher({mod.OVERVIEW_URL: fixture("aiexpo_overview.html")}), NOW, None)
        raw = result.items[0]
        self.assertEqual(len(result.items), 1)
        self.assertEqual(raw["title"], "AI EXPO KOREA 2027 (국제인공지능대전)")
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2027-04-14", "2027-04-16"))
        self.assertEqual((raw["kind"], raw["mode"], raw["country"]), ("event", "offline", "KR"))
        self.assertIn("COEX", raw["region"])
        self.assertIsNone(raw["deadlineDate"])
        self.assertEqual((raw["sourceStatus"], raw["fee"], raw["eligibility"]), ("unknown", "확인 필요", "확인 필요"))
        self.assertIn("한국인공지능협회", raw["organizer"])
        self.assertIsNotNone(rules.normalize_item(raw, "aiexpo", NOW_ISO))

    def test_year_comes_from_page_not_constant(self):
        mod = source("aiexpo")
        html = fixture("aiexpo_overview.html").replace("2027", "2028")
        raw = mod.collect(FakeFetcher({mod.OVERVIEW_URL: html}), NOW, None).items[0]
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2028-04-14", "2028-04-16"))

    def test_cross_month_range(self):
        mod = source("aiexpo")
        html = fixture("aiexpo_overview.html").replace("4월 14일(수) ~ 16일(금)", "4월 30일(금) ~ 5월 2일(일)")
        raw = mod.collect(FakeFetcher({mod.OVERVIEW_URL: html}), NOW, None).items[0]
        self.assertEqual((raw["startDate"], raw["endDate"]), ("2027-04-30", "2027-05-02"))

    def test_missing_or_inconsistent_values_are_errors(self):
        mod = source("aiexpo")
        base = fixture("aiexpo_overview.html")
        for label, html in (
            ("no table", "<html><body><main>준비중</main></body></html>"),
            ("no year", base.replace("2027년 4월 14일", "4월 14일")),
            ("reversed", base.replace("14일(수) ~ 16일(금)", "20일(수) ~ 16일(금)")),
            ("bad day", base.replace("14일(수)", "44일(수)")),
            ("title year differs", base.replace("AI EXPO KOREA 2027", "AI EXPO KOREA 2026")),
        ):
            with self.assertRaises(StructureError, msg=label):
                mod.collect(FakeFetcher({mod.OVERVIEW_URL: html}), NOW, None)

    def test_b2b_notice_is_kept_as_note_when_page_says_so(self):
        mod = source("aiexpo")
        html = fixture("aiexpo_overview.html").replace("</main>", "<p>※ AI EXPO KOREA는 B2B 전문 AI 전시회입니다.</p></main>")
        self.assertIn("B2B", mod.collect(FakeFetcher({mod.OVERVIEW_URL: html}), NOW, None).items[0]["dateNote"])
        self.assertNotIn("B2B", mod.collect(FakeFetcher({mod.OVERVIEW_URL: fixture("aiexpo_overview.html")}), NOW, None).items[0]["dateNote"])

    def test_real_fetcher_robots_and_redirect(self):
        mod = source("aiexpo")
        routes = {"https://aiexpo.co.kr/robots.txt": FakeResp(200, b"User-agent: *\nDisallow: /\n")}
        fetcher, _, _ = make_fetcher(routes)
        with self.assertRaises(FetchError) as cm:
            mod.collect(fetcher, NOW, None)
        self.assertEqual(cm.exception.status, "blocked")
        routes = {"https://aiexpo.co.kr/robots.txt": OK_ROBOTS, mod.OVERVIEW_URL: FakeResp(302, b"", {"Location": "https://evil.example/"})}
        fetcher, session, _ = make_fetcher(routes)
        with self.assertRaises(FetchError):
            mod.collect(fetcher, NOW, None)
        self.assertNotIn("https://evil.example/", session.calls)


# ---------------------------------------------------------------- AI Summit 큰 응답

class PrefixFetchTest(unittest.TestCase):
    def big_main(self, padding_before=0, padding_after=3_000_000):
        html = fixture("aisummit.html")
        marker = "<main"
        i = html.index(marker)
        return (html[:i] + "<!--" + "x" * padding_before + "-->" + html[i:] + "<!--" + "y" * padding_after + "-->").encode("utf-8")

    def test_default_get_still_rejects_oversize_body(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS,
                                      aisummit.MAIN_URL: FakeResp(200, self.big_main())})
        with self.assertRaises(FetchError):
            fetcher.get(aisummit.MAIN_URL)

    def test_prefix_read_returns_bounded_text_without_error(self):
        body = self.big_main()
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS, aisummit.MAIN_URL: FakeResp(200, body)})
        result = fetcher.get(aisummit.MAIN_URL, prefix_bytes=1_000_000)
        self.assertLessEqual(len(result.text.encode("utf-8")), 1_000_000 + 4)
        self.assertTrue(result.truncated)
        small, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS, aisummit.MAIN_URL: FakeResp(200, b"<html>ok</html>")})
        self.assertFalse(small.get(aisummit.MAIN_URL, prefix_bytes=1_000_000).truncated)

    def test_prefix_bytes_cannot_exceed_the_size_cap(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS, aisummit.MAIN_URL: FakeResp(200, b"ok")})
        for bad in (0, -1, fetcher.max_bytes + 1):
            with self.assertRaises(ValueError):
                fetcher.get(aisummit.MAIN_URL, prefix_bytes=bad)

    def test_prefix_read_still_checks_status_robots_and_redirects(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": FakeResp(200, b"User-agent: *\nDisallow: /\n")})
        with self.assertRaises(FetchError) as cm:
            fetcher.get(aisummit.MAIN_URL, prefix_bytes=1_000_000)
        self.assertEqual(cm.exception.status, "blocked")
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS, aisummit.MAIN_URL: FakeResp(503, b"")})
        with self.assertRaises(FetchError):
            fetcher.get(aisummit.MAIN_URL, prefix_bytes=1_000_000)

    def test_aisummit_collects_from_prefix_of_a_page_over_the_size_cap(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS, aisummit.MAIN_URL: FakeResp(200, self.big_main())})
        result = aisummit.collect(fetcher, NOW, 20)
        self.assertEqual((result.items[0]["startDate"], result.items[0]["endDate"]), ("2027-08-11", "2027-08-13"))

    def test_aisummit_collects_when_main_starts_after_the_old_prefix(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS,
                                      aisummit.MAIN_URL: FakeResp(200, self.big_main(padding_before=1_500_000))})
        result = aisummit.collect(fetcher, NOW, 20)
        self.assertEqual((result.items[0]["startDate"], result.items[0]["endDate"]), ("2027-08-11", "2027-08-13"))

    def test_info_beyond_the_safe_cap_is_an_error_not_a_guess(self):
        fetcher, _, _ = make_fetcher({"https://www.aisummit.co.kr/robots.txt": OK_ROBOTS,
                                      aisummit.MAIN_URL: FakeResp(200, self.big_main(padding_before=2_600_000))})
        with self.assertRaises(StructureError):
            aisummit.collect(fetcher, NOW, 20)

    def test_other_sources_keep_the_strict_cap(self):
        mod = source("devevent")
        fetcher, _, _ = make_fetcher({"https://raw.githubusercontent.com/robots.txt": OK_ROBOTS,
                                      mod.README_URL: FakeResp(200, b"x" * 2_600_000)})
        with self.assertRaises(FetchError):
            mod.collect(fetcher, NOW, None)


# ---------------------------------------------------------------- Devpost 목록 깊이

def dp_row(i, title=None, themes=None):
    return {"id": i, "title": title or f"Build With AI {i}", "displayed_location": {"icon": "globe", "location": "Online"}, "open_state": "open",
            "url": f"https://h{i}.devpost.com/", "submission_period_dates": "Sep 22 - Oct 26, 2026",
            "themes": themes if themes is not None else [{"id": 6, "name": "Machine Learning/AI"}], "prize_amount": "", "organization_name": "Org", "invite_only": False}


def dp_page(rows, total, per_page=9):
    return json.dumps({"hackathons": rows, "meta": {"total_count": total, "per_page": per_page}})


class DevpostDepthTest(unittest.TestCase):
    def pages(self, total=23, per_page=9):
        pages, n = {}, 0
        for page in range(1, (total + per_page - 1) // per_page + 1):
            rows = [dp_row(n + k) for k in range(min(per_page, total - n))]
            n += len(rows)
            pages[devpost.page_url(page)] = dp_page(rows, total, per_page)
            for row in rows:
                pages[row["url"]] = fixture("devpost_detail_basics.html")
        return pages

    def test_later_listing_pages_are_read(self):
        fetcher = FakeFetcher(self.pages())
        result = devpost.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 20)  # 23건 중 소스 상한 20건
        self.assertIn(devpost.page_url(3), fetcher.calls)

    def test_stops_paging_once_limit_reached(self):
        fetcher = FakeFetcher(self.pages())
        devpost.collect(fetcher, NOW, 5)
        self.assertEqual([c for c in fetcher.calls if "api/hackathons" in c], [devpost.page_url(1)])
        self.assertEqual(len(fetcher.calls), 1 + 5)

    def test_page_count_is_capped(self):
        web = [{"id": 25, "name": "Web"}]  # AI 테마가 아니라 후보가 쌓이지 않는다 — 페이지 상한만 시험한다
        pages = {devpost.page_url(p): dp_page([dp_row(p * 100 + k, themes=web) for k in range(9)], 9999) for p in range(1, 12)}
        fetcher = FakeFetcher(pages)
        devpost.collect(fetcher, NOW, None)
        self.assertLessEqual(len([c for c in fetcher.calls if "api/hackathons" in c]), devpost.PAGE_LIMIT)

    def test_single_page_meta_makes_no_extra_request(self):
        fetcher = FakeFetcher({devpost.LISTING_URL: fixture("devpost_listing.json"), "https://learn-ai-basics.devpost.com/": fixture("devpost_detail_basics.html")})
        self.assertEqual(len(devpost.collect(fetcher, NOW, None).items), 1)
        self.assertEqual(len(fetcher.calls), 2)

    def test_later_page_error_fails_source(self):
        pages = self.pages()
        pages[devpost.page_url(2)] = FetchError("error", "HTTP 503")
        with self.assertRaises(FetchError):
            devpost.collect(FakeFetcher(pages), NOW, None)
        pages[devpost.page_url(2)] = "<html>blocked</html>"
        with self.assertRaises(StructureError):
            devpost.collect(FakeFetcher(pages), NOW, None)

    def test_page_url_replaces_only_the_page_parameter(self):
        self.assertEqual(devpost.page_url(1), devpost.LISTING_URL)
        self.assertTrue(devpost.page_url(3).endswith("&page=3"))
        self.assertEqual(devpost.page_url(3).count("page="), 1)


# ---------------------------------------------------------------- 위비티 목록 깊이

def wv_listing(rows):
    body = "".join(
        f'<li><div class="tit"><a href="?c=find&amp;gbn=view&amp;ix={ix}">AI 해커톤 {ix}</a></div><div class="organ">주최</div>'
        f'<div class="day">D-3<span class="dday">{status}</span></div></li>' for ix, status in rows)
    return f'<div class="list"><ul class="list"><li class="top"><div class="tit">공모전명</div></li>{body}</ul></div>'


class WevityDepthTest(unittest.TestCase):
    def pages(self, page_rows):
        pages = {}
        for n, rows in enumerate(page_rows, start=1):
            pages[wevity.page_url(n)] = wv_listing(rows)
            for ix, _ in rows:
                pages[wevity.detail_url(str(ix))] = fixture("wevity_detail.html")
        return pages

    def test_closed_rows_are_not_fetched(self):
        fetcher = FakeFetcher(self.pages([[(1, "접수중"), (2, "마감"), (3, "마감임박")], [(4, "마감"), (5, "마감")], []]))
        result = wevity.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(sorted(c.rsplit("ix=", 1)[1] for c in fetcher.calls if "gbn=view" in c), ["1", "3"])

    def test_all_closed_page_does_not_stop_later_active_pages(self):
        fetcher = FakeFetcher(self.pages([[(1, "접수중")], [(2, "마감"), (4, "마감")], [(3, "접수중")], []]))
        result = wevity.collect(fetcher, NOW, None)
        self.assertEqual(len(result.items), 2)
        self.assertIn(wevity.page_url(3), fetcher.calls)
        self.assertIn(wevity.page_url(4), fetcher.calls)  # 빈 페이지에서 멈춘다
        self.assertEqual(sorted(c.rsplit("ix=", 1)[1] for c in fetcher.calls if "gbn=view" in c), ["1", "3"])  # 종료 행 상세는 여전히 제외

    def test_repeated_page_stops(self):
        fetcher = FakeFetcher(self.pages([[(1, "접수중")], [(1, "접수중")], [(9, "접수중")]]))
        wevity.collect(fetcher, NOW, None)
        self.assertNotIn(wevity.page_url(3), fetcher.calls)

    def test_unknown_status_rows_are_still_candidates(self):
        fetcher = FakeFetcher(self.pages([[(1, "상태없음"), (2, "마감")], []]))
        self.assertEqual(len(wevity.collect(fetcher, NOW, None).items), 1)

    def test_page_cap_unchanged(self):
        pages = self.pages([[(n * 15 + k, "접수중") for k in range(15)] for n in range(9)])
        fetcher = FakeFetcher(pages)
        wevity.collect(fetcher, NOW, None)
        self.assertFalse([c for c in fetcher.calls if "gp=7" in c])


# ---------------------------------------------------------------- 교차 출처 중복

class CrossSourceDedupeTest(unittest.TestCase):
    def merged(self, *items):
        order = {"devpost": 0, "dacon": 1, "wevity": 2, "contestkorea": 3, "devevent": 4}
        return pipeline._dedupe(list(items), order)

    def item(self, source_id, n, title, **over):
        raw = {"title": title, "url": f"https://{source_id}.example.com/{n}", "sourceUrl": f"https://{source_id}.example.com/{n}", "sourceName": source_id,
               "deadlineDate": "2026-11-02", "startDate": None, "endDate": None, "country": "KR"}
        raw.update(over)
        from test_opportunities import make_raw
        item = rules.normalize_item(make_raw(**raw), source_id, "2026-10-01T00:00:00Z")
        self.assertIsNotNone(item, raw)
        return item

    def test_same_title_and_deadline_from_two_sources_keeps_earlier_source(self):
        a = self.item("dacon", 1, "항만 문제해결을 위한 AI 기술 공모전")
        b = self.item("devevent", 2, "항만 문제해결을 위한 AI 기술 공모전")
        self.assertEqual([i["sourceId"] for i in self.merged(b, a)], ["dacon"])

    def test_leading_organizer_tag_and_spacing_do_not_hide_duplicates(self):
        a = self.item("contestkorea", 1, "[데이콘] 국부펀드 KIC, AI 에이전트 공모전", organizer="데이콘")
        b = self.item("devevent", 2, "국부펀드 KIC,  AI 에이전트 공모전")
        self.assertEqual(len(self.merged(a, b)), 1)

    def test_distinct_leading_tags_are_preserved(self):
        a = self.item("contestkorea", 1, "[Track1] AI 해커톤", organizer="주최A")
        b = self.item("devevent", 2, "[Track2] AI 해커톤", organizer="주최A")
        self.assertEqual(len(self.merged(a, b)), 2)
        c = self.item("wevity", 3, "[Track1] AI 해커톤", organizer="주최A")
        self.assertEqual(len(self.merged(a, c)), 1)  # 같은 태그는 실제 중복
        d = self.item("devevent", 4, "[Track1]  AI-해커톤", organizer="주최A")
        self.assertEqual(len(self.merged(a, d)), 1)  # 공백·기호 차이는 중복

    def test_organizer_tag_is_stripped_only_when_it_equals_organizer(self):
        a = self.item("contestkorea", 1, "[데이콘] 국부펀드 AI 공모전", organizer="데이콘")
        b = self.item("devevent", 2, "국부펀드 AI 공모전", organizer="다른 주최")
        self.assertEqual(len(self.merged(a, b)), 1)
        c = self.item("devevent", 3, "[Seoul] 국부펀드 AI 공모전", organizer="다른 주최")
        self.assertEqual(len(self.merged(a, c)), 2)

    def test_same_homepage_different_events_are_kept(self):
        a = self.item("wevity", 1, "AI 공모전 가", url="https://org.example.com/", sourceUrl="https://wevity.example.com/1")
        b = self.item("contestkorea", 2, "AI 공모전 나", url="https://org.example.com/", sourceUrl="https://contestkorea.example.com/2")
        self.assertEqual(len(self.merged(a, b)), 2)

    def test_different_deadline_is_a_different_round(self):
        a = self.item("wevity", 1, "제1회 AI 아이디어 공모전")
        b = self.item("contestkorea", 2, "제1회 AI 아이디어 공모전", deadlineDate="2026-12-01")
        self.assertEqual(len(self.merged(a, b)), 2)

    def test_titles_without_any_date_are_not_merged(self):
        a = self.item("wevity", 1, "AI 아이디어 공모전", deadlineDate=None)
        b = self.item("contestkorea", 2, "AI 아이디어 공모전", deadlineDate=None)
        self.assertEqual(len(self.merged(a, b)), 2)

    def test_same_source_items_are_not_merged_by_title(self):
        a = self.item("wevity", 1, "AI 아이디어 공모전")
        b = self.item("wevity", 2, "AI 아이디어 공모전")
        self.assertEqual(len(self.merged(a, b)), 2)

    def test_event_start_date_also_identifies_a_duplicate(self):
        a = self.item("devevent", 1, "AI Day Seoul 2026", deadlineDate=None, startDate="2026-11-09", endDate="2026-11-10")
        b = self.item("devpost", 2, "AI Day Seoul 2026", deadlineDate=None, startDate="2026-11-09", endDate="2026-11-10")
        self.assertEqual([i["sourceId"] for i in self.merged(a, b)], ["devpost"])


# ---------------------------------------------------------------- 워크플로 실행 시간

class DevEventIdentityTest(unittest.TestCase):
    """DevEvent는 sourceUrl이 README 월 anchor 하나로 모이므로, 행사별 ID는 행사 landing url로 갈라야 한다(normalize만이 아니라 _collect_source·run 병합까지)."""
    def spec(self):
        mod = source("devevent")
        return mod, default_sources_spec(mod)

    def raws(self):
        mod = source("devevent")
        return mod.collect(FakeFetcher({mod.README_URL: fixture("devevent_readme.md")}), NOW, None).items

    def test_distinct_events_keep_distinct_ids_through_collect_source(self):
        mod, spec = self.spec()
        raws = self.raws()
        self.assertGreaterEqual(len({r["url"] for r in raws}), 2)
        self.assertGreaterEqual(len({r["sourceUrl"] for r in raws}), 1)
        outcome, items = pipeline._collect_source(spec, FakeFetcher({mod.README_URL: fixture("devevent_readme.md")}), NOW, NOW_ISO, None)
        self.assertEqual(outcome["status"], "ok")
        self.assertEqual(len(items), len(raws))
        self.assertEqual(len({i["id"] for i in items}), len(raws))
        self.assertTrue(all(i["sourceUrl"].startswith("https://github.com/brave-people/Dev-Event#") for i in items))

    def test_ids_survive_full_run_merge_and_are_stable_across_reruns_and_title_edits(self):
        import tempfile
        mod, spec = self.spec()
        text = fixture("devevent_readme.md")
        raws = self.raws()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "opportunities.json"
            first = pipeline.run(out, fetcher=FakeFetcher({mod.README_URL: text}), sources=[spec], now=NOW, dry_run=True)
            again = pipeline.run(out, fetcher=FakeFetcher({mod.README_URL: text}), sources=[spec], now=NOW, dry_run=True)
            edited = pipeline.run(out, fetcher=FakeFetcher({mod.README_URL: text.replace("Intel AI Summit Seoul 2026", "Intel AI Summit Seoul")}),
                                  sources=[spec], now=NOW, dry_run=True)
        ids = {i["id"] for i in first["document"]["items"]}
        self.assertEqual(len(first["document"]["items"]), len(raws))
        self.assertEqual(first["sources"][0]["itemCount"], len(raws))
        self.assertEqual(ids, {i["id"] for i in again["document"]["items"]})
        self.assertEqual(ids, {i["id"] for i in edited["document"]["items"]})

    def test_other_sources_id_rule_is_unchanged(self):
        for source_id in ("devpost", "dacon", "wevity", "contestkorea", "aiexpo"):
            raw = {"title": "AI 해커톤", "kind": "hackathon", "url": "https://a.example.com/landing", "sourceUrl": "https://dacon.io/competitions/1", "country": "KR",
                   "sourceName": source_id}
            item = rules.normalize_item(raw, source_id, NOW_ISO)
            self.assertEqual(item["id"], rules.stable_id(source_id, "https://dacon.io/competitions/1"))


def default_sources_spec(mod):
    from collectors.opportunities.sources.base import SourceSpec
    return SourceSpec(mod.SOURCE_ID, mod.SOURCE_NAME, mod.SOURCE_URL, mod.collect)


class WorkflowBudgetTest(unittest.TestCase):
    def test_collect_step_has_own_budget_inside_a_longer_job_budget(self):
        import re
        text = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
        job = int(re.search(r"^    timeout-minutes:\s*(\d+)", text, re.M)[1])
        step = int(re.search(r"^        timeout-minutes:\s*(\d+)", text, re.M)[1])
        self.assertGreaterEqual(job, 25)
        self.assertLess(step, job)
        self.assertGreaterEqual(step, 15)
        self.assertLess(text.index("id: collect"), text.index("timeout-minutes: %d" % step, text.index("steps:")))
        self.assertLess(text.index("timeout-minutes: %d" % step, text.index("steps:")), text.index("Run tests"))


# ---------------------------------------------------------------- 목록 마감 확인 전파

def wv_future_detail():
    return fixture("wevity_detail.html").replace("2026-10-10", "2026-10-30")


class ListingClosedPropagationTest(unittest.TestCase):
    """저장된 진행 항목이 목록에서 조기 마감으로 바뀌면 종료 행 상세를 다시 읽지 않고 sourceStatus만 closed로 바꾼다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "opportunities.json"

    def spec(self, mod):
        return [SourceSpec(mod.SOURCE_ID, mod.SOURCE_NAME, mod.SOURCE_URL, mod.collect)]

    def run_once(self, mod, pages, now=NOW, **kw):
        fetcher = FakeFetcher(pages)
        report = pipeline.run(self.out, fetcher=fetcher, sources=self.spec(mod), now=now, **kw)
        return report, fetcher

    def wv_pages(self, rows):
        pages = {wevity.page_url(1): wv_listing(rows), wevity.page_url(2): wv_listing([])}
        for ix, _ in rows:
            pages[wevity.detail_url(str(ix))] = wv_future_detail()
        return pages

    def ck_pages(self, rows):
        mod = source("contestkorea")
        pages = {mod.page_url("AI", 1): ck_page(*rows), mod.page_url("AI", 2): ck_page(), mod.page_url("인공지능", 1): ck_page()}
        for no in ("101", "102"):
            pages[mod.detail_url("030310001", no)] = fixture("contestkorea_detail.html")
        return pages

    def items(self):
        return {i["sourceUrl"].rsplit("=", 1)[1]: i for i in json.loads(self.out.read_text(encoding="utf-8"))["items"]}

    def test_wevity_early_closed_row_closes_stored_open_item(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중"), (2, "접수중")]))
        before = self.items()
        self.assertEqual({i["sourceStatus"] for i in before.values()}, {"open"})
        later = datetime(2026, 10, 13, 6, 0, 0, tzinfo=timezone.utc)
        report, fetcher = self.run_once(wevity, self.wv_pages([(1, "마감"), (2, "접수중")]), now=later)
        after = self.items()
        self.assertEqual(after["1"]["sourceStatus"], "closed")
        self.assertFalse(after["1"]["stale"])
        self.assertEqual({k: v for k, v in after["1"].items() if k != "sourceStatus"}, {k: v for k, v in before["1"].items() if k != "sourceStatus"})
        self.assertEqual(after["1"]["verifiedAt"], before["1"]["verifiedAt"])  # 본문을 다시 읽지 않았다
        self.assertEqual(after["2"]["sourceStatus"], "open")
        self.assertEqual(after["2"]["verifiedAt"], "2026-10-13T06:00:00Z")
        self.assertEqual([c for c in fetcher.calls if "gbn=view" in c], [wevity.detail_url("2")])  # 종료 행 상세 GET 없음
        self.assertIn("목록 마감 확인 1건", report["sources"][0]["message"])

    def test_wevity_closed_row_with_no_active_rows_still_closes(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        before = self.items()["1"]
        _, fetcher = self.run_once(wevity, self.wv_pages([(1, "마감")]))
        after = self.items()["1"]
        self.assertEqual(after["sourceStatus"], "closed")
        self.assertEqual(after["verifiedAt"], before["verifiedAt"])
        self.assertEqual(after["deadlineDate"], before["deadlineDate"])
        self.assertFalse([c for c in fetcher.calls if "gbn=view" in c])

    def test_contestkorea_early_closed_row_closes_stored_open_item(self):
        mod = source("contestkorea")
        self.run_once(mod, self.ck_pages([ck_row("101", "AI 공모전 A", "접수중"), ck_row("102", "AI 공모전 B", "접수중")]))
        before = self.items()
        self.assertEqual(before["101"]["sourceStatus"], "open")
        report, fetcher = self.run_once(mod, self.ck_pages([ck_row("101", "AI 공모전 A", "심사중"), ck_row("102", "AI 공모전 B", "접수중")]))
        after = self.items()
        self.assertEqual(after["101"]["sourceStatus"], "closed")
        self.assertFalse(after["101"]["stale"])
        self.assertEqual({k: v for k, v in after["101"].items() if k != "sourceStatus"}, {k: v for k, v in before["101"].items() if k != "sourceStatus"})
        self.assertEqual(after["102"]["sourceStatus"], "open")
        self.assertEqual([c.rsplit("str_no=", 1)[1] for c in detail_calls(fetcher)], ["102"])
        self.assertIn("목록 마감 확인 1건", report["sources"][0]["message"])

    def test_closed_row_never_stored_without_existing_item(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        self.run_once(wevity, self.wv_pages([(1, "접수중"), (7, "마감")]))
        self.assertEqual(set(self.items()), {"1"})

    def test_unobserved_vanished_open_item_only_becomes_stale(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중"), (2, "접수중")]))
        before = self.items()["2"]
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        after = self.items()["2"]
        self.assertTrue(after["stale"])
        self.assertEqual(after["sourceStatus"], "open")
        self.assertEqual({k: v for k, v in after.items() if k != "stale"}, {k: v for k, v in before.items() if k != "stale"})

    def test_closed_url_of_other_source_is_ignored(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        ck = source("contestkorea")
        self.run_once(ck, self.ck_pages([ck_row("1", "AI 공모전", "심사중")]))  # 같은 번호(1)라도 다른 출처 목록
        self.assertEqual(self.items()["1"]["sourceStatus"], "open")

    def test_non_ai_closed_row_is_not_observed(self):
        listing = wv_listing([(5, "마감")]).replace("AI 해커톤", "봉사 모집")
        result = wevity.collect(FakeFetcher({wevity.page_url(1): listing, wevity.page_url(2): wv_listing([])}), NOW, None)
        self.assertEqual(result.closed_source_urls, [])

    def test_both_adapters_observe_closed_detail_urls(self):
        w = wevity.collect(FakeFetcher({wevity.page_url(1): wv_listing([(5, "마감")]), wevity.page_url(2): wv_listing([])}), NOW, None)
        self.assertEqual(w.closed_source_urls, [wevity.detail_url("5")])
        ck = source("contestkorea")
        c = ck.collect(FakeFetcher(self.ck_pages([ck_row("101", "AI 공모전", "마감")])), NOW, None)
        self.assertEqual(c.closed_source_urls, [ck.detail_url("030310001", "101")])
        self.assertEqual(c.items, [])

    def test_max_items_zero_fetches_no_details(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        _, fetcher = self.run_once(wevity, self.wv_pages([(1, "마감")]), max_items=0)
        self.assertFalse([c for c in fetcher.calls if "gbn=view" in c])
        self.assertEqual(self.items()["1"]["sourceStatus"], "closed")  # 목록은 읽었으므로 마감 확인은 유효
        ck = source("contestkorea")
        self.assertEqual(ck.collect(FakeFetcher({}), NOW, 0).closed_source_urls, [])  # 목록을 읽지 않으면 관찰도 없음

    def test_expired_closed_item_is_not_resurrected(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        much_later = datetime(2027, 3, 1, 6, 0, 0, tzinfo=timezone.utc)  # 마감(10-30) 후 90일 초과
        self.run_once(wevity, self.wv_pages([(1, "마감")]), now=much_later)
        self.assertNotIn("1", self.items())

    def test_stored_schema_is_unchanged(self):
        self.run_once(wevity, self.wv_pages([(1, "접수중")]))
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        pipeline.validate_document(doc)
        self.assertEqual(set(doc["items"][0]), set(rules.ITEM_KEYS))


if __name__ == "__main__":
    unittest.main()
