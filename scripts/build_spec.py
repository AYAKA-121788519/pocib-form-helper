# -*- coding: utf-8 -*-
"""把爬取结果整理成程序可用的结构化规格：
   - flow_matrix.json   流程 → 结算方式 → 需提交单据（含条件说明）
   - doc_registry.json  单据登记表（自制/签发、来源、等待时长）
   - fill_docs.json     只含"需自己填制"的单证 + 字段填写规则
"""
import os, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
docs = json.load(open(os.path.join(P, "documents.json"), encoding="utf-8"))

# ---------------------------------------------------------------- 流程矩阵
# 来源：《各流程提交单据列表》（图片表格，已人工逐格转录）
NO = "无"
ALL = ["L/C", "T/T", "D/P", "D/A"]


def same(items):
    return {k: items for k in ALL}


FLOW = [
    {"step": 1, "name": "申请开证", "side": "进口", "by": same([NO]),
     "override": {"L/C": ["不可撤销信用证开证申请书", "合同"]}},
    {"step": 2, "name": "信用证修改申请", "side": "进口", "by": same([NO]),
     "override": {"L/C": ["信用证修改申请书"]}},
    {"step": 3, "name": "订舱", "side": "出口",
     "by": same(["国际海运委托书（空运为国际空运委托书）", "商业发票", "装箱单"]), "override": {}},
    {"step": 4, "name": "出口报检", "side": "出口",
     "by": same(["出境货物检验检疫申请", "商业发票", "装箱单", "外销合同"]),
     "override": {"L/C": ["出境货物检验检疫申请", "商业发票", "装箱单", "外销合同",
                          "信用证", "信用证修改书（修改过信用证才需要，须先点“接受”并提交全部修改书）"]}},
    {"step": 5, "name": "申请产地证", "side": "出口",
     "by": same(["商业发票", "装箱单", "一般原产地证 或 普惠制产地证明书"]), "override": {}},
    {"step": 6, "name": "申请鉴定（部分特定商品需要）", "side": "出口",
     "by": same(["商业发票", "装箱单", "申请鉴定表"]), "override": {}},
    {"step": 7, "name": "办理保险", "side": "出口",
     "by": same(["商业发票（CIF/CIP 才需提交；FOB/CFR/FCA/CPT 无需）", "投保单"]), "override": {}},
    {"step": 8, "name": "送货", "side": "出口",
     "by": same(["货物运输条件鉴定书（仅商品 21001/40001/40002/06002 需要；其他商品送货无需任何单据）"]),
     "override": {}},
    {"step": 9, "name": "出口报关", "side": "出口",
     "by": same(["出口货物报关单", "商业发票", "装箱单",
                 "航空运单（空运需提交）",
                 "货物运输条件鉴定书（商品 21001/40001/40002/06002 需要）"]), "override": {}},
    {"step": 10, "name": "取回提单（空运无需此步）", "side": "出口",
     "by": same(["配舱回单"]), "override": {}},
    {"step": 11, "name": "交单/押汇/T/T寄单（交单与押汇二选一）", "side": "出口",
     "by": {
         "L/C": ["信用证", "信用证修改书（修改过才需要，须点“接受”并提交全部修改书）", "汇票",
                 "商业发票", "装箱单", "海运提单（空运为航空运单）",
                 "货物运输保险单（CIF/CIP 方式下）",
                 "一般原产地证或普惠制产地证明书（类型须符合合同且已申请）",
                 "商检证书-品质证书", "商检证书-健康证书", "商检证书-数量/重量证书",
                 "商检证书-植物检疫证书（4 类商检证书按合同 Document 条款，合同规定必须提交，未规定则无需）",
                 "出口押汇申请书（办理押汇才需提交，仅交单无需）"],
         "T/T": ["商业发票", "装箱单", "海运提单（空运为航空运单）",
                 "货物运输保险单（CIF/CIP 方式下）",
                 "一般原产地证或普惠制产地证明书（类型须符合合同且已申请）",
                 "商检证书（4 类，按合同 Document 条款，规定则必须提交）"],
         "D/P": ["托收委托书", "汇票", "商业发票", "装箱单", "海运提单（空运为航空运单）",
                 "货物运输保险单（CIF/CIP 方式下）",
                 "一般原产地证或普惠制产地证明书（类型须符合合同且已申请）",
                 "商检证书（4 类，按合同 Document 条款，规定则必须提交）",
                 "出口押汇申请书（办理押汇才需提交）"],
         "D/A": ["托收委托书", "汇票", "商业发票", "装箱单", "海运提单（空运为航空运单）",
                 "货物运输保险单（CIF/CIP 方式下）",
                 "一般原产地证或普惠制产地证明书（类型须符合合同且已申请）",
                 "商检证书（4 类，按合同 Document 条款，规定则必须提交）",
                 "出口押汇申请书（办理押汇才需提交）"],
     }, "override": {}},
    {"step": 12, "name": "支付运费", "side": "出口",
     "by": same(["境内汇款申请书", "国际货运代理专业发票"]), "override": {}},
    {"step": 13, "name": "申请出口退税", "side": "出口",
     "by": same(["商业发票", "增值税专用发票"]), "override": {}},
    {"step": 14, "name": "付款", "side": "进口",
     "by": {"L/C": ["信用证"],
            "T/T": ["境外汇款申请书（全款 / 定金 / 尾款三个版本，视付款安排）"],
            "D/P": ["对外付款/承兑通知书"],
            "D/A": ["对外付款/承兑通知书"]}, "override": {}},
    {"step": 15, "name": "承兑", "side": "进口",
     "by": {"L/C": ["对外付款/承兑通知书（远期信用证可先承兑再付款）"],
            "T/T": ["T/T 无需此步骤"],
            "D/P": ["D/P 无需此步骤"],
            "D/A": ["对外付款/承兑通知书"]}, "override": {}},
    {"step": 16, "name": "取提货单", "side": "进口",
     "by": same(["海运提单（空运方式下无需提交单据）"]), "override": {}},
    {"step": 17, "name": "索赔", "side": "进口",
     "by": same(["货物运输保险单", "索赔申请书", "出险通知书"]), "override": {}},
    {"step": 18, "name": "进口报检", "side": "进口",
     "by": same(["提货单（空运为“提货通知单”+“航空运单”）", "入境货物检验检疫申请", "外销合同",
                 "商业发票", "装箱单", "原产地证明书", "普惠制产地证明书",
                 "商检证书 4 类（合同 Document 条款规定了则必须提交）"]), "override": {}},
    {"step": 19, "name": "进口报关", "side": "进口",
     "by": same(["提货单（空运为“提货通知单”+“航空运单”）", "进口货物报关单", "外销合同",
                 "商业发票", "装箱单"]), "override": {}},
    {"step": 20, "name": "进口缴税", "side": "进口",
     "by": same(["海关进口关税专用缴款书", "海关进口增值税专用缴款书",
                 "海关进口消费税专用缴款书（有消费税的商品需要）"]), "override": {}},
    {"step": 21, "name": "提货", "side": "进口",
     "by": same(["提货单（空运为“提货通知单”+“航空运单”）"]), "override": {}},
]
for f in FLOW:
    for k, v in f["override"].items():
        f["by"][k] = v
    f.pop("override")

# ---------------------------------------------------------------- 单据登记表
# 来源：《单据来源和签发时间列表》（图片表格，已人工转录）
# kind: self=玩家需自己填制 / issued=他人签发（只需知道何时能拿到）
REG = [
    # 出口
    ("信用证通知书", "出口", "issued", "出口地银行制作", ""),
    ("信用证修改通知书", "出口", "issued", "出口地银行制作", ""),
    ("商业发票", "出口", "self", "出口商自制", ""),
    ("装箱单", "出口", "self", "出口商自制", ""),
    ("国际海运委托书", "出口", "self", "出口商自制", ""),
    ("国际空运委托书", "出口", "self", "出口商自制", ""),
    ("配舱回单", "出口", "issued", "海运订舱后签发", "1 小时"),
    ("进舱通知单", "出口", "issued", "空运订舱后签发", "1 小时"),
    ("出境货物检验检疫申请", "出口", "self", "出口商自制", ""),
    ("商检证书-品质证书", "出口", "issued", "出口报检后签发", "1 小时"),
    ("商检证书-健康证书", "出口", "issued", "出口报检后签发", "1 小时"),
    ("商检证书-植物检疫证书", "出口", "issued", "出口报检后签发", "1 小时"),
    ("商检证书-数量/重量证书", "出口", "issued", "出口报检后签发", "1 小时"),
    ("一般原产地证", "出口", "self", "出口商自制", ""),
    ("普惠制产地证", "出口", "self", "出口商自制", ""),
    ("申请鉴定表", "出口", "self", "出口商自制", ""),
    ("货物运输条件鉴定书", "出口", "issued", "申请鉴定后签发", "1 小时"),
    ("投保单", "出口", "self", "出口商或进口商自制", ""),
    ("货物运输保险单", "出口", "issued",
     "FOB/FCA 术语需等出口商订舱完成后系统才签发；CIF/CFR/CIP/CPT 无需等待", ""),
    ("航空运单", "出口", "issued", "送货后签发（空运方式下）", ""),
    ("出口货物报关单", "出口", "self", "出口商自制", ""),
    ("国际货运代理专业发票", "出口", "issued", "CIF/CFR 货物出运后签发，FOB 到货时签发", ""),
    ("海运提单", "出口", "issued", "货物出运后到货运公司取回", ""),
    ("托收委托书", "出口", "self", "出口商自制", ""),
    ("出口押汇申请书", "出口", "self", "出口商自制", ""),
    ("汇票", "出口", "self", "出口商自制", ""),
    ("境内汇款申请书", "出口", "self", "出口商或进口商自制", ""),
    ("增值税专用发票", "出口", "issued", "货物出运后签发", ""),
    # 进口
    ("不可撤销信用证开证申请书", "进口", "self", "进口商自制", ""),
    ("信用证", "进口", "issued", "申请开证后签发", "1 小时"),
    ("信用证修改申请书", "进口", "self", "进口商自制", ""),
    ("信用证修改书", "进口", "issued", "申请修改信用证后签发", "1 小时"),
    ("境外汇款申请书", "进口", "self", "进口商自制（T/T 付款用）", ""),
    ("提货单", "进口", "issued", "到货后从货运公司换取（海运）", ""),
    ("提货通知单", "进口", "issued", "到货后从货运公司领取（空运）", ""),
    ("出险通知书", "进口", "issued", "货物发生意外后签发（未办理保险则无此单据）", ""),
    ("索赔申请书", "进口", "self", "进口商自制", ""),
    ("入境货物检验检疫申请", "进口", "self", "进口商自制", ""),
    ("进口货物报关单", "进口", "self", "进口商自制", ""),
    ("进口增值税缴款书", "进口", "issued", "进口报关后签发", "1 小时"),
    ("进口关税缴款书", "进口", "issued", "进口报关后签发", "1 小时"),
    ("进口消费税缴款书", "进口", "issued", "进口报关后签发", "1 小时"),
    # 合同：由出口商起草（不在来源表中，但属自制）
    ("合同（外销合同）", "出口", "self", "出口商起草，双方确认", ""),
]

# 登记名 -> documents.json 中的页面名
PAGE = {
    "商业发票": "商业发票", "装箱单": "装箱单",
    "国际海运委托书": "国际海运委托书", "国际空运委托书": "国际空运委托书",
    "出境货物检验检疫申请": "出境货物检验检疫申请",
    "一般原产地证": "一般原产地证书", "普惠制产地证": "普惠制产地证",
    "申请鉴定表": "申请鉴定表", "投保单": "货物运输投保单",
    "出口货物报关单": "出口货物报关单", "托收委托书": "托收委托书",
    "出口押汇申请书": "出口押汇申请书", "汇票": "汇票",
    "境内汇款申请书": "境内汇款申请书",
    "不可撤销信用证开证申请书": "信用证开证申请书",
    "信用证修改申请书": "信用证修改申请书",
    "境外汇款申请书": "境外汇款申请书",
    "索赔申请书": "索赔申请书",
    "入境货物检验检疫申请": "入境货物检验检疫申请",
    "进口货物报关单": "进口货物报关单",
    "合同（外销合同）": "合同",
    "货物运输保险单": "货物运输保险单",
    "信用证": "信用证",
}

LABEL_EN = re.compile(r'[（(]([A-Za-z0-9 .,&/／\-#\'’]+)[)）]\s*$')


def fields_of(page_key):
    p = docs.get(page_key)
    if not p:
        return []
    out = []
    for s in p["sections"]:
        for f in s["fields"]:
            lab = f["label"]
            m = LABEL_EN.search(lab)
            zh = re.sub(r'[（(][A-Za-z0-9 .,&/／\-#\'’]+[)）]\s*$', '', lab).strip() or lab
            rules = [r for r in f["rules"] if not r.startswith(('例如：', '注：')) or len(r) > 12]
            out.append({"label": lab, "label_zh": zh,
                        "label_en": (m.group(1).strip() if m else ""),
                        "section": s["name"], "rules": rules})
    return out


def main():
    registry = []
    for name, side, kind, issuer, wait in REG:
        pk = PAGE.get(name, name)
        flds = fields_of(pk)
        registry.append({"name": name, "side": side, "kind": kind, "issuer": issuer,
                         "wait": wait, "wiki_page": pk if pk in docs else None,
                         "field_count": len(flds)})
    json.dump(FLOW, open(os.path.join(P, "flow_matrix.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(registry, open(os.path.join(P, "doc_registry.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    fill = []
    for r in registry:
        if r["kind"] != "self":
            continue
        pk = r["wiki_page"]
        entry = {"name": r["name"], "side": r["side"], "issuer": r["issuer"], "fields": []}
        if pk:
            p = docs[pk]
            for s in p["sections"]:
                sec_name = s["name"]
                is_rule_sec = "填写" in sec_name or "说明" in sec_name
                entry["fields"].append({
                    "section": sec_name,
                    "is_fill_section": is_rule_sec,
                    "fields": [{"label": f["label"], "rules": f["rules"]} for f in s["fields"]],
                    "notes": s["paras"],
                })
            # 概念段落留一份，便于生成提示语
            entry["concept"] = [x for s in p["sections"] if "概念" in s["name"] or "概述" in s["name"]
                                for x in s["paras"]][:3]
        fill.append(entry)
    json.dump(fill, open(os.path.join(P, "fill_docs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    self_cnt = sum(1 for r in registry if r["kind"] == "self")
    print("流程环节 %d，单据登记 %d（自制 %d / 签发 %d）" %
          (len(FLOW), len(registry), self_cnt, len(registry) - self_cnt))
    print()
    print("%-24s %-4s %-4s %s" % ("单据", "方向", "字段", "页面"))
    for r in registry:
        if r["kind"] == "self":
            print("%-24s %-4s %-4d %s" % (r["name"], r["side"], r["field_count"], r["wiki_page"]))
    zero = [r["name"] for r in registry if r["kind"] == "self" and r["field_count"] == 0]
    print("\n无字段的自制单据:", zero)


if __name__ == "__main__":
    main()
