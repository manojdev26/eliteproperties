#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reorder the footer "Discover" column on every page:

  - drop the Projects link (it stays in the header nav)
  - move Blog to the top of the column

Idempotent: safe to run repeatedly.

Run:  python tools/reorder-footer-links.py
"""

import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The Discover column: <div><h2>LABEL</h2> ...anchors... </div>
COLUMN = re.compile(
    r'(<div><h2>[^<]*</h2>\s*)(.*?)(\s*</div>)', re.S)

PROJECTS = re.compile(
    r'\s*<a href="(?:/(?:fr|de|ru|ar|es))?/projects\.html"[^>]*>[^<]*</a>')
BLOG = re.compile(r'\s*<a href="/blog"[^>]*>[^<]*</a>')


def is_discover_column(anchors):
    """Only touch the column that holds the site's section links."""
    return "villas-and-townhouses" in anchors or "/blog" in anchors


def process(path):
    src = open(path, encoding="utf-8").read()
    changed = False
    out = []
    pos = 0

    for m in COLUMN.finditer(src):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        if not is_discover_column(body):
            continue

        blog = BLOG.search(body)
        if not blog:
            continue
        blog_tag = blog.group(0).strip()

        new_body = BLOG.sub("", body)          # lift Blog out
        new_body = PROJECTS.sub("", new_body)  # drop Projects

        # Re-insert Blog first, matching the column's existing indentation.
        indent = re.search(r"\n(\s*)<a ", new_body)
        indent = "\n" + indent.group(1) if indent else "\n        "
        new_body = indent + blog_tag + new_body.rstrip()

        if new_body != body:
            out.append(src[pos:m.start()])
            out.append(head + new_body + tail)
            pos = m.end()
            changed = True

    if not changed:
        return "skip"

    out.append(src[pos:])
    open(path, "w", encoding="utf-8", newline="").write("".join(out))
    return "ok"


def main():
    counts = {"ok": 0, "skip": 0}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "node_modules", ".vercel",
                                    "content", "tools", "blog", "assets")]
        for fn in filenames:
            if fn.endswith(".html"):
                counts[process(os.path.join(dirpath, fn))] += 1

    print("updated : %d" % counts["ok"])
    print("skipped : %d" % counts["skip"])


if __name__ == "__main__":
    main()
