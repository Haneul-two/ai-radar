"""서울 AI 허브 공개 공지. 공식 발췌 fixture와 경계 조건 합성 HTML만 사용한다."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from collectors.opportunities import rules
from collectors.opportunities.errors import FetchError, SourceError, StructureError
from collectors.opportunities.sources import seoulaihub as source
from test_opportunities import FakeFetcher, fixture

NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)
TITLE = '[AI SEOUL FELLOW 런치톡] 5회차 강연 안내 - 영상을 이해하는 VLM'
POST_ID = '00000001702026000059'


def listing(rows):
    return '<form name="actForm"><ul class="faq_board_sty03 faq_board_sty03_tit"><li>제목</li></ul>' + ''.join(
        f'''<ul class="faq_board_sty03"><li>1</li><li onclick="javascript:goDetail('{key}','bd_num');"><p>{title}</p></li><li>2026-11-04</li></ul>'''
        for key, title in rows) + '</form>'


class SeoulAiHubTest(unittest.TestCase):
    def test_deadline_time_range_uses_end_time(self):
        self.assertEqual(source._deadline('2026-11-23 09:00 ~ 18:00'), ('2026-11-23', '2026-11-23T18:00:00+09:00'))

    def test_ambiguous_meridiem_and_overnight_ranges_do_not_guess(self):
        self.assertEqual(source._deadline('2026-11-23 오후 2시 ~ 6시'), ('2026-11-23', None))
        self.assertEqual(source._deadline('2026-11-23 23:00 ~ 01:00'), ('2026-11-23', None))
        self.assertEqual(source._deadline('2026-11-23 오후 2시 ~ 오후 6시'), ('2026-11-23', '2026-11-23T18:00:00+09:00'))

    def test_hyphenated_abbreviated_date_range_is_not_single_day(self):
        self.assertEqual(source._dates('2026-11-25 - 11/26'), (None, None))

    def test_company_affiliation_alone_is_not_individual_participation(self):
        html = fixture('seoulaihub_detail.html').replace('서울 AI 허브 입주·멤버십 기업 대표 및 엔지니어, AI에 관심 있는 일반 시민', '서울 AI 허브 입주기업 소속 엔지니어')
        self.assertIsNone(source.parse_detail(html, source.detail_url(POST_ID)))

    def test_official_detail_event_and_deadline_are_separate(self):
        raw = source.parse_detail(fixture('seoulaihub_detail.html'), source.detail_url(POST_ID))
        self.assertEqual(raw['title'], TITLE)
        self.assertEqual((raw['startDate'], raw['endDate']), ('2026-11-25', '2026-11-25'))
        self.assertEqual(raw['deadlineDate'], '2026-11-23')
        self.assertEqual(raw['deadlineAt'], '2026-11-23T18:00:00+09:00')
        self.assertEqual(raw['sourceStatus'], 'unknown')
        self.assertTrue(raw['eligibilityVerified'])
        self.assertIn('일반 시민', raw['eligibility'])
        self.assertEqual(raw['mode'], 'unknown')  # 온라인 추론/신청은 온라인 행사가 아니다.
        item = rules.normalize_item(raw, source.SOURCE_ID, NOW.isoformat())
        self.assertIsNotNone(item)
        rules.validate_item(item)

    def test_no_year_in_event_never_uses_publication_or_current_year(self):
        html = fixture('seoulaihub_detail.html').replace('2026년 11월 25일', '11월 25일')
        self.assertIsNone(source.parse_detail(html, source.detail_url(POST_ID)))

    def test_missing_deadline_is_unknown_not_event_day(self):
        html = fixture('seoulaihub_detail.html').replace('신청 마감:', '문의:')
        raw = source.parse_detail(html, source.detail_url(POST_ID))
        self.assertIsNone(raw['deadlineDate'])
        self.assertIsNone(raw['deadlineAt'])
        self.assertEqual(raw['sourceStatus'], 'unknown')

    def test_listing_includes_lecture_but_rejects_business_and_training(self):
        excluded = ['AI 세미나 참가기업 모집', 'AI EXPO 전시 부스 기업모집', 'AI 입주기업 모집',
                    'AI 지원금 사업', 'AI 장기 교육생 모집', 'AI 채용 세미나', 'AI 교육과정 모집']
        rows = source.parse_listing(listing([(POST_ID, TITLE), *[(str(i), t) for i, t in enumerate(excluded)]]))
        self.assertEqual(rows, [{'id': POST_ID, 'title': TITLE}])

    def test_detail_requires_individual_participation_and_event_title(self):
        html = fixture('seoulaihub_detail.html')
        self.assertIsNone(source.parse_detail(html.replace('서울 AI 허브 입주·멤버십 기업 대표 및 엔지니어, AI에 관심 있는 일반 시민', '선정된 입주기업만'), source.detail_url(POST_ID)))
        self.assertIsNone(source.parse_detail(html.replace(TITLE, 'AI 공동관 참가기업 모집'), source.detail_url(POST_ID)))

    def test_body_only_and_contacts_masked(self):
        # 합성 연락처도 문자열 조합으로 생성한다. fixture에는 연락처가 없다.
        contact = 'tester' + '@' + 'example.invalid'
        html = fixture('seoulaihub_detail.html').replace('일반 시민', '일반 시민 ' + contact)
        raw = source.parse_detail(html + '<footer>일시: 2030년 1월 1일</footer>', source.detail_url(POST_ID))
        self.assertNotIn(contact, str(raw))
        self.assertIn(rules.CONTACT_PLACEHOLDER, raw['eligibility'])
        self.assertEqual(raw['startDate'], '2026-11-25')

    def test_broken_structure_raises_but_empty_listing_is_valid(self):
        with self.assertRaises(StructureError):
            source.parse_listing('<html>maintenance</html>')
        self.assertEqual(source.parse_listing(listing([])), [])
        with self.assertRaises(StructureError):
            source.parse_detail('<html>maintenance</html>', source.detail_url(POST_ID))

    def test_collect_deduplicates_pinned_posts_and_reads_at_most_three_pages(self):
        pages = {source.page_url(n): listing([(POST_ID, TITLE), (str(n), '지원사업')]) for n in range(1, 4)}
        pages[source.detail_url(POST_ID)] = fixture('seoulaihub_detail.html')
        fetcher = FakeFetcher(pages)
        result = source.collect(fetcher, NOW)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(fetcher.calls.count(source.detail_url(POST_ID)), 1)
        self.assertLessEqual(sum('board_list.asp' in c for c in fetcher.calls), 3)

    def test_caps_zero_and_twenty(self):
        f = FakeFetcher({})
        self.assertEqual(source.collect(f, NOW, 0).items, [])
        self.assertEqual(f.calls, [])
        rows = [(str(i), TITLE) for i in range(40)]
        pages = {source.page_url(1): listing(rows)}
        pages.update({source.detail_url(str(i)): fixture('seoulaihub_detail.html') for i in range(40)})
        f = FakeFetcher(pages)
        self.assertEqual(len(source.collect(f, NOW, 999).items), 20)
        self.assertEqual(len(f.calls), 21)

    def test_non_event_page_does_not_hide_later_event(self):
        pages = {
            source.page_url(1): listing([('1', 'AI 지원사업')]),
            source.page_url(2): listing([('2', 'AI 기업 모집')]),
            source.page_url(3): listing([(POST_ID, TITLE)]),
            source.detail_url(POST_ID): fixture('seoulaihub_detail.html'),
        }
        self.assertEqual(len(source.collect(FakeFetcher(pages), NOW).items), 1)

    def test_same_post_twice_on_one_page_is_fetched_once(self):
        pages = {source.page_url(1): listing([(POST_ID, TITLE), (POST_ID, TITLE)]),
                 source.detail_url(POST_ID): fixture('seoulaihub_detail.html')}
        fetcher = FakeFetcher(pages)
        self.assertEqual(len(source.collect(fetcher, NOW, 1).items), 1)
        self.assertEqual(fetcher.calls.count(source.detail_url(POST_ID)), 1)

    def test_all_detail_failures_and_later_listing_error_propagate(self):
        pages = {source.page_url(1): listing([(POST_ID, TITLE)]), source.page_url(2): listing([])}
        with self.assertRaises(SourceError):
            source.collect(FakeFetcher(pages), NOW)
        pages[source.page_url(2)] = FetchError('error', '503')
        with self.assertRaises(FetchError):
            source.collect(FakeFetcher(pages), NOW)

    def test_fixture_has_no_contacts(self):
        html = fixture('seoulaihub_detail.html')
        self.assertEqual(rules.mask_contacts(html), html)

    def test_menu_number_stays_four_while_board_page_changes(self):
        for page in range(1, 4):
            query = parse_qs(urlsplit(source.page_url(page)).query)
            self.assertEqual(query['pageNum'], ['4'])
            self.assertEqual(query.get('page', ['1']), [str(page)])

    def test_original_event_year_is_kept_and_invalid_dates_are_rejected(self):
        html = fixture('seoulaihub_detail.html')
        raw = source.parse_detail(html.replace('2026년 11월 25일', '2025년 11월 25일'), source.detail_url(POST_ID))
        self.assertEqual(raw['startDate'], '2025-11-25')
        self.assertIsNone(source.parse_detail(html.replace('2026년 11월 25일', '2026년 2월 30일'), source.detail_url(POST_ID)))

    def test_full_year_range_and_date_only_deadline(self):
        html = fixture('seoulaihub_detail.html').replace('2026년 11월 25일(수) 오전 11시 30분 ~ 오후 1시',
                                                         '2026년 12월 31일 ~ 2027년 1월 1일')
        html = html.replace('2026년 11월 23일(월) 오후 6시까지', '2026년 11월 23일')
        raw = source.parse_detail(html, source.detail_url(POST_ID))
        self.assertEqual((raw['startDate'], raw['endDate']), ('2026-12-31', '2027-01-01'))
        self.assertEqual(raw['deadlineDate'], '2026-11-23')
        self.assertIsNone(raw['deadlineAt'])

    def test_three_pages_without_events_and_all_three_pages_are_distinct(self):
        pages = {source.page_url(n): listing([(str(n), 'AI 지원사업')]) for n in range(1, 4)}
        fetcher = FakeFetcher(pages)
        self.assertEqual(source.collect(fetcher, NOW).items, [])
        self.assertEqual(fetcher.calls, [source.page_url(n) for n in range(1, 4)])

    def test_date_range_without_full_year_or_supported_end_is_not_single_day(self):
        html = fixture('seoulaihub_detail.html').replace('2026년 11월 25일(수) 오전 11시 30분 ~ 오후 1시',
                                                         '2026-11-25 ~ 11/26')
        self.assertIsNone(source.parse_detail(html, source.detail_url(POST_ID)))


if __name__ == '__main__':
    unittest.main()
