"""배포된 커뮤니티 출처·DACON 제외·검색·모바일 화면을 읽기 전용으로 확인한다."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://haneul-two.github.io/ai-radar/'
NEW_SOURCES = {'gpters', 'modulabs', 'seoulaihub'}


def main():
    suffix = '?verify=' + str(int(time.time()))
    docs = {}
    for name in ('opportunities.json', 'ingest-status.json'):
        response = requests.get(BASE + 'data/' + name + suffix, timeout=30)
        response.raise_for_status()
        docs[name] = response.json()
        assert docs[name] == json.loads((ROOT / 'data' / name).read_text(encoding='utf-8')), name
    status = docs['ingest-status.json']
    sources = {s['id']: s for s in status['sources']}
    assert len(sources) == 14 and 'dacon' not in sources
    assert all(sources[s]['status'] == 'ok' for s in NEW_SOURCES)
    errors, checks = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        for width in (1440, 390):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(BASE + suffix, wait_until='networkidle')
            expect(page.locator('#content')).to_have_attribute('aria-busy', 'false')
            assert page.locator('.opp').count() > 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#sources').evaluate('(e) => { e.open = true; }')
            source_text = page.locator('#sources').inner_text()
            assert 'DACON' not in source_text
            assert all(name in source_text for name in ('지피터스', '모두의연구소', '서울 AI 허브'))
            page.locator('#q').fill('런치톡')
            page.locator('#q').press('Enter')
            expect(page.locator('.opp').first).to_be_visible()
            assert '런치톡' in page.locator('#content').inner_text()
            checks.append({'width': width, 'sourcesVisible': True, 'daconHidden': True, 'newEventSearch': True, 'overflow': False})
            page.close()
        browser.close()
    assert not errors, errors
    result = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'datasetUpdatedAt': docs['opportunities.json']['updatedAt'],
              'storedItems': len(docs['opportunities.json']['items']), 'sources': sources, 'checks': checks, 'errors': errors}
    (ROOT / 'docs/evidence/community-sources-public.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
