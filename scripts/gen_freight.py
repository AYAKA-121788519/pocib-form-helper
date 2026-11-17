# -*- coding: utf-8 -*-
"""把 data/freight.json 压成 FREIGHT 常量，写进 app/index.html 的标记区间。

用法：python scripts/gen_freight.py [--check]
     --check 只比对，不写文件（CI / 自测用）
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "freight.json")
APP = os.path.join(ROOT, "app", "index.html")
BEGIN = "/* __FREIGHT_DATA_BEGIN__ */"
END = "/* __FREIGHT_DATA_END__ */"


def build():
    d = json.load(open(SRC, encoding="utf-8"))
    out = {"meta": d.get("meta", {}), "sea": {}, "air": {}}
    for mode in ("sea", "air"):
        for route, v in d.get(mode, {}).items():
            k = route.lower()
            if mode == "sea":
                dry, rf = v.get("dry") or {}, v.get("rf") or {}
                out["sea"][k] = {
                    "name": route, "o": v.get("o"), "d": v.get("d"), "h": v.get("h"),
                    "dry": [dry.get("c20"), dry.get("c40"), dry.get("c40h"),
                            dry.get("mtq"), dry.get("tne")],
                    "rf": [rf.get("c20"), rf.get("c40"), rf.get("c40h"),
                           rf.get("mtq"), rf.get("tne")],
                }
            else:
                t = v.get("tiers") or {}
                out["air"][k] = {
                    "name": route, "o": v.get("o"), "d": v.get("d"), "h": v.get("h"),
                    "t": [t.get("Minimum"), t.get("Normal"), t.get("45kgs"),
                          t.get("100kgs"), t.get("300kgs"), t.get("500kgs"),
                          t.get("1000kgs")],
                }
    out["meta"]["n"] = [len(out["sea"]), len(out["air"])]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    data = build()
    js = "const FREIGHT=" + json.dumps(data, ensure_ascii=False,
                                      separators=(",", ":")) + ";"
    html = open(APP, encoding="utf-8").read()
    m = re.search(re.escape(BEGIN) + r"([\s\S]*?)" + re.escape(END), html)
    if not m:
        print("✗ 找不到标记区间 %s ... %s" % (BEGIN, END), file=sys.stderr)
        sys.exit(1)
    cur = m.group(1).strip()
    if cur == js:
        print("已是最新：海运 %d 条 / 空运 %d 条" % tuple(data["meta"]["n"]))
        return
    if a.check:
        print("✗ 内嵌的 FREIGHT 与 data/freight.json 不一致，先跑 python scripts/gen_freight.py",
              file=sys.stderr)
        sys.exit(1)
    html = html[:m.start(1)] + "\n" + js + "\n" + html[m.end(1):]
    open(APP, "w", encoding="utf-8", newline="").write(html)
    print("已写入 app/index.html：海运 %d 条 / 空运 %d 条（%d KB）"
          % (data["meta"]["n"][0], data["meta"]["n"][1], len(js) // 1024))


if __name__ == "__main__":
    main()
