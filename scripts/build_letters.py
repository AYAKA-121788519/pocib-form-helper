# -*- coding: utf-8 -*-
"""把 app/_letters_src.html base64 内嵌进 app/index.html 的 LETTERS_B64。

改函电模块（_letters_src.html）之后必须跑一次，否则主程序 iframe 里还是旧的。
用法：python scripts/build_letters.py [--check]
"""
import base64
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "app", "_letters_src.html")
APP = os.path.join(ROOT, "app", "index.html")
PAT = re.compile(rb'const LETTERS_B64="[^"]*";')


def main():
    src = open(SRC, "rb").read()
    html = open(APP, "rb").read()
    m = PAT.search(html)
    if not m:
        sys.exit("找不到 LETTERS_B64 常量")
    old = base64.b64decode(m.group(0).split(b'"')[1])
    same = old == src
    if "--check" in sys.argv:
        print("源码 md5", hashlib.md5(src).hexdigest())
        print("内嵌 md5", hashlib.md5(old).hexdigest(), "| 一致" if same else "| 不一致，需要重新内嵌")
        sys.exit(0 if same else 1)
    if same:
        print("已是最新，无需重嵌")
        return
    b64 = base64.b64encode(src)
    html = html[:m.start()] + b'const LETTERS_B64="' + b64 + b'";' + html[m.end():]
    open(APP, "wb").write(html)
    print("已内嵌 %d 字节函电源码（base64 %d）" % (len(src), len(b64)))


if __name__ == "__main__":
    main()
