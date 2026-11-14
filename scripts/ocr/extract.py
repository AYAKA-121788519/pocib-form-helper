# -*- coding: utf-8 -*-
"""POCIB 识图取数 —— 截取客户端窗口 → OCR → 拆成字段。

平时直接跑「识图服务.bat」就好（网页里一键取数）；
本文件也保留命令行用法，方便单次识别或调试：

  python extract.py                      自动找 POCIB 窗口识别，结果复制到剪贴板
  python extract.py --list               列出可识别的窗口
  python extract.py --hwnd 123456        指定窗口句柄
  python extract.py --file 截图.png       直接识别一张图（也支持 --clip 读剪贴板图片）
  python extract.py --kind goods         明确按商品档案解析
  python extract.py --out 结果.json       另存一份 json（默认不留文件）
  python extract.py --no-clip            不写剪贴板
"""
import argparse
import ctypes
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocrlib as O
import parse as P

TITLE_HINTS = ("世格 POCIB", "Business-", "基本资料", "商品", "我的", "市场", "合同", "库存", "订单")
SKIP_TITLE = ("POCIB 识图", "识图取数", "命令提示符", "Windows PowerShell")


def say(*a):
    try:
        print(*a, flush=True)
    except UnicodeEncodeError:
        txt = " ".join(str(x) for x in a)
        enc = sys.stdout.encoding or "gbk"
        print(txt.encode(enc, "replace").decode(enc, "replace"), flush=True)


# ---------------------------------------------------------------- 窗口挑选

def candidate_windows():
    """能用来识别的窗口：够大、没最小化、标题不像我们自己的黑窗口。"""
    out = []
    for w in O.list_windows():
        t = (w.get("title") or "").strip()
        if not t or any(s in t for s in SKIP_TITLE):
            continue
        x0, y0, x1, y1 = w["rect"]
        if x1 - x0 < 400 or y1 - y0 < 300:
            continue
        if x0 <= -30000 or y0 <= -30000:
            continue
        if (w.get("style") or 0) & 0x20000000:  # WS_MINIMIZE
            continue
        out.append({"hwnd": w["hwnd"], "title": t,
                    "w": x1 - x0, "h": y1 - y0,
                    "kind": guess_kind(t), "score": title_score(t),
                    "z": w.get("z", 9999)})
    # 同分时按 z 序：最近用过的窗口排前面（同名商品页开多个时靠这个分）
    out.sort(key=lambda x: (-x["score"], x["z"], -x["w"] * x["h"]))
    return out


def title_score(t):
    """越像 POCIB 内容页分越高，用于自动挑窗口。"""
    s = 0
    for i, h in enumerate(TITLE_HINTS):
        if h.lower() in t.lower():
            s += 40 - i * 2
    if "http" in t.lower() or "aspx" in t.lower():
        s -= 6
    return s


def guess_kind(title):
    t = title or ""
    if "商品" in t:
        return "goods"
    if "基本资料" in t or "公司" in t:
        return "company"
    return "auto"


def pick_window(hwnd=None, title=None, interactive=True):
    wins = candidate_windows()
    if hwnd:
        hit = [w for w in wins if w["hwnd"] == hwnd]
        if hit:
            return hit[0], wins
        return {"hwnd": hwnd, "title": "(指定句柄)", "kind": "auto", "score": 0}, wins
    if title:
        hit = [w for w in wins if title.lower() in w["title"].lower()]
        if hit:
            return hit[0], wins
        return None, wins
    best = [w for w in wins if w["score"] > 0]
    if not best:
        return None, wins
    if len(best) == 1 or not interactive:
        return best[0], wins
    say("发现 %d 个可能的窗口：" % len(best))
    for i, w in enumerate(best):
        say("  [%d] %-46s %dx%d" % (i + 1, w["title"][:46], w["w"], w["h"]))
    idx = input("要识别哪个？输入序号（直接回车=第1个）：").strip() or "1"
    try:
        return best[int(idx) - 1], wins
    except Exception:
        return best[0], wins


# ---------------------------------------------------------------- 剪贴板

def set_clipboard_text(text):
    """写 Unicode 剪贴板。命令行的 clip / Set-Clipboard 会走 ANSI 代码页，
    中文粘贴出去就是乱码，只有 CF_UNICODETEXT 是稳的。"""
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
    u32.SetClipboardData.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = (ctypes.c_void_p,)
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    buf = (text + "\x00").encode("utf-16-le")
    if not u32.OpenClipboard(None):
        return False
    try:
        u32.EmptyClipboard()
        h = k32.GlobalAlloc(0x0002, len(buf))          # GMEM_MOVEABLE
        if not h:
            return False
        p = k32.GlobalLock(h)
        ctypes.memmove(p, buf, len(buf))
        k32.GlobalUnlock(h)
        return bool(u32.SetClipboardData(13, h))       # CF_UNICODETEXT，所有权交给系统
    finally:
        u32.CloseClipboard()


def from_clipboard():
    import subprocess
    tmp = os.path.join(os.environ.get("TEMP", "."), "pocib_clip_%d.png" % int(time.time()))
    code = ("Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$i=[System.Windows.Forms.Clipboard]::GetImage();"
            "if($i){$i.Save('%s',[System.Drawing.Imaging.ImageFormat]::Png);'OK'}else{'EMPTY'}"
            % tmp.replace("\\", "\\\\"))
    r = subprocess.run(["powershell", "-Sta", "-NoProfile", "-Command", code],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore",
                       creationflags=0x08000000)
    if "OK" not in (r.stdout or ""):
        raise RuntimeError("剪贴板里没有图片。先按 Win+Shift+S 截图，或用 --file 指定图片。")
    return tmp


# ---------------------------------------------------------------- 主流程

def detect_kind(res):
    txt = "".join((l.get("text") or "") for l in res.get("lines") or [])
    goods_hint = sum(k in txt for k in ("商品编号", "毛重", "净重", "销售单位", "商品属类", "包装"))
    comp_hint = sum(k in txt for k in ("公司全称", "开户行", "统一社会信用代码", "法人代表", "本币账号"))
    return "goods" if goods_hint > comp_hint else "company"


def pipeline(hwnd=None, title=None, file=None, clip=False, kind="auto",
             engine="auto", interactive=True, want_png=False, log=None):
    """截窗口/读图 → OCR → 解析。返回 {payload, png, img, log}。"""
    logs = log if log is not None else []

    def note(msg):
        logs.append(msg)

    # ---- 1. 取图
    src = {"title": "", "hwnd": 0}
    img = None
    tmp_img = None
    win = None
    if file:
        img_path = file
        if not os.path.exists(img_path):
            raise RuntimeError("找不到文件：%s" % img_path)
        src["title"] = os.path.basename(img_path)
    elif clip:
        img_path = from_clipboard()
        tmp_img = img_path
        src["title"] = "剪贴板截图"
        if kind == "auto":
            kind = "auto"
    else:
        win, wins = pick_window(hwnd, title, interactive=interactive)
        if not win:
            raise RuntimeError("没找到 POCIB 窗口。请把客户端窗口打开（不要最小化）后再试。")
        img = O.capture_window(win["hwnd"])
        try:
            img = img.trim_border()      # 去掉窗口外圈黑边，认字更稳、预览更干净
        except Exception:
            pass
        src = {"title": win["title"], "hwnd": win["hwnd"]}
        img_path = None
        note("已截取窗口「%s」 %dx%d" % (win["title"], img.w, img.h))
        if kind == "auto" and win.get("kind") in ("goods", "company"):
            kind = win["kind"]

    # ---- 2. 识别
    t0 = time.time()
    if engine == "auto":
        engine = "rapid" if O.rapid_available() else "win"
    if engine == "rapid" and not O.rapid_available():
        note("没装 rapidocr-onnxruntime，改用系统自带 OCR（中文精度较低）")
        engine = "win"

    if engine == "rapid":
        if img is None:
            try:
                img = O.read_png(img_path)
            except Exception:
                img = None
        res = O.ocr_best(img) if img is not None else O.ocr_rapid(img_path)
    else:
        res = O.ocr([("0", img_path)]).get("0", {})
    if not res or not res.get("ok", True):
        raise RuntimeError("识别失败：%s" % (res or {}).get("error", "未知错误"))
    note("识别完成（%s，%.1fs，%d 行）" % (engine, time.time() - t0, len(res.get("lines") or [])))

    # ---- 3. 解析
    if kind == "auto":
        kind = detect_kind(res)
    out = P.extract(res, kind)
    fields = out["fields"]
    note("解析出 %d 个字段" % len(fields))

    payload = {
        "tool": "pocib-ocr",
        "v": 2,
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "source": src,
        "engine": engine,
        "size": [res.get("width"), res.get("height")],
        "fields": fields,
        "extras": out["extras"],
    }
    png = None
    if want_png and img is not None:
        try:
            png = img.to_png()
        except Exception:
            png = None

    if tmp_img and os.path.exists(tmp_img):
        try:
            os.remove(tmp_img)
        except OSError:
            pass
    return {"payload": payload, "png": png, "img": img, "win": win, "log": logs}


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hwnd", type=int)
    ap.add_argument("--title")
    ap.add_argument("--file")
    ap.add_argument("--clip", action="store_true", help="识别剪贴板里的截图")
    ap.add_argument("--kind", choices=["auto", "company", "goods"], default="auto")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", help="把结果另存为 json（默认只在剪贴板和屏幕上）")
    ap.add_argument("--no-clip", action="store_true")
    ap.add_argument("--engine", choices=["auto", "rapid", "win"], default="auto")
    ap.add_argument("--save-img", action="store_true", help="同时保存截图，便于对照")
    a = ap.parse_args()

    if a.list:
        for w in candidate_windows():
            say("%-10s %5dx%-5d %-6s %s" % (w["hwnd"], w["w"], w["h"],
                                            w["kind"], w["title"][:66]))
        return

    try:
        r = pipeline(hwnd=a.hwnd, title=a.title, file=a.file, clip=a.clip,
                     kind=a.kind, engine=a.engine, want_png=a.save_img)
    except RuntimeError as e:
        raise SystemExit(str(e))

    for msg in r["log"]:
        say(msg)
    payload, fields = r["payload"], r["payload"]["fields"]
    say("")
    say("  %-12s %-28s %s" % ("字段", "识别值", "置信"))
    say("  " + "-" * 62)
    for f in fields:
        v = f["value"]
        if len(v) > 26:
            v = v[:25] + "…"
        say("  %-12s %-28s %.2f" % (f["key"], v, f["conf"]))
    ex = payload.get("extras") or []
    if ex:
        say("")
        say("  另有 %d 段未归类文字：" % len(ex))
        for e in ex[:6]:
            say("    · " + e["text"][:50])

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if a.out:
        out_path = a.out
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        if a.save_img and r["png"]:
            shot_out = os.path.splitext(out_path)[0] + ".png"
            with open(shot_out, "wb") as f:
                f.write(r["png"])
            say("")
            say("截图已保存：%s" % shot_out)
    elif a.save_img and r["png"]:
        shot_out = os.path.join(os.environ.get("TEMP", "."), "POCIB截图_%s.png" % stamp)
        with open(shot_out, "wb") as f:
            f.write(r["png"])
        say("")
        say("截图已保存：%s" % shot_out)

    ok_clip = False
    if not a.no_clip:
        ok_clip = set_clipboard_text(json.dumps(payload, ensure_ascii=False))

    say("")
    if ok_clip:
        say("已复制到剪贴板（中文不会乱码）。回网页点「📷 截图识别」→ Ctrl+V → 解析。")
    elif not a.no_clip:
        say("写剪贴板失败，可加 --out 结果.json 再在网页里拖入该文件。")
    say("提示：跑「识图服务.bat」后网页里可以直接一键截取，不用剪贴板、不留文件。")


if __name__ == "__main__":
    main()
