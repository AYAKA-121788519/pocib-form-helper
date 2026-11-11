# -*- coding: utf-8 -*-
"""单据决策器：输入交易剖面 → 输出 21 个环节要交的单据与执行方。

用它来验证数据模型：跑 6 种官方组合，与《操作示例》的实际单据序列比对。
"""
import os, json, re, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
FLOW = json.load(open(os.path.join(P, "flow_matrix.json"), encoding="utf-8"))

CERT_GOODS = {"21001", "40001", "40002", "06002"}   # 需货物运输条件鉴定的商品
CERTS = ["商检证书-品质证书", "商检证书-健康证书", "商检证书-数量/重量证书", "商检证书-植物检疫证书"]


def norm(d, term, transport, goods_code):
    """把矩阵里"二选一"的写法归一化成具体单据名；不适用则返回 []。"""
    import re as _re
    sea, air = transport == "海运", transport == "空运"
    ins = term in ("CIF", "CIP")

    # 组合写法的单据：按运输方式展开
    if d.startswith("国际海运委托书"):
        return ["国际海运委托书"] if sea else ["国际空运委托书"]
    if d.startswith("提货单（空运"):
        return ["提货单"] if sea else ["提货通知单", "航空运单"]
    if d.startswith("海运提单"):
        if "空运方式下无需" in d:          # 取提货单环节
            return ["海运提单"] if sea else []
        return ["海运提单"] if sea else ["航空运单"]   # 交单环节
    if d.startswith("航空运单"):
        return ["航空运单"] if air else []
    # 条件性单据
    if d.startswith("商业发票（CIF"):
        return ["商业发票"] if ins else []
    if d.startswith("货物运输保险单"):
        return ["货物运输保险单"] if ins else []   # 交单时仅 CIF/CIP 需提交保单
    if d.startswith("货物运输条件鉴定书"):
        return ["货物运输条件鉴定书"] if goods_code in CERT_GOODS else []
    if d.startswith("商检证书"):
        return []                                    # 由合同 Document 条款决定
    # 去掉括注，保留主名
    m = _re.match(r'^([^（(]+)', d)
    return [m.group(1).strip() if m else d]


def decide(term="FOB", payment="L/C", transport="海运", goods_code="08002",
           docs_clause=None, dest_country="德国"):
    """返回 [{'step','name','side','actor','docs'}]"""
    docs_clause = docs_clause or []
    out = []
    for f in FLOW:
        keep = []
        for d in f["by"].get(payment, []):
            for x in norm(d, term, transport, goods_code):
                if x not in keep:
                    keep.append(x)
        # 索赔环节：所有术语都已投保（CIF/CIP 出口商投，其余进口商投），保单都在手上
        if f["step"] == 17 and "货物运输保险单" not in keep:
            keep.insert(0, "货物运输保险单")
        # 申请鉴定：仅需鉴定的商品才走这一步
        if f["name"].startswith("申请鉴定") and goods_code not in CERT_GOODS:
            keep = []
        # 产地证二选一：美国需一般原产地证，其他国家可用普惠制
        cert = "一般原产地证" if dest_country == "美国" else "普惠制产地证"
        keep = [cert if ("或" in x and "原产地证" in x) else x for x in keep]
        # 按合同 Document 条款补商检证书
        for c in docs_clause:
            name = c if c.startswith("商检证书") else "商检证书-" + c
            if name in CERTS and name not in keep:
                keep.append(name)
        out.append({"step": f["step"], "name": f["name"], "side": f["side"],
                    "actor": actor_of(f["name"], term), "docs": keep})
    return out


def actor_of(step, term):
    if step == "办理保险":
        return "出口商" if term in ("CIF", "CIP") else "进口商"
    side = {"申请开证": "进口商", "信用证修改申请": "进口商", "付款": "进口商",
            "承兑": "进口商", "取提货单": "进口商", "索赔": "进口商",
            "进口报检": "进口商", "进口报关": "进口商", "进口缴税": "进口商", "提货": "进口商"}
    return side.get(step, "出口商")


def show(term, payment, transport, goods_code="08002", docs_clause=None, dest_country="德国"):
    rows = decide(term, payment, transport, goods_code, docs_clause, dest_country)
    print("=" * 78)
    print("组合：%s + %s + %s    （商品 %s，商检条款 %s，进口国 %s）" %
          (payment, term, transport, goods_code, docs_clause or "无", dest_country))
    print("=" * 78)
    for r in rows:
        ds = "、".join(r["docs"]) if r["docs"] else "—"
        print("%2d %-10s %-4s %s" % (r["step"], r["name"][:10], r["actor"], ds[:88]))
    return rows


if __name__ == "__main__":
    combos = [("L/C", "FOB", "海运"), ("T/T", "CIF", "海运"),
              ("T/T", "CPT", "空运"), ("T/T", "FCA", "空运"),
              ("D/P", "CIP", "空运"), ("D/A", "CIF", "海运")]
    for pay, term, tr in combos:
        show(term, pay, tr)
        print()
