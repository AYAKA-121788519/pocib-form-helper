# -*- coding: utf-8 -*-
"""激活窗口 -> 重新取坐标 -> 点击 -> 重新取坐标 -> 截图。
用法：python tap.py <标题关键字> <x> <y> <输出名> [--double]
坐标以窗口左上角为原点，与截图一致。"""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win as W

KEY, X, Y, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
DBL = "--double" in sys.argv
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "img")

w = W.find_window(KEY)[0]
hwnd = w["hwnd"]
W.activate(hwnd)
time.sleep(0.8)
r1 = W.rect_of(hwnd)
W.click(r1[0] + X, r1[1] + Y, double=DBL)
time.sleep(1.2)
r2 = W.rect_of(hwnd)
pw, ph = r2[2] - r2[0], r2[3] - r2[1]
full = os.path.join(IMG, "_full.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab",
                "-i", "desktop", "-frames:v", "1", full], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", full,
                "-vf", "crop=%d:%d:%d:%d" % (pw, ph, r2[0], r2[1]),
                os.path.join(IMG, OUT)], check=True)
os.remove(full)
print("rect_before=%s rect_after=%s click=(%d,%d) size=%dx%d -> %s" %
      (r1, r2, r1[0] + X, r1[1] + Y, pw, ph, OUT))
