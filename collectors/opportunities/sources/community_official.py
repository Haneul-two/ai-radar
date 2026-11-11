"""커뮤니티에서 발견한 공식 페이지의 JSON-LD Event만 행사 정보로 사용한다."""
import json
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .. import rules
from ..errors import StructureError
from .jsonld import _nodes, _is_event, raw_from_event, read_event

# 신청 Offer의 유효기간을 접수 기간으로 확인한 공식 모집 사이트만 허용한다.
REGISTRATION_OFFER_HOSTS = {'www.axchallenge.com'}


def parse_official_event(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    for tag in soup.find_all('script', type='application/ld+json'):
        try:
            events.extend(n for n in _nodes(json.loads(tag.get_text())) if _is_event(n))
        except ValueError as exc:
            raise StructureError('공식 행사 JSON-LD 해석 실패') from exc
    if len(events) != 1:
        raise StructureError('공식 페이지에서 단일 행사를 확인하지 못함')
    event = events[0]
    location = event.get('location')
    location = location[0] if isinstance(location, list) and len(location) == 1 else location
    address = location.get('address') if isinstance(location, dict) else None
    country = address.get('addressCountry') if isinstance(address, dict) else None
    if isinstance(country, dict):
        country = country.get('name')
    if country != 'KR':
        raise StructureError('공식 페이지에서 국내 참가 장소를 확인하지 못함')
    data = read_event(html, '공식 행사')
    if not data['organizer'] or not rules.is_ai_related(data['name'], description=data['description']):
        raise StructureError('공식 페이지에서 AI 관련 행사·주최를 확인하지 못함')
    kind = rules.classify_kind(data['name'], 'event')
    if kind is None:
        raise StructureError('수집 대상이 아닌 교육·채용 안내')
    raw = raw_from_event(data, data['organizer'], url, [], '참가 조건은 공식 페이지에서 확인 필요', kind=kind)
    if urlsplit(url).hostname in REGISTRATION_OFFER_HOSTS:
        offers = list(_nodes(event.get('offers')))
        deadlines = {o.get('validThrough') for o in offers if isinstance(o.get('validThrough'), str)}
        starts = {o.get('validFrom') for o in offers if isinstance(o.get('validFrom'), str)}
        if len(deadlines) == 1:
            deadline = deadlines.pop()
            if rules.parse_iso_datetime(deadline):
                raw['deadlineAt'] = deadline
                raw['deadlineDate'] = rules.seoul_date_from_iso(deadline)
            else:
                raw['deadlineDate'] = rules.parse_date(deadline)
        if len(starts) == 1:
            raw['registrationStartDate'] = rules.parse_date(starts.pop())
        if raw['deadlineDate'] and raw['deadlineDate'] > raw['endDate']:
            raise StructureError('공식 접수 마감이 행사 종료일보다 늦음')
    for key in ('title', 'description', 'organizer', 'region', 'dateNote'):
        if raw.get(key):
            raw[key] = rules.mask_contacts(raw[key])
    return raw
