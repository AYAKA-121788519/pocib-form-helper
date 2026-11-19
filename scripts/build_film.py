#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按旁白时长生成 video/film.html 时间线（以及每个分区的取景页 shots/NN.html）。

数据来源：video/vo.json（每句时长）+ 下面的 SHOTS 表（镜头取景）。
改文案 → 重跑 scripts/tts_local.py → 重跑本脚本 → 重新 render，镜头时长自动跟着变。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(ROOT, "video")
SHOTDIR = os.path.join(VID, "shots")
LEAD = 0.15      # 画面先出，声音后进
GAP = 0.30       # 句间留白
TAIL = 1.40      # 收尾停留

# key, 页面（None=用 zoom 模板生成）, 取景参数（坐标是截图里的 CSS 像素）
SHOTS = [
    ("01", "01-numbers.html", None),
    ("02", "02-mess.html", None),
    ("03", None, dict(img="assets/shots/panel.png", cx=340, cy0=380, cy1=860, s=1.22,
                      hl="12,150,332,900", label="交易剖面", sub="源头数据都在这一栏")),
    ("04", None, dict(img="assets/shots/panel.png", cx=488, cy0=360, cy1=1000, s=1.42,
                      hl="354,130,270,980", label="履约流程", sub="21 个环节")),
    ("05", None, dict(img="assets/shots/panel.png", cx=1271, cy0=420, cy1=760, s=1.08,
                      hl="632,150,1278,880", label="派生值", sub="改一个数，全部重算")),
    ("06", None, dict(img="assets/shots/panel.png", cx=960, cy0=2080, cy1=2120, s=0.86,
                      hl="12,1799,1896,570", label="选品参考", sub="五国价差排行")),
    ("07", None, dict(img="assets/shots/panel-tariff.png", cx=960, cy0=2540, cy1=2600, s=0.92,
                      hl="12,2413,1896,340", label="海关税率查询", sub="内置全库")),
    ("08", None, dict(img="assets/shots/letters.png", cx=960, cy0=700, cy1=1150, s=1.0,
                      hl="682,431,1124,1010", label="进出口预算", sub="运费联动")),
    ("09", None, dict(img="assets/shots/letters.png", cx=960, cy0=3120, cy1=3240, s=0.95,
                      hl="114,2794,1692,780", label="全套函电", sub="中英对照")),
    ("10", "end.html", None),
]

TPL = open(os.path.join(VID, "zoom.tpl"), encoding="utf-8").read()


def write_zoom(key, cfg, dur, cap):
    os.makedirs(SHOTDIR, exist_ok=True)
    cfg = dict(cfg, dur=round(dur, 2), cap=cap)
    cfg["img"] = "../" + cfg["img"]
    html = TPL.replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
    path = os.path.join(SHOTDIR, key + ".html")
    open(path, "w", encoding="utf-8").write(html)
    return "shots/%s.html" % key


def main():
    vo = json.load(open(os.path.join(VID, "vo.json"), encoding="utf-8"))
    rows = []
    t = 0.0
    for key, page, args in SHOTS:
        info = vo.get(key)
        if not info:
            raise SystemExit(f"vo.json 里没有第 {key} 句，先跑 tts_local.py")
        dur = float(info["dur"])
        clip = dur + LEAD + GAP
        src = write_zoom(key, args, clip, info["text"]) if args else page
        src = src + "#t=0,%.2f" % clip
        rows.append((key, src, t, clip, t + LEAD, dur, info["wav"]))
        t += clip

    total = t + TAIL
    head = [
        "<!doctype html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=1920, height=1080">',
        "<style>",
        "  html,body{margin:0;background:#0b0e13}",
        "  .clip{position:absolute;left:0;top:0;width:1920px;height:1080px}",
        "</style>",
        "</head>",
        "<body>",
        "<section>",
    ]
    for key, src, at, clip, _, _, _ in rows:
        head.append(
            f'  <iframe id="s{key}" class="clip" src="{src}" at="{at:.2f}"></iframe>'
        )
    head += ["</section>", "<section>"]
    for key, _, _, _, aat, _, audio in rows:
        head.append(f'  <audio id="vo{key}" src="{audio}" at="{aat:.2f}" volume="1"></audio>')
    head += ["</section>", "</body>", "</html>"]

    open(os.path.join(VID, "film.html"), "w", encoding="utf-8").write("\n".join(head) + "\n")

    print(f"film.html 写好：{len(rows)} 个镜头，总长 {total:.2f}s")
    for key, src, at, clip, aat, dur, _ in rows:
        print(f"  {key}  画面 {at:6.2f}–{at+clip:6.2f}  旁白 {aat:6.2f}+{dur:.2f}s  {src}")


if __name__ == "__main__":
    main()
