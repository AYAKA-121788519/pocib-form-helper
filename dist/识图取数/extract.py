# -*- coding: utf-8 -*-
"""POCIB 识图取数 —— 截取客户端窗口 → OCR → 拆成字段 → 输出 JSON 供主程序核对填入。

常用：
  python extract.py                      自动找 POCIB 窗口，识别并输出结果
  python extract.py --list               只列出候选窗口
  python extract.py --hwnd 123456        指定窗口句柄
  python extract.py --file 截图.png       直接识别一张图（支持 Win+Shift+S 剪贴板图）
  python extract.py --kind goods         明确按商品档案解析
  python extract.py --no-clip            不把结果复制到剪贴板
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocrlib as O
import parse as P

TITLE_HINTS = ("世格 POCIB", "Business-", "基本资料", "商品", "我的", "市场", "合同", "库存", "订单")


def desk_dir():
    home = os.path.expanduser("~")
    for d in (os.path.join(home, "Desktop"),
              os.path.join(home, "OneDrive", "Desktop"),
              os.path.join(home, "桌面")):
        if os.path.isdir(d):
            return d
    return os.environ.get("TEMP", ".")


OUT_DIR = desk_dir()


def say(*a):
    try:
        print(*a, flush=True)
    except UnicodeEncodeError:
        txt = " ".join(str(x) for x in a)
        enc = sys.stdout.encoding or "gbk"
        print(txt.encode(enc, "replace").decode(enc, "replace"), flush=True)


def pick_window(hwnd=None, title=None):
    wins = O.list_windows()
    if hwnd:
        for w in wins:
            if w["hwnd"] == hwnd:
                return w
        return {"hwnd": hwnd, "title": "(指定句柄)", "rect": (0, 0, 0, 0)}
    if title:
        hit = [w for w in wins if title.lower() in w["title"].lower()]
        return hit[0] if hit else None
    cands = []
    for w in wins:
        t = w["title"]
        if any(h.lower() in t.lower() for h in TITLE_HINTS):
            x0, y0, x1, y1 = w["rect"]
            if x1 - x0 < 400 or y1 - y0 < 300:
                continue  # 太小，不是内容窗
            if x0 <= -30000 or y0 <= -30000:
                continue  # 已最小化
            cands.append(w)
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    say("发现 %d 个可能的窗口：" % len(cands))
    for i, w in enumerate(cands):
        x0, y0, x1, y1 = w["rect"]
        say("  [%d] %-46s %dx%d" % (i + 1, w["title"][:46], x1 - x0, y1 - y0))
    idx = input("要识别哪个？输入序号（直接回车=第1个）：").strip() or "1"
    try:
        return cands[int(idx) - 1]
    except Exception:
        return cands[0]


def from_clipboard():
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
        raise SystemExit("剪贴板里没有图片。先按 Win+Shift+S 截图，或直接给 --file 路径。")
    return tmp


def detect_kind(res):
    txt = "".join((l.get("text") or "") for l in res.get("lines") or [])
    goods_hint = sum(k in txt for k in ("商品编号", "毛重", "净重", "销售单位", "商品属类", "包装"))
    comp_hint = sum(k in txt for k in ("公司全称", "开户行", "统一社会信用代码", "法人代表", "本币账号"))
    return "goods" if goods_hint > comp_hint else "company"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hwnd", type=int)
    ap.add_argument("--title")
    ap.add_argument("--file")
    ap.add_argument("--clip", action="store_true", help="识别剪贴板里的截图")
    ap.add_argument("--kind", choices=["auto", "company", "goods"], default="auto")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--no-clip", action="store_true")
    ap.add_argument("--engine", choices=["auto", "rapid", "win"], default="auto")
    ap.add_argument("--save-img", action="store_true", help="同时保存截图，便于对照")
    a = ap.parse_args()

    if a.list:
        for w in O.list_windows():
            x0, y0, x1, y1 = w["rect"]
            say("%-10s %5dx%-5d %s" % (w["hwnd"], x1 - x0, y1 - y0, w["title"][:70]))
        return

    # ---- 1. 取图
    src = {"title": "", "hwnd": 0}
    img = None
    tmp_img = None
    if a.file:
        img_path = a.file
        if not os.path.exists(img_path):
            raise SystemExit("找不到文件：%s" % img_path)
        src["title"] = os.path.basename(img_path)
    elif a.clip:
        img_path = from_clipboard()
        tmp_img = img_path
        src["title"] = "剪贴板截图"
    else:
        w = pick_window(a.hwnd, a.title)
        if not w:
            raise SystemExit("没找到 POCIB 窗口。请把客户端窗口打开（不要最小化），"
                             "或用 --file 指定一张截图。--list 可以看当前所有窗口标题。")
        img = O.capture_window(w["hwnd"])
        src = {"title": w["title"], "hwnd": w["hwnd"]}
        tmp_img = os.path.join(os.environ.get("TEMP", "."), "pocib_shot_%d.png" % int(time.time()))
        img.save(tmp_img)
        img_path = tmp_img
        say("[1/3] 已截取窗口「%s」 %dx%d" % (w["title"], img.w, img.h))

    # ---- 2. 识别
    t0 = time.time()
    engine = a.engine
    if engine == "auto":
        engine = "rapid" if O.rapid_available() else "win"
    if engine == "rapid" and not O.rapid_available():
        say("提示：未装 rapidocr-onnxruntime，改用系统自带 OCR（中文精度较低，建议先 pip install rapidocr-onnxruntime）")
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
        raise SystemExit("识别失败：%s" % (res or {}).get("error", "未知错误"))
    say("[2/3] 识别完成（%s，%.1fs，%d 行）" % (engine, time.time() - t0, len(res.get("lines") or [])))

    # ---- 3. 解析
    kind = a.kind
    if kind == "auto":
        kind = detect_kind(res)
    out = P.extract(res, kind)
    fields = out["fields"]
    say("[3/3] 解析出 %d 个字段" % len(fields))
    say("")
    say("  %-12s %-28s %s" % ("字段", "识别值", "置信"))
    say("  " + "-" * 62)
    for f in fields:
        v = f["value"]
        if len(v) > 26:
            v = v[:25] + "…"
        say("  %-12s %-28s %.2f" % (f["key"], v, f["conf"]))
    if out["extras"]:
        say("")
        say("  另有 %d 段未归类文字（可在主程序里手动对号入座）：" % len(out["extras"]))
        for e in out["extras"][:6]:
            say("    · " + (e["text"][:50]))

    # ---- 4. 输出
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {
        "tool": "pocib-ocr",
        "v": 1,
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "source": src,
        "engine": engine,
        "size": [res.get("width"), res.get("height")],
        "fields": fields,
        "extras": out["extras"],
    }
    out_path = a.out or os.path.join(OUT_DIR, "POCIB识别_%s.json" % stamp)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    except OSError:
        out_path = os.path.join(os.environ.get("TEMP", "."), "POCIB识别_%s.json" % stamp)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    clip_txt = json.dumps(payload, ensure_ascii=False)
    if not a.no_clip:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "$t=[Console]::In.ReadToEnd(); Set-Clipboard -Value $t"],
                           input=clip_txt, text=True, encoding="utf-8",
                           capture_output=True, creationflags=0x08000000)
        except Exception:
            pass

    if a.save_img and tmp_img and os.path.exists(tmp_img):
        shot_out = os.path.splitext(out_path)[0] + ".png"
        try:
            os.replace(tmp_img, shot_out)
            say("")
            say("截图已保存：%s" % shot_out)
        except OSError:
            pass
    elif tmp_img and os.path.exists(tmp_img) and not a.file:
        try:
            os.remove(tmp_img)
        except OSError:
            pass

    say("")
    say("结果文件：%s" % out_path)
    if not a.no_clip:
        say("（内容已复制到剪贴板，可在网页里 Ctrl+V 直接粘贴）")
    say("下一步：打开 POCIB 填单助手 → 左栏「📷 截图识别公司信息 / 商品」"
        "→ Ctrl+V → 解析 → 核对后填入。")


if __name__ == "__main__":
    main()
