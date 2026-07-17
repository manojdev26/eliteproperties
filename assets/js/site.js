/* Elite Global Properties - site behaviour + conversion tracking
   Consent Mode v2 default is set INLINE in <head> before GTM (see each page).
   Conversions fire ONLY on a real HTTP 200 from the lead endpoint. */
(function () {
  'use strict';
  var EGP = window.EGP || {};
  var AW = EGP.ads || 'AW-18195945164';
  function dl(o){ window.dataLayer = window.dataLayer || []; window.dataLayer.push(o); }
  function gtagSafe(){ if (typeof window.gtag === 'function') window.gtag.apply(null, arguments); }
  // Google Ads conversions. gtag.js is loaded async in <head>; calls made before
  // it arrives queue in dataLayer, so none are lost. Each type fires once per view.
  var fired = {};
  function convert(label, extra){
    if (!label || fired[label]) return;
    fired[label] = true;
    var p = { send_to: AW + '/' + label };
    if (extra) for (var k in extra) p[k] = extra[k];
    gtagSafe('event', 'conversion', p);
  }
  function toast(msg){ var t=document.getElementById('toast'); if(!t) return;
    t.textContent=msg; t.classList.add('show'); clearTimeout(t._t); t._t=setTimeout(function(){t.classList.remove('show');},2600); }

  /* --- Mobile drawer (accessible: inert when closed, focus trap + restore) --- */
  var body=document.body;
  var drawer=document.querySelector('.drawer');
  var menuTrigger=null;
  function openMenu(btn){ body.classList.add('menu-open'); if(drawer){ drawer.removeAttribute('inert');
    var f=drawer.querySelector('a[href],button'); if(f) setTimeout(function(){f.focus();},50); } menuTrigger=btn||menuTrigger; }
  function closeMenu(){ if(!body.classList.contains('menu-open')) return; body.classList.remove('menu-open');
    if(drawer) drawer.setAttribute('inert','');
    if(menuTrigger && menuTrigger.focus) menuTrigger.focus(); }
  document.querySelectorAll('[data-menu-open]').forEach(function(b){b.addEventListener('click',function(){openMenu(b);});});
  document.querySelectorAll('[data-menu-close]').forEach(function(b){b.addEventListener('click',closeMenu);});
  document.querySelectorAll('.drawer nav a').forEach(function(a){a.addEventListener('click',closeMenu);});
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') closeMenu(); });
  document.addEventListener('keydown',function(e){ // focus trap within drawer while open
    if(e.key!=='Tab'||!body.classList.contains('menu-open')||!drawer) return;
    var f=drawer.querySelectorAll('a[href],button'); if(!f.length) return;
    var first=f[0], last=f[f.length-1];
    if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
  });

  /* --- Reveal on scroll (with failsafe so content is never left invisible) --- */
  var reveals=document.querySelectorAll('.reveal');
  function revealAll(){ reveals.forEach(function(el){el.classList.add('in');}); }
  if('IntersectionObserver' in window && reveals.length){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.12,rootMargin:'0px 0px -8% 0px'});
    reveals.forEach(function(el){io.observe(el);});
    // Failsafe: if the observer never fired (nothing revealed after 1.6s), show everything.
    setTimeout(function(){ if(!document.querySelector('.reveal.in')) revealAll(); },1600);
  } else { revealAll(); }

  /* --- Capture gclid / gbraid / wbraid + referrer into hidden fields --- */
  var qp=new URLSearchParams(location.search);
  ['gclid','gbraid','wbraid'].forEach(function(k){
    var v=qp.get(k); if(!v){ try{v=sessionStorage.getItem('egp_'+k);}catch(e){} } if(!v) return;
    try{sessionStorage.setItem('egp_'+k,v);}catch(e){}
    document.querySelectorAll('input[name="'+k+'"]').forEach(function(el){ if(!el.value) el.value=v; });
  });
  document.querySelectorAll('input[name="page_ref"]').forEach(function(el){ if(!el.value) el.value=(document.referrer||'direct'); });
  document.querySelectorAll('input[name="landing_url"]').forEach(function(el){ if(!el.value) el.value=location.href; });

  /* --- Lead form --- */
  document.querySelectorAll('form.lead-form').forEach(function(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();
      var hp=form.querySelector('input[name="company_website"]'); // honeypot
      if(hp && hp.value) return;                                   // silently drop bots
      if(!form.checkValidity()){ form.reportValidity(); return; }  // enforce required fields (form is novalidate for styling)
      var btn=form.querySelector('[type=submit]');
      var okBox=form.querySelector('.form-msg.ok'), errBox=form.querySelector('.form-msg.err');
      if(errBox) errBox.hidden=true;
      if(btn){ btn.disabled=true; btn._label=btn.textContent; btn.textContent=btn.getAttribute('data-sending')||'Sending…'; }
      var fd=new FormData(form);
      var body=new URLSearchParams(); fd.forEach(function(v,k){ body.append(k,v); });
      fetch(form.getAttribute('action')||'/api/lead',{method:'POST',body:body,headers:{'Accept':'application/json'}})
        .then(function(r){ if(!r.ok) throw new Error('bad'); return r; })
        .then(function(){
          var redir=form.getAttribute('data-thankyou');
          var went=false;
          var go=function(){ if(went||!redir) return; went=true; location.href=redir; };
          if(!form._leadSent){ form._leadSent=true;
            dl({event:'lead_form_submit',
              lead_budget:(fd.get('budget')||''),
              lead_source:(form.getAttribute('data-page')||'')});
            // Redirect when Google confirms the conversion ping, with a 1200ms
            // fallback so a blocked gtag can never strand the visitor.
            convert(EGP.leadLabel, {value:1.0, currency:'AED', event_callback: go});
          }
          form.reset();
          if(okBox){ okBox.hidden=false; okBox.setAttribute('tabindex','-1'); okBox.focus(); }
          setTimeout(go, 1200);
        })
        .catch(function(){
          if(btn){ btn.disabled=false; btn.textContent=btn._label; }
          if(errBox){ errBox.hidden=false; errBox.setAttribute('tabindex','-1'); errBox.focus(); }
        });
    });
  });

  /* --- Phone + WhatsApp taps: dataLayer event AND a Google Ads conversion
     ("Website Call" / "WhatsApp Website" actions, labels read live from the
     Ads account). WhatsApp is the dominant UAE enquiry channel, so these taps
     are conversions in their own right, not just analytics events. --- */
  document.addEventListener('click',function(e){
    var a=e.target.closest('a[href^="tel:"], a[href*="wa.me"], a[href*="api.whatsapp"]');
    if(!a) return;
    var isCall=a.getAttribute('href').indexOf('tel:')===0;
    dl({event:isCall?'call_click':'whatsapp_click', page_ref:(document.title||'')});
    convert(isCall ? EGP.callLabel : EGP.waLabel);
  });

  /* --- Consent banner: shown only in European timezones (EEA/UK/CH), where
     Consent Mode defaults to denied. Accept flips consent to granted so real
     (not modeled) conversions and remarketing work in the primary target geo. --- */
  (function(){
    var el=document.getElementById('consent');
    if(!el) return;
    var KEY='egp_consent';
    var saved=null; try{ saved=localStorage.getItem(KEY); }catch(e){}
    var tz=''; try{ tz=Intl.DateTimeFormat().resolvedOptions().timeZone||''; }catch(e){}
    var european=tz.indexOf('Europe/')===0;
    function grant(){ gtagSafe('consent','update',{ad_storage:'granted',ad_user_data:'granted',ad_personalization:'granted',analytics_storage:'granted'}); }
    if(saved==='granted'){ grant(); return; }
    if(saved==='denied'){ return; }
    if(!european) return;               /* non-EU regions are granted by default */
    el.classList.add('show');
    el.querySelectorAll('[data-consent]').forEach(function(b){
      b.addEventListener('click',function(){
        var v=b.getAttribute('data-consent')==='grant'?'granted':'denied';
        try{ localStorage.setItem(KEY,v); }catch(e){}
        if(v==='granted') grant();
        el.classList.remove('show');
      });
    });
  })();

  window.egpToast=toast;
})();
