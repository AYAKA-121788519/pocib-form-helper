# -*- coding: utf-8 -*-
"""生成可读版规格书 Markdown。"""
import os, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
S = os.path.join(ROOT, "spec")
os.makedirs(S, exist_ok=True)

FLOW = json.load(open(os.path.join(P, "flow_matrix.json"), encoding="utf-8"))
REG = json.load(open(os.path.join(P, "doc_registry.json"), encoding="utf-8"))
FILL = json.load(open(os.path.join(P, "fill_docs.json"), encoding="utf-8"))
DOCS = json.load(open(os.path.join(P, "documents.json"), encoding="utf-8"))

POCIB_HINT = re.compile(r'(在\s*POCIB|POCIB\s*中|系统自动|自动生成|系统将)')


def esc(s):
    return s.replace("|", "\\|")


def sec_flow():
    L = ["## 二、流程 × 结算方式 → 需提交单据", "",
         "来源：《各流程提交单据列表》（原页面为图片，已逐格转录）。共 21 个业务环节。", ""]
    L += ["| # | 环节 | 方向 | L/C | T/T | D/P | D/A |", "|---|---|---|---|---|---|---|"]
    for f in FLOW:
        cells = []
        for k in ("L/C", "T/T", "D/P", "D/A"):
            v = f["by"][k]
            txt = "无" if v == ["无"] else "<br>".join("%d. %s" % (i + 1, esc(x)) for i, x in enumerate(v))
            cells.append(txt)
        L.append("| %d | %s | %s | %s |" % (f["step"], f["name"], f["side"], " | ".join(cells)))
    L.append("")
    # 差异点
    same_all = [f["name"] for f in FLOW if len({tuple(f["by"][k]) for k in f["by"]}) == 1]
    diff = [f["name"] for f in FLOW if f["name"] not in same_all]
    L += ["**四种结算方式下单据完全相同的环节（%d 个）**：%s" % (len(same_all), "、".join(same_all)), "",
          "**结算方式会影响单据的环节（%d 个）**：%s" % (len(diff), "、".join(diff)), ""]
    return "\n".join(L)


def sec_registry():
    L = ["## 三、单据登记表：自己填制 vs 他人签发", "",
         "来源：《单据来源和签发时间列表》＋《常用单证》。这是本项目的范围边界。", ""]
    for kind, title in (("self", "### 1. 需要玩家自己填制（程序要做的事）"),
                        ("issued", "### 2. 他人/系统签发（程序只需提示“何时能拿到”）")):
        rows = [r for r in REG if r["kind"] == kind]
        L += [title, "", "| 单据 | 方向 | 来源 | 等待 | 字段数 |", "|---|---|---|---|---|"]
        for r in rows:
            L.append("| %s | %s | %s | %s | %s |" % (
                r["name"], r["side"], esc(r["issuer"]), r["wait"] or "—",
                r["field_count"] if kind == "self" else "—"))
        L.append("")
    return "\n".join(L)


def sec_fields():
    L = ["## 四、每份自制单证的字段与填写规则", "",
         "以下按“出口 → 进口”顺序展开，字段取自已抓取的百科填写说明原文；",
         "标注 🔹 的条目是 POCIB 系统特有规则（例如“由系统自动生成”），程序里必须特殊处理。", ""]
    order = [r["name"] for r in REG if r["kind"] == "self"]
    for entry in FILL:
        L.append("### %s（%s）" % (entry["name"], entry["side"]))
        L.append("")
        if entry.get("concept"):
            c = entry["concept"][0]
            L.append("> %s" % c[:180])
            L.append("")
        for sec in entry["fields"]:
            if not sec["fields"]:
                continue
            if sec["is_fill_section"]:
                L.append("**%s**" % sec["section"])
                L.append("")
            for f in sec["fields"]:
                L.append("- **%s**" % f["label"])
                for r in f["rules"][:6]:
                    mark = " 🔹" if POCIB_HINT.search(r) else ""
                    L.append("  - %s%s" % (r[:260], mark))
            L.append("")
    return "\n".join(L)


def main():
    header = """# POCIB i+ 单证填写规格书

> 数据来源：POCIB i+ 百科（`http://192.168.150.135:61234/baike/`），全站 366 个页面 + 4 张关键表格图片。
> 抓取与结构化时间：2026-11-11。仅作内部分析与辅助工具开发依据。

## 一、总体结论

| 指标 | 数量 |
|---|---|
| 百科页面（已抓取） | 366 |
| 业务环节（流程节点） | 21 |
| 涉及单证（登记表口径） | 43 |
| 其中**需自己填制** | 21 |
| 其中**由银行/承运人/海关/系统签发** | 22 |
| 自制单证的字段（表单项）总数 | 489 |

**三条对产品设计最关键的事实：**

1. **真正要“填”的只有 21 份单证，489 个字段。** 其余 22 份是签发件（配舱回单、商检证书、提单、缴款书等），程序不需要生成，但需要告诉用户“先做什么、等多久才能拿到”。
2. **单据清单由两个维度决定：结算方式（L/C / T/T / D/P / D/A）× 贸易术语（FOB/CFR/CIF/FCA/CPT/CIP/DAP/DPU）。** 21 个环节里有 5 个环节的单据随结算方式变化；保险单、投保单、国际货运代理发票等随术语变化；商检证书则取决于合同的 Document 条款。
3. **大量字段是“由其他单据推导”而非独立录入**（发票号→报关单号、合同→发票/装箱单/委托书、信用证→发票/汇票/提单）。这正是“预处理数据、减少重复填写”的价值所在。

"""
    body = "\n".join([header, sec_flow(), sec_registry(), sec_fields()])
    with open(os.path.join(S, "POCIB单证填写规格.md"), "w", encoding="utf-8") as f:
        f.write(body)
    print("written", len(body), "chars")


if __name__ == "__main__":
    main()
