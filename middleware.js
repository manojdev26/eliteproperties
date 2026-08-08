/**
 * Elite Global Properties - automatic language routing
 * Vercel Routing Middleware. Place this file at the REPO ROOT (same level as vercel.json).
 *
 * Zero dependencies on purpose: it reads Vercel's injected geo header directly
 * instead of importing @vercel/functions, so the repo still needs no package.json
 * and no build step.
 *
 * Decision order (first match wins):
 *   1. Search engine crawler          -> no redirect (hreflang does the job)
 *   2. Paid click (gclid and friends) -> no redirect (the ad's final URL is the destination)
 *   3. ?lang=xx in the URL            -> honour it and remember it
 *   4. egp_lang cookie                -> honour the visitor's earlier choice
 *   5. Accept-Language header         -> the browser's own stated preference
 *   6. Country from IP                -> fallback only
 *   7. Nothing matched                -> stay on English
 */

/* Language folders that actually exist in the repo. /it/ and /pt/ went live on
   8 Aug 2026, so they are included. Never add a code here before its folder is
   live: the matcher below assumes every listed language has every matched page,
   and a redirect into a missing folder would 404. */
const SUPPORTED = ['fr', 'de', 'es', 'ru', 'ar', 'it', 'pt'];

/* Country to language, used only when the browser did not state a preference.
   Arabic is deliberately absent: a UAE or Saudi IP does not imply an Arabic
   reader, and most Dubai property buyers browse in English. Arabic is served
   when Accept-Language asks for it, never on geography alone. */
const COUNTRY_TO_LANG = {
  FR: 'fr', BE: 'fr', LU: 'fr', MC: 'fr',

  ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es', VE: 'es',
  EC: 'es', UY: 'es', PY: 'es', BO: 'es', CR: 'es', PA: 'es', DO: 'es',
  GT: 'es', HN: 'es', SV: 'es', NI: 'es', CU: 'es', PR: 'es',

  DE: 'de', AT: 'de', CH: 'de', LI: 'de',

  RU: 'ru', BY: 'ru', KZ: 'ru', KG: 'ru', UZ: 'ru', AM: 'ru',
  AZ: 'ru', MD: 'ru', TJ: 'ru', TM: 'ru',

  IT: 'it', SM: 'it', VA: 'it',

  /* The Portuguese pages are written in European Portuguese, but a Brazilian or
     Angolan reader is still far better served by them than by English. */
  PT: 'pt', BR: 'pt', AO: 'pt', MZ: 'pt', CV: 'pt',
};

/* Only these paths are considered. Every one of them exists inside every
   language folder, so a redirect can never land on a 404.
   /index.html is left out because vercel.json already redirects it to /. */
export const config = {
  matcher: [
    '/',
    '/about.html',
    '/apartments-for-sale-in-dubai.html',
    '/buy-property-in-dubai.html',
    '/dubai-real-estate-investment.html',
    '/off-plan-property-in-dubai.html',
    '/projects.html',
    '/villas-and-townhouses-in-dubai.html',
  ],
};

const BOT_RE = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|pinterest|whatsapp|telegram|lighthouse|gtmetrix|pagespeed|adsbot|mediapartners|google-inspectiontool|chrome-lighthouse/i;

const PAID_PARAMS = ['gclid', 'gbraid', 'wbraid', 'msclkid', 'dclid'];

const COOKIE_NAME = 'egp_lang';

/**
 * Reads Accept-Language and returns 'en', a supported language code, or null.
 * Returns 'en' as soon as English outranks every supported language, so an
 * English speaker sitting in Paris is left on the English site.
 */
function fromAcceptLanguage(header) {
  if (!header) return null;

  const ranked = header
    .split(',')
    .map((part) => {
      const [tag, ...params] = part.trim().split(';');
      const qParam = params.find((p) => p.trim().startsWith('q='));
      const q = qParam ? parseFloat(qParam.split('=')[1]) : 1;
      return { tag: tag.trim().toLowerCase(), q: Number.isNaN(q) ? 0 : q };
    })
    .filter((entry) => entry.tag && entry.tag !== '*')
    .sort((a, b) => b.q - a.q);

  for (const entry of ranked) {
    const base = entry.tag.split('-')[0];
    if (base === 'en') return 'en';
    if (SUPPORTED.includes(base)) return base;
  }
  return null;
}

/**
 * Builds the redirect. The query string is carried over untouched, which is what
 * keeps gclid, utm_* and any Clarity or GA4 parameters alive through the hop.
 */
function redirect(request, lang, remember) {
  const target = new URL(request.url);
  const path = target.pathname;

  target.pathname = lang === 'en'
    ? path
    : '/' + lang + (path === '/' ? '' : path);

  // The lang parameter has done its job. Leaving it on the target URL would make
  // ?lang=en redirect to itself for ever.
  target.searchParams.delete('lang');

  // Hard stop against redirect loops: never send a visitor to the URL they are
  // already on, whatever the rest of the logic decided.
  if (target.toString() === request.url) return;

  const headers = {
    Location: target.toString(),
    // A per visitor redirect must never be cached by the CDN or a shared proxy.
    'Cache-Control': 'no-store, max-age=0',
    Vary: 'Accept-Language, Cookie',
  };

  if (remember) {
    headers['Set-Cookie'] =
      COOKIE_NAME + '=' + lang + '; Path=/; Max-Age=31536000; SameSite=Lax; Secure';
  }

  // 302, not 301. The correct destination differs per visitor, so it must never
  // be treated as a permanent property of the URL.
  return new Response(null, { status: 302, headers });
}

export default function middleware(request) {
  const url = new URL(request.url);
  const path = url.pathname;

  // 1. Crawlers see the page they asked for. hreflang tells them about the rest.
  const ua = request.headers.get('user-agent') || '';
  if (BOT_RE.test(ua)) return;

  // 2. Paid clicks are never redirected. The language of an ad click is decided
  //    by which campaign it came from, so the ad's final URL is already correct.
  for (const param of PAID_PARAMS) {
    if (url.searchParams.has(param)) return;
  }

  // 3. An explicit ?lang= choice wins and is remembered for a year.
  const requested = (url.searchParams.get('lang') || '').toLowerCase();
  if (requested === 'en' || SUPPORTED.includes(requested)) {
    return redirect(request, requested, true);
  }

  // 4. A visitor who has already chosen stays where they chose.
  const cookieHeader = request.headers.get('cookie') || '';
  const saved = /(?:^|;\s*)egp_lang=([a-z]{2})/.exec(cookieHeader);
  if (saved) {
    const lang = saved[1];
    if (lang === 'en') return;
    if (SUPPORTED.includes(lang)) return redirect(request, lang, false);
  }

  // 5. The browser's own preference is the most reliable signal available.
  const fromHeader = fromAcceptLanguage(request.headers.get('accept-language'));
  if (fromHeader === 'en') return;
  if (fromHeader) return redirect(request, fromHeader, false);

  // 6. Geography, only as a fallback.
  const country = (request.headers.get('x-vercel-ip-country') || '').toUpperCase();
  const byCountry = COUNTRY_TO_LANG[country];
  if (byCountry && SUPPORTED.includes(byCountry)) {
    return redirect(request, byCountry, false);
  }

  // 7. Default: English, no redirect, no extra latency.
  return;
}
