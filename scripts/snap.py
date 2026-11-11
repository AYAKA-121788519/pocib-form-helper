# -*- coding: utf-8 -*-
"""激活指定标题的窗口并截取该窗口区域。用法：python snap.py 标题关键字 输出名"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win as W

KEY = sys.argv[1] if len(sys.argv) > 1 else "Business-2026"
OUT = sys.argv[2] if len(sys.argv) > 2 else "win.png"
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "img")

ws = W.find_window(KEY)
if not ws:
    print("NOT FOUND"); sys.exit(1)
w = ws[0]
W.activate(w["hwnd"])
l, t, r, b = W.rect_of(w["hwnd"])
pw, ph = r - l, b - t
full = os.path.join(IMG, "_full.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab",
                "-i", "desktop", "-frames:v", "1", full], check=True)
out = os.path.join(IMG, OUT)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", full,
                "-vf", "crop=%d:%d:%d:%d" % (pw, ph, l, t), out], check=True)
if os.path.exists(full):
    os.remove(full)
print(w["title"], "rect=", (l, t, r, b), "->", OUT, pw, "x", ph)
