# -*- coding: utf-8 -*-
"""直接向 IE 控件投递鼠标消息，绕开输入队列，用于触发 ondblclick。
用法：python ieclick.py <窗口标题关键字> <窗口内x> <窗口内y> <输出图> [--single]"""
import sys, os, time, subprocess, ctypes, ctypes.wintypes as wt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win as W

KEY, X, Y, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
SINGLE = "--single" in sys.argv

u32 = W.u32
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0200, 0x0201, 0x0202, 0x0203
MK_LBUTTON = 0x0001


def makelparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def children(root, cls_filter="Internet Explorer_Server"):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        cls = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(h, cls, 256)
        if cls.value == cls_filter:
            r = W.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            out.append((h, (r.left, r.top, r.right, r.bottom)))
        return True

    u32.EnumChildWindows(root, cb, 0)
    return out


w = W.find_window(KEY)[0]
hwnd = w["hwnd"]
W.activate(hwnd)
time.sleep(0.6)
r = W.rect_of(hwnd)
sx, sy = r[0] + X, r[1] + Y
print("窗口", r, "目标屏幕点", (sx, sy))

for h, cr in children(hwnd):
    cx, cy = sx - cr[0], sy - cr[1]
    if not (0 <= cx < cr[2] - cr[0] and 0 <= cy < cr[3] - cr[1]):
        print("  skip child", h, cr)
        continue
    lp = makelparam(cx, cy)
    u32.PostMessageW(h, WM_MOUSEMOVE, 0, lp)
    u32.PostMessageW(h, WM_LBUTTONDOWN, MK_LBUTTON, lp)
    u32.PostMessageW(h, WM_LBUTTONUP, 0, lp)
    if not SINGLE:
        u32.PostMessageW(h, WM_LBUTTONDBLCLK, MK_LBUTTON, lp)
        u32.PostMessageW(h, WM_LBUTTONUP, 0, lp)
    print("  sent to child", h, "client", (cx, cy))

time.sleep(1.6)
r2 = W.rect_of(hwnd)
pw, ph = r2[2] - r2[0], r2[3] - r2[1]
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "img")
full = os.path.join(IMG, "_f.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab", "-i", "desktop",
                "-frames:v", "1", full], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", full,
                "-vf", "crop=%d:%d:%d:%d" % (pw, ph, r2[0], r2[1]),
                os.path.join(IMG, OUT)], check=True)
os.remove(full)
print("saved", OUT)

# 检查是否出现新窗口（单据编辑窗口）
for t in W.find_window(""):
    if t["title"].strip() and t["title"] not in ("Business-2026110301", "Business-2026110302"):
        pass
