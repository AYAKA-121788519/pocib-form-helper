# -*- coding: utf-8 -*-
"""抽出所有 POCIB 系统特有规则（"在POCIB中..."），按单证归类。"""
import os, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
FILL = json.load(open(os.path.join(P, "fill_docs.json"), encoding="utf-8"))

HINT = re.compile(r'(在\s*POCIB|POCIB\s*中|系统自动|自动生成|系统将)')
L = ["# POCIB 系统特有规则清单", "",
     "> 从百科填写说明中筛出的“POCIB 平台行为”类描述（非通用外贸惯例）。",
     "> 这类规则决定了辅助填单程序必须内置的系统逻辑，通用制单软件通常不会覆盖。", ""]

total = 0
for e in FILL:
    hits = []
    for sec in e["fields"]:
        for f in sec["fields"]:
            for r in f["rules"]:
                if HINT.search(r):
                    hits.append((f["label"], r))
    if not hits:
        continue
    L.append("## %s（%s，%d 条）" % (e["name"], e["side"], len(hits)))
    L.append("")
    for lab, r in hits:
        L.append("- **%s** — %s" % (lab, r))
        total += 1
    L.append("")

L.insert(4, "合计 %d 条。\n" % total)
open(os.path.join(ROOT, "spec", "POCIB系统特有规则.md"), "w", encoding="utf-8").write("\n".join(L))
print("rules", total)
