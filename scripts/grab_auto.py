# -*- coding: utf-8 -*-
"""把业务窗口挪到屏幕内 -> 自动识别单据网格 -> 按行列双击打开并截图。

用法：python grab_auto.py <业务标题> <清单json>
清单：{"row1": [{"col":1,"name":"商业发票","file":"301_invoice"}, ...], "row2":[...], "row3":[...]}
col 从 1 开始。
"""
import sys, os, time, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win as W
import ctypes

u32 = W.u32
SWP_NOZORDER, SWP_SHOWWINDOW = 0x0004, 0x0040
WM_CLOSE = 0x0010
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "img")

ROW_BAND = {"row1": (255, 380), "row2": (430, 570), "row3": (610, 740)}


def capture(hwnd, out_png=None, raw=False):
    r = W.rect_of(hwnd)
    pw, ph = r[2] - r[0], r[3] - r[1]
    target = os.path.join(IMG, "_w.raw") if raw else os.path.join(IMG, out_png)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab", "-i", "desktop",
           "-frames:v", "1", "-vf", "crop=%d:%d:%d:%d" % (pw, ph, r[0], r[1])]
    if raw:
        cmd += ["-pix_fmt", "rgb24", "-f", "rawvideo"]
    cmd.append(target)
    subprocess.run(cmd, check=True)
    return r, pw, ph


def detect(raw_path, pw, ph, nrows=3):
    """自适应：先按纵向密度找图标行，再在每行内找列。"""
    d = open(raw_path, "rb").read()

    def px(x, y):
        i = (y * pw + x) * 3
        return (d[i] + d[i + 1] + d[i + 2]) / 3

    # 纵向：每行暗像素数
    prof = []
    for y in range(120, ph - 20):
        c = sum(1 for x in range(100, pw - 20, 2) if px(x, y) < 235)
        prof.append((y, c))
    thr = max(8, max(c for _, c in prof) * 0.12)
    rows, st = [], None
    for y, c in prof:
        if c > thr and st is None:
            st = y
        elif c <= thr and st is not None:
            if y - st > 40:
                rows.append((st, y))
            st = None
    if st is not None:
        rows.append((st, ph - 20))
    # 合并过近的行
    merged = []
    for r in rows:
        if merged and r[0] - merged[-1][1] < 25:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r) if False else (r[0], r[1]))
    rows = merged[:nrows]

    res = {}
    for i, (y0, y1) in enumerate(rows, 1):
        cols = [sum(1 for y in range(y0, y1) if px(x, y) < 238) for x in range(pw)]
        runs, st = [], None
        for x, c in enumerate(cols):
            if c >= 3 and st is None:
                st = x
            elif c < 3 and st is not None:
                if x - st > 40:
                    runs.append(((st + x - 1) // 2, (y0 + y1) // 2))
                st = None
        res["row%d" % i] = runs
    return res


def main():
    key, spec_path = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path, encoding="utf-8"))
    bw = W.find_window(key)[0]
    hwnd = bw["hwnd"]
    u32.ShowWindow(hwnd, 9)
    u32.SetWindowPos(hwnd, 0, 60, 40, 1300, 850, SWP_NOZORDER | SWP_SHOWWINDOW)
    time.sleep(0.9)
    W.activate(hwnd)
    time.sleep(0.8)
    r, pw, ph = capture(hwnd, raw=True)
    print("窗口", r, pw, ph)
    grid = detect(os.path.join(IMG, "_w.raw"), pw, ph)
    for k, v in grid.items():
        print(" ", k, [c[0] for c in v])

    for row, items in spec.items():
        cells = grid.get(row, [])
        for it in items:
            idx = it["col"] - 1
            if idx >= len(cells):
                print("NO CELL", row, it["name"])
                continue
            x, y = cells[idx]
            u32.SetCursorPos(r[0] + x, r[1] + y)
            time.sleep(0.2)
            for _ in range(2):
                u32.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.05)
                u32.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(0.15)
            time.sleep(1.7)
            ws = [w for w in W.find_window(it["name"]) if w["hwnd"] != hwnd]
            if not ws:
                print("MISS", it["name"], (x, y))
                continue
            ws.sort(key=lambda w: -((w["rect"][2] - w["rect"][0]) * (w["rect"][3] - w["rect"][1])))
            w = ws[0]
            W.activate(w["hwnd"])
            time.sleep(0.6)
            rr = W.rect_of(w["hwnd"])
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab", "-i", "desktop",
                            "-frames:v", "1", "-vf", "crop=%d:%d:%d:%d" % (
                                rr[2] - rr[0], rr[3] - rr[1], rr[0], rr[1]),
                            os.path.join(IMG, "doc_%s.png" % it["file"])], check=True)
            print("OK", it["name"], "-> doc_%s.png" % it["file"])
            u32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
            time.sleep(0.5)


if __name__ == "__main__":
    main()
