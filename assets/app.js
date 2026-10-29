// 진입점: 상태 보관, 저장/필터 지속, 데이터 로딩, 화면 연결
import { h } from './dom.js';
import { icon } from './icons.js';
import { sanitizeFilters, selectItems, DEFAULT_FILTERS } from './filters.mjs';
import { getStorage, loadSavedIds, saveSavedIds, toggleSaved, loadFilters, saveFilters, resolveFilters, serializeFilters } from './storage.mjs';
import { loadBoardData } from './data.mjs';
import { parseDebug, isLocalHost } from './debug.mjs';
import { monthOf, shiftMonth } from './calendar.mjs';
import { createRenderer } from './render.js';
import { createDetail } from './view-detail.js';
import { syncSaveButton } from './item-parts.js';
import { isListed } from './visibility.mjs';

const SEARCH_DEBOUNCE_MS = 200;
const CLOCK_TICK_MS = 15000; // 분 단위 마감 제외를 따라가기 위한 점검 주기
const EMPTY_DATA = { items: [], dropped: 0, sources: [], updatedAt: null, lastAttemptAt: null, statusLoaded: true };

const debug = parseDebug(location.search, location.hostname);
const getNow = () => (debug.nowMs !== null ? debug.nowMs : Date.now());
const storage = getStorage(window);

const $ = (id) => document.getElementById(id);
const els = {
  debugBanner: $('debug-banner'), today: $('today'), updated: $('updated'), navExplore: $('nav-explore'), savedToggle: $('saved-toggle'), refresh: $('refresh'),
  searchField: $('search-field'), kindTabs: $('kind-tabs'), notices: $('notices'),
  rail: $('filter-rail'), railToggle: $('rail-toggle'), statusOptions: $('status-options'), modeOptions: $('mode-options'),
  resetFilters: $('reset-filters'), resultsHeading: $('results-heading'), resultCount: $('result-count'),
  sort: $('sort'), viewSwitch: $('view-switch'), content: $('content'), urgent: $('urgent'), sources: $('sources'),
  statTotal: $('stat-total'), statSoon: $('stat-soon'), statUpdated: $('stat-updated'),
};

const saved = loadSavedIds(storage);
const state = {
  phase: 'loading', // loading | ready | error
  data: null,
  filters: resolveFilters(location.search, loadFilters(storage)),
  savedIds: saved.ids,
  savedStatus: saved.status,
  saveFailure: null,
  refreshing: false,
  refreshFailed: false,
  expiredTitle: null, // 열려 있던 상세가 마감으로 닫혔을 때 안내할 제목
  month: monthOf(getNow()),
  now: getNow,
};

// ---- 검색 입력: 한 번만 만들고 다시 그리지 않는다(포커스·캐럿 유지) ----
const searchInput = h('input', {
  id: 'q', type: 'search', class: 'search-input', autocomplete: 'off', maxlength: '100',
  placeholder: '제목·주최·태그 검색', value: state.filters.q,
});
els.searchField.append(icon('search'), searchInput);
let searchTimer = null;
function flushSearch() {
  clearTimeout(searchTimer);
  searchTimer = null;
  if (searchInput.value.trim() !== state.filters.q) setFilters({ q: searchInput.value });
}
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(flushSearch, SEARCH_DEBOUNCE_MS);
});
searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') flushSearch(); });

// ---- 필터 상태 ----
function syncUrl() {
  const params = new URLSearchParams(location.search);
  for (const key of ['q', 'kind', 'status', 'mode', 'sort', 'view', 'saved']) params.delete(key);
  const filterQs = serializeFilters(state.filters);
  const rest = params.toString(); // debug/now 등 기타 파라미터 보존
  const qs = [filterQs, rest].filter(Boolean).join('&');
  history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
}

function setFilters(patch) {
  state.filters = sanitizeFilters({ ...state.filters, ...patch });
  saveFilters(storage, state.filters); // 실패해도 필터는 현재 화면에서 계속 동작한다
  syncUrl();
  renderer.render(state);
}

function resetFilters() {
  clearTimeout(searchTimer);
  searchInput.value = '';
  state.expiredTitle = null;
  setFilters({ q: '', kind: 'all', status: 'all', mode: 'all', saved: false });
}

// ---- 저장 ----
function toggleSave(id) {
  const before = document.activeElement;
  state.savedIds = toggleSaved(state.savedIds, id);
  const result = saveSavedIds(storage, state.savedIds);
  state.saveFailure = result.ok ? null : result.reason;
  const isSaved = state.savedIds.includes(id);
  document.querySelectorAll('[data-save-id]').forEach((btn) => {
    if (btn.dataset.saveId === id) syncSaveButton(btn, isSaved);
  });
  if (!state.filters.saved) {
    renderer.renderSaveChrome(state);
    return;
  }
  // 저장 보기에서는 해제한 행이 사라진다: 다시 그린 뒤 포커스를 잃지 않게 한다
  const rows = [...els.content.querySelectorAll('.opp')];
  const index = rows.findIndex((row) => row.contains(before));
  renderer.render(state);
  if (index >= 0 && !detail.isOpen()) {
    const next = els.content.querySelectorAll('.opp')[Math.min(index, els.content.querySelectorAll('.opp').length - 1)];
    (next ? next.querySelector('[data-open-id]') : els.resultsHeading).focus();
  }
}

// ---- 상세 ----
const detail = createDetail({
  getContext: () => ({ now: getNow(), sources: state.data ? state.data.sources : [], savedSet: new Set(state.savedIds) }),
  onToggleSave: toggleSave,
  onClosed(id, opener) {
    const target = opener && document.contains(opener) ? opener : document.querySelector(`[data-open-id="${CSS.escape(id || '')}"]`);
    (target || els.resultsHeading).focus();
  },
});

function openDetail(id, opener) {
  const item = state.data && state.data.items.find((i) => i.id === id);
  if (!item) return;
  if (!isListed(item, getNow())) { // 화면을 그린 뒤 마감 시각이 지난 항목은 열지 않고 목록에서 뺀다
    state.expiredTitle = item.title;
    renderer.render(state);
    return;
  }
  if (state.expiredTitle) { state.expiredTitle = null; renderer.renderSaveChrome(state); }
  detail.open(item, opener);
}

// 열린 상세가 마감됐거나 데이터에서 사라졌으면 닫고 이유를 알린다
function revalidateDetail() {
  if (!detail.isOpen()) return;
  const item = state.data && state.data.items.find((i) => i.id === detail.currentId());
  if (item && isListed(item, getNow())) return;
  state.expiredTitle = detail.currentTitle();
  detail.close();
  renderer.render(state);
  if (document.activeElement === document.body) els.resultsHeading.focus();
}

// ---- 시간 경과: 렌더 뒤 마감 시각이 지나면 목록·건수·상세를 다시 맞춘다 ----
let lastMinute = Math.floor(getNow() / 60000);
function syncClock(force) {
  const minute = Math.floor(getNow() / 60000);
  if (!force && minute === lastMinute) return;
  lastMinute = minute;
  if (state.phase !== 'ready') return;
  revalidateDetail();
  renderer.render(state);
}
setInterval(() => { if (!document.hidden) syncClock(false); }, CLOCK_TICK_MS);
document.addEventListener('visibilitychange', () => { if (!document.hidden) syncClock(true); });
window.addEventListener('focus', () => syncClock(true));

// ---- 달력 ----
function changeMonth(step) {
  state.month = step === 'today' ? monthOf(getNow()) : shiftMonth(state.month, step);
  renderer.render(state);
}

// ---- 데이터 ----
async function fetchData() {
  if (debug.mode === 'error') throw new Error('검증 모드: 오류 상태');
  if (debug.mode === 'empty') return EMPTY_DATA;
  if (debug.mode === 'loading') return new Promise(() => {});
  return loadBoardData();
}

async function load() {
  state.phase = 'loading';
  renderer.render(state);
  try {
    state.data = await fetchData();
    state.phase = 'ready';
  } catch {
    state.phase = 'error';
  }
  renderer.render(state);
}

async function refresh() {
  if (state.refreshing) return;
  state.refreshing = true;
  renderer.render(state);
  try {
    state.data = await fetchData();
    state.phase = 'ready';
    state.refreshFailed = false;
    state.expiredTitle = null;
  } catch {
    // 이미 불러온 데이터가 있으면 그대로 보여주고 실패를 알린다
    if (state.data) state.refreshFailed = true;
    else state.phase = 'error';
  }
  state.refreshing = false;
  renderer.render(state);
  revalidateDetail();
  if (document.activeElement === document.body) els.refresh.focus();
}

// 예전 status=closed 링크는 주소창에서도 정리한다
if (new URLSearchParams(location.search).get('status') === 'closed') syncUrl();

const actions = { setFilters, resetFilters, toggleSave, openDetail, changeMonth, refresh, retry: load };
const renderer = createRenderer(els, actions);

// ---- 검증 모드 ----
if (debug.enabled) {
  const parts = [];
  if (debug.mode) parts.push(`debug=${debug.mode}`);
  if (debug.nowMs !== null) parts.push(`now=${new Date(debug.nowMs).toISOString()}`);
  els.debugBanner.textContent = `검증 모드 — ${parts.join(' · ')} (테스트용 화면)`;
  els.debugBanner.hidden = false;
}
if (isLocalHost(location.hostname)) {
  // 검증 도구 전용. production 호스트에서는 만들지 않는다.
  window.__boardDebug = {
    get state() { return { phase: state.phase, filters: { ...state.filters }, savedIds: [...state.savedIds], savedStatus: state.savedStatus, refreshing: state.refreshing, month: { ...state.month } }; },
    get items() { return state.data ? state.data.items : []; },
    get visible() { return state.data ? selectItems(state.data.items, state.filters, { now: getNow(), savedIds: new Set(state.savedIds) }) : []; },
    now: getNow,
    defaults: { ...DEFAULT_FILTERS },
    // 'loading' | 'error' | 'ready' | 'empty' 상태에서 멈춰 화면을 확인한다
    setPhase(phase) {
      if (phase === 'empty') { state.data = EMPTY_DATA; state.phase = 'ready'; }
      else if (['loading', 'error', 'ready'].includes(phase)) state.phase = phase;
      renderer.render(state);
    },
  };
}

load();
