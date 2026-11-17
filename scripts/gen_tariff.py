# -*- coding: utf-8 -*-
"""把 data/tariff.json 压成 TARIFF 常量，写进 app/index.html 的标记区间。

用法：python scripts/gen_tariff.py [--check]
     --check 只比对，不写文件（自测 / 校验用）

压缩方式：行是数组，单位为字典下标，监管条件同理；
数字为 null 用 -1 表示（0 是有意义的「免税」）。
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "tariff.json")
APP = os.path.join(ROOT, "app", "index.html")
BEGIN = "/* __TARIFF_DATA_BEGIN__ */"
END = "/* __TARIFF_DATA_END__ */"


def build():
    d = json.load(open(SRC, encoding="utf-8"))
    items = d.get("items", [])
    units, ctrls = [], []
    rows = []
    for it in items:
        u = it.get("unit") or ""
        c = it.get("ctrl") or ""
        if u not in units:
            units.append(u)
        if c not in ctrls:
            ctrls.append(c)

        def n(v):
            return -1 if v is None else round(float(v), 4)

        rows.append([
            it["hs"], it["name"],
            n(it.get("imGen")), n(it.get("imPref")), n(it.get("ex")), n(it.get("vat")),
            n(it.get("csQty")), n(it.get("csVal")), n(it.get("rebate")),
            units.index(u), ctrls.index(c),
        ])
    return {
        "meta": {"count": len(rows), "generated": d.get("meta", {}).get("generated", "")},
        "units": units, "ctrls": ctrls, "rows": rows,
    }


def js_of(data):
    parts = [
        "const TARIFF_UNIT=" + json.dumps(data["units"], ensure_ascii=False, separators=(",", ":")) + ";",
        "const TARIFF_CTRL=" + json.dumps(data["ctrls"], ensure_ascii=False, separators=(",", ":")) + ";",
        '/* [HS编码, 品名, 进口普通, 进口优惠, 出口税, 增值税, 消费税从量, 消费税从价, 退税, 单位, 监管条件] */',
        "const TARIFF=" + json.dumps(data["rows"], ensure_ascii=False, separators=(",", ":")) + ";",
    ]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    data = build()
    js = js_of(data)
    html = open(APP, encoding="utf-8").read()
    m = re.search(re.escape(BEGIN) + r"([\s\S]*?)" + re.escape(END), html)
    if not m:
        print("✗ 找不到标记区间 %s ... %s" % (BEGIN, END), file=sys.stderr)
        sys.exit(1)
    if m.group(1).strip() == js:
        print("已是最新：%d 条税率" % data["meta"]["count"])
        return
    if a.check:
        print("✗ 内嵌税率与 data/tariff.json 不一致，先跑 python scripts/gen_tariff.py",
              file=sys.stderr)
        sys.exit(1)
    html = html[:m.start(1)] + "\n" + js + "\n" + html[m.end(1):]
    open(APP, "w", encoding="utf-8", newline="").write(html)
    print("已写入 app/index.html：%d 条税率（%d KB，单位 %d 种 / 监管条件 %d 种）"
          % (data["meta"]["count"], len(js) // 1024, len(data["units"]), len(data["ctrls"])))


if __name__ == "__main__":
    main()
