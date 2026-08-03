#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add a Blog link to the footer "Discover" column on every page.

The blog is English-only, so non-English pages link to the English blog and
carry hreflang="en" plus lang="en" to tell both crawlers and screen readers
that the destination is in a different language.

Idempotent: running it twice does not add the link twice.

Run:  python tools/add-blog-footer-link.py
"""

import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Locale -> label for the blog link. English pages get a plain link; the others
# point at the same English blog, so the label stays "Blog" (it reads the same
# in these languages) but the anchor is marked as an English destination.
LOCALES = {
    "": ("Blog", ""),
    "fr": ("Blog", ' hreflang="en" lang="en"'),
    "de": ("Blog", ' hreflang="en" lang="en"'),
    "ru": ("Блог", ' hreflang="en" lang="en"'),
    "ar": ("المدونة", ' hreflang="en" lang="en"'),
    "es": ("Blog", ' hreflang="en" lang="en"'),
}

# The footer Discover column ends with the apartments link on every page.
# Anchor the insertion to that line so we do not disturb anything else.
ANCHOR = re.compile(
    r'(<a href="(?:/(?:fr|de|ru|ar|es))?/apartments-for-sale-in-dubai\.html">'
    r'[^<]*</a>)(\s*)(</div>)'
)


def locale_of(relpath):
    parts = relpath.replace("\\", "/").split("/")
    if parts[0] in ("fr", "de", "ru", "ar", "es"):
        return parts[0]
    return ""


def process(path, relpath):
    src = open(path, encoding="utf-8").read()

    if 'href="/blog"' in src:
        return "skip"                      # already has the link

    loc = locale_of(relpath)
    if loc not in LOCALES:
        return "skip"
    label, attrs = LOCALES[loc]

    m = ANCHOR.search(src)
    if not m:
        return "no-anchor"

    indent = m.group(2) if "\n" in m.group(2) else "\n        "
    link = '%s<a href="/blog"%s>%s</a>' % (indent, attrs, label)
    out = src[:m.end(1)] + link + src[m.end(1):]

    open(path, "w", encoding="utf-8", newline="").write(out)
    return "ok"


def main():
    counts = {"ok": 0, "skip": 0, "no-anchor": 0}
    noanchor = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", ".vercel",
                                    "content", "tools", "blog", "assets")]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            r = process(full, rel)
            counts[r] += 1
            if r == "no-anchor":
                noanchor.append(rel)

    print("updated : %d" % counts["ok"])
    print("skipped : %d (already linked or not a locale page)" % counts["skip"])
    print("no footer Discover column: %d" % counts["no-anchor"])
    for n in noanchor[:12]:
        print("   ", n)


if __name__ == "__main__":
    main()
