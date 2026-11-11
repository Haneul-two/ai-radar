"""커뮤니티 출처는 기존 우선순위와 네트워크 경계를 유지한다."""
import unittest

from collectors.opportunities.sources import default_sources
from collectors.opportunities.urlsafe import is_fetch_allowed


class CommunityRegistryTest(unittest.TestCase):
    def test_active_sources_and_priority(self):
        self.assertEqual([s.id for s in default_sources()], [
            'devpost', 'wevity', 'aisummit', 'seocho', 'nvidia', 'aifesta',
            'contestkorea', 'devevent', 'aiexpo', 'lotteax', 'linkareer',
            'gpters', 'modulabs', 'seoulaihub',
        ])

    def test_exact_community_hosts_only(self):
        for host in ('www.gpters.org', 'www.axchallenge.com', 'modulabs.co.kr', 'biz.modulabs.co.kr', 'seoulaihub.kr', 'www.seoulaihub.kr'):
            self.assertTrue(is_fetch_allowed(f'https://{host}/'))
            self.assertFalse(is_fetch_allowed(f'https://evil.{host}/'))
            self.assertFalse(is_fetch_allowed(f'http://{host}/'))
