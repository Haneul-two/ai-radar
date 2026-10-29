// 시안별 화면 구성. 각 layout(controls)은 { element, showReady(m), showState(phase) }를 돌려준다.
// 출처 문자열은 h()/text node로만 넣는다.
import { h } from '../../assets/dom.js';

const LAB_NOTE = '디자인 비교 시안 · 운영 화면은 그대로';

function labBar() {
  return h('div', { class: 'lab' },
    h('span', { class: 'lab__note' }, LAB_NOTE),
    h('a', { class: 'lab__back', href: './index.html' }, '← 비교 갤러리로'));
}

const srOnly = (t) => h('span', { class: 'sr-only' }, t);

// 제목 링크: 제목은 줄바꿈을 허용한다. 집계 사이트일 수 있어 '공식 신청'이라 부르지 않는다.
function titleLink(row, cls = 'title') {
  if (!row.url) return h('span', { class: cls }, row.title, srOnly(' (안내 링크 없음)'));
  return h('a', { class: `${cls} title-link`, href: row.url, target: '_blank', rel: 'noopener noreferrer' },
    row.title, srOnly(' (안내 페이지, 새 탭에서 열림)'));
}

const recheckMark = (row) => (row.recheck ? h('span', { class: 'recheck' }, '다시 확인 필요') : null);

function ddayChip(row) {
  if (!row.dday) return h('span', { class: 'dday dday--none' }, '확인 필요');
  return h('span', { class: `dday${row.daysLeft <= 7 ? ' is-soon' : ''}` }, row.dday);
}

function dataNote(m) {
  const parts = [];
  if (m.stale) parts.push('데이터 갱신이 늦어지고 있어요');
  if (m.failedSources > 0) parts.push(`일부 출처 ${m.failedSources}곳은 최근 확인에 실패했어요`);
  return parts.length ? h('p', { class: 'data-note' }, parts.join(' · ')) : null;
}

const skeleton = (n) => h('div', { class: 'skeletons', 'aria-hidden': 'true' },
  Array.from({ length: n }, () => h('div', { class: 'skeleton' })));

function stateBlock(phase, controls) {
  if (phase === 'loading') {
    return h('div', { class: 'state', role: 'status' }, h('p', { class: 'state__t' }, '불러오는 중이에요'), skeleton(6));
  }
  return h('div', { class: 'state', role: 'alert' },
    h('p', { class: 'state__t' }, '목록을 불러오지 못했어요'),
    h('p', { class: 'state__d' }, '잠시 뒤에 다시 시도해 주세요.'),
    h('button', { type: 'button', class: 'btn', onClick: controls.actions.retry }, '다시 시도'));
}

function emptyBlock(controls) {
  return h('div', { class: 'state' },
    h('p', { class: 'state__t' }, '조건에 맞는 기회가 없어요'),
    h('p', { class: 'state__d' }, '검색어나 필터를 바꾸면 더 보여요.'),
    h('button', { type: 'button', class: 'btn', onClick: controls.actions.reset }, '조건 초기화'));
}

// 공통 골격: 결과 영역만 다시 그린다. 입력·필터는 layout이 한 번 배치한다.
function shell(controls, build) {
  const results = h('div', { class: 'results' });
  const status = h('p', { class: 'result-status', role: 'status', 'aria-live': 'polite' });
  const slots = { results, status, text: new Map() };
  const element = build(slots);
  return {
    element,
    showState(phase) {
      status.textContent = phase === 'loading' ? '불러오는 중…' : '';
      results.replaceChildren(stateBlock(phase, controls));
      results.setAttribute('aria-busy', String(phase === 'loading'));
    },
    showReady(m) {
      results.setAttribute('aria-busy', 'false');
      status.textContent = m.filtered ? `조건에 맞는 기회 ${m.rows.length}건 (전체 ${m.total}건)` : `전체 ${m.total}건`;
      for (const [el, fn] of slots.text) el.textContent = fn(m);
      results.replaceChildren(m.rows.length ? slots.renderRows(m) : emptyBlock(controls));
      const note = dataNote(m);
      if (note) results.appendChild(note);
    },
  };
}

const bind = (slots, el, fn) => { slots.text.set(el, fn); return el; };
const stat = (slots, label, fn) => {
  const v = bind(slots, h('b', { class: 'stat__v' }), fn);
  return h('p', { class: 'stat' }, h('span', { class: 'stat__l' }, label), v);
};

/* ---------- 01 포커스 ---------- */
function focusRow(r) {
  return h('li', { class: 'fx-row' },
    h('div', { class: 'fx-main' }, titleLink(r), h('p', { class: 'sub' }, r.organizer, recheckMark(r))),
    h('div', { class: 'cell', 'data-label': '유형' }, r.kindLabel),
    h('div', { class: 'cell', 'data-label': '참가' }, r.modeLabel),
    h('div', { class: 'cell cell--dl', 'data-label': '마감' }, ddayChip(r), h('span', { class: 'cell__d' }, r.deadline.kind === 'none' ? '' : r.dateShort)),
    h('div', { class: 'cell', 'data-label': '개최' }, r.range),
    h('div', { class: 'cell', 'data-label': '상금' }, r.prize));
}

function focusLayout(c) {
  return shell(c, (s) => {
    s.renderRows = (m) => h('ul', { class: 'fx-list' }, m.rows.map(focusRow));
    return h('div', { class: 'fx' },
      labBar(),
      h('header', { class: 'fx-head' },
        h('div', {},
          h('h1', { class: 'brand' }, 'AI Radar'),
          h('p', { class: 'intro' }, '참가할 AI 기회를, 놓치지 않도록.')),
        h('div', { class: 'stats' },
          stat(s, '참가 가능한 기회', (m) => `${m.total}건`),
          stat(s, '7일 내 마감', (m) => `${m.soon}건`),
          stat(s, '마지막 확인', (m) => m.updatedText))),
      h('div', { class: 'fx-body' },
        h('aside', { class: 'fx-side', 'aria-label': '찾기와 필터' },
          c.search,
          h('p', { class: 'side-h' }, '유형'), c.kind,
          h('p', { class: 'side-h' }, '참가 방식'), c.mode,
          h('p', { class: 'side-h' }, '정렬'), c.sort),
        h('main', { class: 'fx-main-col' },
          s.status,
          h('div', { class: 'fx-cols', 'aria-hidden': 'true' },
            h('span', {}, '제목 · 주최'), h('span', {}, '유형'), h('span', {}, '참가'), h('span', {}, '마감'), h('span', {}, '개최'), h('span', {}, '상금')),
          s.results)));
  });
}

/* ---------- 02 에디토리얼 ---------- */
function editorialItem(r, i) {
  return h('li', { class: 'ed-item' },
    h('span', { class: 'ed-no', 'aria-hidden': 'true' }, String(i + 1).padStart(2, '0')),
    h('div', { class: 'ed-body' },
      titleLink(r, 'ed-title'),
      h('p', { class: 'ed-meta' }, [r.organizer, r.kindLabel, r.modeLabel].join(' · '), recheckMark(r)),
      r.tags.length ? h('p', { class: 'ed-tags' }, r.tags.join(' · ')) : null,
      h('p', { class: 'ed-meta' }, `개최 ${r.range} · 상금 ${r.prize}`)),
    h('div', { class: `ed-dl${r.dday && r.daysLeft <= 7 ? ' is-soon' : ''}` },
      r.dday ? h('b', { class: 'ed-d' }, r.dday) : h('b', { class: 'ed-d ed-d--none' }, '확인 필요'),
      r.dday ? h('span', { class: 'ed-date' }, r.dateShort) : h('span', { class: 'ed-date' }, '마감일'),
      r.timeText ? h('span', { class: 'ed-date' }, r.timeText) : null));
}

function editorialLayout(c) {
  return shell(c, (s) => {
    s.renderRows = (m) => h('ol', { class: 'ed-list' }, m.rows.map(editorialItem));
    const dateEl = bind(s, h('span', {}), (m) => m.today.replace(/-/g, '.'));
    const updEl = bind(s, h('span', {}), (m) => `마지막 확인 ${m.updatedText}`);
    const sum = (label, fn) => h('p', { class: 'ed-sum' }, h('span', {}, label), bind(s, h('b', {}), fn));
    return h('div', { class: 'ed' },
      labBar(),
      h('header', { class: 'ed-head' },
        h('p', { class: 'ed-folio' }, h('span', {}, 'AI Radar'), dateEl, updEl),
        h('h1', { class: 'ed-h1' }, h('span', {}, '다음 도전은'), h('span', {}, '어디인가요.'))),
      h('div', { class: 'ed-tools' }, c.search, c.kind, c.mode, c.sort),
      h('div', { class: 'ed-body-col' },
        h('main', {}, s.status, s.results),
        h('aside', { class: 'ed-aside', 'aria-label': '마감 요약' },
          h('h2', { class: 'ed-aside-h' }, '마감 요약'),
          h('p', { class: 'ed-aside-s' }, '현재 목록 기준'),
          sum('7일 안에 마감', (m) => `${m.windowCounts.soon}건`),
          sum('30일 안에 마감', (m) => `${m.windowCounts.month}건`),
          sum('마감일 확인 필요', (m) => `${m.windowCounts.none}건`),
          sum('보이는 기회', (m) => `${m.rows.length}건`))));
  });
}

/* ---------- 03 디스커버 ---------- */
function discoverCard(r) {
  return h('li', { class: 'dc' },
    h('div', { class: 'dc-top' }, h('span', { class: 'dc-kind' }, r.kindLabel), recheckMark(r)),
    h('div', { class: 'dc-main' },
      titleLink(r, 'dc-title'),
      h('p', { class: 'dc-org' }, r.organizer)),
    h('dl', { class: 'dc-facts' },
      h('div', {}, h('dt', {}, '참가 방식'), h('dd', {}, r.modeLabel)),
      h('div', {}, h('dt', {}, '상금'), h('dd', {}, r.prize))),
    h('div', { class: `dc-band${r.dday && r.daysLeft <= 7 ? ' is-soon' : ''}` },
      h('span', { class: 'dc-band__l' }, '마감'),
      h('span', { class: 'dc-band__v' }, r.deadline.kind === 'none' ? '확인 필요' : r.dateShort),
      r.dday ? h('b', { class: 'dc-band__d' }, r.dday) : null));
}

function discoverLayout(c) {
  return shell(c, (s) => {
    s.renderRows = (m) => h('ul', { class: 'dc-grid' }, m.rows.map(discoverCard));
    return h('div', { class: 'dc-page' },
      labBar(),
      h('header', { class: 'dc-head' },
        h('div', { class: 'dc-brandrow' }, h('h1', { class: 'dc-brand' }, 'AI Radar'), bind(s, h('span', { class: 'dc-count' }), (m) => `전체 ${m.total}건`)),
        c.kind),
      h('section', { class: 'dc-find' },
        h('h2', { class: 'dc-h2' }, '나에게 맞는 AI 기회 찾기'),
        h('div', { class: 'dc-bar' }, c.search, c.mode, c.sort)),
      h('main', { class: 'dc-main-col' }, s.status, s.results));
  });
}

/* ---------- 04 플래너 ---------- */
function groupByDeadline(rows) {
  const days = new Map();
  const none = [];
  for (const r of rows) {
    if (r.deadline.kind === 'none') { none.push(r); continue; }
    if (!days.has(r.deadline.date)) days.set(r.deadline.date, []);
    days.get(r.deadline.date).push(r);
  }
  const groups = [...days.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, items]) => ({ date, items }));
  return { groups, none };
}

function plannerRow(r) {
  return h('li', { class: 'pl-row' },
    h('div', { class: 'pl-main' }, titleLink(r, 'pl-title'),
      h('p', { class: 'sub' }, [r.organizer, r.kindLabel, r.modeLabel].join(' · '), recheckMark(r))),
    h('p', { class: 'pl-time' }, r.timeText ?? '마감일 확인 필요'),
    h('p', { class: 'pl-prize' }, h('span', { class: 'pl-k' }, '상금 '), r.prize));
}

function plannerGroup(id, head, sub, items, soon) {
  return h('section', { class: `pl-day${soon ? ' is-soon' : ''}`, id, 'aria-label': `${head} ${sub}` },
    h('header', { class: 'pl-day-h' }, h('h2', { class: 'pl-date' }, head), h('p', { class: 'pl-sub' }, sub)),
    h('ul', { class: 'pl-rows' }, items.map(plannerRow)));
}

function plannerLayout(c) {
  return shell(c, (s) => {
    const upcoming = h('ul', { class: 'pl-up' });
    s.text.set(upcoming, () => '');
    s.renderRows = (m) => {
      const { groups, none } = groupByDeadline(m.rows);
      const soonGroups = groups.filter((g) => g.items[0].daysLeft <= 7);
      upcoming.replaceChildren(...(soonGroups.length
        ? soonGroups.map((g) => h('li', {}, h('a', { class: 'pl-up__a', href: `#day-${g.date}` },
          h('span', {}, g.items[0].dateShort), h('b', {}, `${g.items.length}건`))))
        : [h('li', { class: 'pl-up__none' }, '7일 안에 마감되는 기회가 없어요')]));
      const nodes = groups.map((g) => plannerGroup(`day-${g.date}`, g.items[0].dateShort,
        `${g.items[0].dday} · ${g.items.length}건`, g.items, g.items[0].daysLeft <= 7));
      if (none.length) nodes.push(plannerGroup('day-none', '마감일 확인 필요', `${none.length}건`, none, false));
      return h('div', { class: 'pl-days' }, nodes);
    };
    return h('div', { class: 'pl' },
      labBar(),
      h('div', { class: 'pl-wrap' },
        h('aside', { class: 'pl-side', 'aria-label': '일정 개요' },
          h('h2', { class: 'pl-side-h' }, '일정 개요'),
          stat(s, '참가 가능한 기회', (m) => `${m.total}건`),
          stat(s, '7일 내 마감', (m) => `${m.soon}건`),
          stat(s, '마감일 확인 필요', (m) => `${m.noDeadline}건`),
          h('h3', { class: 'pl-side-h2' }, '곧 마감되는 날 (현재 목록 기준)'),
          upcoming,
          h('p', { class: 'pl-upd' }, bind(s, h('span', {}), (m) => `마지막 확인 ${m.updatedText}`))),
        h('div', { class: 'pl-col' },
          h('header', { class: 'pl-head' },
            h('h1', { class: 'pl-h1' }, '기회에도 타이밍이 있으니까.'),
            h('p', { class: 'pl-brand' }, 'AI Radar · 마감일 기준으로 모아봤어요')),
          h('div', { class: 'pl-tools' }, c.window, c.search, c.kind, c.mode, c.sort),
          h('main', {}, s.status, s.results))));
  });
}

export const LAYOUTS = { focus: focusLayout, editorial: editorialLayout, discover: discoverLayout, planner: plannerLayout };
