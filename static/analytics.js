/* promtchi — GA4 hodisa kuzatuvi (TZ 17-bo'lim). gtag() bazaviy loader base.html/
   static/index*.html'da alohida ulanadi; bu fayl faqat click-delegatsiyani beradi. */
(function () {
  if (typeof gtag !== 'function') return;

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a || !a.href) return;
    var href = a.href;

    if (href.indexOf('tel:') === 0) {
      gtag('event', 'phone_click', { link_url: href });
    } else if (href.indexOf('mailto:') === 0) {
      gtag('event', 'email_click', { link_url: href });
    } else if (href.indexOf('t.me/') !== -1 || href.indexOf('telegram.me/') !== -1) {
      gtag('event', 'telegram_click', { link_url: href });
    } else if (/\/portfolio\/[^/]+\/?(#.*)?$/.test(href)) {
      gtag('event', 'portfolio_click', { link_url: href });
    } else if (/\/xizmatlar\/[^/]+\/?(#.*)?$/.test(href)) {
      /* TZ 19-bo'lim: "Blog -> service click" — maqoladan xizmat sahifasiga
         o'tish alohida hodisa sifatida yoziladi (qaysi maqola konvertsiya
         beradi degan savolga javob); boshqa sahifalardan kelgan klik esa
         oddiy service_click bo'lib qoladi. */
      var fromBlog = /\/blog\//.test(location.pathname);
      gtag('event', fromBlog ? 'blog_to_service_click' : 'service_click', {
        link_url: href,
        page_path: location.pathname,
      });
    }

    if (a.classList.contains('btn-acid')) {
      gtag('event', 'cta_click', {
        link_text: (a.textContent || '').trim().slice(0, 60),
        page_path: location.pathname,
      });
    }
  }, { passive: true });

  var typeSelect = document.getElementById('cf-type') || document.getElementById('fS');
  if (typeSelect) {
    typeSelect.addEventListener('change', function () {
      gtag('event', 'select_project_type', { project_type: typeSelect.value });
    });
  }
})();
