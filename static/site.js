/* promtchi — ichki (SSR) sahifalar uchun progressive-enhancement effektlar:
   custom kursor (bosh sahifadagi kabi) va scroll progress chizig'i.
   JS o'chirilgan bo'lsa ikkalasi ham ishlamaydi va sahifa to'liq o'qiladi
   (SEO/GEO talabi) — brauzerning oddiy kursori ishlaydi. */
(function () {
  'use strict';

  /* ---------- custom kursor ---------- */
  (function () {
    /* faqat sichqonchali va keng ekranlarda — touch qurilmalarda kerak emas */
    if (!matchMedia('(hover:hover) and (min-width:961px)').matches) return;
    var dot = document.querySelector('.cur-dot'), tag = document.getElementById('curTag');
    if (!dot || !tag) return;
    var defaultLabel = tag.getAttribute('data-default-label') || '';
    var mx = 0, my = 0, tx = 0, ty = 0, on = false;

    /* Sahifa yangi ochilganda 'mousemove' hali bo'lmaydi — foydalanuvchi
       havolani bosib kelib, sichqonchani qimirlatmay o'qiy boshlasa brauzerning
       oddiy strelkasi ko'rinib qolardi. Shuning uchun kursorni koordinata bergan
       HAR QANDAY birinchi hodisada yoqamiz: harakat, hover, bosish va scroll. */
    function point(e) {
      if (typeof e.clientX !== 'number') return;
      mx = e.clientX; my = e.clientY;
      dot.style.left = mx + 'px'; dot.style.top = my + 'px';
      if (!on) {
        on = true; tx = mx; ty = my;
        document.body.classList.add('cur-on');
        dot.style.opacity = tag.style.opacity = 1;
      }
    }

    addEventListener('mousemove', point, { passive: true });
    addEventListener('mouseover', point, { passive: true });
    addEventListener('mousedown', point, { passive: true });
    addEventListener('wheel', point, { passive: true });

    document.addEventListener('mouseleave', function () {
      document.body.classList.remove('cur-on');
      dot.style.opacity = tag.style.opacity = 0;
      tag.classList.remove('show');
      on = false;
    });

    /* yorliq nuqtadan biroz orqada, yumshoq ergashadi */
    (function loop() {
      tx += (mx - tx) * .16; ty += (my - ty) * .16;
      tag.style.left = tx + 'px'; tag.style.top = ty + 'px';
      requestAnimationFrame(loop);
    })();

    var HOT = '[data-cursor],.card,.con-a,.faq-list summary,.btn';
    document.addEventListener('mouseover', function (e) {
      var t = e.target.closest(HOT);
      if (!t) return;
      var label = t.getAttribute('data-cursor') || defaultLabel;
      if (!label) return;
      tag.textContent = label;
      tag.classList.add('show');
    });
    document.addEventListener('mouseout', function (e) {
      if (e.target.closest(HOT)) tag.classList.remove('show');
    });
  })();

  /* ---------- FAQ akkordeon: bir vaqtda faqat bitta savol ochiq ----------
     Bosh sahifadagi #faqList bilan bir xil xatti-harakat. Zamonaviy brauzerlar
     buni <details name="faq"> orqali o'zi bajaradi, bu kod esa eski
     brauzerlar (Chrome<120, Safari<17.2, Firefox<130) uchun zaxira.
     JS o'chiq bo'lsa savollar oddiy <details> bo'lib ochilaveradi — kontent
     baribir DOM'da, SEO/GEO'ga ta'sir qilmaydi. */
  (function () {
    var each = Array.prototype.forEach;
    each.call(document.querySelectorAll('.faq-list'), function (list) {
      /* 'toggle' hodisasi asinxron ishlaydi va ikkala savol bir lahza ochiq
         qolardi — shuning uchun 'click'da, brauzer <details>ni ochishidan
         oldin qolganlarini yopamiz. Enter/Probel bilan ham 'click' keladi. */
      list.addEventListener('click', function (e) {
        var s = e.target.closest('summary');
        if (!s) return;
        var d = s.parentElement;
        if (!d || d.tagName !== 'DETAILS' || d.parentElement !== list) return;
        each.call(list.querySelectorAll('details[open]'), function (other) {
          if (other !== d) other.open = false;
        });
      });
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
