// 시안 공통: 실제 데이터 읽기, 필터 상태, 항목 표시 모델, 화면 수명주기.
// 판정(마감 제외·상태·정렬·건수)은 운영 assets/ 순수 로직을 그대로 쓴다. 여기서 새로 판정하지 않는다.
import { loadBoardData, datasetFreshness, itemFlags } from '../../assets/data.mjs';
import { DEFAULT_FILTERS, selectItems, facetCounts } from '../../assets/filters.mjs';
import { getDeadline } from '../../assets/status.mjs';
import { listedItems } from '../../assets/visibility.mjs';
import { safeHttpsUrl } from '../../assets/safe-url.mjs';
import { KIND_LABELS, MODE_LABELS, formatRange, ddayLabel, deadlineText, formatSeoulDateTime, formatSeoulTime, formatDateShort } from '../../assets/format.mjs';
import { createControls } from './controls.js';
import { LAYOUTS } from './views.js';

export const UNKNOWN = '확인 필요';
const DEBOUNCE_MS = 200;
const SOON_DAYS = 7;

// 상위 폴더의 data/ 를 읽는 어댑터 (원본 data는 읽기만 한다)
const fetchData = (url, options) => fetch(`../../${url}`, options);

const known = (v) => (typeof v === 'string' && v.trim() && !v.includes('확인 필요') ? v.trim() : null);

// 화면에 쓰는 항목 모델. 없는 값은 만들지 않고 null/'확인 필요'로 둔다.
export function toRow(item, data, now) {
  const deadline = getDeadline(item, now);
  const text = deadlineText(deadline);
  const flags = itemFlags(item, data.sources, now);
  return {
    id: item.id,
    title: item.title,
    organizer: known(item.organizer) ?? UNKNOWN,
    kind: item.kind,
    kindLabel: KIND_LABELS[item.kind] ?? UNKNOWN,
    modeLabel: MODE_LABELS[item.mode] && item.mode !== 'unknown' ? MODE_LABELS[item.mode] : UNKNOWN,
    deadline,
    deadlineText: deadline.kind === 'none' ? UNKNOWN : text.primary,
    deadlineNote: text.note,
    dateShort: deadline.kind === 'none' ? UNKNOWN : formatDateShort(deadline.date),
    timeText: deadline.kind === 'exact' ? `${formatSeoulTime(deadline.ms)} 마감` : deadline.kind === 'dateOnly' ? '마감 시각 확인 필요' : null,
    dday: deadline.kind === 'none' ? null : ddayLabel(deadline.daysLeft),
    daysLeft: deadline.daysLeft,
    startDate: item.startDate ?? '',
    range: formatRange(item.startDate, item.endDate) ?? UNKNOWN,
    prize: known(item.prize) ?? UNKNOWN,
    tags: Array.isArray(item.tags) ? item.tags.filter((t) => typeof t === 'string').slice(0, 4) : [],
    url: safeHttpsUrl(item.url) ?? safeHttpsUrl(item.sourceUrl),
    sourceName: known(item.sourceName) ?? UNKNOWN,
    recheck: flags.recheck || flags.sourceDelayed,
  };
}

const isSoon = (d) => d.kind !== 'none' && d.daysLeft >= 0 && d.daysLeft <= SOON_DAYS;

// 플래너 전용 기간 pill. 목록을 실제로 좁힌다.
const WINDOWS = {
  all: () => true,
  soon: (r) => isSoon(r.deadline),
  month: (r) => r.deadline.kind !== 'none' && r.deadline.daysLeft <= 30,
  none: (r) => r.deadline.kind === 'none',
};

export function mount(theme) {
  const root = document.getElementById('app');
  const filters = { ...DEFAULT_FILTERS };
  const state = { phase: 'loading', data: null, windowKey: 'all', timer: 0 };
  const ctx = (now) => ({ now, savedIds: new Set() });

  const layout = LAYOUTS[theme];
  const controls = createControls(theme, {
    filters,
    onChange: () => { render(); },
    onSearch: (q) => {
      clearTimeout(state.timer);
      state.timer = setTimeout(() => { filters.q = q.trim().slice(0, 100); render(); }, DEBOUNCE_MS);
    },
    onWindow: (key) => { state.windowKey = key; render(); },
    onReset: () => {
      clearTimeout(state.timer);
      Object.assign(filters, DEFAULT_FILTERS);
      state.windowKey = 'all';
      controls.sync(null);
      render();
    },
    onRetry: () => { load(); },
  });
  const view = layout(controls);
  root.replaceChildren(view.element);

  function model() {
    const now = Date.now();
    const data = state.data;
    const c = ctx(now);
    const listed = listedItems(data.items, now).map((i) => toRow(i, data, now));
    const selected = selectItems(data.items, filters, c).map((i) => toRow(i, data, now));
    const rows = selected.filter(WINDOWS[state.windowKey]);
    const sources = data.sources;
    return {
      now,
      rows,
      total: listed.length,
      soon: listed.filter((r) => isSoon(r.deadline)).length,
      noDeadline: listed.filter((r) => r.deadline.kind === 'none').length,
      windowCounts: Object.fromEntries(Object.entries(WINDOWS).map(([k, fn]) => [k, selected.filter(fn).length])),
      facets: facetCounts(data.items, filters, c),
      filtered: filters.q !== '' || filters.kind !== 'all' || filters.mode !== 'all' || state.windowKey !== 'all',
      updatedText: data.updatedAt ? formatSeoulDateTime(data.updatedAt) : UNKNOWN,
      today: new Date(now + 9 * 3600 * 1000).toISOString().slice(0, 10),
      stale: datasetFreshness(data, now) === 'stale',
      failedSources: sources.filter((s) => s.status && s.status !== 'ok').length,
    };
  }

  function render() {
    if (state.phase === 'ready') {
      const m = model();
      controls.sync(m, state.windowKey);
      view.showReady(m);
    } else {
      view.showState(state.phase);
    }
  }

  async function load() {
    state.phase = 'loading';
    render();
    try {
      state.data = await loadBoardData(fetchData);
      state.phase = 'ready';
    } catch {
      state.phase = 'error';
    }
    render();
  }

  load();
}
