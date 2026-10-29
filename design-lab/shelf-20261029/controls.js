// 시안 공통 조작부. 검색 입력과 선택 그룹은 한 번만 만들고 값·건수만 바꾼다(포커스·캐럿 유지).
import { h } from '../../assets/dom.js';

const KIND_OPTIONS = [['all', '전체'], ['event', '행사'], ['contest', '공모전'], ['hackathon', '해커톤']];
const MODE_OPTIONS = [['all', '전체'], ['online', '온라인'], ['offline', '오프라인'], ['hybrid', '혼합']];
const SORT_OPTIONS = [['deadline', '마감순'], ['start', '개최순']];
const WINDOW_OPTIONS = [['all', '전체 기간'], ['soon', '7일 내 마감'], ['month', '30일 내 마감'], ['none', '마감일 확인 필요']];

// 선택 그룹: 버튼 여러 개, 눌린 값은 aria-pressed. 건수 칸은 있으면 갱신한다.
function choiceGroup(label, key, options, onPick) {
  const buttons = new Map();
  const counts = new Map();
  const el = h('div', { class: `choice choice--${key}`, role: 'group', 'aria-label': label });
  for (const [value, text] of options) {
    const n = h('span', { class: 'choice__n' });
    counts.set(value, n);
    const btn = h('button', { type: 'button', class: 'choice__btn', 'aria-pressed': 'false', onClick: () => onPick(value) },
      h('span', { class: 'choice__t' }, text), n);
    buttons.set(value, btn);
    el.appendChild(btn);
  }
  return {
    el,
    update(current, countMap) {
      for (const [value, btn] of buttons) {
        btn.setAttribute('aria-pressed', String(value === current));
        counts.get(value).textContent = countMap && value in countMap ? String(countMap[value]) : '';
      }
    },
  };
}

export function createControls(theme, { filters, onChange, onSearch, onWindow, onReset, onRetry }) {
  const pick = (key) => (value) => { filters[key] = value; onChange(); };
  const kind = choiceGroup('유형', 'kind', KIND_OPTIONS, pick('kind'));
  const mode = choiceGroup('참가 방식', 'mode', MODE_OPTIONS, pick('mode'));
  const sort = choiceGroup('정렬', 'sort', SORT_OPTIONS, pick('sort'));
  const win = choiceGroup('마감 기간', 'window', WINDOW_OPTIONS, onWindow);

  const input = h('input', {
    type: 'search', class: 'search__input', id: `q-${theme}`, autocomplete: 'off', spellcheck: 'false',
    placeholder: '제목, 주최, 태그로 검색', maxlength: '100',
    onInput: (e) => onSearch(e.target.value),
  });
  const search = h('div', { class: 'search' },
    h('label', { class: 'search__label', for: `q-${theme}` }, '검색'), input);

  function sync(m, windowKey = 'all') {
    kind.update(filters.kind, m && m.facets.kind);
    mode.update(filters.mode, m && m.facets.mode);
    sort.update(filters.sort, null);
    win.update(windowKey, m && m.windowCounts);
    if (m === null) input.value = '';
  }
  sync(null);

  return {
    search, kind: kind.el, mode: mode.el, sort: sort.el, window: win.el,
    actions: { reset: onReset, retry: onRetry },
    sync,
  };
}
