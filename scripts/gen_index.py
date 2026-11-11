# -*- coding: utf-8 -*-
"""导出字段总览 CSV + 项目 README。"""
import os, json, re, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
FILL = json.load(open(os.path.join(P, "fill_docs.json"), encoding="utf-8"))
REG = json.load(open(os.path.join(P, "doc_registry.json"), encoding="utf-8"))
FLOW = json.load(open(os.path.join(P, "flow_matrix.json"), encoding="utf-8"))

rows = []
for e in FILL:
    for sec in e["fields"]:
        for f in sec["fields"]:
            lab = f["label"]
            m = re.search(r'[（(]([A-Za-z0-9 .,&/／\-#\'’]+)[)）]\s*$', lab)
            zh = re.sub(r'[（(][A-Za-z0-9 .,&/／\-#\'’]+[)）]\s*$', '', lab).strip() or lab
            rows.append([e["name"], e["side"], sec["section"],
                         lab, zh, (m.group(1).strip() if m else ""), len(f["rules"])])

with open(os.path.join(ROOT, "spec", "字段总览.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["单证", "方向", "章节", "字段原文", "中文字段名", "英文名", "规则条数"])
    w.writerows(rows)
print("fields", len(rows))

self_docs = [r for r in REG if r["kind"] == "self"]
issued = [r for r in REG if r["kind"] == "issued"]
readme = f"""# POCIB 辅助填单工具 · 资料与规格库

本目录是对 POCIB i+ 百科官方教程的完整抓取与结构化，作为开发“辅助填单本地程序”的依据。

## 目录结构

```
pocib-helper/
├─ data/
│  ├─ raw/           367 个原始 HTML 页面（全站，含 _graph.json 链接图）
│  ├─ img/           4 张关键表格图片 + slices/ 切片放大图
│  └─ parsed/
│     ├─ documents.json     每页的章节/字段/填写说明原文（366 页）
│     ├─ flow_matrix.json   21 个流程环节 × 4 种结算方式 → 需提交单据
│     ├─ doc_registry.json  43 份单证登记（自制/签发、来源、等待时长、字段数）
│     └─ fill_docs.json     21 份自制单证的字段与规则（程序主数据源）
├─ spec/
│  ├─ POCIB单证填写规格.md   可读版规格书（结论 + 流程矩阵 + 字段规则）
│  ├─ POCIB系统特有规则.md   241 条平台行为规则（最容易踩坑的部分）
│  └─ 字段总览.csv          489 个字段的扁平清单，便于筛选与映射
└─ scripts/          抓取与生成脚本（crawl / parse_docs / build_spec / gen_md / gen_rules）
```

## 关键口径

- 涉及单证 **{len(REG)}** 份，其中**需玩家自己填制 {len(self_docs)} 份**，他人/系统签发 {len(issued)} 份。
- 自制单证字段合计 **{len(rows)}** 个。
- 流程环节 **{len(FLOW)}** 个；其中 {sum(1 for f in FLOW if len({tuple(f['by'][k]) for k in f['by']}) > 1)} 个环节的单据会随结算方式变化。

## 重新生成

```bash
python scripts/crawl.py      # 重新抓站（需能访问 192.168.150.135:61234）
python scripts/parse_docs.py # HTML -> documents.json
python scripts/build_spec.py # -> flow_matrix / doc_registry / fill_docs
python scripts/gen_md.py     # -> 规格书
python scripts/gen_rules.py  # -> 系统特有规则
```
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)
print("readme ok")
