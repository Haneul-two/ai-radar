// 필터 상태 정의·검증, 필터/정렬/건수 계산. 순수 함수.
import { getStatus, getDeadline } from './status.mjs';
import { toMs, seoulDate, endOfSeoulDateMs, isValidDateStr } from './time.mjs';
import { isListed } from './visibility.mjs';
import { expandToken } from './search-aliases.mjs';

export const KINDS = ['all', 'event', 'contest', 'hackathon'];
export const STATUS_FILTERS = ['all', 'open', 'upcoming', 'ongoing', 'unknown'];
export const MODES = ['all', 'online', 'offline', 'hybrid'];
export const SORTS = ['deadline', 'start', 'verified'];
export const VIEWS = ['list', 'calendar'];

export const DEFAULT_FILTERS = Object.freeze({
  q: '', kind: 'all', status: 'all', mode: 'all', sort: 'deadline', view: 'list', saved: false,
});

const MAX_QUERY = 100;
const oneOf = (list, v, fallback) => (list.includes(v) ? v : fallback);

export function sanitizeFilters(raw) {
  const r = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  const D = DEFAULT_FILTERS;
  return {
    q: typeof r.q === 'string' ? r.q.trim().slice(0, MAX_QUERY) : D.q,
    kind: oneOf(KINDS, r.kind, D.kind),
    status: oneOf(STATUS_FILTERS, r.status, D.status),
    mode: oneOf(MODES, r.mode, D.mode),
    sort: oneOf(SORTS, r.sort, D.sort),
    view: oneOf(VIEWS, r.view, D.view),
    saved: r.saved === true,
  };
}

function matchesStatus(status, filter) {
  return filter === 'all' || status === filter;
}

function searchText(item) {
  return [item.title, item.organizer, ...(Array.isArray(item.tags) ? item.tags : []), item.description]
    .filter((v) => typeof v === 'string')
    .join('\n')
    .normalize('NFC')
    .toLowerCase();
}

function matchesQuery(item, q) {
  const tokens = q.normalize('NFC').toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length) return true;
  const hay = searchText(item);
  return tokens.every((t) => expandToken(t).some((alt) => hay.includes(alt)));
}

// skip: 건수 계산 시 제외할 차원 ('kind' | 'status' | 'mode')
function filterWith(items, f, { now, savedIds }, skip) {
  return items.filter((item) => {
    if (!isListed(item, now)) return false; // 어떤 차원을 건너뛰어도 마감 선필터는 풀리지 않는다
    if (skip !== 'kind' && f.kind !== 'all' && item.kind !== f.kind) return false;
    if (skip !== 'mode' && f.mode !== 'all' && item.mode !== f.mode) return false;
    if (skip !== 'status' && !matchesStatus(getStatus(item, now), f.status)) return false;
    if (f.saved && !savedIds.has(item.id)) return false;
    return matchesQuery(item, f.q);
  });
}

export function applyFilters(items, filters, ctx) {
  return filterWith(items, filters, ctx, null);
}

// 각 선택지의 건수 = 그 선택지를 눌렀을 때 나오는 결과 수
export function facetCounts(items, filters, ctx) {
  const counts = { kind: {}, status: {}, mode: {} };
  const dims = [['kind', KINDS], ['status', STATUS_FILTERS], ['mode', MODES]];
  for (const [dim, values] of dims) {
    const pool = filterWith(items, filters, ctx, dim);
    for (const v of values) {
      counts[dim][v] = pool.filter((item) => {
        if (v === 'all' && dim !== 'status') return true;
        if (dim === 'kind') return item.kind === v;
        if (dim === 'mode') return item.mode === v;
        return matchesStatus(getStatus(item, ctx.now), v);
      }).length;
    }
  }
  return counts;
}

// 마감이 없는 행사는 참가할 수 있는 마지막 기회(개최일, 이미 진행 중이면 오늘)를 기준으로 마감 임박 항목 사이에 둔다.
// 개최일도 없으면 맨 뒤. 마감 날짜를 만들어 내는 것이 아니라 정렬 순서에만 쓴다.
function openUntilMs(item, now) {
  const today = seoulDate(now);
  if (isValidDateStr(item.startDate) && item.startDate >= today) return endOfSeoulDateMs(item.startDate);
  if (isValidDateStr(item.endDate) && item.endDate >= today) return endOfSeoulDateMs(today);
  return null;
}

function deadlineRank(item, now) {
  const d = getDeadline(item, now);
  if (d.kind === 'none') {
    const ms = openUntilMs(item, now);
    return ms === null ? [2, 0] : [0, ms];
  }
  const upcoming = d.ms >= toMs(now);
  return upcoming ? [0, d.ms] : [1, -d.ms];
}

const dateKey = (s) => (typeof s === 'string' && s ? s : '9999-99-99');

export function sortItems(items, sort, now) {
  const indexed = items.map((item, i) => ({ item, i }));
  let cmp;
  if (sort === 'start') {
    cmp = (a, b) => dateKey(a.item.startDate).localeCompare(dateKey(b.item.startDate));
  } else if (sort === 'verified') {
    cmp = (a, b) => (toMs(b.item.verifiedAt) ?? 0) - (toMs(a.item.verifiedAt) ?? 0);
  } else {
    cmp = (a, b) => {
      const [ga, ka] = deadlineRank(a.item, now);
      const [gb, kb] = deadlineRank(b.item, now);
      return ga - gb || ka - kb;
    };
  }
  return indexed.sort((a, b) => cmp(a, b) || a.i - b.i).map((x) => x.item);
}

export function selectItems(items, filters, ctx) {
  return sortItems(applyFilters(items, filters, ctx), filters.sort, ctx.now);
}

// 접힌 필터 레일의 "적용 중" 표시용: 레일 안의 상태·방식만 센다
export function activeFilterCount(filters) {
  let n = 0;
  if (filters.status !== DEFAULT_FILTERS.status) n += 1;
  if (filters.mode !== DEFAULT_FILTERS.mode) n += 1;
  return n;
}
