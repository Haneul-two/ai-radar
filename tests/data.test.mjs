import { test } from 'node:test';
import assert from 'node:assert/strict';
import { overlaySources, loadBoardData, datasetFreshness, itemFlags } from '../assets/data.mjs';
import { safeHttpsUrl } from '../assets/safe-url.mjs';
import { parseDebug, isLocalHost } from '../assets/debug.mjs';
import { NOW, makeItem } from './helpers.mjs';

const src = (o) => ({ id: 's1', name: '출처1', url: 'https://example.com', status: 'ok', checkedAt: '2026-10-01T00:00:00Z', lastSuccessAt: '2026-10-01T00:00:00Z', itemCount: 3, message: '', ...o });

function fakeFetch(map) {
  return async (url) => {
    const r = map[url];
    if (r === undefined) return { ok: false, status: 404, json: async () => { throw new Error('no body'); } };
    if (r instanceof Error) throw r;
    return { ok: r.status === undefined || r.status < 400, status: r.status ?? 200, json: async () => { if (r.bad) throw new SyntaxError('bad json'); return r.body; } };
  };
}
const good = { schemaVersion: 2, updatedAt: '2026-10-01T00:00:00Z', lastAttemptAt: '2026-10-01T00:00:00Z', sources: [src()], items: [makeItem({ id: 'a' }), makeItem({ id: 'b' })] };

test('loadBoardData: DACON은 제외하고 원본과 다른 출처 오류는 보존한다', async () => {
  for (const statusSources of [null, [src({ id: 'dacon', status: 'error' }), src({ id: 'wevity', status: 'blocked' })]]) {
    const body = { ...good, sources: [src({ id: 'dacon', status: 'error' }), src({ id: 'wevity', status: 'blocked' })], items: [makeItem({ id: 'old', sourceId: 'dacon' }), makeItem({ id: 'keep', sourceId: 'wevity' })] };
    const original = structuredClone(body);
    const map = { 'data/opportunities.json': { body } };
    if (statusSources) map['data/ingest-status.json'] = { body: { sources: statusSources } };
    const data = await loadBoardData(fakeFetch(map));
    assert.deepEqual(data.items.map((i) => i.id), ['keep']);
    assert.deepEqual(data.sources.map((s) => [s.id, s.status]), [['wevity', 'blocked']]);
    assert.equal(data.dropped, 0);
    assert.deepEqual(body, original);
  }
});

test('loadBoardData: 상태 파일에만 남은 DACON도 제외한다', async () => {
  const data = await loadBoardData(fakeFetch({
    'data/opportunities.json': { body: good },
    'data/ingest-status.json': { body: { sources: [src({ id: 'dacon', status: 'error' })] } },
  }));
  assert.deepEqual(data.sources.map((s) => s.id), ['s1']);
  assert.equal(data.items.length, good.items.length);
});

test('overlaySources: id가 같은 출처는 ingest-status 값으로 덮어쓰고 나머지 필드는 유지', () => {
  const out = overlaySources([src()], [{ id: 's1', status: 'error', checkedAt: '2026-10-02T00:00:00Z', message: 'x' }]);
  assert.equal(out.length, 1);
  assert.equal(out[0].status, 'error');
  assert.equal(out[0].checkedAt, '2026-10-02T00:00:00Z');
  assert.equal(out[0].lastSuccessAt, '2026-10-01T00:00:00Z'); // 실패해도 마지막 성공 시각은 유지
  assert.equal(out[0].name, '출처1');
});

test('overlaySources: 상태에만 있는 출처는 추가하고, 상태가 없으면 그대로', () => {
  assert.equal(overlaySources([src()], [src({ id: 's2' })]).length, 2);
  const base = [src()];
  assert.deepEqual(overlaySources(base, null), base);
  assert.deepEqual(overlaySources(base, undefined), base);
});

test('loadBoardData: 두 파일을 상대 경로로 읽고 overlay한다', async () => {
  const calls = [];
  const f = fakeFetch({
    'data/opportunities.json': { body: good },
    'data/ingest-status.json': { body: { lastAttemptAt: '2026-10-02T00:00:00Z', sources: [{ id: 's1', status: 'blocked', checkedAt: '2026-10-02T00:00:00Z' }] } },
  });
  const data = await loadBoardData((u, o) => { calls.push(u); return f(u, o); });
  assert.deepEqual(calls.sort(), ['data/ingest-status.json', 'data/opportunities.json']);
  assert.equal(data.items.length, 2);
  assert.equal(data.statusLoaded, true);
  assert.equal(data.sources[0].status, 'blocked');
  assert.equal(data.lastAttemptAt, '2026-10-02T00:00:00Z');
});

test('loadBoardData: ingest-status가 없어도 기회 목록은 보여준다', async () => {
  const data = await loadBoardData(fakeFetch({ 'data/opportunities.json': { body: good } }));
  assert.equal(data.items.length, 2);
  assert.equal(data.statusLoaded, false);
  assert.equal(data.sources[0].status, 'ok');
});

test('loadBoardData: ingest-status JSON이 깨져도 목록은 보여준다', async () => {
  const data = await loadBoardData(fakeFetch({ 'data/opportunities.json': { body: good }, 'data/ingest-status.json': { bad: true } }));
  assert.equal(data.statusLoaded, false);
  assert.equal(data.items.length, 2);
});

test('loadBoardData: opportunities 실패/손상/스키마 불일치는 예외', async () => {
  await assert.rejects(loadBoardData(fakeFetch({})));
  await assert.rejects(loadBoardData(fakeFetch({ 'data/opportunities.json': { status: 500 } })));
  await assert.rejects(loadBoardData(fakeFetch({ 'data/opportunities.json': { bad: true } })));
  await assert.rejects(loadBoardData(fakeFetch({ 'data/opportunities.json': { body: { ...good, schemaVersion: 1 } } })));
  await assert.rejects(loadBoardData(fakeFetch({ 'data/opportunities.json': { body: { ...good, items: 'x' } } })));
  await assert.rejects(loadBoardData(fakeFetch({ 'data/opportunities.json': new Error('network') })));
});

test('loadBoardData: 필수 키가 없는 항목은 버리고 건수를 알린다', async () => {
  const body = { ...good, items: [makeItem({ id: 'ok' }), { title: 'no id', kind: 'event' }, makeItem({ id: 'k', kind: 'news' })] };
  const data = await loadBoardData(fakeFetch({ 'data/opportunities.json': { body } }));
  assert.deepEqual(data.items.map((i) => i.id), ['ok']);
  assert.equal(data.dropped, 2);
});

test('datasetFreshness: updatedAt이 없으면 none, 3일 넘으면 stale', () => {
  assert.equal(datasetFreshness({ updatedAt: null }, NOW), 'none');
  assert.equal(datasetFreshness({ updatedAt: '2026-10-01T00:00:00Z' }, NOW), 'fresh');
  assert.equal(datasetFreshness({ updatedAt: '2026-09-28T00:00:00Z' }, NOW), 'stale');
  assert.equal(datasetFreshness({ updatedAt: 'garbage' }, NOW), 'none');
});

test('itemFlags: stale, 수집 지연 출처, 시간 확인, 조건 확인', () => {
  const sources = [src({ id: 'bad', status: 'error' }), src({ id: 'good' })];
  const a = itemFlags(makeItem({ stale: true, sourceId: 'good' }), sources, NOW);
  assert.equal(a.recheck, true);
  const b = itemFlags(makeItem({ sourceId: 'bad' }), sources, NOW);
  assert.equal(b.sourceDelayed, true);
  assert.equal(b.recheck, false);
  const c = itemFlags(makeItem({ sourceId: 'good', deadlineDate: '2026-10-05', country: 'KR', eligibilityVerified: false }), sources, NOW);
  assert.equal(c.timeCheck, true);
  assert.equal(c.eligibilityCheck, true);
  const d = itemFlags(makeItem({ sourceId: 'good', deadlineAt: '2026-10-05T00:00:00Z', eligibilityVerified: true }), sources, NOW);
  assert.equal(d.timeCheck, false);
  assert.equal(d.eligibilityCheck, false);
});

test('safeHttpsUrl: https만 허용하고 userinfo·다른 스킴은 거부', () => {
  assert.equal(safeHttpsUrl('https://example.com/a b'), 'https://example.com/a%20b');
  assert.equal(safeHttpsUrl('http://example.com'), null);
  assert.equal(safeHttpsUrl('javascript:alert(1)'), null);
  assert.equal(safeHttpsUrl('https://user:pw@example.com'), null);
  assert.equal(safeHttpsUrl('//example.com'), null);
  assert.equal(safeHttpsUrl('nonsense'), null);
  assert.equal(safeHttpsUrl(null), null);
  assert.equal(safeHttpsUrl(42), null);
});

test('isLocalHost: localhost와 127.0.0.1만', () => {
  assert.equal(isLocalHost('localhost'), true);
  assert.equal(isLocalHost('127.0.0.1'), true);
  assert.equal(isLocalHost('haneul-two.github.io'), false);
  assert.equal(isLocalHost('localhost.evil.com'), false);
  assert.equal(isLocalHost(''), false);
});

test('parseDebug: 로컬에서는 debug와 고정 now가 작동한다', () => {
  const d = parseDebug('?debug=empty&now=2026-10-02T03:00:00Z', 'localhost');
  assert.equal(d.enabled, true);
  assert.equal(d.mode, 'empty');
  assert.equal(d.nowMs, Date.parse('2026-10-02T03:00:00Z'));
  assert.equal(parseDebug('?debug=error', '127.0.0.1').mode, 'error');
  assert.equal(parseDebug('?debug=loading', 'localhost').mode, 'loading');
});

test('parseDebug: production 호스트에서는 모두 무시한다', () => {
  const d = parseDebug('?debug=empty&now=2026-10-02T03:00:00Z', 'haneul-two.github.io');
  assert.deepEqual(d, { enabled: false, mode: null, nowMs: null });
});

test('parseDebug: 알 수 없는 debug 값과 잘못된 now는 무시', () => {
  const d = parseDebug('?debug=hack&now=yesterday', 'localhost');
  assert.equal(d.mode, null);
  assert.equal(d.nowMs, null);
  assert.equal(d.enabled, false);
  assert.equal(parseDebug('', 'localhost').enabled, false);
});
