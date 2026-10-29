// 미리보기 iframe은 1280px 너비로 그려 두고, 칸 너비에 맞게 축소만 한다.
const FRAME_W = 1280;
const frames = document.querySelectorAll('.g-frame');

function fit(el) {
  el.style.setProperty('--scale', String(el.clientWidth / FRAME_W));
}

if ('ResizeObserver' in window) {
  const ro = new ResizeObserver((entries) => entries.forEach((e) => fit(e.target)));
  frames.forEach((f) => ro.observe(f));
} else {
  frames.forEach(fit);
}
