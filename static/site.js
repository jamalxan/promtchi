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
     Bosh sahifadagi #faqList bilan AYNAN bir xil xatti-harakat: bosilgan
     savol ochiladi, qolganlari yopiladi, javob balandligi 0 <-> kontent
     balandligi orasida silliq animatsiya qilinadi (.fa-body'dagi max-height
     o'tishi), ochiq savol qayta bosilsa yopiladi.

     Nega JS: <details name="faq"> brauzerning o'zida faqat BIR ZUMDA yopadi
     (avvalgi javob sakrab yo'qoladi) va ochilishda 0 -> 60em o'tishi ham
     animatsiya qilinmaydi. Shuning uchun JS bor ekan, 'name' olib
     tashlanadi va yopish/ochish shu yerda boshqariladi.

     JS o'chiq bo'lsa hech narsa buzilmaydi: HTML'da 'name="faq"' saqlanadi,
     ya'ni zamonaviy brauzer baribir bittadan ochadi, CSS esa
     details[open] .fa-body{max-height:60em} bilan javobni ko'rsatadi.
     Kontent har doim DOM'da — SEO/GEO'ga ta'sir qilmaydi. */
  (function () {
    var each = Array.prototype.forEach;
    var lists = document.querySelectorAll('.faq-list');
    if (!lists.length) return;

    function bodyOf(d) { return d.querySelector('.fa-body'); }

    /* yopish — avval joriy balandlikni px'da qotiramiz, keyin 0 ga
       o'tkazamiz; o'tish tugagach <details>ni yopamiz (kontent a11y
       daraxtidan ham chiqib ketsin). '.closing' klassi + belgisini darhol
       qaytaradi, xuddi bosh sahifadagi .fitem.open klassi olib tashlangandek. */
    function closeItem(d) {
      var b = bodyOf(d);
      if (!b) { d.open = false; return; }
      d.classList.add('closing');
      b.style.maxHeight = b.scrollHeight + 'px';
      void b.offsetHeight;
      b.style.maxHeight = '0px';
      var timer;
      function done(e) {
        if (e && e.propertyName && e.propertyName !== 'max-height') return;
        b.removeEventListener('transitionend', done);
        clearTimeout(timer);
        if (!d.classList.contains('closing')) return; // oraliqda qayta ochilgan
        d.classList.remove('closing');
        d.open = false;
        b.style.maxHeight = '';
      }
      b.addEventListener('transitionend', done);
      timer = setTimeout(done, 700); // transition kelmasa ham yopilsin
    }

    function openItem(d) {
      var b = bodyOf(d);
      d.classList.remove('closing');
      d.open = true;
      if (!b) return;
      b.style.maxHeight = '0px';
      void b.offsetHeight;
      b.style.maxHeight = b.scrollHeight + 'px';
      function grown(e) {
        if (e.propertyName && e.propertyName !== 'max-height') return;
        b.removeEventListener('transitionend', grown);
        /* ochiq javob keyin ham kesilmasin (shrift kech yuklansa, oyna
           kengligi o'zgarsa) — qat'iy px o'rniga cheklovni olib tashlaymiz */
        if (d.open && !d.classList.contains('closing')) b.style.maxHeight = 'none';
      }
      b.addEventListener('transitionend', grown);
    }

    each.call(lists, function (list) {
      each.call(list.children, function (d) {
        /* animatsiyali yopishni JS boshqaradi — aks holda brauzer guruhdagi
           avvalgi savolni bir zumda yopib qo'yadi */
        if (d.tagName === 'DETAILS') d.removeAttribute('name');
      });
      /* Enter/Probel bilan ham 'click' keladi, shuning uchun 'toggle' emas,
         'click' ushlanadi va brauzerning o'z ochishi bekor qilinadi. */
      list.addEventListener('click', function (e) {
        var s = e.target.closest && e.target.closest('summary');
        if (!s) return;
        var d = s.parentElement;
        if (!d || d.tagName !== 'DETAILS' || d.parentElement !== list) return;
        e.preventDefault();
        var isOpen = d.open && !d.classList.contains('closing');
        each.call(list.querySelectorAll('details[open]'), function (other) {
          if (other !== d) closeItem(other);
        });
        if (isOpen) closeItem(d); else openItem(d);
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
