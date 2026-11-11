// 데이터 로딩(opportunities.json + ingest-status.json overlay)과 신선도·항목 표시 플래그.
import { toMs } from './time.mjs';
import { getDeadline } from './status.mjs';

const OPPORTUNITIES_URL = 'data/opportunities.json';
const STATUS_URL = 'data/ingest-status.json';
const STALE_AFTER_MS = 3 * 24 * 60 * 60 * 1000; // 하루 1회 수집 기준 3일 넘으면 지연
const KINDS = ['event', 'contest', 'hackathon'];

export function overlaySources(sources, statusSources) {
  const base = Array.isArray(sources) ? sources : [];
  if (!Array.isArray(statusSources)) return base;
  const byId = new Map(statusSources.filter((s) => s && s.id).map((s) => [s.id, s]));
  const merged = base.map((s) => (byId.has(s.id) ? { ...s, ...byId.get(s.id) } : s));
  const known = new Set(base.map((s) => s.id));
  for (const [id, s] of byId) if (!known.has(id)) merged.push(s);
  return merged;
}

async function fetchJson(fetchFn, url) {
  const res = await fetchFn(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

const isUsableItem = (i) => i && typeof i.id === 'string' && i.id && typeof i.title === 'string' && i.title && KINDS.includes(i.kind);

export async function loadBoardData(fetchFn = fetch) {
  const [oppResult, statusResult] = await Promise.allSettled([
    fetchJson(fetchFn, OPPORTUNITIES_URL),
    fetchJson(fetchFn, STATUS_URL),
  ]);
  if (oppResult.status === 'rejected') throw oppResult.reason;
  const opp = oppResult.value;
  if (!opp || opp.schemaVersion !== 2 || !Array.isArray(opp.items)) {
    throw new Error('지원하지 않는 데이터 형식');
  }
  const status = statusResult.status === 'fulfilled' && statusResult.value && Array.isArray(statusResult.value.sources)
    ? statusResult.value
    : null;
  const usable = opp.items.filter(isUsableItem);
  // 수집을 중단한 DACON은 원본을 보존하고 화면에서만 제외한다.
  const items = usable.filter((i) => i.sourceId !== 'dacon');
  return {
    items,
    dropped: opp.items.length - usable.length,
    sources: overlaySources(opp.sources, status && status.sources).filter((s) => s.id !== 'dacon'),
    updatedAt: opp.updatedAt ?? null,
    lastAttemptAt: (status && status.lastAttemptAt) || opp.lastAttemptAt || null,
    statusLoaded: status !== null,
  };
}

// 'fresh' | 'stale' | 'none'
export function datasetFreshness(data, now) {
  const updated = toMs(data.updatedAt);
  if (updated === null) return 'none';
  return toMs(now) - updated > STALE_AFTER_MS ? 'stale' : 'fresh';
}

export function itemFlags(item, sources, now) {
  const source = sources.find((s) => s.id === item.sourceId);
  const deadline = getDeadline(item, now);
  return {
    recheck: item.stale === true,
    sourceDelayed: !!source && source.status !== 'ok',
    timeCheck: deadline.kind === 'dateOnly',
    eligibilityCheck: item.eligibilityVerified !== true,
  };
}
