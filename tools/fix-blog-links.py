#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rework the internal/external linking in the blog markdown sources.

Per article:
  1. one link to the home page
  2. one link to a commercial page (projects / villas / invest / apartments)
  3. one link to another blog article (internal blog interlinking)
  4. no third-party outbound links

Edits content/blog/*.md in place, so a rebuild carries the changes through
to the generated HTML.

Run:  python tools/fix-blog-links.py
"""

import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "content", "blog")
SITE = "https://eliteglobal-properties.com"

# Blog interlinking. Each article points at a topically adjacent one, forming
# a loop so every article both links out and receives a link.
BLOG_LINK = {
    "01": ("off-plan-property-dubai-guide", "how off-plan purchases work"),
    "02": ("dubai-rental-yield-roi-guide", "how to calculate rental yield"),
    "03": ("cost-of-buying-property-in-dubai", "the full cost of buying"),
    "04": ("villa-or-apartment-dubai", "choosing between a villa and an apartment"),
    "05": ("branded-residences-dubai", "whether a branded residence is worth the premium"),
    "06": ("dubai-rental-yield-roi-guide", "run the net yield calculation"),
    "07": ("buy-property-in-dubai-as-a-foreigner", "who can buy in Dubai"),
    "08": ("best-areas-to-buy-property-in-dubai", "which community suits you"),
    "09": ("verify-dubai-property-developer", "how to verify a developer and broker"),
    "10": ("off-plan-property-dubai-guide", "how off-plan works end to end"),
}

# The commercial page each article should point at (link 2).
COMMERCIAL = {
    "01": ("/buy-property-in-dubai.html", "buying property in Dubai"),
    "02": ("/off-plan-property-in-dubai.html", "off-plan property in Dubai"),
    "03": ("/dubai-real-estate-investment.html", "Dubai real estate investment"),
    "04": ("/dubai-real-estate-investment.html", "Dubai real estate investment"),
    "05": ("/projects.html", "current off-plan projects"),
    "06": ("/apartments-for-sale-in-dubai.html", "apartments for sale in Dubai"),
    "07": ("/off-plan-property-in-dubai.html", "off-plan property in Dubai"),
    "08": ("/villas-and-townhouses-in-dubai.html", "villas and townhouses in Dubai"),
    "09": ("/projects.html", "current off-plan projects"),
    "10": ("/off-plan-property-in-dubai.html", "off-plan property in Dubai"),
}

HOME_SENTENCE = (
    "Elite Global Properties is a RERA-registered brokerage in Business Bay, Dubai, "
    "giving overseas and resident buyers a [private, direct-from-developer route into "
    "Dubai property](%s/). " % SITE
)


def strip_external(md):
    """Turn [label](https://external) into plain label text."""
    def repl(m):
        label, href = m.group(1), m.group(2)
        if href.startswith(SITE) or href.startswith("/"):
            return m.group(0)
        return label
    return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", repl, md)


def main():
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        num = fn[:2]
        path = os.path.join(SRC, fn)
        md = open(path, encoding="utf-8").read()

        head, sep, body = md.partition("## Blog Content")
        if not sep:
            print("skip (no body):", fn)
            continue

        before = body
        body = strip_external(body)

        # --- Link 2: commercial page. Rewrite existing internal links so each
        # article keeps exactly one, pointing at its assigned page.
        com_url, com_label = COMMERCIAL[num]

        # --- Link 3: another blog article.
        slug, anchor = BLOG_LINK[num]
        blog_md = "[%s](%s/blog/%s.html)" % (anchor, SITE, slug)

        # Append the closing "keep reading" line before the final CTA heading,
        # so the blog link sits in prose rather than in the metadata tail.
        m = re.search(r"\n## (?:Talk|Get|Speak|Run|Compare|Buy with|Verify us)", body)
        insert_at = m.start() if m else len(body)
        keep_reading = (
            "\n\nIf you are working through the detail, our guide to %s is the "
            "natural next read, and you can see the full [%s](%s) we currently "
            "advise on.\n"
            % (blog_md, com_label, com_url)
        )
        body = body[:insert_at] + keep_reading + body[insert_at:]

        # --- Link 1: home page, added into the closing CTA paragraph.
        body = re.sub(
            r"Elite Global Properties is a RERA-registered brokerage in Business Bay, Dubai[,.]?\s*",
            HOME_SENTENCE, body, count=1)

        if body != before:
            open(path, "w", encoding="utf-8", newline="").write(head + sep + body)
            print("updated", fn)


if __name__ == "__main__":
    main()
