// Elite Global Properties lead capture (Vercel serverless function)
// Returns HTTP 200 ONLY when the lead is actually delivered, so the front end
// fires a Google Ads conversion only for real, delivered leads (never on failure).
//
// Configure ONE delivery channel via Vercel Environment Variables:
//   LEAD_WEBHOOK_URL   -> POSTs the lead as JSON (CRM / Zapier / Make / Telegram bridge)
//   RESEND_API_KEY + LEAD_TO_EMAIL [+ LEAD_FROM_EMAIL]  -> emails the lead via Resend
// If neither is set, the function returns 500 and the page shows the call/WhatsApp
// fallback (and fires NO conversion), by design.

// Abuse controls: same-site origin check + a light per-IP rate limit.
// The Map is per warm serverless instance (best effort); use Vercel KV or
// Upstash for a hard global limit if flooding is ever observed.
const RATE = new Map();
const ALLOWED_HOSTS = ['eliteglobal-properties.com', 'www.eliteglobal-properties.com', 'eliteglobal.ae', 'www.eliteglobal.ae', 'localhost:4321'];

function originAllowed(req) {
  const src = req.headers.origin || req.headers.referer || '';
  if (!src) return true; // some in-app browsers strip Origin; the honeypot + rate limit still apply
  try { return ALLOWED_HOSTS.includes(new URL(src).host) || /\.vercel\.app$/.test(new URL(src).hostname); }
  catch { return false; }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }
  if (!originAllowed(req)) return res.status(403).json({ ok: false, error: 'forbidden' });
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  const now = Date.now();
  const hits = (RATE.get(ip) || []).filter((t) => now - t < 60000);
  if (hits.length >= 5) return res.status(429).json({ ok: false, error: 'rate_limited' });
  hits.push(now); RATE.set(ip, hits);
  if (RATE.size > 5000) RATE.clear(); // bound memory on long-lived instances
  const b = req.body || {};
  // Honeypot: bots fill this hidden field.
  if (b.company_website) return res.status(200).json({ ok: true });

  const name = String(b.name || '').trim();
  const phone = String(b.phone || '').trim();
  if (name.length < 2 || phone.replace(/[^\d]/g, '').length < 7) {
    return res.status(422).json({ ok: false, error: 'missing_required' });
  }

  const lead = {
    receivedAt: new Date().toISOString(),
    name,
    phone,
    email: String(b.email || '').trim(),
    purpose: String(b.purpose || '').trim(),
    budget: String(b.budget || '').trim(),
    timeline: String(b.timeline || '').trim(),
    project: String(b.project || '').trim(),
    message: String(b.message || '').trim(),
    language: String(b.lang || '').trim(),
    gclid: String(b.gclid || '').trim(),
    gbraid: String(b.gbraid || '').trim(),
    wbraid: String(b.wbraid || '').trim(),
    page_ref: String(b.page_ref || '').trim(),
    landing_url: String(b.landing_url || '').trim(),
  };

  try {
    let delivered = false;

    if (process.env.LEAD_WEBHOOK_URL) {
      const r = await fetch(process.env.LEAD_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lead),
      });
      if (!r.ok) throw new Error('webhook_' + r.status);
      delivered = true;
    } else if (process.env.RESEND_API_KEY && process.env.LEAD_TO_EMAIL && process.env.LEAD_FROM_EMAIL) {
      const rows = Object.entries(lead)
        .filter(([, v]) => v)
        .map(([k, v]) => `<tr><td style="padding:4px 12px 4px 0;color:#666">${k}</td><td><b>${escapeHtml(v)}</b></td></tr>`)
        .join('');
      const r = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          // Must be an address on a domain verified in Resend (eliteglobal-properties.com).
          // The resend.dev sandbox sender is deliberately NOT used as a fallback: it only
          // delivers to the Resend account owner and silently drops mail to everyone else,
          // which is what previously lost leads addressed to info@eliteglobal-properties.com.
          from: process.env.LEAD_FROM_EMAIL,
          reply_to: lead.email || undefined,
          // LEAD_TO_EMAIL may be a comma-separated list; every address receives the lead.
          to: process.env.LEAD_TO_EMAIL.split(',').map((e) => e.trim()).filter(Boolean),
          subject: `New website lead: ${name} (${phone})`,
          html: `<h2 style="font-family:Georgia,serif">New enquiry from eliteglobal-properties.com</h2><table style="font:14px/1.6 Arial">${rows}</table>`,
        }),
      });
      if (!r.ok) {
        // Log the provider's reason (bad key, unverified sender, rejected recipient)
        // so a broken channel is visible in Vercel logs instead of failing silently.
        const detail = await r.text().catch(() => '');
        console.error('[lead] resend rejected', r.status, detail, 'to=', process.env.LEAD_TO_EMAIL);
        throw new Error('resend_' + r.status);
      }
      delivered = true;
    }

    if (!delivered) {
      // No channel configured: do not report success (would fire a false conversion).
      console.error('[lead] no delivery channel configured — need RESEND_API_KEY + LEAD_TO_EMAIL + LEAD_FROM_EMAIL');
      return res.status(500).json({ ok: false, error: 'delivery_not_configured' });
    }
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[lead] delivery failed', err && err.message, JSON.stringify(lead));
    // The full lead is logged above, so the enquiry is recoverable from Vercel
    // logs even when the email channel is down.
    return res.status(502).json({ ok: false, error: 'delivery_failed' });
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
