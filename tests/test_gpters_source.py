"""지피터스는 발견에만 쓰고 공식 행사 페이지에서 확인한다."""
import json
import unittest
from datetime import datetime, timezone

from collectors.opportunities.errors import FetchError, SourceError, StructureError
from collectors.opportunities.sources import gpters
from collectors.opportunities.sources.community_official import parse_official_event

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)
POST = 'https://www.gpters.org/newsletter/post/example'
OFFICIAL = 'https://www.axchallenge.com/'


def official(**overrides):
    event = {'@type': 'Event', 'name': '2026 AI 방탈출 해커톤',
             'description': 'AI로 문제를 푸는 행사', 'startDate': '2026-11-13T15:00:00+09:00',
             'endDate': '2026-11-14T17:30:00+09:00', 'organizer': {'name': '주최기관'},
             'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
             'location': {'name': '행사장', 'address': {'addressCountry': 'KR'}},
             'offers': {'price': '0', 'validFrom': '2026-10-28', 'validThrough': '2026-11-09T23:30:00+09:00'},
             **overrides}
    return '<script type="application/ld+json">' + json.dumps(event) + '</script>'


class FakeFetcher:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url):
        from types import SimpleNamespace
        self.calls.append(url)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return SimpleNamespace(text=page, url=url)


class GptersTest(unittest.TestCase):
    def sitemap(self, url=POST, date='2026-11-09T00:00:00Z'):
        return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{url}</loc><lastmod>{date}</lastmod></url></urlset>'

    def test_sitemap_accepts_only_recent_public_newsletters(self):
        self.assertEqual(gpters.parse_sitemap(self.sitemap(), NOW), [POST])
        self.assertEqual(gpters.parse_sitemap(self.sitemap('https://evil.example/newsletter/post/a'), NOW), [])
        self.assertEqual(gpters.parse_sitemap(self.sitemap(date='2024-01-01T00:00:00Z'), NOW), [])
        with self.assertRaises(StructureError):
            gpters.parse_sitemap('<html>점검</html>', NOW)

    def test_candidate_links_come_from_article_and_strip_tracking(self):
        html = '<a href="https://evil.example">행사 신청</a><article class="prose"><a href="https://www.axchallenge.com/?utm_source=gpters">AX Challenge 신청하기</a><a href="https://www.axchallenge.com/">행사 참가</a></article>'
        self.assertEqual(gpters.discover_links(html), [OFFICIAL])

    def test_official_page_is_source_and_deadline_is_not_event_date(self):
        pages = {gpters.SITEMAP_URL: self.sitemap(), POST: f'<article class="prose"><a href="{OFFICIAL}">AI 행사 신청</a></article>', OFFICIAL: official()}
        fetcher = FakeFetcher(pages)
        result = gpters.collect(fetcher, NOW, 1)
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item['sourceUrl'], OFFICIAL)
        self.assertEqual(item['deadlineDate'], '2026-11-09')
        self.assertEqual(item['startDate'], '2026-11-13')
        self.assertIn(POST, item['dateNote'])
        self.assertNotIn('https://event-us.kr/', fetcher.calls)

    def test_unknown_host_is_not_fetched_or_accepted(self):
        fetcher = FakeFetcher({gpters.SITEMAP_URL: self.sitemap(), POST: '<article class="prose"><a href="https://unknown.example/">AI 행사 신청</a></article>'})
        result = gpters.collect(fetcher, NOW)
        self.assertEqual(result.items, [])
        self.assertEqual(fetcher.calls, [gpters.SITEMAP_URL, POST])
        self.assertIn('미지원 공식 호스트 1건', result.message)

    def test_all_official_fetches_failing_is_not_empty_success(self):
        fetcher = FakeFetcher({gpters.SITEMAP_URL: self.sitemap(), POST: f'<article class="prose"><a href="{OFFICIAL}">AI 행사 신청</a></article>', OFFICIAL: FetchError('blocked', 'robots 차단')})
        with self.assertRaises(SourceError):
            gpters.collect(fetcher, NOW)

    def test_missing_article_is_structure_error(self):
        with self.assertRaises(StructureError):
            gpters.discover_links('<html>로그인이 필요합니다</html>')


class OfficialTest(unittest.TestCase):
    def test_unknown_country_and_non_ai_are_not_inferred(self):
        for html in (official(location={'name': '어딘가'}), official(name='사진 세미나', description='사진 이야기')):
            with self.assertRaises(StructureError):
                parse_official_event(html, OFFICIAL)

    def test_conflicting_offer_deadlines_remain_unknown(self):
        item = parse_official_event(official(offers=[{'validThrough': '2026-11-09'}, {'validThrough': '2026-11-10'}]), OFFICIAL)
        self.assertIsNone(item['deadlineDate'])

    def test_contacts_are_masked_before_return(self):
        item = parse_official_event(official(description='AI 행사 contact@example.org 010-1234-5678'), OFFICIAL)
        self.assertNotIn('contact@example.org', item['description'])
        self.assertNotIn('010-1234-5678', item['description'])
