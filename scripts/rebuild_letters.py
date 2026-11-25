# -*- coding: utf-8 -*-
"""把 app/_letters_src.html 重新编码进 app/index.html 的 LETTERS_B64。"""
import base64
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "app", "_letters_src.html")
idx = os.path.join(ROOT, "app", "index.html")

raw = open(src, "rb").read()
b64 = base64.b64encode(raw).decode("ascii")

html = io.open(idx, encoding="utf-8", newline=None).read()
m = re.search(r'const LETTERS_B64="[A-Za-z0-9+/=]*"', html)
assert m, "找不到 LETTERS_B64"
old_len = len(m.group(0))
html = html[:m.start()] + 'const LETTERS_B64="%s"' % b64 + html[m.end():]
io.open(idx, "w", encoding="utf-8", newline=None).write(html)
print("源 %d 字节 → base64 %d 字符；常量 %d → %d" % (len(raw), len(b64), old_len, len(b64) + 22))
