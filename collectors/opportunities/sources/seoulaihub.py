"""서울 AI 허브 공개 공지 목록과 공식 상세. 신청폼·이미지·첨부파일은 조회하지 않는다."""
import re
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .. import rules
from ..errors import FetchError, StructureError
from .base import CollectResult, domestic_region, effective_limit, fail_if_every_fetch_failed

SOURCE_ID = 'seoulaihub'
SOURCE_NAME = '서울 AI 허브'
_BASE = 'https://seoulaihub.kr/board/board_basic/'
_QUERY = {'scrID': '0000000170', 'pageNum': '4', 'subNum': '1', 'ssubNum': '1'}
SOURCE_URL = _BASE + 'board_list.asp?' + urlencode(_QUERY)
PAGE_LIMIT = 3
ITEM_LIMIT = 20
_POST_RE = re.compile(r"goDetail\('([0-9]+)'\s*,\s*'bd_num'\)")
_EVENT_RE = re.compile(r'행사|세미나|밋업|포럼|컨퍼런스|콘퍼런스|웨비나|런치톡|강연|성과공유회|토론회|meetup|seminar|conference|forum|webinar', re.I)
_EXCLUDE_RE = re.compile(r'참[가여]\s*기업\s*모집|기업\s*모집|입주\s*기업|지원금|지원사업|부스|공동관.*모집|교육생|수강생|부트캠프|교육과정|장기\s*교육|채용|인턴\s*모집')
_INDIVIDUAL_RE = re.compile(r'시민|누구나|일반인|개인|일반\s*참가자|관심\s*있는\s*(?:분|사람)')
_DATE_RE = re.compile(r'(20\d{2})\s*(?:년|[-./])\s*(\d{1,2})\s*(?:월|[-./])\s*(\d{1,2})\s*일?')
_TIME_RE = re.compile(r'(오전|오후)?\s*(\d{1,2})\s*(?:시|:)\s*(?:(\d{1,2})\s*분?)?')


def page_url(page):
    return SOURCE_URL if page == 1 else SOURCE_URL + '&page=' + str(page)


def detail_url(post_id):
    if not re.fullmatch(r'[0-9]+', str(post_id)):
        raise ValueError('서울 AI 허브 게시글 번호는 숫자여야 함')
    return _BASE + 'board_detail.asp?' + urlencode({**_QUERY, 'bd_num': post_id, 'act': 'view'})


def _candidate(title):
    # 입주기업도 참가 가능한 시민 행사와 기업 모집 공고를 구분한다.
    return bool(rules.is_ai_related(title) and _EVENT_RE.search(title) and not _EXCLUDE_RE.search(title))


def parse_listing(text, candidates_only=True):
    soup = BeautifulSoup(text, 'html.parser')
    form = soup.select_one('form[name="actForm"]')
    if form is None or form.select_one('.faq_board_sty03') is None:
        raise StructureError('서울 AI 허브 공지 목록 구조가 없음')
    rows = []
    for node in form.select('.faq_board_sty03 [onclick]'):
        match = _POST_RE.search(node.get('onclick', ''))
        if not match:
            raise StructureError('서울 AI 허브 게시글 이동 번호를 읽지 못함')
        title = rules.mask_contacts(rules.clean_text(node.get_text(' ', strip=True)))
        if not title:
            raise StructureError('서울 AI 허브 공지 제목이 없음')
        if not candidates_only or _candidate(title):
            rows.append({'id': match[1], 'title': title})
    return rows


def _field(lines, labels):
    pattern = re.compile(r'^\s*[*○■●·\-]*\s*(?:' + labels + r')\s*[:：]\s*(.+)$')
    for line in lines:
        match = pattern.match(line)
        if match:
            return match[1].strip()
    return ''


def _dates(text):
    # 게시일·현재 연도는 행사 연도로 사용하지 않는다.
    matches = list(_DATE_RE.finditer(text))
    if not matches:
        return None, None
    start = rules.parse_date('-'.join(matches[0].groups()))
    end = rules.parse_date('-'.join(matches[1].groups())) if len(matches) > 1 else start
    # 축약된 날짜 범위의 끝을 하루짜리 행사로 잘못 저장하지 않는다.
    tail = text[matches[0].end():]
    range_end = re.search(r'[~～∼–—-]\s*(.*)', tail)
    if len(matches) == 1 and range_end and re.match(r'\d', range_end[1]) and not _TIME_RE.match(range_end[1]):
        return None, None
    if not start or not end or end < start:
        return None, None
    return start, end


def _deadline(text):
    start, end = _dates(text)
    matches = list(_DATE_RE.finditer(text))
    if not end or not matches:
        return None, None
    tail = text[matches[-1].end():]
    clocks = list(_TIME_RE.finditer(tail))
    if not clocks:
        return end, None
    clock = clocks[-1]  # 같은 날의 시간 범위는 시작이 아니라 끝이 접수 마감이다.
    if len(clocks) > 1 and not clock[1] and any(c[1] for c in clocks[:-1]):
        return end, None  # '오후 2시 ~ 6시'의 끝 시각을 오전으로 확정하지 않는다.
    hour, minute = int(clock[2]), int(clock[3] or 0)
    if minute > 59 or hour > 23 or (clock[1] and not 1 <= hour <= 12):
        return end, None
    if clock[1]:
        hour = hour % 12 + (12 if clock[1] == '오후' else 0)
    if len(clocks) > 1:
        first = clocks[0]
        first_hour = int(first[2])
        if first[1]:
            first_hour = first_hour % 12 + (12 if first[1] == '오후' else 0)
        if (hour, minute) < (first_hour, int(first[3] or 0)):
            return end, None  # 다음 날로 넘어가는지 확인할 수 없는 범위는 날짜만 남긴다.
    return end, datetime.fromisoformat(end).replace(hour=hour, minute=minute, tzinfo=rules.SEOUL).isoformat()


def parse_detail(text, url):
    soup = BeautifulSoup(text, 'html.parser')
    heading = soup.select_one('.board_view_sty01 .pro_tit p')
    body = soup.select_one('.board_view_sty01 .pro_con')
    if heading is None or body is None:
        raise StructureError('서울 AI 허브 공지 상세 제목·본문이 없음')
    title = rules.mask_contacts(rules.clean_text(heading.get_text(' ', strip=True)))
    if not _candidate(title):
        return None
    for node in body.select('script, style'):
        node.decompose()
    for node in body.select('br'):
        node.replace_with('\n')
    for node in body.select('li, p, tr'):
        node.insert_after('\n')
    lines = [rules.mask_contacts(rules.clean_text(line)) for line in body.get_text(' ').splitlines()]
    target = _field(lines, r'참가\s*대상|참여\s*대상|모집\s*대상|대상')
    if not _INDIVIDUAL_RE.search(target) or re.search(r'기업만|기업\s*한정|초청자만|초청\s*전용', target):
        return None
    start, end = _dates(_field(lines, r'행사\s*일시|개최\s*일시|강연\s*일시|일시|행사\s*일정|행사\s*기간'))
    if not start:
        return None  # 날짜가 포스터에만 있거나 연도를 확인할 수 없으면 저장하지 않는다.
    deadline, deadline_at = _deadline(_field(lines, r'신청\s*마감|접수\s*마감|신청\s*기간|접수\s*기간'))
    reg_start, _ = _dates(_field(lines, r'신청\s*기간|접수\s*기간'))
    venue = _field(lines, r'행사\s*장소|장소')
    online = bool(re.search(r'온라인|비대면|줌|zoom', venue, re.I))
    offline = bool(re.search(r'오프라인|서울|센터|층|회의실', venue))
    mode = 'hybrid' if online and offline else 'online' if online else 'offline' if offline else 'unknown'
    return {
        'kind': 'event', 'title': title, 'organizer': SOURCE_NAME,
        'description': rules.shorten(title + '. ' + _field(lines, r'프로그램|주제')),
        'tags': ['AI'], 'mode': mode, 'region': domestic_region(mode), 'country': 'KR',
        'startDate': start, 'endDate': end, 'registrationStartDate': reg_start,
        'deadlineDate': deadline, 'deadlineAt': deadline_at,
        'eligibility': target, 'eligibilityVerified': True,
        'fee': _field(lines, r'참가비|참여비') or rules.UNKNOWN_TEXT, 'prize': None,
        'url': url, 'sourceUrl': url, 'sourceName': SOURCE_NAME,
        'dateNote': '공식 공지 본문 행사 일시 기준. 접수 마감은 별도 표시하며 접수 상태는 확인 필요',
        'sourceStatus': 'unknown',
    }


def collect(fetcher, now, max_items=None):
    limit = effective_limit(max_items)
    if not limit:
        return CollectResult([], '조회 상한 0건')
    rows, seen, pages_read = [], set(), 0
    for page in range(1, PAGE_LIMIT + 1):
        listing = parse_listing(fetcher.get(page_url(page)).text, candidates_only=False)
        pages_read += 1
        fresh = []
        for row in listing:
            if row['id'] not in seen:
                seen.add(row['id'])
                fresh.append(row)
        rows.extend(row for row in fresh if _candidate(row['title']))
        if len(rows) >= limit or not fresh:
            break
    rows = rows[:limit]
    items, failures = [], []
    for row in rows:
        try:
            raw = parse_detail(fetcher.get(detail_url(row['id'])).text, detail_url(row['id']))
            if raw is not None and raw['title'] != row['title']:
                raise StructureError('서울 AI 허브 목록·상세 제목이 다름')
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        if raw is not None:
            items.append(raw)
    fail_if_every_fetch_failed(len(rows), failures, SOURCE_NAME)
    return CollectResult(items, f'공지 {pages_read}페이지, 후보 {len(rows)}건 중 개인 참가·일정 확인 {len(items)}건, 상세 조회·검증 실패 {len(failures)}건')
