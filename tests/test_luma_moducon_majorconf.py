"""루마 iCal·모두콘 JSON-LD·주요 AI 학회(ccfddl) 출처. 2026-11-18 실제 응답 모양을 줄여 재구성했다."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from collectors.opportunities import rules
from collectors.opportunities.errors import SourceError, StructureError
from collectors.opportunities.sources import default_sources, luma, majorconf, moducon
from collectors.opportunities.sources.ical import parse_events, parse_moment
from collectors.opportunities.urlsafe import is_fetch_allowed
from test_opportunities import FakeFetcher

NOW = datetime(2026, 11, 18, 3, 0, tzinfo=timezone.utc)  # 한국 12:00


def vevent(uid="evt-AAA111", summary="Upstage Open Stage", start="20261119T100000Z", end="20261119T130000Z",
           geo="37.503074999999995;127.02811170000001", status="TENTATIVE", slug="xqjtwhc9", body="Hosted by Upstage"):
    lines = [
        "BEGIN:VEVENT", f"DTSTART:{start}", f"DTEND:{end}",
        'ORGANIZER;CN="홍길동":MAILTO:calendar-invite@lu.ma', f"UID:{uid}@events.lu.ma", f"SUMMARY:{summary}",
        # 실제 피드처럼 DESCRIPTION이 75자 근처에서 접힌다.
        f"DESCRIPTION:Get up-to-date information at: https://luma.com/{slug}\\n\\nAd",
        f" dress:\\nAlver Coffee Gangnam\\nSeoul, South Korea\\n\\n{body}",
        "LOCATION:https://luma.com/event/" + uid,
    ]
    if geo:
        lines.append(f"GEO:{geo}")
    lines += [f"STATUS:{status}", "END:VEVENT"]
    return "\r\n".join(lines)


def calendar(*events):
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", *events, "END:VCALENDAR"])


def luma_fetcher(by_index=None, default=None):
    pages = {}
    for i, (url, _, _) in enumerate(luma.feeds()):
        pages[url] = (by_index or {}).get(i, default if default is not None else calendar())
    return FakeFetcher(pages)


UPSTAGE_INDEX = 1  # feeds()[0]은 서울 탐색 피드, [1]은 Upstage AI Events
NOTION_INDEX = 1 + [c for c, _, _ in luma.CALENDARS].index("cal-Md9x0T9gv5euc9v")


class IcalTest(unittest.TestCase):
    def test_unfold_unescape_and_params(self):
        events = parse_events(calendar(vevent()))
        self.assertEqual(len(events), 1)
        self.assertIn("Address:\nAlver Coffee Gangnam\nSeoul, South Korea", events[0]["DESCRIPTION"][0])
        self.assertEqual(events[0]["ORGANIZER"][1]["CN"], '"홍길동"')

    def test_moments(self):
        self.assertEqual(parse_moment("20261119T100000Z", {}).isoformat(), "2026-11-19T19:00:00+09:00")
        self.assertEqual(parse_moment("20261119", {"VALUE": "DATE"}).date().isoformat(), "2026-11-19")
        self.assertEqual(parse_moment("20261119T190000", {"TZID": "Asia/Seoul"}).hour, 19)
        self.assertIsNone(parse_moment("20261119T190000", {"TZID": "America/New_York"}))
        self.assertIsNone(parse_moment("garbage", {}))

    def test_not_a_calendar(self):
        with self.assertRaises(StructureError):
            parse_events("<html>blocked</html>")


class LumaTest(unittest.TestCase):
    def test_ai_calendar_accepts_title_without_ai_word(self):
        result = luma.collect(luma_fetcher({UPSTAGE_INDEX: calendar(vevent())}), NOW)
        raw = result.items[0]
        self.assertEqual(raw["title"], "Upstage Open Stage")
        self.assertEqual(raw["url"], "https://luma.com/xqjtwhc9")
        self.assertEqual((raw["startDate"], raw["country"], raw["mode"]), ("2026-11-19", "KR", "offline"))
        self.assertEqual(raw["region"], "국내 오프라인 · 서울")
        self.assertEqual(raw["organizer"], "Upstage AI Events")  # 개인 호스트 이름(ORGANIZER CN)은 저장하지 않는다
        self.assertNotIn("홍길동", str(raw))
        self.assertIsNotNone(rules.normalize_item(raw, "luma", NOW.isoformat()))

    def test_general_calendar_needs_ai_in_title_or_description(self):
        feed = calendar(vevent(uid="evt-N1", summary="Backend Meetup"), vevent(uid="evt-N2", summary="Notion Meetup", body="생성형 AI 사례 공유"))
        titles = [r["title"] for r in luma.collect(luma_fetcher({NOTION_INDEX: feed}), NOW).items]
        self.assertEqual(titles, ["Notion Meetup"])

    def test_outside_korea_past_long_and_cancelled(self):
        feed = calendar(
            vevent(uid="evt-SF", summary="AI Night SF", geo="37.7749;-122.4194"),
            vevent(uid="evt-OLD", summary="AI Past", start="20261101T100000Z", end="20261101T120000Z"),
            vevent(uid="evt-LONG", summary="AI 8주 과정", start="20261120T000000Z", end="20261231T000000Z"),
            vevent(uid="evt-CXL", summary="AI Cancelled", status="CANCELLED"),
        )
        items = luma.collect(luma_fetcher({UPSTAGE_INDEX: feed}), NOW).items
        self.assertEqual([(r["title"], r["sourceStatus"]) for r in items], [("AI Cancelled", "closed")])

    def test_korea_by_address_text_when_geo_missing(self):
        items = luma.collect(luma_fetcher({UPSTAGE_INDEX: calendar(vevent(geo=None))}), NOW).items
        self.assertEqual(len(items), 1)

    def test_same_uid_kept_once_and_seoul_feed_miss_recovered_by_ai_calendar(self):
        seoul = calendar(vevent(summary="Upstage Open Stage"))  # 서울 피드에서는 AI 단어가 없어 채택 안 됨
        result = luma.collect(luma_fetcher({0: seoul, UPSTAGE_INDEX: calendar(vevent())}), NOW)
        self.assertEqual([r["organizer"] for r in result.items], ["Upstage AI Events"])
        dup = calendar(vevent(summary="AI Open Stage"))
        result = luma.collect(luma_fetcher({0: dup, UPSTAGE_INDEX: dup}), NOW)
        self.assertEqual(len(result.items), 1)

    def test_url_falls_back_to_event_uid(self):
        feed = calendar(vevent(slug="").replace("https://luma.com/\\n", "\\n"))
        self.assertEqual(luma.collect(luma_fetcher({UPSTAGE_INDEX: feed}), NOW).items[0]["url"], "https://luma.com/event/evt-AAA111")

    def test_all_feeds_failing_is_source_error(self):
        with self.assertRaises(SourceError):
            luma.collect(FakeFetcher({}), NOW)

    def test_one_feed_failing_is_partial_with_message(self):
        fetcher = luma_fetcher({UPSTAGE_INDEX: calendar(vevent())})
        del fetcher.pages[luma.feeds()[NOTION_INDEX][0]]
        result = luma.collect(fetcher, NOW)
        self.assertEqual(len(result.items), 1)
        self.assertIn(f"피드 {len(luma.feeds())}개 중 {len(luma.feeds()) - 1}개", result.message)

    def test_only_official_ics_host(self):
        for url, _, _ in luma.feeds():
            self.assertTrue(url.startswith("https://api.lu.ma/ics/get?entity="))
            self.assertTrue(is_fetch_allowed(url))
        self.assertFalse(is_fetch_allowed("https://luma.com/seoul"))
        self.assertFalse(is_fetch_allowed("https://evil.api.lu.ma/ics/get"))


MODUCON_HTML = """<html><head><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
{"@type":"Organization","@id":"https://moducon.modulabs.co.kr/#organizer","name":"모두의연구소"},
{"@type":"Event","name":"모두콘 2026 · Deeper in AI","url":"https://moducon.modulabs.co.kr/",
"description":"모두의연구소 AI 컨퍼런스","startDate":"2026-12-12T10:00:00+09:00","endDate":"2026-12-12T18:00:00+09:00",
"eventStatus":"https://schema.org/EventScheduled","eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
"location":{"@type":"Place","name":"이화여자대학교 ECC","address":{"@type":"PostalAddress","addressRegion":"서울특별시","addressCountry":"KR"}},
"organizer":{"@id":"https://moducon.modulabs.co.kr/#organizer"}}]}</script></head><body></body></html>"""


class ModuconTest(unittest.TestCase):
    def test_reads_json_ld_event(self):
        raw = moducon.collect(FakeFetcher({moducon.MAIN_URL: MODUCON_HTML}), NOW).items[0]
        self.assertEqual((raw["title"], raw["startDate"], raw["mode"]), ("모두콘 2026 · Deeper in AI", "2026-12-12", "offline"))
        self.assertEqual(raw["organizer"], "모두의연구소")
        self.assertIsNone(raw["deadlineDate"])
        self.assertIsNotNone(rules.normalize_item(raw, "moducon", NOW.isoformat()))

    def test_missing_event_is_error(self):
        with self.assertRaises(StructureError):
            moducon.collect(FakeFetcher({moducon.MAIN_URL: "<html></html>"}), NOW)


NIPS_YML = """- title: NeurIPS
  description: Conference on Neural Information Processing Systems
  sub: AI
  rank:
    ccf: A
  confs:
    - year: 2025
      id: nips25
      link: https://neurips.cc/Conferences/2025
      timeline:
        - deadline: '2025-05-15 23:59:59'
      timezone: AoE
      date: December 3-5 (San Diego and Mexico City), 2025
      place: San Diego Convention Center, USA; Mexico City, Mexico
    - year: 2026
      id: nips26
      link: https://neurips.cc/Conferences/2026
      timeline:
        - abstract_deadline: '2026-05-05 11:59:00'
          deadline: '2026-05-07 11:59:59'
      timezone: UTC+0
      date: December 8-10 (Sydney), December 9-11 (Atlanta and Paris), 2026
      place: Sydney, Australia; Atlanta, USA; Paris, France
"""


def conf_yml(title, year, date, place, link=None):
    return (f"- title: {title}\n  description: {title} conference\n  confs:\n    - year: {year}\n"
            f"      link: {link or f'https://{title.lower()}.cc/{year}'}\n      date: '{date}'\n      place: {place}\n")


def conf_fetcher(overrides):
    pages = {majorconf.RAW.format(path=p): conf_yml("X" + p[-3:], 2020, "May 1-2, 2020", "Nowhere") for p in majorconf.CONFS}
    pages.update({majorconf.RAW.format(path=p): text for p, text in overrides.items()})
    return FakeFetcher(pages)


class MajorConfTest(unittest.TestCase):
    def test_periods(self):
        p = majorconf.parse_period
        self.assertEqual(p("December 8-10 (Sydney), December 9-11 (Atlanta and Paris), 2026", 2026), (datetime(2026, 12, 8).date(), datetime(2026, 12, 11).date()))
        self.assertEqual(p("July 6-11, 2026", 2026)[1].isoformat(), "2026-07-11")
        self.assertEqual(p("June 30 - July 4, 2027", 2027), (datetime(2027, 6, 30).date(), datetime(2027, 7, 4).date()))
        self.assertEqual(p("Feb. 16, 2027", 2027)[0].isoformat(), "2027-02-16")
        self.assertIsNone(p("December 30 - January 2, 2027", 2027))  # 연도 넘김은 추측하지 않는다
        self.assertIsNone(p("TBD", 2027))
        self.assertIsNone(p("February 30, 2027", 2027))

    def test_upcoming_overseas_conference(self):
        items = majorconf.collect(conf_fetcher({"AI/nips": NIPS_YML}), NOW).items
        self.assertEqual(len(items), 1)
        raw = items[0]
        self.assertEqual((raw["title"], raw["startDate"], raw["endDate"]), ("NeurIPS 2026", "2026-12-08", "2026-12-11"))
        self.assertEqual((raw["country"], raw["mode"]), ("GLOBAL", "offline"))
        self.assertTrue(raw["region"].startswith("해외 현장 · Sydney"))
        self.assertIsNone(raw["deadlineDate"])  # 논문 마감은 참가 신청 마감이 아니다
        item = rules.normalize_item(raw, "majorconf", NOW.isoformat())
        self.assertIsNotNone(item)
        self.assertTrue(rules.meets_contract(item))
        self.assertEqual(item["id"], rules.stable_id("majorconf", "https://neurips.cc/Conferences/2026"))  # 회차별 공식 링크가 id

    def test_korea_place_is_domestic(self):
        text = conf_yml("ICML", 2026, "December 1-3, 2026", "COEX, Seoul, South Korea")
        raw = majorconf.collect(conf_fetcher({"AI/icml": text}), NOW).items[0]
        self.assertEqual((raw["country"], raw["region"]), ("KR", "국내 오프라인 · COEX, Seoul, South Korea"))

    def test_horizon_and_unsafe_link(self):
        far = conf_yml("ICLR", 2029, "May 1-3, 2029", "Paris, France")
        bad = conf_yml("CVPR", 2027, "June 1-3, 2027", "Seattle", link="http://cvpr.example/2027")
        self.assertEqual(majorconf.collect(conf_fetcher({"AI/iclr": far, "AI/cvpr": bad}), NOW).items, [])

    def test_broken_file_counts_as_failure_and_all_failing_is_error(self):
        result = majorconf.collect(conf_fetcher({"AI/nips": "not yaml"}), NOW)
        self.assertIn(f"{len(majorconf.CONFS) - 1}곳 확인", result.message)
        with self.assertRaises(SourceError):
            majorconf.collect(FakeFetcher({}), NOW)

    def test_global_offline_exception_only_for_majorconf(self):
        raw = majorconf.build_raw("AI/nips", "NeurIPS", "d", majorconf.parse_conf_file(NIPS_YML)[2][1], NOW.date())
        self.assertIsNone(rules.normalize_item(raw, "luma", NOW.isoformat()))
        self.assertIsNone(rules.normalize_item({**raw, "mode": "online"}, "devpost", NOW.isoformat()))


class RegistryTest(unittest.TestCase):
    def test_new_sources_last_and_exact_hosts(self):
        self.assertEqual([s.id for s in default_sources()][-3:], ["moducon", "luma", "majorconf"])
        self.assertTrue(is_fetch_allowed("https://moducon.modulabs.co.kr/"))
        self.assertFalse(is_fetch_allowed("https://evil.moducon.modulabs.co.kr/"))


if __name__ == "__main__":
    unittest.main()
