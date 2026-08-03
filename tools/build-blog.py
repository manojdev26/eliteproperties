#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build static blog pages for Elite Global Properties.

Reads the markdown articles in content/blog/, extracts the shared page shell
(head CSS, header, footer, forms, scripts) from about.html so the blog inherits
the exact site design system, and writes:

  blog/index.html          blog listing page
  blog/<slug>.html         one page per article

Also rewrites sitemap.xml to include the new URLs.

Run:  python tools/build-blog.py
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "blog")
OUT = os.path.join(ROOT, "blog")
SHELL_PAGE = os.path.join(ROOT, "about.html")
SITE = "https://eliteglobal-properties.com"

# Hero background images reused from the existing project imagery, chosen so
# adjacent articles in the listing do not repeat the same picture.
HERO = {
    "buy-property-in-dubai-as-a-foreigner": "address-zabeel",
    "off-plan-property-dubai-guide": "avarra",
    "uae-golden-visa-property-investment": "palace-hillside",
    "dubai-rental-yield-roi-guide": "kanyon",
    "best-areas-to-buy-property-in-dubai": "bella",
    "branded-residences-dubai": "address-zabeel",
    "cost-of-buying-property-in-dubai": "sobha-city",
    "villa-or-apartment-dubai": "mareva",
    "buying-dubai-property-from-abroad": "hado",
    "verify-dubai-property-developer": "al-ghadeer-gardens",
}


# Social copy, distinct from the search title/description. Open Graph is
# phrased for a link preview; Twitter is shorter and more direct. Keeping all
# three different means each surface gets copy written for it.
SOCIAL = {
    "buy-property-in-dubai-as-a-foreigner": {
        "og_title": "Yes, foreigners can own property in Dubai outright",
        "og_desc": "Freehold ownership, designated areas, and a title deed in your own name. What overseas buyers actually need to know before they commit.",
        "tw_title": "Can foreigners buy property in Dubai?",
        "tw_desc": "Short answer: yes, freehold, in your own name. Here is where, and what to check first.",
    },
    "off-plan-property-dubai-guide": {
        "og_title": "Off-plan in Dubai: the case for it, and the risks",
        "og_desc": "Lower entry prices and staged payment plans, set against construction timing and delivery risk. A candid look from a RERA-registered brokerage.",
        "tw_title": "Off-plan property in Dubai, explained",
        "tw_desc": "Why buyers choose it, what escrow protects, and when a finished unit is the better call.",
    },
    "uae-golden-visa-property-investment": {
        "og_title": "The Golden Visa property route, without the myths",
        "og_desc": "What actually qualifies, how family inclusion works, and why an off-plan purchase and a residency timeline are not the same thing.",
        "tw_title": "UAE Golden Visa through property",
        "tw_desc": "It is a residence visa, not citizenship. Here is what qualifies and what to verify.",
    },
    "dubai-rental-yield-roi-guide": {
        "og_title": "Most Dubai yield figures you see are gross",
        "og_desc": "Service charges, voids and management fees decide what you actually keep. The net yield calculation, worked through line by line.",
        "tw_title": "How to calculate Dubai rental yield properly",
        "tw_desc": "Gross yield flatters. Net yield is what you bank. Here is the arithmetic.",
    },
    "best-areas-to-buy-property-in-dubai": {
        "og_title": "There is no best area in Dubai, only the right one",
        "og_desc": "Palm Jumeirah, Dubai Hills, Business Bay, The Oasis and the emerging waterfront. Which buyer each community actually suits, and the trade-offs.",
        "tw_title": "Where to buy in Dubai, by buyer type",
        "tw_desc": "Beachfront, family, central or emerging. Match the address to your goal first.",
    },
    "branded-residences-dubai": {
        "og_title": "Branded residences: what the premium actually buys",
        "og_desc": "Enforced specification, hotel-standard service and a name that travels, weighed against higher service charges and what that does to net yield.",
        "tw_title": "Are branded residences worth it in Dubai?",
        "tw_desc": "Sometimes. It depends on whether you will use what you are paying for.",
    },
    "cost-of-buying-property-in-dubai": {
        "og_title": "The Dubai purchase costs nobody totals up front",
        "og_desc": "DLD registration, Oqood, trustee fees and the annual service charges that follow. A budgeting framework you can ask to be filled in writing.",
        "tw_title": "What buying in Dubai really costs",
        "tw_desc": "Beyond the price: registration, trustee and admin fees, plus what recurs every year.",
    },
    "villa-or-apartment-dubai": {
        "og_title": "Villa or apartment? It is a purpose question",
        "og_desc": "Yield, tenant profile, service charges and maintenance all pull in different directions. How to decide before you start comparing floor plans.",
        "tw_title": "Villa or apartment in Dubai?",
        "tw_desc": "Apartments win on yield and liquidity. Villas win on space and tenancy length.",
    },
    "buying-dubai-property-from-abroad": {
        "og_title": "Buying in Dubai from the UK or Europe, remotely",
        "og_desc": "Virtual viewings, remote reservation, escrow payments and handover. How overseas buyers complete a purchase without flying in.",
        "tw_title": "Buy Dubai property without flying in",
        "tw_desc": "View, reserve, pay and complete remotely. Here is the process, and what to verify.",
    },
    "verify-dubai-property-developer": {
        "og_title": "Twenty minutes of checks before you transfer anything",
        "og_desc": "ORN, BRN, Trakheesi permit and the escrow account named in your SPA. The verification list we would want our own family to follow.",
        "tw_title": "Verify before you pay in Dubai",
        "tw_desc": "Check the broker, the permit and the escrow account. Never pay a personal account.",
    },
}


# --------------------------------------------------------------------------
# Markdown article parsing
# --------------------------------------------------------------------------

def field(text, label):
    """Pull a '**Label:** value' metadata line from the article header."""
    m = re.search(r"^\*\*%s:\*\*\s*(.+?)\s*$" % re.escape(label), text, re.M)
    return m.group(1).strip() if m else ""


def strip_char_note(value):
    """'Some Title (48 chars)' -> 'Some Title'."""
    return re.sub(r"\s*\(\d+\s*chars?\)\s*$", "", value).strip()


def parse_article(path):
    raw = open(path, encoding="utf-8").read()

    body = re.search(r"^## Blog Content\s*(.*?)^---\s*$", raw, re.S | re.M)
    if not body:
        raise SystemExit("No '## Blog Content' section in %s" % path)
    body = body.group(1).strip()

    slug = field(raw, "URL Slug").replace("/blog/", "").strip("/")

    # Featured image ALT is the first ALT under Image Suggestions.
    alt = re.search(r"\*\*ALT:\*\*\s*(.+)", raw)

    return {
        "path": path,
        "slug": slug,
        "title": strip_char_note(field(raw, "SEO Title")),
        "keyword": field(raw, "Primary Keyword"),
        "desc": strip_char_note(field(raw, "Meta Description")),
        "read": field(raw, "Estimated Reading Time"),
        "alt": alt.group(1).strip() if alt else "Dubai property",
        "body": body,
    }


# --------------------------------------------------------------------------
# Minimal markdown -> HTML for the article body
# --------------------------------------------------------------------------

def inline(text):
    """Links, bold, italic. Escapes first so authored text cannot inject HTML."""
    text = html.escape(text, quote=False)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith(SITE):
            href = href[len(SITE):] or "/"
            return '<a href="%s">%s</a>' % (href, label)
        return ('<a href="%s" rel="nofollow noopener" target="_blank">%s</a>'
                % (href, label))

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    return text


def render_table(rows):
    head, body = rows[0], rows[2:]          # rows[1] is the ---|--- separator
    out = ['<div class="table-scroll"><table><thead><tr>']
    out += ["<th>%s</th>" % inline(c) for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_to_html(md):
    """
    Converts the article body. Returns (intro_html, faq_pairs, cta_html).

    The FAQ block is pulled out so it can render as the site's <details>
    accordion and feed FAQPage schema, matching how FAQs behave elsewhere
    on the site.
    """
    lines = md.split("\n")
    out, faq, i = [], [], 0
    in_faq = False
    in_cta = False
    cta = []
    q = None

    def flush_list(buf, tag):
        if buf:
            out.append("<%s>%s</%s>" % (tag, "".join(buf), tag))
            del buf[:]

    ul, ol = [], []

    while i < len(lines):
        line = lines[i].rstrip()

        # tables
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            flush_list(ul, "ul"); flush_list(ol, "ol")
            out.append(render_table(rows))
            continue

        if not line.strip():
            flush_list(ul, "ul"); flush_list(ol, "ol")
            i += 1
            continue

        h = re.match(r"^(#{1,3})\s+(.*)$", line)
        if h:
            flush_list(ul, "ul"); flush_list(ol, "ol")
            level, text = len(h.group(1)), h.group(2).strip()

            if level == 1:                       # H1 lives in the hero
                i += 1
                continue

            if level == 2:
                low = text.lower()
                in_faq = "frequently asked" in low
                # Everything from the final CTA heading onward is the closing
                # block, rendered inside the enquiry section.
                in_cta = not in_faq and (
                    low.startswith("talk to") or low.startswith("get ")
                    or low.startswith("speak to") or low.startswith("run your")
                    or low.startswith("compare branded") or low.startswith("buy with")
                    or low.startswith("verify us")
                )
                if in_faq or in_cta:
                    i += 1
                    continue
                out.append("<h2>%s</h2>" % inline(text))
                i += 1
                continue

            if level == 3:
                if in_faq:
                    q = text
                else:
                    (cta if in_cta else out).append("<h3>%s</h3>" % inline(text))
                i += 1
                continue

        if line.startswith("- "):
            ul.append("<li>%s</li>" % inline(line[2:]))
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            ol.append("<li>%s</li>" % inline(m.group(1)))
            i += 1
            continue

        # paragraph
        para = inline(line.strip())
        if in_faq and q:
            faq.append((q, line.strip()))
            q = None
        elif in_cta:
            cta.append("<p>%s</p>" % para)
        else:
            cls = ' class="lead"' if not out else ""
            out.append("<p%s>%s</p>" % (cls, para))
        i += 1

    flush_list(ul, "ul"); flush_list(ol, "ol")
    return "".join(out), faq, "".join(cta)


# --------------------------------------------------------------------------
# Shell extraction
# --------------------------------------------------------------------------

def load_shell():
    src = open(SHELL_PAGE, encoding="utf-8").read()

    style = re.search(r"<style>.*?</style>", src, re.S).group(0)

    # Everything from <body> to <main> is the header + mobile menu.
    header = re.search(r"(<body>.*?)<main id=\"main\">", src, re.S).group(1)

    # Enquiry section, footer and tail scripts.
    enquire = re.search(
        r'(<section class="section on-cream-2" id="enquire">.*?</section>)'
        r'<section class="section" id="invest">', src, re.S).group(1)
    tail = re.search(r"(</main>.*?</body>)", src, re.S).group(1)

    # The shared shell markup is authored for about.html. Neutralise the
    # page-specific bits so blog pages do not claim to be the About page.
    header = header.replace(' aria-current="page"', "")
    header = re.sub(r'href="/(fr|de|ru|ar)/about\.html"',
                    lambda m: 'href="/%s/"' % m.group(1), header)
    header = header.replace('<a href="/about.html" hreflang="en" aria-current="true" lang="en">EN</a>',
                            '<a href="/blog" hreflang="en" aria-current="true" lang="en">EN</a>')
    enquire = enquire.replace('data-page="about"', 'data-page="blog"')

    return style, header, enquire, tail


EXTRA_CSS = """
<style>
/* ---- Blog ---- */
.post-meta{margin-top:16px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;
  font-size:.82rem;color:rgba(255,255,255,.72)}
.post-meta .dot{width:4px;height:4px;border-radius:50%;background:var(--champagne);opacity:.8}
.prose ol{padding-inline-start:22px}
.prose ol li{margin-top:10px}
.prose table{width:100%;border-collapse:collapse;margin-top:22px;font-size:.92rem}
.prose th,.prose td{padding:11px 13px;border:1px solid var(--line-2);text-align:start;vertical-align:top}
.prose th{background:var(--paper-soft);font-weight:700;color:var(--ink)}
.prose td{color:var(--muted)}
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.prose blockquote{margin:22px 0;padding:16px 20px;border-inline-start:3px solid var(--champagne);
  background:var(--paper-soft);border-radius:var(--r-sm);color:var(--muted)}
.post-faq{margin-top:44px}
.post-faq h2{font-size:1.6rem;margin-bottom:18px}
/* The article is a run of consecutive .section blocks (body, FAQ, CTA, nav).
   Collapse the doubled padding where they meet so the prose reads as one
   column rather than as separate stacked bands. */
.post-body{padding-bottom:0}
.post-body + .section,.post-body ~ .section{padding-top:26px}
.post-nav{margin-top:44px;padding-top:26px;border-top:1px solid var(--line-2);
  display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:center}
.post-nav a{color:var(--champagne-deep);text-decoration:underline;font-size:.94rem}
.crumbs{font-size:.8rem;color:rgba(255,255,255,.7);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.crumbs a{text-decoration:underline}
.crumbs span{opacity:.6}
.post-grid{display:grid;gap:20px;grid-template-columns:1fr;margin-top:34px}
@media(min-width:760px){.post-grid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1080px){.post-grid{grid-template-columns:repeat(3,1fr)}}
.post-card{display:flex;flex-direction:column;background:var(--paper);border:1px solid var(--line-2);
  border-radius:var(--r-lg);overflow:hidden;box-shadow:var(--shadow-sm);
  transition:transform .25s var(--ease),box-shadow .25s var(--ease)}
.post-card:hover{transform:translateY(-3px);box-shadow:var(--shadow)}
.post-card-img{aspect-ratio:16/10;overflow:hidden;background:var(--obsidian-2)}
.post-card-img img{width:100%;height:100%;object-fit:cover}
.post-card-in{padding:20px 22px 24px;display:flex;flex-direction:column;gap:10px;flex:1}
.post-card h2{font-size:1.22rem;line-height:1.25}
.post-card p{color:var(--muted);font-size:.9rem;line-height:1.6}
.post-card .read{margin-top:auto;font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;
  font-weight:800;color:var(--champagne-deep)}
@media (prefers-reduced-motion:reduce){.post-card{transition:none}.post-card:hover{transform:none}}
</style>
"""


def head_block(title, desc, canon, og_img, og_alt, kind, extra_ld,
               og_title=None, og_desc=None, tw_title=None, tw_desc=None):
    """
    Head tags. Mirrors about.html but with per-article metadata.

    Search, Open Graph and Twitter each get their own title and description.
    Search copy leads with the keyword; social copy is written to earn a tap
    in a feed, so duplicating one into the other wastes both.
    """
    og_title = og_title or title
    og_desc = og_desc or desc
    tw_title = tw_title or og_title
    tw_desc = tw_desc or og_desc
    return f"""<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="Elite Global Properties">
<meta property="og:title" content="{html.escape(og_title, quote=True)}">
<meta property="og:description" content="{html.escape(og_desc, quote=True)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/assets/img/projects/{og_img}.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="750">
<meta property="og:image:alt" content="{html.escape(og_alt, quote=True)}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(tw_title, quote=True)}">
<meta name="twitter:description" content="{html.escape(tw_desc, quote=True)}">
<meta name="twitter:image" content="{SITE}/assets/img/projects/{og_img}.jpg">
<meta name="twitter:image:alt" content="{html.escape(og_alt, quote=True)}">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/img/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/img/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/img/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" as="image" href="/assets/img/projects/{og_img}.webp" imagesrcset="/assets/img/projects/{og_img}-sm.webp 760w, /assets/img/projects/{og_img}.webp 1400w" imagesizes="100vw" fetchpriority="high">
{extra_ld}"""


HEAD_TOP = """<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0d12">
<meta name="color-scheme" content="light">
<script>document.documentElement.classList.add('js');
setTimeout(function(){if(!document.querySelector('.reveal.in'))document.querySelectorAll('.reveal').forEach(function(e){e.classList.add('in')})},2200);</script>
"""

ANALYTICS = None  # filled from about.html at build time


def json_ld(obj_json):
    return '<script type="application/ld+json">%s</script>' % obj_json


def build():
    style, header, enquire, tail = load_shell()

    src_full = open(SHELL_PAGE, encoding="utf-8").read()
    analytics = "\n".join(
        m.group(0) for m in re.finditer(
            r"<script>\s*window\.dataLayer.*?</script>"
            r"|<script async src=\"https://www\.googletagmanager\.com/gtag/js[^\"]*\"></script>"
            r"|<script>\s*/\* Defer GTM.*?</script>", src_full, re.S))
    org_ld = re.search(
        r'<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"RealEstateAgent".*?</script>',
        src_full, re.S).group(0)

    os.makedirs(OUT, exist_ok=True)

    files = sorted(f for f in os.listdir(SRC) if f.endswith(".md"))
    posts = [parse_article(os.path.join(SRC, f)) for f in files]

    for p in posts:
        img = HERO.get(p["slug"], "palace-hillside")
        canon = "%s/blog/%s.html" % (SITE, p["slug"])
        body_html, faq, cta = md_to_html(p["body"])
        h1 = re.search(r"^#\s+(.*)$", p["body"], re.M).group(1).strip()

        faq_html = ""
        if faq:
            items = "".join(
                "<details><summary>%s</summary><p>%s</p></details>"
                % (inline(q), inline(a)) for q, a in faq)
            faq_html = ('<section class="section"><div class="wrap">'
                        '<div class="post-faq"><h2>Frequently asked questions</h2>'
                        '<div class="faq">%s</div></div></div></section>' % items)

        # Schema: Article + FAQPage + BreadcrumbList
        import json
        article_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": h1,
            "description": p["desc"],
            "url": canon,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canon},
            "image": "%s/assets/img/projects/%s.jpg" % (SITE, img),
            "author": {"@id": "%s/#org" % SITE},
            "publisher": {"@id": "%s/#org" % SITE},
            "inLanguage": "en",
            "about": p["keyword"],
        }, ensure_ascii=False)

        crumb_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog"},
                {"@type": "ListItem", "position": 3, "name": h1, "item": canon},
            ],
        }, ensure_ascii=False)

        lds = [org_ld, json_ld(article_ld), json_ld(crumb_ld)]
        if faq:
            faq_ld = json.dumps({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q,
                     "acceptedAnswer": {"@type": "Answer", "text": a}}
                    for q, a in faq],
            }, ensure_ascii=False)
            lds.append(json_ld(faq_ld))

        soc = SOCIAL.get(p["slug"], {})
        head = head_block(p["title"], p["desc"], canon, img, p["alt"],
                          "article", "\n".join(lds),
                          og_title=soc.get("og_title"),
                          og_desc=soc.get("og_desc"),
                          tw_title=soc.get("tw_title"),
                          tw_desc=soc.get("tw_desc"))

        hero = f"""<section class="hero page-hero"><div class="hero-bg"><img src="/assets/img/projects/{img}.webp" srcset="/assets/img/projects/{img}-sm.webp 760w, /assets/img/projects/{img}.webp 1400w" sizes="100vw" alt="{html.escape(p['alt'], quote=True)}" width="1400" height="875" fetchpriority="high" decoding="async"></div>
    <div class="wrap"><div class="page-hero-in reveal">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <a href="/blog">Blog</a></nav>
      <h1>{inline(h1)}</h1>
      <p class="lead">{html.escape(p['desc'])}</p>
      <div class="post-meta"><span>Elite Global Properties</span><span class="dot"></span><span>{html.escape(p['read'])} read</span></div>
    </div></div>
  </section>"""

        trust = re.search(r'<div class="trust-row">.*?</div></div>', src_full, re.S).group(0)

        cta_block = ""
        if cta:
            cta_block = ('<section class="section"><div class="wrap prose">%s</div></section>' % cta)

        page = "".join([
            HEAD_TOP,
            head, "\n", analytics, "\n", style, EXTRA_CSS, "</head>\n",
            header,
            '<main id="main">',
            hero, trust,
            '<section class="section post-body"><div class="wrap prose">', body_html, '</div></section>',
            faq_html,
            cta_block,
            '<section class="section"><div class="wrap prose"><div class="post-nav">'
            '<a href="/blog">Back to all articles</a>'
            '<a href="/projects.html">See current off-plan projects</a>'
            '</div></div></section>',
            enquire,
            tail,
            "\n</html>\n",
        ])
        open(os.path.join(OUT, p["slug"] + ".html"), "w", encoding="utf-8").write(page)
        print("wrote blog/%s.html" % p["slug"])

    # ---------------- listing page ----------------
    import json
    cards = []
    for p in posts:
        img = HERO.get(p["slug"], "palace-hillside")
        h1 = re.search(r"^#\s+(.*)$", p["body"], re.M).group(1).strip()
        cards.append(f"""<article class="post-card reveal">
  <a class="post-card-img" href="/blog/{p['slug']}.html" tabindex="-1" aria-hidden="true"><img src="/assets/img/projects/{img}-sm.webp" alt="" width="760" height="475" loading="lazy" decoding="async"></a>
  <div class="post-card-in">
    <h2><a href="/blog/{p['slug']}.html">{inline(h1)}</a></h2>
    <p>{html.escape(p['desc'])}</p>
    <span class="read">{html.escape(p['read'])} read</span>
  </div>
</article>""")

    list_canon = SITE + "/blog"
    list_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Blog",
        "@id": list_canon,
        "name": "Elite Global Properties Insights",
        "description": "Guides on buying, investing in and owning Dubai property, from a RERA-registered brokerage.",
        "url": list_canon,
        "publisher": {"@id": "%s/#org" % SITE},
        "blogPost": [
            {"@type": "BlogPosting", "headline": re.search(r"^#\s+(.*)$", p["body"], re.M).group(1).strip(),
             "url": "%s/blog/%s.html" % (SITE, p["slug"]), "description": p["desc"]}
            for p in posts],
    }, ensure_ascii=False)

    crumb_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": list_canon},
        ],
    }, ensure_ascii=False)

    head = head_block(
        "Dubai Property Insights & Buying Guides | Elite Global",
        "Guides on buying property in Dubai, off-plan investment, the Golden Visa, yields and verification, from a RERA-registered Dubai brokerage.",
        list_canon, "palace-hillside", "Elite Global Properties, Dubai property",
        "website", "\n".join([org_ld, json_ld(list_ld), json_ld(crumb_ld)]),
        og_title="Dubai property, explained by the people who sell it",
        og_desc="Ten practical guides on buying, investing and owning in Dubai and Abu Dhabi. Written by our advisory team, with the numbers before the brochure.",
        tw_title="Dubai property, explained",
        tw_desc="Practical guides on buying, yields, the Golden Visa and how to verify who you are dealing with.")

    trust = re.search(r'<div class="trust-row">.*?</div></div>', src_full, re.S).group(0)

    listing = "".join([
        HEAD_TOP, head, "\n", analytics, "\n", style, EXTRA_CSS, "</head>\n",
        header,
        '<main id="main">',
        f"""<section class="hero page-hero"><div class="hero-bg"><img src="/assets/img/projects/palace-hillside.webp" srcset="/assets/img/projects/palace-hillside-sm.webp 760w, /assets/img/projects/palace-hillside.webp 1400w" sizes="100vw" alt="" width="1400" height="875" fetchpriority="high" decoding="async"></div>
    <div class="wrap"><div class="page-hero-in reveal">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <span>Blog</span></nav>
      <span class="eyebrow on-dark">Insights</span>
      <h1>Dubai property, <em>explained.</em></h1>
      <p class="lead">Practical guides on buying, investing and owning in Dubai and Abu Dhabi. Written by our advisory team, with the numbers before the brochure.</p>
    </div></div>
  </section>""",
        trust,
        '<section class="section"><div class="wrap"><div class="post-grid">',
        "".join(cards),
        '</div></div></section>',
        enquire, tail, "\n</html>\n",
    ])
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(listing)
    print("wrote blog/index.html")

    return posts


def update_sitemap(posts):
    path = os.path.join(ROOT, "sitemap.xml")
    xml = open(path, encoding="utf-8").read()

    # Drop any previously generated blog entries so reruns stay idempotent.
    # Strip both the listing entry (/blog, no extension) and the article
    # entries (/blog/<slug>.html) so reruns stay idempotent.
    xml = re.sub(r"\s*<url>\s*<loc>%s/blog(?:/[^<]*)?</loc>.*?</url>" % re.escape(SITE),
                 "", xml, flags=re.S)

    date = re.search(r"<lastmod>([^<]+)</lastmod>", xml)
    date = date.group(1) if date else "2026-08-01"

    entries = ['\n<url><loc>%s/blog</loc><lastmod>%s</lastmod>'
               '<changefreq>weekly</changefreq><priority>0.7</priority></url>' % (SITE, date)]
    for p in posts:
        entries.append('\n<url><loc>%s/blog/%s.html</loc><lastmod>%s</lastmod>'
                       '<changefreq>monthly</changefreq><priority>0.6</priority></url>'
                       % (SITE, p["slug"], date))

    xml = xml.replace("</urlset>", "".join(entries) + "\n</urlset>")
    open(path, "w", encoding="utf-8").write(xml)
    print("updated sitemap.xml (+%d urls)" % (len(posts) + 1))


if __name__ == "__main__":
    posts = build()
    update_sitemap(posts)
    print("\nDone. %d articles + listing." % len(posts))
