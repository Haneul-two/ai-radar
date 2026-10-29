"""포커스 디자인 계약 검증: 제목·요약 3종·검색/유형 상시 노출·좌측 필터. 로컬 서버 8012와 설치된 Edge가 필요하다.

기능 회귀 전체는 tools/check_radar_ui.py가 맡는다. 여기서는 이번 디자인이 새로 약속한 것만 본다.
결과는 docs/evidence/focus-ui-checks.json 과 focus-*.png 로 남긴다.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'evidence'
BASE = 'http://127.0.0.1:8012/'
READY = '.opp, .state, .cal'
TITLE = 'AI 공모전·해커톤·행사 모아보기'
sys.stdout.reconfigure(encoding='utf-8')
checks = []
errors = []


def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
    print(('PASS ' if condition else 'FAIL ') + name + (f' | {detail}' if detail not in (None, '') else ''), flush=True)


def new_page(browser, width):
    context = browser.new_context(viewport={'width': width, 'height': 900}, device_scale_factor=1, locale='ko-KR')
    page = context.new_page()
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda m: errors.append(f'console: {m.text}') if m.type == 'error' else None)
    return context, page


def ready(page, url=BASE):
    page.goto(url)
    page.wait_for_selector(READY)
    expect(page.locator('#content')).to_have_attribute('aria-busy', 'false')


def stats(page):
    return page.evaluate("""() => [...document.querySelectorAll('.stat')].map(s => ({
      label: s.querySelector('.stat-label')?.textContent.trim(), value: s.querySelector('.stat-value')?.textContent.trim() }))""")


def overflow(page):
    return page.evaluate('''() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
      outside: [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
        return r.width && s.position !== 'absolute' && r.right > innerWidth + 1;
      }).map(e => e.className || e.tagName).slice(0, 8) })''')


# 화면 코드와 따로 계산한 7일 내 마감 건수(서울 날짜 기준)
SOON_JS = """() => {
  const day = (ms) => new Date(ms + 9 * 3600000).toISOString().slice(0, 10);
  const today = day(__boardDebug.now());
  const diff = (d) => Math.round((Date.parse(d) - Date.parse(today)) / 86400000);
  return __boardDebug.visible.filter((i) => {
    const d = i.deadlineAt ? day(Date.parse(i.deadlineAt)) : i.deadlineDate;
    return d && diff(d) >= 0 && diff(d) <= 7;
  }).length;
}"""


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)

    # ---------- 1440: 제목·요약·좌측 필터 ----------
    context, page = new_page(browser, 1440)
    ready(page)
    h1 = page.locator('h1')
    size = h1.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')
    check('h1 제목이 보이고 문구 일치', h1.is_visible() and h1.inner_text().strip() == TITLE, h1.inner_text())
    check('h1 글자 크기 28~32px', 28 <= size <= 32, size)
    s = stats(page)
    check('요약 3종 라벨', [x['label'] for x in s] == ['참가 가능한 기회', '7일 내 마감', '데이터 갱신'], s)

    page.get_by_role('button', name='필터 초기화', exact=True).click()
    page.wait_for_selector(READY)
    total = page.locator('.opp').count()
    check('요약 건수 = 기본 필터의 노출 건수', s and stats(page)[0]['value'] == str(total), {'stat': stats(page)[0]['value'], 'rows': total})
    soon = page.evaluate(SOON_JS)
    check('7일 내 마감 = 독립 계산', stats(page)[1]['value'] == str(soon), {'stat': stats(page)[1]['value'], 'calc': soon})
    check('데이터 갱신 값 표시', len(stats(page)[2]['value']) > 4, stats(page)[2]['value'])

    before = stats(page)
    page.locator('#q').fill('zzzz없는검색어')
    page.keyboard.press('Enter')
    expect(page.locator('#result-count')).to_contain_text('0건')
    page.get_by_role('button', name='해커톤').first.click()
    check('검색·유형이 바뀌어도 전역 요약은 그대로', stats(page) == before, stats(page))
    page.get_by_role('button', name='필터 초기화', exact=True).first.click()

    rail = page.locator('#filter-rail').bounding_box()
    res = page.locator('#results').bounding_box()
    check('좌측 필터 폭 약 200px · 결과 목록이 오른쪽', 190 <= rail['width'] <= 210 and res['x'] > rail['x'] + rail['width'], {'rail': rail, 'results': res['x']})
    check('검색·유형이 필터 열 안에 있음', page.evaluate("()=>document.getElementById('filter-rail').contains(document.getElementById('q')) && document.getElementById('filter-rail').contains(document.getElementById('kind-tabs'))"))
    check('상태·방식·초기화·마감임박·출처 모두 보임', all(page.locator(x).is_visible() for x in ('#status-options', '#mode-options', '#reset-filters', '#urgent', '#sources')))
    check('결과 영역 상단에 건수·정렬·보기 전환', all(page.locator(x).is_visible() for x in ('#result-count', '#sort', '#view-switch')))
    check('마감·개최·참가 열 보존', all(page.locator('.opp').first.locator(x).is_visible() for x in ('.is-deadline', '.is-when', '.is-terms', '[data-save-id]')))
    page.screenshot(path=str(OUT / 'focus-1440.png'), scale='css')

    # 새로고침 실패: 기존 데이터와 요약을 유지하고 알림을 남긴다
    base_stats = stats(page)
    page.route('**/data/opportunities.json*', lambda r: r.abort())
    page.locator('#refresh').click()
    expect(page.locator('#refresh')).to_be_enabled()
    check('새로고침 실패 시 요약 유지 + 실패 알림', stats(page) == base_stats and page.locator('#notices .notice').count() > 0, stats(page))
    context.close()

    # ---------- 로딩/오류 상태 요약 ----------
    context, page = new_page(browser, 1440)
    page.goto(BASE + '?debug=loading')
    expect(page.locator('.skeleton')).to_be_visible()
    s = stats(page)
    check('로딩: 건수 —, 갱신 불러오는 중, 가짜 0건 없음', s[0]['value'] == '—' and s[1]['value'] == '—' and s[2]['value'] == '불러오는 중', s)
    page.goto(BASE + '?debug=error')
    expect(page.get_by_role('button', name='다시 시도', exact=True)).to_be_visible()
    s = stats(page)
    check('오류: 건수 —, 갱신 확인 필요', s[0]['value'] == '—' and s[1]['value'] == '—' and s[2]['value'] == '확인 필요', s)
    context.close()

    # ---------- 폭별: 검색·유형 상시 노출, 접힘, 넘침 ----------
    for width in (1440, 1280, 1279, 1024, 768, 390, 320):
        context, page = new_page(browser, width)
        ready(page)
        always = all(page.locator(x).is_visible() for x in ('#q', '#kind-tabs', '.tab >> nth=0'))
        toggle = page.locator('#rail-toggle').is_visible()
        panel = page.locator('#rail-panel').is_visible()
        if width >= 1280:
            ok = always and not toggle and panel
        else:
            ok = always and toggle and not panel
        check(f'폭 {width}: 검색·유형 항상 보임, 추가 필터 {"고정" if width >= 1280 else "접힘"}', ok, {'always': always, 'toggle': toggle, 'panel': panel})
        if width < 1280:
            page.locator('#rail-toggle').click()
            check(f'폭 {width}: 토글로 진행 상태·참가 방식 펼침', page.locator('#status-options').is_visible() and page.locator('#mode-options').is_visible())
            page.locator('#rail-toggle').click()
        m = overflow(page)
        check(f'폭 {width}: 가로 넘침 0', m['scroll'] <= width and not m['outside'], m)
        h1w = page.locator('h1').bounding_box()
        statw = page.locator('.stats').bounding_box()
        check(f'폭 {width}: 제목·요약이 화면 안', h1w['x'] >= 0 and h1w['x'] + h1w['width'] <= width + 1 and statw['x'] + statw['width'] <= width + 1, {'h1': h1w, 'stats': statw})
        if width in (768, 390):
            page.screenshot(path=str(OUT / f'focus-{width}.png'), scale='css')
        context.close()

    real = [e for e in errors if 'net::ERR_FAILED' not in e]  # 새로고침 실패 검사가 일부러 일으킨 요청 중단
    check('pageerror·console error 0 (의도한 요청 중단 제외)', not real, real[:5])
    browser.close()

failed = [c for c in checks if not c['passed']]
(OUT / 'focus-ui-checks.json').write_text(json.dumps({'passed': len(checks) - len(failed), 'total': len(checks), 'checks': checks}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n{len(checks) - len(failed)}/{len(checks)} 통과')
sys.exit(1 if failed else 0)
