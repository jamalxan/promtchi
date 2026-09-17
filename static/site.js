/* promtchi — ichki (SSR) sahifalar uchun progressive-enhancement kursor.
   JS o'chirilgan yoki hover/pointer bo'lmagan qurilmalarda hech narsa qilmaydi —
   sahifa bu skriptsiz ham to'liq ishlaydi (SEO/GEO talabi). */
(function(){
  if(!matchMedia('(hover:hover) and (min-width:961px)').matches)return;
  var dot=document.querySelector('.cur-dot'),tag=document.getElementById('curTag');
  if(!dot||!tag)return;
  var defaultLabel=tag.getAttribute('data-default-label')||'';
  var mx=0,my=0,tx=0,ty=0,on=false;
  addEventListener('mousemove',function(e){
    mx=e.clientX;my=e.clientY;dot.style.left=mx+'px';dot.style.top=my+'px';
    if(!on){on=true;tx=mx;ty=my;document.body.classList.add('cur-on');dot.style.opacity=tag.style.opacity=1;}
  });
  document.addEventListener('mouseleave',function(){
    document.body.classList.remove('cur-on');dot.style.opacity=tag.style.opacity=0;on=false;
  });
  (function loop(){
    tx+=(mx-tx)*.16;ty+=(my-ty)*.16;
    tag.style.left=tx+'px';tag.style.top=ty+'px';
    requestAnimationFrame(loop);
  })();
  document.addEventListener('mouseover',function(e){
    var t=e.target.closest('[data-cursor],.card');
    if(!t)return;
    var label=t.getAttribute('data-cursor')||defaultLabel;
    if(!label)return;
    tag.textContent=label;tag.classList.add('show');
  });
  document.addEventListener('mouseout',function(e){
    if(e.target.closest('[data-cursor],.card'))tag.classList.remove('show');
  });
})();
