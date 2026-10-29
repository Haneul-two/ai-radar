// 상태(state) → 화면. 선택 그룹·헤더 버튼처럼 포커스를 가진 요소는 한 번 만들고 값만 갱신한다.
import { h, replaceChildrenOf } from './dom.js';
import { icon } from './icons.js';
import { applyFilters, selectItems, facetCounts, activeFilterCount, DEFAULT_FILTERS } from './filters.mjs';
import { listedSavedCount, hiddenSavedIds } from './visibility.mjs';
import { getStatus, getDeadline } from './status.mjs';
import { buildNotices } from './notices.mjs';
import { seoulDate } from './time.mjs';
import { formatDateKo, formatSeoulDateTime } from './format.mjs';
import { createChoiceGroup } from './view-controls.js';
import { renderRows } from './view-list.js';
import { renderCalendar } from './view-calendar.js';
import { renderUrgent, renderSources } from './view-urgent.js';

const KIND_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'event', label: '행사' },
  { value: 'contest', label: '공모전' },
  { value: 'hackathon', label: '해커톤' },
];
const STATUS_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'open', label: '모집중' },
  { value: 'upcoming', label: '예정' },
  { value: 'ongoing', label: '진행중' },
  { value: 'unknown', label: '일정 미정' },
];
const MODE_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'online', label: '온라인' },
  { value: 'offline', label: '오프라인' },
  { value: 'hybrid', label: '혼합' },
];

function stateCard(title, text, action) {
  return h('div', { class: 'state' },
    h('h3', {}, title),
    text ? h('p', {}, text) : null,
    action ? h('button', { type: 'button', class: 'btn btn-primary', onclick: action.onClick }, action.label) : null);
}

export function createRenderer(els, actions) {
  const tabs = createChoiceGroup(els.kindTabs, { options: KIND_OPTIONS, buttonClass: 'tab', countClass: 'tab-count', onSelect: (v) => actions.setFilters({ kind: v }) });
  const statusGroup = createChoiceGroup(els.statusOptions, { options: STATUS_OPTIONS, buttonClass: 'option', countClass: 'option-count', onSelect: (v) => actions.setFilters({ status: v }) });
  const modeGroup = createChoiceGroup(els.modeOptions, { options: MODE_OPTIONS, buttonClass: 'option', countClass: 'option-count', onSelect: (v) => actions.setFilters({ mode: v }) });

  const viewButtons = {
    list: h('button', { type: 'button', class: 'btn', 'aria-pressed': 'false', onclick: () => actions.setFilters({ view: 'list' }) }, icon('list'), '목록'),
    calendar: h('button', { type: 'button', class: 'btn', 'aria-pressed': 'false', onclick: () => actions.setFilters({ view: 'calendar' }) }, icon('calendar'), '달력'),
  };
  els.viewSwitch.append(viewButtons.list, viewButtons.calendar);

  const savedCount = h('span', { class: 'nav-count' }, '0');
  els.savedToggle.append('저장', savedCount);
  els.savedToggle.addEventListener('click', () => actions.setFilters({ saved: true }));
  els.navExplore.addEventListener('click', () => actions.setFilters({ saved: false }));

  const refreshIcon = icon('refresh');
  const refreshLabel = h('span', { class: 'btn-text' }, '새로고침');
  els.refresh.append(refreshIcon, refreshLabel);
  els.refresh.addEventListener('click', () => actions.refresh());

  const railLabel = h('span', { class: 'rail-toggle-label' }, '필터');
  els.railToggle.append(icon('sliders'), railLabel);
  els.railToggle.addEventListener('click', () => {
    const open = !els.rail.classList.contains('is-open');
    els.rail.classList.toggle('is-open', open);
    els.railToggle.setAttribute('aria-expanded', String(open));
  });
  els.resetFilters.addEventListener('click', () => actions.resetFilters());
  els.sort.addEventListener('change', () => actions.setFilters({ sort: els.sort.value }));

  let noticeSignature = '';
  let sideKey = null;
  let lastSideData = null;
  let contentSignature = null;
  let dataVersion = 0;
  let lastDataRef = null;

  function renderNotices(state, orphanCount) {
    const notices = buildNotices({
      data: state.data || { items: [], sources: [], updatedAt: null, dropped: 0 },
      now: state.now(),
      phase: state.phase,
      savedStatus: state.savedStatus,
      saveFailure: state.saveFailure,
      refreshFailed: state.refreshFailed,
      orphanCount,
      savedView: state.filters.saved,
      expiredTitle: state.expiredTitle,
    });
    const signature = JSON.stringify(notices);
    if (signature === noticeSignature) return;
    noticeSignature = signature;
    replaceChildrenOf(els.notices, notices.map((n) => h('div', { class: `notice notice-${n.tone}` }, icon('alert'), h('span', {}, n.text))));
  }

  function renderContent(state, selected, items, ctx) {
    const { filters } = state;
    els.content.setAttribute('aria-busy', state.phase === 'loading' ? 'true' : 'false');
    if (state.phase === 'loading') {
      replaceChildrenOf(els.content, h('div', { class: 'skeleton', role: 'status' },
        h('span', { class: 'visually-hidden' }, '기회 목록을 불러오는 중입니다'),
        [1, 2, 3].map(() => h('div', { class: 'skeleton-row', 'aria-hidden': 'true' }))));
      return;
    }
    if (state.phase === 'error') {
      replaceChildrenOf(els.content, stateCard('데이터를 불러오지 못했습니다', '네트워크 상태를 확인한 뒤 다시 시도하세요. 저장한 항목은 그대로 유지됩니다.', { label: '다시 시도', onClick: () => actions.retry() }));
      return;
    }
    if (items.length === 0) {
      replaceChildrenOf(els.content, stateCard('표시할 기회가 없습니다', '수집된 AI 공모전·해커톤·행사가 생기면 이곳에 표시됩니다.', null));
      return;
    }
    if (selected.length === 0) {
      if (filters.saved && state.savedIds.length === 0) {
        replaceChildrenOf(els.content, stateCard('저장한 기회가 없습니다', '목록에서 저장을 누르면 이곳에 모입니다.', { label: '전체 목록 보기', onClick: () => actions.setFilters({ saved: false }) }));
      } else if (filters.saved && !filters.q && ctx.savedHidden > 0) {
        replaceChildrenOf(els.content, stateCard('표시할 저장 항목이 없습니다', '신청이 마감된 저장 항목은 목록에서 제외됩니다. 저장 기록은 보관됩니다.', { label: '전체 목록 보기', onClick: () => actions.setFilters({ saved: false }) }));
      } else {
        replaceChildrenOf(els.content, stateCard('조건에 맞는 기회가 없습니다', '검색어나 필터를 바꾸거나 초기화하세요.', { label: '필터 초기화', onClick: () => actions.resetFilters() }));
      }
      return;
    }
    if (filters.view === 'calendar') {
      renderCalendar(els.content, {
        items: selected,
        now: state.now(),
        month: state.month,
        onMonth: actions.changeMonth,
        onOpen: actions.openDetail,
        onShowList: () => actions.setFilters({ view: 'list' }),
      });
    } else {
      renderRows(els.content, selected, ctx);
    }
  }

  // 저장 토글처럼 목록을 다시 그리지 않아야 하는 갱신(포커스 유지): 저장 개수와 알림만 바꾼다
  function renderSaveChrome(state) {
    const items = state.data ? state.data.items : [];
    const now = state.now();
    const hidden = state.phase === 'ready' ? hiddenSavedIds(state.savedIds, items, now) : [];
    savedCount.textContent = String(state.phase === 'ready' ? listedSavedCount(state.savedIds, items, now) : state.savedIds.length);
    renderNotices(state, hidden.length);
    return hidden.length;
  }

  // 시간만 흘러 바뀐 것이 없으면 목록을 다시 그리지 않는다(키보드 포커스 유지)
  function contentKey(state, selected, savedHidden, now) {
    if (state.data !== lastDataRef) { lastDataRef = state.data; dataVersion += 1; }
    const rows = selected.map((item) => {
      const d = getDeadline(item, now);
      return [item.id, getStatus(item, now), d.daysLeft, d.date];
    });
    const { filters } = state;
    return JSON.stringify([state.phase, dataVersion, filters.view, filters.view === 'calendar' ? state.month : null,
      filters.saved, filters.q, filters.saved ? state.savedIds.length : 0, savedHidden, rows]);
  }

  function drawContent(state, selected, items, ctx) {
    const key = contentKey(state, selected, ctx.savedHidden, ctx.now);
    if (key === contentSignature) return;
    contentSignature = key;
    const active = document.activeElement;
    const focusKey = active && els.content.contains(active) ? (active.dataset.openId ? ['openId', active.dataset.openId] : active.dataset.saveId ? ['saveId', active.dataset.saveId] : null) : null;
    renderContent(state, selected, items, ctx);
    if (focusKey && document.activeElement === document.body) {
      const attr = focusKey[0] === 'openId' ? 'data-open-id' : 'data-save-id';
      const target = els.content.querySelector(`[${attr}="${CSS.escape(focusKey[1])}"]`);
      if (target) target.focus();
    }
  }

  function render(state) {
    const now = state.now();
    const { filters } = state;
    const items = state.data ? state.data.items : [];
    const savedSet = new Set(state.savedIds);
    const ctx = {
      now,
      sources: state.data ? state.data.sources : [],
      savedSet,
      savedHidden: 0,
      onOpen: actions.openDetail,
      onToggleSave: actions.toggleSave,
    };
    const filterCtx = { now, savedIds: savedSet };
    const ready = state.phase === 'ready';

    const selected = ready ? selectItems(items, filters, filterCtx) : [];
    const counts = facetCounts(ready ? items : [], filters, filterCtx);
    const activeItems = ready ? applyFilters(items, { ...DEFAULT_FILTERS }, filterCtx) : [];
    const activeTotal = activeItems.length;
    const soonTotal = activeItems.filter((item) => { const d = getDeadline(item, now).daysLeft; return d !== null && d >= 0 && d <= 7; }).length;

    els.today.textContent = `${formatDateKo(seoulDate(now))} 서울 기준`;
    els.updated.textContent = state.data && state.data.updatedAt ? `데이터 갱신 ${formatSeoulDateTime(state.data.updatedAt).slice(5)}` : '';
    // 요약은 검색·유형·저장 필터와 무관한 전역 집계다. 로딩·오류에는 건수를 만들지 않는다.
    els.statTotal.textContent = ready ? String(activeTotal) : '—';
    els.statSoon.textContent = ready ? String(soonTotal) : '—';
    els.statUpdated.textContent = state.data && state.data.updatedAt ? formatSeoulDateTime(state.data.updatedAt).slice(5) : state.phase === 'loading' ? '불러오는 중' : '확인 필요';
    els.navExplore.setAttribute('aria-pressed', String(!filters.saved));
    els.savedToggle.setAttribute('aria-pressed', String(filters.saved));
    els.savedToggle.setAttribute('aria-label', '저장한 기회만 보기');

    refreshLabel.textContent = state.refreshing ? '불러오는 중' : '새로고침';
    els.refresh.disabled = state.refreshing;
    els.refresh.setAttribute('aria-busy', String(state.refreshing));

    tabs.update(filters.kind, counts.kind);
    statusGroup.update(filters.status, counts.status);
    modeGroup.update(filters.mode, counts.mode);
    const active = activeFilterCount(filters);
    railLabel.textContent = active ? `필터 · ${active}개 적용` : '필터';

    els.sort.value = filters.sort;
    els.sort.hidden = filters.view === 'calendar';
    viewButtons.list.setAttribute('aria-pressed', String(filters.view === 'list'));
    viewButtons.calendar.setAttribute('aria-pressed', String(filters.view === 'calendar'));

    ctx.savedHidden = renderSaveChrome(state) || 0;

    if (state.phase === 'loading') els.resultCount.textContent = '불러오는 중…';
    else if (state.phase === 'error') els.resultCount.textContent = '';
    else {
      els.resultCount.textContent = filters.saved ? `저장 ${selected.length}건` : `${selected.length}건`;
      if (!filters.saved && selected.length !== activeTotal) els.resultCount.append(h('small', {}, ` / 진행 중 ${activeTotal}건`));
    }

    drawContent(state, selected, items, ctx);

    const minute = Math.floor(now / 60000);
    const key = `${state.data ? state.data.updatedAt : 'none'}|${state.data ? state.data.items.length : 0}|${minute}|${state.phase}`;
    if (key !== sideKey || state.data !== lastSideData) {
      sideKey = key;
      lastSideData = state.data;
      renderUrgent(els.urgent, { items: ready ? items : [], now, onOpen: actions.openDetail });
      if (state.data) renderSources(els.sources, { data: state.data });
      else replaceChildrenOf(els.sources, h('summary', {}, '출처 상태'));
    }
  }

  return { render, renderSaveChrome };
}
