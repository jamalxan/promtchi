/* promtchi — ichki (SSR) sahifalar uchun progressive-enhancement effektlar:
   custom kursor va scroll progress. JS o'chirilgan bo'lsa
   hech biri ishlamaydi va sahifa to'liq o'qiladi (SEO/GEO talabi). */
(function () {
  'use strict';

  /* ---------- custom kursor ---------- */
  (function () {
    if (!matchMedia('(hover:hover) and (min-width:961px)').matches) return;
    var dot = document.querySelector('.cur-dot'), tag = document.getElementById('curTag');
    if (!dot || !tag) return;
    var defaultLabel = tag.getAttribute('data-default-label') || '';
    var mx = 0, my = 0, tx = 0, ty = 0, on = false;
    addEventListener('mousemove', function (e) {
      mx = e.clientX; my = e.clientY; dot.style.left = mx + 'px'; dot.style.top = my + 'px';
      if (!on) { on = true; tx = mx; ty = my; document.body.classList.add('cur-on'); dot.style.opacity = tag.style.opacity = 1; }
    });
    document.addEventListener('mouseleave', function () {
      document.body.classList.remove('cur-on'); dot.style.opacity = tag.style.opacity = 0; on = false;
    });
    (function loop() {
      tx += (mx - tx) * .16; ty += (my - ty) * .16;
      tag.style.left = tx + 'px'; tag.style.top = ty + 'px';
      requestAnimationFrame(loop);
    })();
    document.addEventListener('mouseover', function (e) {
      var t = e.target.closest('[data-cursor],.card,.con-a');
      if (!t) return;
      var label = t.getAttribute('data-cursor') || defaultLabel;
      if (!label) return;
      tag.textContent = label; tag.classList.add('show');
    });
    document.addEventListener('mouseout', function (e) {
      if (e.target.closest('[data-cursor],.card,.con-a')) tag.classList.remove('show');
    });
  })();

  /* ---------- scroll progress ---------- */
  (function () {
    var bar = document.getElementById('prog');
    if (!bar) return;
    var ticking = false;
    function update() {
      var h = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + '%';
      ticking = false;
    }
    addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    }, { passive: true });
    update();
  })();
})();
