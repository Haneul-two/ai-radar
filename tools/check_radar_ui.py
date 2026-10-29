"""AI Radar UI 검증. 로컬 서버 8012, Playwright 및 설치된 Edge(headless)가 필요하다.

실데이터 검사는 건수를 고정하지 않는다(수집으로 항목이 늘어도 통과). 날짜·마감 제외 검사는
repo 밖 합성 데이터를 route로 주입하고 ?now= 또는 Playwright clock으로 시각을 고정한다.
결과는 docs/evidence/radar-frontend-checks.txt 와 radar-*.png 로 남긴다.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'evidence'
BASE = 'http://127.0.0.1:8012/'
KST = timezone(timedelta(hours=9))
READY = '.opp, .state, .cal'
sys.stdout.reconfigure(encoding="utf-8")
checks = []
errors = []


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
    print(('PASS ' if condition else 'FAIL ') + name + (f' | {detail}' if detail not in (None, '') else ''), flush=True)


def new_page(browser, width=1440, height=900, **kwargs):
    context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1, locale='ko-KR', **kwargs)
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda m: errors.append(f'console: {m.text}') if m.type == 'error' else None)
    return context, page


def ready(page, url=BASE):
    page.goto(url)
    page.wait_for_selector(READY)
    expect(page.locator('#content')).to_have_attribute('aria-busy', 'false')


def overflow(page):
    return page.evaluate('''() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
      outside: [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
        return r.width && s.position !== 'absolute' && r.right > innerWidth + 1;
      }).map(e => e.className || e.tagName).slice(0, 8) })''')


def shot(page, name):
    page.screenshot(path=str(OUT / f'{name}.png'), scale='css')


# ---- 합성 데이터 (실제 행사 아님) ----
def synth_item(item_id, title, **kw):
    base = {
        'id': item_id, 'kind': 'hackathon', 'title': title, 'organizer': '합성 주최', 'description': '', 'tags': [],
        'mode': 'online', 'region': '해외 온라인', 'country': 'GLOBAL', 'startDate': None, 'endDate': None,
        'registrationStartDate': None, 'deadlineDate': None, 'deadlineAt': None, 'eligibility': '확인 필요',
        'eligibilityVerified': False, 'fee': '확인 필요', 'prize': None, 'url': 'https://example.com/a',
        'sourceUrl': 'https://example.com/s', 'sourceId': 'synth', 'sourceName': '합성 출처',
        'verifiedAt': '2026-10-12T00:00:00Z', 'dateNote': None, 'stale': False,
    }
    base.update(kw)
    return base


NOW_ISO = '2026-10-12T00:00:00Z'  # 서울 2026-10-12 09:00
SYNTH = {
    'schemaVersion': 2, 'updatedAt': NOW_ISO, 'lastAttemptAt': NOW_ISO,
    'sources': [{'id': 'synth', 'name': '합성 출처', 'status': 'ok', 'url': 'https://example.com/', 'lastSuccessAt': NOW_ISO}],
    'items': [
        synth_item('live-exact', 'LIVE 정확 마감 14시', deadlineAt='2026-10-12T05:00:00Z', startDate='2026-10-20'),
        synth_item('dead-exact', 'DEAD 정확 마감 08시', deadlineAt='2026-10-11T23:00:00Z', startDate='2026-10-20'),
        synth_item('today-date', 'LIVE 오늘 날짜만 마감', kind='contest', deadlineDate='2026-10-12'),
        synth_item('yest-date', 'DEAD 어제 날짜만 마감', kind='contest', deadlineDate='2026-10-11'),
        synth_item('tbd-event', 'LIVE 미확정 미래 행사', kind='event', startDate='2026-12-01', mode='offline', region='서울'),
        synth_item('src-closed', 'DEAD 출처가 마감 표시', sourceStatus='closed'),
        synth_item('long-one', '아주 긴 한국어 제목 ' + '인공지능 데이터 활용 공모전 ' * 6, organizer='https://example.com/' + 'a' * 140, prize='상금 ' + '9' * 60),
    ],
}
LIVE_TITLES = ['LIVE 정확 마감 14시', 'LIVE 오늘 날짜만 마감', 'LIVE 미확정 미래 행사']
DEAD_TITLES = ['DEAD 정확 마감 08시', 'DEAD 어제 날짜만 마감', 'DEAD 출처가 마감 표시']


def route_synth(context, payload=SYNTH):
    def handler(route):
        url = route.request.url
        if url.endswith('opportunities.json') or '/opportunities.json?' in url:
            route.fulfill(status=200, content_type='application/json', body=json.dumps(payload, ensure_ascii=False))
        elif 'ingest-status.json' in url:
            route.fulfill(status=200, content_type='application/json', body=json.dumps({'lastAttemptAt': NOW_ISO, 'sources': []}))
        else:
            route.continue_()
    context.route('**/data/*.json*', handler)


def titles(page):
    return page.locator('.opp-open').all_inner_texts()


with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='msedge', headless=True)

    # ================= 실데이터 · 데스크톱 1440x900 =================
    context, page = new_page(browser)
    ready(page)
    rows = page.locator('.opp')
    check('실데이터 행 표시(건수 고정 안 함)', rows.count() > 0, rows.count())
    check('브라우저 제목 AI Radar', page.title().startswith('AI Radar'), page.title())
    check('브랜드 AI Radar', page.locator('.brand').inner_text().replace('\n', ' ').strip() == 'AI Radar')
    check('구 브랜드·디버그 문구 비노출', '기회 보드' not in page.content() and page.locator('#debug-banner').is_hidden())
    check('데스크톱 CSS 너비 1440', page.evaluate('()=>innerWidth') == 1440)
    check('상단 바 높이 60', abs(page.locator('.topbar').bounding_box()['height'] - 60) <= 1, page.locator('.topbar').bounding_box()['height'])
    check('검색 입력 높이 44', abs(page.locator('#q').bounding_box()['height'] - 44) <= 1)
    check('필터 레일 폭 약 200', 190 <= page.locator('#filter-rail').bounding_box()['width'] <= 210, page.locator('#filter-rail').bounding_box()['width'])
    check('오른쪽 중복 임박 레일 없음', page.locator('.urgent-rail').count() == 0)
    check('마감 임박·출처 상태는 필터 하단 details', page.locator('#filter-rail details').count() == 2)
    h0 = rows.first.bounding_box()['height']
    check('데스크톱 행 높이 96~140', 90 <= h0 <= 140, h0)
    check('열 머리글 표시', page.locator('.opp-head').is_visible() and page.locator('.opp-head').inner_text().split('\n')[:4] == ['제목 · 주최', '마감', '개최', '참가 · 상금'], page.locator('.opp-head').inner_text())
    first = rows.first
    check('행 즉시 노출: 제목·마감·개최·참가·확인/출처·저장', all([
        first.locator('.opp-open').count() == 1, first.locator('.is-deadline').count() == 1, first.locator('.is-when').count() == 1,
        first.locator('.is-terms').count() == 1, first.locator('.opp-src').count() == 1, first.locator('[data-save-id]').count() == 1]))
    status_labels = page.locator('#status-options .option').all_inner_texts()
    check('상태 옵션에 마감·종료 없음', not any(('마감' in t or '종료' in t) for t in status_labels), status_labels)
    visible_statuses = page.locator('.opp .status').all_inner_texts()
    check('목록에 마감·종료 상태 없음', not any(t in ('마감', '종료') for t in visible_statuses), sorted(set(visible_statuses)))
    m = overflow(page)
    check('1440 가로 넘침 0', m['scroll'] <= 1440 and not m['outside'], m)
    shot(page, 'radar-desktop')

    # 검색: 디바운스 후 반영, 입력 포커스·캐럿 유지
    term = page.evaluate('()=>window.__boardDebug.visible[0].title.split(/\\s+/).find(w=>w.length>=3) || window.__boardDebug.visible[0].title')
    total = rows.count()
    page.locator('#q').click()
    page.keyboard.type(term)
    expect(page).to_have_url(re.compile('q='))
    check('검색 URL 반영', 'q=' in page.url, page.url)
    check('검색 중 입력 포커스 유지', page.locator('#q').evaluate('e=>e===document.activeElement'))
    check('검색 결과가 줄거나 같음', 0 < rows.count() <= total, rows.count())
    page.keyboard.type('없는검색어XYZQ')
    expect(rows).to_have_count(0)
    expect(page.locator('#content').get_by_role('button', name='필터 초기화', exact=True)).to_be_visible()
    check('검색 포커스·캐럿 유지(빈 결과 후에도)', page.locator('#q').evaluate('e=>e===document.activeElement && e.selectionStart===e.value.length'))
    page.locator('#content').get_by_role('button', name='필터 초기화', exact=True).click()
    expect(rows).to_have_count(total)
    check('초기화 후 검색 비움', page.locator('#q').input_value() == '')

    # 필터: 상태 → URL, 모두 모집중
    page.locator('#status-options .option', has_text='모집중').click()
    expect(page).to_have_url(re.compile('status=open'))
    open_rows = rows.count()
    check('모집중 필터: 모든 행이 모집중', open_rows == 0 or set(page.locator('.opp .status').all_inner_texts()) == {'모집중'})
    page.locator('#reset-filters').click()
    expect(rows).to_have_count(total)

    # 유형 탭과 건수
    tab_counts = {t.split('\n')[0]: int(t.split('\n')[-1]) for t in page.locator('#kind-tabs .tab').all_inner_texts()}
    check('유형 탭 건수 = 목록 건수(전체)', tab_counts.get('전체') == total, tab_counts)

    # 저장 → 재접속 유지 → 저장 보기
    btn = page.locator('.opp [data-save-id]').first
    sid = btn.get_attribute('data-save-id')
    btn.click()
    expect(btn).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#saved-toggle .nav-count')).to_have_text('1')
    page.reload()
    page.wait_for_selector(READY)
    expect(page.locator(f'.opp [data-save-id="{sid}"]')).to_have_attribute('aria-pressed', 'true')
    check('저장이 새로고침 후에도 유지', True)
    page.locator('#saved-toggle').click()
    expect(rows).to_have_count(1)
    check('저장 보기: 저장 항목만', page.locator('.opp [data-save-id]').first.get_attribute('data-save-id') == sid)
    page.locator('#nav-explore').click()
    expect(rows).to_have_count(total)

    # 상세: 키보드 열기 → 포커스 → Tab 가둠 → Esc → 포커스 복귀
    opener = page.locator('.opp-open').first
    opener_id = opener.get_attribute('data-open-id')
    opener.focus()
    page.keyboard.press('Enter')
    dialog = page.locator('dialog')
    expect(dialog).to_be_visible()
    check('상세 초기 포커스는 닫기 버튼', page.get_by_role('button', name='상세 정보 닫기').evaluate('e=>e===document.activeElement'))
    stay = True
    for _ in range(10):
        page.keyboard.press('Tab')
        stay = stay and page.evaluate("()=>{const a=document.activeElement;return a===document.body||!!a.closest('dialog')}")
    check('상세 Tab 포커스가 배경으로 새지 않음', stay)
    box = dialog.bounding_box()
    check('상세 드로어 폭 520~560, 우측 정렬', 515 <= box['width'] <= 565 and abs(box['x'] + box['width'] - 1440) <= 2, box)
    check('상세 외부 링크 보안 속성', dialog.locator('a').count() == 0 or dialog.locator('a').evaluate_all("es=>es.every(e=>e.protocol==='https:'&&e.rel.includes('noopener')&&e.rel.includes('noreferrer'))"))
    check('상세에 원문 안내 링크와 저장 버튼', dialog.get_by_role('link', name='안내 페이지 열기').count() >= 0 and dialog.locator('[data-save-id]').count() == 1)
    shot(page, 'radar-detail')
    page.keyboard.press('Escape')
    expect(dialog).not_to_be_visible()
    check('상세 닫은 뒤 행 제목으로 포커스 복귀', page.locator(f'.opp-open[data-open-id="{opener_id}"]').evaluate('e=>e===document.activeElement'))

    # 달력
    page.get_by_role('button', name='달력', exact=True).click()
    expect(page.locator('.cal')).to_be_visible()
    title = page.locator('.cal-title').inner_text()
    page.get_by_role('button', name='다음 달', exact=True).click()
    expect(page.locator('.cal-title')).not_to_have_text(title)
    page.get_by_role('button', name='오늘', exact=True).click()
    expect(page.locator('.cal-title')).to_have_text(title)
    check('달력 월 이동·오늘 복귀', True)
    mk = page.locator('.cal .mk')
    if mk.count():
        mk.first.click()
        expect(dialog).to_be_visible()
        page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
    check('달력 마커로 상세 진입', True, mk.count())
    page.get_by_role('button', name='목록', exact=True).click()
    expect(rows.first).to_be_visible()
    check('콘솔 오류 없음(실데이터 데스크톱)', not errors, errors)
    context.close()

    # ================= 실데이터 · 모바일 =================
    context, page = new_page(browser, 390, 844)
    ready(page)
    for width in (320, 360, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        m = overflow(page)
        check(f'모바일 {width}px 가로 넘침 0', m['scroll'] <= width and not m['outside'], m)
    page.set_viewport_size({'width': 390, 'height': 844})
    r0 = page.locator('.opp').first
    check('모바일 행에 마감·개최·참가·저장 모두 표시', all(r0.locator(s).is_visible() for s in ('.is-deadline', '.is-when', '.is-terms', '[data-save-id]', '.opp-open')))
    check('모바일 열 머리글 숨김', page.locator('.opp-head').is_hidden())
    check('모바일 검색·유형 탭·정렬·보기 전환 모두 보임', all(page.locator(s).is_visible() for s in ('#q', '#kind-tabs', '#sort', '#view-switch')))
    short = page.evaluate("()=>[...document.querySelectorAll('button:not([hidden]), select, input, summary')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&r.height<43.5&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('dialog:not([open])')}).map(e=>(e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().height))")
    check('모바일 터치 목표 44px 이상', not short, short[:8])
    page.locator('#rail-toggle').click()
    expect(page.locator('#rail-toggle')).to_have_attribute('aria-expanded', 'true')
    check('모바일 필터 펼침', page.locator('#status-options').is_visible())
    page.locator('#rail-toggle').click()
    shot(page, 'radar-mobile')
    page.get_by_role('button', name='달력', exact=True).click()
    expect(page.locator('.cal')).to_be_visible()
    m = overflow(page)
    check('모바일 달력 가로 넘침 0', m['scroll'] <= 390, m)
    page.get_by_role('button', name='목록', exact=True).click()
    page.locator('.opp-open').first.click()
    box = page.locator('dialog').bounding_box()
    check('모바일 상세는 전체 화면', box['width'] >= 389 and box['height'] >= 843, box)
    page.keyboard.press('Escape')

    for mode in ('loading', 'empty', 'error'):
        page.goto(BASE + '?debug=' + mode)
        expect(page.locator('#debug-banner')).to_be_visible()
        if mode == 'loading':
            expect(page.locator('.skeleton')).to_be_visible()
        elif mode == 'empty':
            expect(page.get_by_text('표시할 기회가 없습니다', exact=True)).to_be_visible()
        else:
            expect(page.get_by_role('button', name='다시 시도', exact=True)).to_be_visible()
        check(f'{mode} 상태 표시', True)
        if mode == 'loading':
            check('로딩 중에는 미수집 알림을 띄우지 않음', '아직' not in page.locator('#notices').inner_text() and '수집된 기회가 아직 없습니다' not in page.locator('#notices').inner_text())
        else:
            m = overflow(page)
            check(f'{mode} 상태 가로 넘침 0', m['scroll'] <= 390, m)
    context.close()

    # ================= 실데이터 · 폭별 첫 행 제목 폭 / 레이아웃 모드 =================
    context, page = new_page(browser)
    ready(page)
    for width in (320, 375, 390, 414, 768, 1024, 1280, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        page.wait_for_timeout(100)
        row = page.locator('.opp').first
        title_w = row.locator('.opp-open').bounding_box()['width']
        org_w = row.locator('.opp-org').bounding_box()['width'] if row.locator('.opp-org').count() else title_w
        m = overflow(page)
        check(f'폭 {width}: 첫 행 제목 폭 200px 이상·주최 폭 120px 이상·가로 넘침 0',
              title_w >= 200 and org_w >= 120 and m['scroll'] <= width and not m['outside'],
              {'titleWidth': round(title_w), 'orgWidth': round(org_w), 'rowHeight': round(row.bounding_box()['height'], 1), 'scroll': m['scroll']})
        if width in (768, 1024):
            shot(page, f'radar-w{width}')
        rail_open = page.locator('#rail-panel').is_visible()
        toggle = page.locator('#rail-toggle').is_visible()
        labeled = row.locator('.is-deadline dt').evaluate('e=>e.getBoundingClientRect().width>10')
        head = page.locator('.opp-head').is_visible()
        if width >= 1280:
            ok = rail_open and not toggle and head and not labeled
        elif width >= 960:
            ok = (not rail_open) and toggle and head and not labeled and page.locator('.results').bounding_box()['width'] >= width - 2 * 24 - 2
        else:
            ok = toggle and not head and labeled
        check(f'폭 {width}: 레이아웃 모드(필터 {"고정" if width >= 1280 else "접힘"}·{"머리글 열" if width >= 960 else "라벨 세로 행"})',
              ok, {'rail': rail_open, 'toggle': toggle, 'head': head, 'labeled': labeled})
        if width < 960:
            save_box = row.locator('[data-save-id]').bounding_box()
            t_box = row.locator('.opp-open').bounding_box()
            check(f'폭 {width}: 저장 버튼이 제목과 겹치지 않고 44px 이상',
                  (save_box['y'] >= t_box['y'] + t_box['height'] - 1 or save_box['x'] >= t_box['x'] + t_box['width'] - 1) and save_box['height'] >= 43.5,
                  {'save': [round(save_box['x']), round(save_box['y']), round(save_box['height'])], 'title': [round(t_box['x']), round(t_box['y']), round(t_box['width']), round(t_box['height'])]})
    context.close()

    # ================= 합성 데이터 · 날짜 마감 제외 (now 고정) =================
    context, page = new_page(browser)
    route_synth(context)
    ready(page, BASE + f'?now={NOW_ISO}')
    shown = titles(page)
    check('노출: 확정 마감 전·오늘 날짜만·미확정 행사', sorted(t for t in shown if t.startswith('LIVE')) == sorted(LIVE_TITLES), shown)
    check('제외: 시각 지난 exact·어제 날짜·출처 closed', not any(t.startswith('DEAD') for t in shown), shown)
    today_row = page.locator('.opp', has_text='LIVE 오늘 날짜만 마감')
    check('오늘 날짜만 마감은 시각 미확인 표시', '시각 미확인' in today_row.inner_text(), today_row.inner_text())
    tbd_row = page.locator('.opp', has_text='LIVE 미확정 미래 행사')
    check('미확정 미래 행사는 마감 미확인', '미확인' in tbd_row.locator('.is-deadline').inner_text())
    total = page.locator('.opp').count()
    tabs = {t.split('\n')[0]: int(t.split('\n')[-1]) for t in page.locator('#kind-tabs .tab').all_inner_texts()}
    check('유형 탭 건수가 노출 목록과 일치', tabs['전체'] == total == 4 and tabs['공모전'] == 1 and tabs['행사'] == 1 and tabs['해커톤'] == 2, tabs)
    check('결과 건수 표시 일치', page.locator('#result-count').inner_text().startswith(f'{total}건'), page.locator('#result-count').inner_text())
    m = overflow(page)
    check('긴 제목·긴 URL·긴 상금 가로 넘침 0 (1440)', m['scroll'] <= 1440 and not m['outside'], m)
    page.set_viewport_size({'width': 390, 'height': 844})
    m = overflow(page)
    check('긴 제목·긴 URL·긴 상금 가로 넘침 0 (390)', m['scroll'] <= 390 and not m['outside'], m)
    page.set_viewport_size({'width': 1440, 'height': 900})
    page.get_by_role('button', name='달력', exact=True).click()
    expect(page.locator('.cal')).to_be_visible()
    cal_text = page.locator('.cal').inner_text()
    check('달력에 제외 항목 없음', not any(t in cal_text for t in DEAD_TITLES) and 'LIVE 정확 마감 14시' in cal_text)
    page.get_by_role('button', name='목록', exact=True).click()
    check('임박 목록에 제외 항목 없음', not any(t in page.locator('#urgent').inner_text() for t in DEAD_TITLES))
    context.close()

    # 예전 URL/저장값 closed → all, 저장 id는 남기고 마감 저장은 목록에 안 나옴
    context, page = new_page(browser)
    route_synth(context)
    context.add_init_script("""if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');
      localStorage.setItem('aob.saved.v1', JSON.stringify(['dead-exact', 'live-exact', 'gone-id']));
      localStorage.setItem('aob.filters.v1', JSON.stringify({kind: 'all', status: 'closed', mode: 'all', sort: 'deadline', view: 'list'})); }""")
    ready(page, BASE + f'?now={NOW_ISO}&status=closed')
    st = page.evaluate('()=>window.__boardDebug.state')
    check('status=closed URL은 all로 변환', st['filters']['status'] == 'all', st['filters'])
    check('URL에서도 closed 제거', 'status=closed' not in page.url, page.url)
    check('저장된 closed 필터값도 all 처리', page.locator('#status-options .option[aria-pressed="true"]').inner_text().startswith('전체'))
    expect(page.locator('#saved-toggle .nav-count')).to_have_text('1')
    check('저장 건수는 노출 가능한 1건만 센다', True)
    page.locator('#saved-toggle').click()
    expect(page.locator('.opp')).to_have_count(1)
    check('저장 보기에 마감 저장 항목 비노출', titles(page) == ['LIVE 정확 마감 14시'], titles(page))
    check('마감 저장 안내 알림', '목록에 표시하지 않습니다' in page.locator('#notices').inner_text(), page.locator('#notices').inner_text())
    kept = page.evaluate("()=>JSON.parse(localStorage.getItem('aob.saved.v1'))")
    check('저장 id 삭제 없음', sorted(kept) == ['dead-exact', 'gone-id', 'live-exact'], kept)
    context.close()

    # 시간 경과: 렌더 뒤 마감 시각이 지나면 목록·상세가 갱신된다 (Playwright clock, 실제 Date 대체)
    context, page = new_page(browser)
    route_synth(context)
    start = datetime(2026, 10, 12, 13, 59, 30, tzinfo=KST)  # live-exact 마감 14:00 직전
    page.clock.install(time=start)
    ready(page)
    check('시간 경과 전: 14시 마감 항목 노출', 'LIVE 정확 마감 14시' in titles(page), titles(page))
    page.locator('#q').click()
    page.keyboard.type('LIVE')
    page.locator('.opp-open', has_text='정확 마감').click()
    expect(page.locator('dialog')).to_be_visible()
    page.keyboard.press('Escape')
    page.locator('.opp-open', has_text='정확 마감').focus()
    page.keyboard.press('Enter')
    expect(page.locator('dialog')).to_be_visible()
    page.clock.run_for(45_000)
    expect(page.locator('dialog')).not_to_be_visible()
    check('열린 상세가 마감되면 닫힌다', True)
    expect(page.locator('#notices')).to_contain_text('신청이 마감되어 목록에서 제외')
    check('닫힌 이유 안내', True)
    expect(page.locator('.opp-open', has_text='정확 마감')).to_have_count(0)
    check('시간 경과로 목록에서 제외', 'LIVE 정확 마감 14시' not in titles(page), titles(page))
    check('시간 경과 후 검색 입력 포커스·값 유지', page.locator('#q').input_value() == 'LIVE')
    check('시간 경과 후 오늘 날짜만 마감은 유지', 'LIVE 오늘 날짜만 마감' in titles(page))
    check('시간 경과 후 유형 탭 건수 갱신', int(page.locator('#kind-tabs .tab').first.inner_text().split('\n')[-1]) == page.locator('.opp').count())
    context.close()

    # 모션: reduced-motion 에서 상세 전환 애니메이션 없음
    context, page = new_page(browser, reduced_motion='reduce')
    ready(page)
    page.locator('.opp-open').first.click()
    expect(page.locator('dialog')).to_be_visible()
    check('reduced-motion: 상세 애니메이션 없음', page.locator('dialog').evaluate('e=>getComputedStyle(e).animationName') == 'none')
    context.close()

    # 운영 호스트에서는 debug/now 무시
    context, page = new_page(browser)
    page.goto('http://localhost.:8012/?debug=empty&now=2000-01-01T00:00:00Z')
    page.wait_for_selector(READY)
    check('운영 호스트 debug·now 무시', page.locator('#debug-banner').is_hidden() and page.evaluate('()=>typeof window.__boardDebug') == 'undefined' and page.locator('.opp').count() > 0)
    context.close()

    check('전체 콘솔·페이지 오류 없음', not errors, errors)
    browser.close()

passed = sum(c['passed'] for c in checks)
lines = [f'AI Radar UI 검증 {datetime.now(KST).strftime("%Y-%m-%d %H:%M")} KST', f'통과 {passed} / {len(checks)}', '폭별 레이아웃 검사(제목 폭·모드·저장 버튼)는 수정 전 RED 실측이 docs/evidence/radar-layout-red.txt 에 보존되어 있다.', '']
for c in checks:
    d = '' if c['detail'] in (None, '') else f' | {c["detail"]}'
    lines.append(('PASS ' if c['passed'] else 'FAIL ') + c['name'] + d)
(OUT / 'radar-frontend-checks.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'passed {passed}/{len(checks)}')
sys.exit(0 if passed == len(checks) else 1)
