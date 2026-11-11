# -*- coding: utf-8 -*-
"""批量打开单据窗口 -> 截图 -> 关闭。
用法：python grab_docs.py <业务窗口标题> <清单json文件>
清单格式：[{"name":"商业发票","x":530,"y":560}, ...]
"""
import sys, os, time, ctypes, ctypes.wintypes as wt, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win as W

u32 = W.u32
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "img")
WM_CLOSE = 0x0010


def grab(rect, out):
    full = os.path.join(IMG, "_f.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "gdigrab",
                    "-i", "desktop", "-frames:v", "1", full], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", full,
                    "-vf", "crop=%d:%d:%d:%d" % (rect[2] - rect[0], rect[3] - rect[1], rect[0], rect[1]),
                    os.path.join(IMG, out)], check=True)
    os.remove(full)


def close_all(titles):
    for t in titles:
        for w in W.find_window(t):
            u32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)


def main():
    key = sys.argv[1]
    items = json.load(open(sys.argv[2], encoding="utf-8"))
    close_all(["商业发票", "装箱单", "托收委托书", "国际海运委托书", "出境货物检验检疫申请",
               "一般原产地证", "出口货物报关单", "汇票", "进口货物报关单", "入境货物检验检疫申请",
               "不可撤销信用证开证申请书", "境外汇款申请书", "合同"])
    time.sleep(0.8)

    bw = W.find_window(key)[0]
    for it in items:
        W.activate(bw["hwnd"])
        time.sleep(0.7)
        r = W.rect_of(bw["hwnd"])
        sx, sy = r[0] + it["x"], r[1] + it["y"]
        u32.SetCursorPos(sx, sy)
        time.sleep(0.25)
        for _ in range(2):
            u32.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.05)
            u32.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(0.15)
        time.sleep(1.6)
        ws = [w for w in W.find_window(it["name"]) if w["hwnd"] != bw["hwnd"]]
        if not ws:
            print("MISS", it["name"])
            continue
        ws.sort(key=lambda w: -((w["rect"][2] - w["rect"][0]) * (w["rect"][3] - w["rect"][1])))
        w = ws[0]
        W.activate(w["hwnd"])
        time.sleep(0.6)
        rr = W.rect_of(w["hwnd"])
        out = "doc_%s.png" % it["file"]
        grab(rr, out)
        print("OK", it["name"], "->", out, rr)
        u32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
        time.sleep(0.6)


if __name__ == "__main__":
    main()
