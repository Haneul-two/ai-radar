"""지피터스 공개 뉴스레터에서 행사를 발견하고 허용된 공식 페이지로 확인한다."""
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .. import rules
from ..errors import FetchError, StructureError
from ..urlsafe import canonical_url, is_fetch_allowed, is_safe_https_url
from .base import CollectResult, effective_limit, fail_if_every_fetch_failed
from .community_official import parse_official_event

SOURCE_ID = 'gpters'
SOURCE_NAME = '지피터스·공식 확인'
SOURCE_URL = 'https://www.gpters.org/newsletter'
SITEMAP_URL = 'https://www.gpters.org/sitemap.xml'  # 옛 /newsletter/sitemap.xml은 2026-11-23부터 여기로 308 이동
CHILD_SITEMAP_LIMIT = 40  # 2026-11-24 실측 21개
POST_LIMIT = 8
OFFICIAL_LIMIT = 10
LOOKBACK_DAYS = 60
OFFICIAL_HOSTS = {'www.axchallenge.com', 'modulabs.co.kr', 'seoulaihub.kr', 'www.seoulaihub.kr',
                  'www.aifesta.kr', 'aifesta.kr', 'www.aisummit.co.kr', 'www.nvidia.com', 'aiexpo.co.kr', 'lotteaxchallenge.com'}
_NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
_SITEMAP = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
_EVENT_LINK = re.compile(r'신청|참가|등록|행사|밋업|해커톤|세미나|챌린지|challenge|meetup|conference|summit', re.I)


def _xml_root(text):
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise StructureError('지피터스 뉴스레터 sitemap 해석 실패') from exc


def _is_gpters(url, path_prefix):
    parts = urlsplit(url)
    return (is_safe_https_url(url) and parts.hostname == 'www.gpters.org'
            and parts.path.startswith(path_prefix) and not parts.query)


def _newsletter_rows(root):
    """urlset에서 (lastmod, 뉴스레터 글 URL)을 모두 꺼낸다. 기간 필터는 parse_sitemap이 한다."""
    if root.tag != _SITEMAP + 'urlset':
        raise StructureError('지피터스 뉴스레터 sitemap 구조가 다름')
    rows = []
    for node in root.findall('s:url', _NS):
        url = node.findtext('s:loc', '', _NS)
        if _is_gpters(url, '/newsletter/post/'):
            rows.append((rules.parse_iso_datetime(node.findtext('s:lastmod', '', _NS)), url))
    return rows


def _latest(rows, now):
    recent = [(stamp, url) for stamp, url in rows if stamp and now - timedelta(days=LOOKBACK_DAYS) <= stamp <= now]
    return list(dict.fromkeys(url for _, url in sorted(recent, reverse=True)))[:POST_LIMIT]


def parse_sitemap(text, now):
    return _latest(_newsletter_rows(_xml_root(text)), now)


def parse_sitemap_index(root):
    """사이트 전체 색인에서 같은 호스트의 하위 sitemap 주소만 받는다."""
    children = [node.findtext('s:loc', '', _NS) for node in root.findall('s:sitemap', _NS)]
    children = list(dict.fromkeys(url for url in children if _is_gpters(url, '/sitemap/') and url.endswith('.xml')))
    if not children or len(children) > CHILD_SITEMAP_LIMIT:
        raise StructureError(f'지피터스 sitemap 색인의 하위 파일 수가 예상과 다름({len(children)}개)')
    return children


def fetch_posts(fetcher, now):
    root = _xml_root(fetcher.get(SITEMAP_URL).text)
    if root.tag != _SITEMAP + 'sitemapindex':
        return _latest(_newsletter_rows(root), now)
    # 2026-11-23부터 뉴스레터 글이 사이트 전체 sitemap 하위 파일에 흩어져 있다. 하나라도 못 읽으면 실패로 둔다.
    rows = []
    for child in parse_sitemap_index(root):
        rows.extend(_newsletter_rows(_xml_root(fetcher.get(child).text)))
    if not rows:
        raise StructureError('지피터스 sitemap 색인에서 뉴스레터 글을 찾지 못함')
    return _latest(rows, now)


def discover_links(html):
    # 2026-11-23부터 본문이 article 바로가 아니라 그 안의 div.prose다. 머리글·댓글 링크는 보지 않는다.
    article = BeautifulSoup(html, 'html.parser').select_one('article.prose, article .prose')
    if article is None:
        raise StructureError('지피터스 공개 글 본문을 확인하지 못함')
    links = []
    for a in article.select('a[href]'):
        url = a.get('href', '')
        if is_safe_https_url(url) and _EVENT_LINK.search(a.get_text(' ', strip=True)):
            if urlsplit(url).hostname not in {'www.gpters.org', 'gpters.org'}:
                links.append(canonical_url(url))
    return list(dict.fromkeys(links))


def collect(fetcher, now, max_items=None):
    posts = fetch_posts(fetcher, now)
    candidates, failures, post_failures = {}, [], []
    for post in posts:
        try:
            for url in discover_links(fetcher.get(post).text):
                candidates.setdefault(url, post)
        except (FetchError, StructureError) as exc:
            post_failures.append(exc)
    # 목록 일부를 못 읽었다면 기존 자료를 보존하고 다음 수집에서 다시 확인한다.
    if post_failures:
        raise post_failures[0]
    supported = [(url, post) for url, post in candidates.items()
                 if urlsplit(url).hostname in OFFICIAL_HOSTS and is_fetch_allowed(url)]
    unsupported = len(candidates) - len(supported)
    limit = min(effective_limit(max_items), OFFICIAL_LIMIT)
    items = []
    for url, post in supported[:limit]:
        try:
            page = fetcher.get(url)
            if urlsplit(page.url).hostname not in OFFICIAL_HOSTS:
                raise StructureError('공식 확인 페이지가 승인된 호스트 밖으로 이동함')
            raw = parse_official_event(page.text, page.url)
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        raw['sourceName'] = SOURCE_NAME
        raw['dateNote'] += f'. 지피터스에서 발견: {post}. 일정·조건은 공식 페이지 기준'
        items.append(raw)
    fail_if_every_fetch_failed(min(len(supported), limit), failures, '지피터스 공식 확인')
    return CollectResult(items, f'뉴스레터 {len(posts)}건, 공식 확인 {len(items)}건, 미지원 공식 호스트 {unsupported}건, 공식 조회·검증 실패 {len(failures)}건')
