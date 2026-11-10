"""Checks every link, image, script and stylesheet on every page of a built site folder.
Internal addresses must exist as files; external ones get one HEAD/GET request each.
Usage: python linkcheck.py <site folder>"""
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SITE = sys.argv[1]
ATTR = re.compile(r'(?:href|src|content)="([^"]+)"')
pages = []
for d, _, files in os.walk(SITE):
    for f in files:
        if f.endswith(".html"):
            pages.append(os.path.join(d, f))

def exists(path):
    path = path.split("#")[0].split("?")[0]
    if path.endswith("/"):
        return os.path.isfile(os.path.join(SITE, path.strip("/"), "index.html")) if path != "/" else os.path.isfile(os.path.join(SITE, "index.html"))
    return os.path.isfile(os.path.join(SITE, path.lstrip("/")))

internal_bad, external = {}, {}
own = re.compile(r"^https://(www\.)?lumoslatin\.nl")
for p in pages:
    h = open(p, encoding="utf-8").read()
    rel = os.path.relpath(p, SITE)
    for u in set(ATTR.findall(h)):
        if u.startswith(("mailto:", "tel:", "data:", "javascript:")) or u in ("#", "") or u.startswith("#"):
            continue
        if own.match(u):
            u2 = own.sub("", u) or "/"
            if u2.startswith("/") and not exists(u2):
                internal_bad.setdefault(u, []).append(rel)
            continue
        if u.startswith("/"):
            if not exists(u):
                internal_bad.setdefault(u, []).append(rel)
        elif u.startswith("http"):
            external.setdefault(u, []).append(rel)

def probe(u):
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(u, method=method, headers={"User-Agent": "Mozilla/5.0 (link check)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if method == "GET":
                return e.code
        except Exception as e:
            if method == "GET":
                return str(e)[:60]
    return "?"

with ThreadPoolExecutor(12) as ex:
    results = dict(zip(external, ex.map(probe, external)))

print("pages:", len(pages), " internal addresses missing:", len(internal_bad), " external checked:", len(external))
for u, where in internal_bad.items():
    print("MISSING", u, "on", ", ".join(where[:3]), ("and %d more" % (len(where) - 3)) if len(where) > 3 else "")
for u, st in results.items():
    if st not in (200, 301, 302, 303, 307, 308):
        print("EXTERNAL", st, u, "on", ", ".join(external[u][:2]))
print("link check done")
