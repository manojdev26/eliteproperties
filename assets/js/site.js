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
  function closeLangSwitches(){ document.querySelectorAll('details.lang-switch[open]').forEach(function(d){
    var hadFocus=d.contains(document.activeElement);
    d.removeAttribute('open');
    if(hadFocus){ var s=d.querySelector('summary'); if(s) s.focus(); }
  }); }
  function openMenu(btn){ closeLangSwitches(); body.classList.add('menu-open'); if(drawer){ drawer.removeAttribute('inert');
    var f=drawer.querySelector('a[href],button'); if(f) setTimeout(function(){f.focus();},50); } menuTrigger=btn||menuTrigger; }
  function closeMenu(){ if(!body.classList.contains('menu-open')) return; body.classList.remove('menu-open');
    if(drawer) drawer.setAttribute('inert','');
    if(menuTrigger && menuTrigger.focus) menuTrigger.focus(); }
  document.querySelectorAll('[data-menu-open]').forEach(function(b){b.addEventListener('click',function(){openMenu(b);});});
  document.querySelectorAll('[data-menu-close]').forEach(function(b){b.addEventListener('click',closeMenu);});
  document.querySelectorAll('.drawer nav a').forEach(function(a){a.addEventListener('click',closeMenu);});
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'){ closeMenu(); closeLangSwitches(); } });
  document.addEventListener('keydown',function(e){ // focus trap within drawer while open
    if(e.key!=='Tab'||!body.classList.contains('menu-open')||!drawer) return;
    var f=drawer.querySelectorAll('a[href],button'); if(!f.length) return;
    var first=f[0], last=f[f.length-1];
    if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
  });

  /* --- Language switcher (details/summary): close on outside click, and close
     the mobile drawer if it opens (avoid two floating panels at once) --- */
  document.addEventListener('click',function(e){
    document.querySelectorAll('details.lang-switch[open]').forEach(function(d){ if(!d.contains(e.target)) d.removeAttribute('open'); });
  });
  document.querySelectorAll('details.lang-switch').forEach(function(d){
    // Tabbing past the last link with no other close trigger would otherwise
    // leave the panel visibly open; close once focus leaves the widget entirely.
    d.addEventListener('focusout',function(e){
      if(!d.open) return;
      setTimeout(function(){ if(!d.contains(document.activeElement)) d.removeAttribute('open'); },0);
    });
    d.addEventListener('toggle',function(){ if(d.open) closeMenu(); });
  });

  /* --- Remember a manual language choice -------------------------------------
     Required by the automatic language routing in /middleware.js. Without it a
     visitor auto-sent to, say, /fr/ could never get back: clicking English goes
     to "/", the middleware re-reads their French browser setting and returns
     them to /fr/ again. Writing the cookie the middleware checks (it is read
     BEFORE Accept-Language) makes a deliberate choice stick for a year.
     Delegated so it survives any re-render, and it reads the hreflang already
     on the switcher anchors, so no page markup had to change. --- */
  (function(){
    var LANGS=['en','fr','de','es','ru','ar','it','pt'];
    document.addEventListener('click',function(e){
      var a=e.target.closest && e.target.closest('a[hreflang]');
      if(!a) return;
      /* The footer blog link also carries hreflang="en". It is a link to an
         English article, not a request to browse the site in English. */
      var href=a.getAttribute('href')||'';
      if(href.indexOf('/blog')===0) return;
      var lang=(a.getAttribute('hreflang')||'').toLowerCase();
      if(LANGS.indexOf(lang)===-1) return;
      document.cookie='egp_lang='+lang+';path=/;max-age=31536000;samesite=lax'+(location.protocol==='https:'?';secure':'');
    },{passive:true});
  })();

  /* --- Reveal on scroll (with failsafe so content is never left invisible) --- */
  var reveals=document.querySelectorAll('.reveal');
  function revealAll(){ reveals.forEach(function(el){el.classList.add('in');}); }
  if('IntersectionObserver' in window && reveals.length){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.12,rootMargin:'0px 0px -8% 0px'});
    reveals.forEach(function(el){io.observe(el);});
    // Failsafe: if the observer never fired (nothing revealed after 1.6s), show everything.
    setTimeout(function(){ if(!document.querySelector('.reveal.in')) revealAll(); },1600);
  } else { revealAll(); }

  /* --- Phone field: country code follows the PAGE, not the visitor ------------
     The dial code shown is the one for the language/region page being viewed
     (data-dial-default in the markup: pt -> +351, it -> +39, fr -> +33, and so
     on). It is deliberately NOT geo-detected from the visitor's device: a
     Portuguese page must show +351 even when read from India, otherwise the
     visitor is prompted for the wrong country's number.

     The placeholder itself is already correct in the HTML, so nothing here
     changes what is displayed. This only makes sure the code is actually
     PRESENT on the submitted number when someone types a local number, so the
     sales team always receives a dialable international number. --- */
  function pagePhoneDial(form){
    var el=form && form.querySelector('input[name="phone"][data-dial-default]');
    return el ? el.getAttribute('data-dial-default') : '';
  }
  /* National trunk prefix that must be dropped when converting a locally
     written number to international form. Italy is the deliberate exception:
     Italian landlines keep their leading 0 internationally (+39 06 ...), and
     Italian mobiles never carry one, so nothing is stripped there. */
  var TRUNK={'+44':'0','+33':'0','+49':'0','+34':'','+351':'0','+39':'','+7':'8','+971':'0','+1':''};
  function toInternational(raw, dial){
    var v=String(raw||'').trim();
    if(!v || !dial) return v;
    if(v.charAt(0)==='+') return v;                    /* already international */
    var digits=v.replace(/[^\d]/g,'');
    if(!digits) return v;                              /* nothing usable, leave alone */
    if(v.indexOf('00')===0) return '+'+digits.replace(/^00/,'');
    var cc=dial.replace(/[^\d]/g,'');
    if(digits.indexOf(cc)===0) return '+'+digits;      /* code typed without the plus */
    var trunk=TRUNK[dial];
    if(trunk && digits.indexOf(trunk)===0) digits=digits.slice(trunk.length);
    return dial+digits;
  }

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
      // Normalise the phone to international form using THIS page's country
      // code, so someone who typed only their local number still reaches us as
      // a dialable number. Runs before FormData so both the POST and the
      // WhatsApp fallback below carry the same corrected value.
      var phoneEl=form.querySelector('input[name="phone"][data-dial-default]');
      if(phoneEl && phoneEl.value) phoneEl.value=toInternational(phoneEl.value, pagePhoneDial(form));
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
          // Delivery-safety net: if the server cannot deliver the lead (e.g. the
          // email/webhook channel is not configured), hand the enquiry off to
          // WhatsApp pre-filled with what the visitor typed, so no lead is lost.
          // The number is read from the error box's wa.me link, so it stays in
          // sync sitewide and per-locale without hardcoding it here.
          try{
            var waHref=(errBox&&errBox.querySelector('a[href*="wa.me"]')||{}).href||'';
            var num=(waHref.match(/wa\.me\/(\d+)/)||[])[1];
            if(num){
              var name=(fd.get('name')||'').toString().trim();
              var phone=(fd.get('phone')||'').toString().trim();
              var budget=(fd.get('budget')||'').toString().trim();
              var timeline=(fd.get('timeline')||'').toString().trim();
              var lines=['Hi Elite Global, I just submitted an enquiry on your website and would like the current Dubai price list and floor plans.'];
              if(name) lines.push('Name: '+name);
              if(phone) lines.push('Phone: '+phone);
              if(budget) lines.push('Budget: '+budget);
              if(timeline) lines.push('Timeline: '+timeline);
              window.open('https://wa.me/'+num+'?text='+encodeURIComponent(lines.join('\n')),'_blank','noopener');
            }
          }catch(_){}
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
