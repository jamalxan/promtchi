/* promtchi — ichki (SSR) sahifalar uchun progressive-enhancement effekt:
   scroll progress chizig'i. JS o'chirilgan bo'lsa ishlamaydi va sahifa
   to'liq o'qiladi (SEO/GEO talabi). */
(function () {
  'use strict';
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
