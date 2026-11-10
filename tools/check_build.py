"""Rebuilds the site and reports whether prototype/ changed against git, and whether every
content file is saved in the fixed layout. Run: python tools/check_build.py [--today YYYY-MM-DD]"""
import json
import os
import subprocess
import sys

import content_io

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

build = subprocess.run([sys.executable, os.path.join(HERE, "build_prototype.py")] + sys.argv[1:], cwd=REPO)
if build.returncode:
    sys.exit("build failed")

untidy = []
for p in content_io.all_files():
    with open(p, encoding="utf-8") as f:
        text = f.read()
    if content_io.dumps(json.loads(text)) != text:
        untidy.append(os.path.relpath(p, REPO))
for p in untidy:
    print("not in the fixed layout:", p)

changed = subprocess.run(["git", "status", "--porcelain", "prototype"], cwd=REPO,
                         capture_output=True, text=True).stdout
if changed.strip():
    print("prototype/ changed:")
    print(changed.rstrip())
    sys.exit(1)
print("prototype/ unchanged" + ("" if not untidy else ", but some content files need re-saving"))
sys.exit(1 if untidy else 0)
