# -*- coding: utf-8 -*-
"""把单据字段分类映射到「源头输入 / 派生计算 / 主体档案 / 平台常量 / 预印栏目 / 人工填写」。

kind 含义：
  subject   主体档案整块带入（出口商/进口商公司资料）
  source    直接取交易条件里的某个值
  derived   由源头字段计算或拼接
  const     POCIB 平台的固定值（如监管方式=一般贸易）
  preprinted 单据预印文字，用户不需要填
  manual    需要人判断的少量字段
"""
import os, json, re, csv
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "parsed")
M = os.path.join(ROOT, "data", "model")
S = os.path.join(ROOT, "spec")
os.makedirs(M, exist_ok=True)

SCHEMA = {
    "seller": {"_label": "出口商（卖方/受益人/发货人/出票人）", "fields": {
        "name_en": ("text", "英文公司名称"), "name_zh": ("text", "中文公司名称"),
        "address_en": ("text", "英文地址"), "tel": ("text", "电话"), "fax": ("text", "传真"),
        "email": ("text", "电子邮箱"), "country": ("text", "国家（英文）"),
        "city": ("text", "城市（英文）"), "postcode": ("text", "邮编"),
        "bank": ("text", "开户银行（英文）"), "account": ("text", "银行账号"),
        "reg_no": ("text", "登记号/注册号")}},
    "buyer": {"_label": "进口商（买方/开证申请人/收货人/受票人）", "fields": {
        "name_en": ("text", "英文公司名称"), "name_zh": ("text", "中文公司名称"),
        "address_en": ("text", "英文地址"), "tel": ("text", "电话"), "fax": ("text", "传真"),
        "email": ("text", "电子邮箱"), "country": ("text", "国家（英文）"),
        "city": ("text", "城市（英文）"), "postcode": ("text", "邮编"),
        "bank": ("text", "开户银行（英文）"), "account": ("text", "银行账号"),
        "reg_no": ("text", "登记号/注册号")}},
    "goods": {"_label": "商品（来自 My City → 国内工厂 商品资料）", "fields": {
        "code": ("text", "POCIB 商品编码，如 08002"), "name_zh": ("text", "中文品名"),
        "name_en": ("text", "英文品名"), "desc_en": ("text", "英文规格描述"),
        "hs_code": ("text", "H.S. 编码"), "unit": ("text", "销售计量单位"),
        "pack_qty": ("number", "每包装单位含销售数量"), "pack_unit": ("text", "包装单位"),
        "gw_per_pack": ("number", "每包装单位毛重 KG"), "nw_per_pack": ("number", "每包装单位净重 KG"),
        "vol_per_pack": ("number", "每包装单位体积 CBM"), "cost": ("number", "工厂采购单价（人民币）"),
        "origin": ("text", "原产国/产地")}},
    "deal": {"_label": "交易条件", "fields": {
        "contract_no": ("text", "合同号 S/C No."), "contract_date": ("date", "合同日期"),
        "term": ("enum", "贸易术语"), "payment": ("enum", "结算方式"),
        "transport": ("enum", "运输方式 海运/空运"),
        "port_load": ("text", "装运港（港口名+国家）"), "port_dest": ("text", "目的港（港口名+国家）"),
        "currency": ("text", "计价货币"), "qty": ("number", "成交数量"),
        "unit_price": ("number", "单价"), "amount": ("money", "总金额"),
        "say_total": ("text", "总金额大写"), "shipping_mark": ("text", "唛头"),
        "documents_clause": ("list", "合同 Document 条款要求的商检证书"),
        "insurance_cover": ("text", "投保险别"), "insurance_rate": ("number", "保险加成率"),
        "lc_no": ("text", "信用证号"), "lc_date": ("date", "开证日期"),
        "invoice_no": ("text", "发票号"), "invoice_date": ("date", "发票日期"),
        "trade_country": ("text", "贸易国（地区）"), "vessel": ("text", "船名/航班号"),
        "voyage": ("text", "航次号"), "b/l_no": ("text", "提单号"),
        "freight_forwarder": ("text", "货代公司中文名称（境内付运费收款人）"),
        "pack_total": ("number", "外包装总件数"), "gw_total": ("number", "总毛重"),
        "nw_total": ("number", "总净重"), "vol_total": ("number", "总体积"),
    }},
}

# 预印栏目 / 无需用户填写
PREPRINTED = re.compile(
    r'^(首先|其次|再次|然后|最后|仅供|签证机构|出口方声明|签证证明|签证机构证明|声明|签字|签名|盖章|'
    r'注意事项?|说明|附注|备注$|此栏|以下|注|例如|报表上方|小数|空白栏|Manager Signature|'
    r'Issue by|Parital|Partial|Transhipment|sight payment|acceptance|negotiation|'
    r'deferred payment|Credit available|Other documents|Additional instructions|'
    r'Other terms|Documents required|against the documents)')

# POCIB 平台固定值
CONST = [
    (r'监管方式|贸易方式', "一般贸易", "POCIB 统一按一般贸易申报"),
    (r'征免性质', "一般征税", "POCIB 统一按一般征税"),
    (r'用途', "其他", "按系统默认"),
    (r'境内货源地|货源地', "{seller.city}", "取出口商所在城市"),
    (r'结汇方式|收汇方式', "{payment}", "随结算方式变化"),
    (r'成交方式', "{term}", "随贸易术语变化"),
    (r'查验|放行', "无需填写", "海关作业栏"),
    (r'关别|关区', "口岸海关", "按运输口岸对应海关"),
    (r'备案号|许可证|审批号', "无需填写", "POCIB 一般不涉及"),
    (r'征免', "照章征税", "系统默认"),
    (r'报关人员|申报单位|申报员|证号', "系统代填", "由申报系统带出"),
    (r'企业性质', "外贸企业", "公司档案固定"),
    (r'托收行|代收行|收电行|付款行', "银行", "由系统/银行填写"),
    (r'费用承担|核销项下', "申请人承担", "按默认"),
]

MAP = [
    # ——— 英文表单项（合同、开证申请书等）
    (r'^Messrs$|^Applicant$', "buyer", "subject"),
    (r'^Beneficiary$', "seller", "subject"),
    (r'^TO$|^致$|Advising Bank|开证行|通知行', "const:银行", "const"),
    (r'Product No', "goods.code", "source"),
    (r'^Quantity$|^数量$', "deal.qty", "derived"),
    (r'^Unit$|计量单位', "goods.unit", "source"),
    (r'^Amount$|^金额$', "deal.amount", "derived"),
    (r'^Packing$', "deal.pack_total", "derived"),
    (r'Port of Shipment', "deal.port_load", "source"),
    (r'Port of Destination|For transportation to', "deal.port_dest", "source"),
    (r'^Shipment$|not later than|装运期|最迟装运', "deal.contract_date", "derived"),
    (r'Shipping Mark', "deal.shipping_mark", "source"),
    (r'^Quality$|^Specification$', "goods.desc_en", "derived"),
    (r'^Insurance$|保险', "deal.insurance_cover", "source"),
    (r'^Documents$', "deal.documents_clause", "derived"),
    (r'^Payment$|^No\.$', "deal.payment", "derived"),
    (r'^Date$', "deal.contract_date", "source"),
    # ——— 汇款申请书专用
    (r'汇款人', "buyer", "subject"),
    (r'收款人开户银行|收款银行|代理行', "seller.bank", "subject"),
    (r'收款人账号', "seller.account", "subject"),
    (r'收款人', "seller", "subject"),
    (r'汇款币种|现汇金额|购汇金额|其他金额|汇款金额', "deal.amount", "derived"),
    (r'组织机构代码', "buyer.reg_no", "subject"),
    (r'常驻国家', "seller.country", "subject"),
    (r'交易编码|外汇局批件|核注|发电等级|汇款方式', "const:银行", "const"),
    (r'附言', "deal.contract_no", "derived"),
    (r'申请人姓名|电话', "buyer.tel", "subject"),
    # ——— 国家/地区（先于"收货人"匹配，避免误判）
    (r'输往国家|输往国别|目的地国|进口国别|运抵国|贸易国|消费国|国别', "buyer.country", "source"),
    # ——— 港口/地点
    (r'装运港|启运港|起运港|启运地|离境口岸|出口港|始发站', "deal.port_load", "source"),
    (r'目的港|卸货港|到达口岸|抵运港|到达站', "deal.port_dest", "source"),
    # ——— 主体：卖方
    (r'出票人|出单方|受益人|发货人|卖方|出口商|出口方|申请单位|生产单位|生产厂家|委托人|开户人|'
     r'境内发货人|境内收发货人', "seller", "subject"),
    # ——— 主体：买方
    (r'受票人|受单方|开证申请人|买方|进口商|进口方|收货人|抬头人|通知人|境外收货人', "buyer", "subject"),
    # ——— 合同/信用证
    (r'合同号|合同协议号|合同号码|S/C', "deal.contract_no", "source"),
    (r'合同日期|签约日期', "deal.contract_date", "source"),
    (r'信用证号|L/C No|L/C号码', "deal.lc_no", "source"),
    (r'开证日期|信用证日期|开证时间', "deal.lc_date", "source"),
    (r'发票号|Invoice No', "deal.invoice_no", "derived"),
    (r'发票日期', "deal.invoice_date", "derived"),
    (r'编号|号码|证书编号|单据编号', "deal.contract_no", "derived"),
    # ——— 金额/数量
    (r'SAY TOTAL|大写', "deal.say_total", "derived"),
    (r'单价|Unit Price', "deal.unit_price", "derived"),
    (r'总金额|货物总值|金额小计|合计金额|总值|^Total$|发票金额', "deal.amount", "derived"),
    (r'数/重量|数量及单位|数量|量值|件数', "deal.qty", "derived"),
    (r'币制|币别|货币|Currency', "deal.currency", "source"),
    # ——— 运输
    (r'运输方式|运输工具|船名|航次|航班|提单号|运单号', "deal.vessel", "source"),
    (r'运输说明|运输路线|运输方式和路线|装运情况', "deal.vessel", "derived"),
    (r'贸易术语|价格术语', "deal.term", "derived"),
    (r'支付条款|付款条件|付款方式|付款期限', "deal.payment", "derived"),
    (r'唛头|标记及号码|标记唛码|Marks', "deal.shipping_mark", "source"),
    (r'运费|保费|杂费|保险金额', "deal.amount", "derived"),
    (r'件数|包装种类|包装数量|外包装|总件数', "deal.pack_total", "derived"),
    (r'毛重|G\.?W', "deal.gw_total", "derived"),
    (r'净重|N\.?W', "deal.nw_total", "derived"),
    (r'体积|尺码|Meas', "deal.vol_total", "derived"),
    (r'集装箱', "deal.pack_total", "derived"),
    # ——— 商品
    (r'H\.?S|税则|商品编号|商品编码|海关协调制度', "goods.hs_code", "source"),
    (r'货物名称|品名|商品名称|货物描述|description', "goods.name_en", "derived"),
    (r'规格|型号', "goods.desc_en", "derived"),
    (r'原产国|原产地|产地', "goods.origin", "source"),
    # ——— 保险
    (r'险别|承保险别|投保险别', "deal.insurance_cover", "source"),
    (r'加成', "deal.insurance_rate", "source"),
    (r'赔付地点|赔款地点', "deal.port_dest", "derived"),
    # ——— 检验检疫
    (r'随附单据|随附单证|需要证单名称|所需单证', "deal.documents_clause", "derived"),
    (r'检验检疫条款|特殊要求', "deal.documents_clause", "manual"),
    # ——— 报关单专属
    (r'消费使用单位', "buyer", "subject"),
    (r'生产销售单位', "seller", "subject"),
    (r'启运国|启运国家', "seller.country", "source"),
    (r'最终目的国', "buyer.country", "source"),
    (r'指运港|入境口岸|经停港|经停口岸|^目的地$', "deal.port_dest", "source"),
    (r'总价', "deal.amount", "derived"),
    (r'项号|序号', "deal.qty", "derived"),
    (r'包装件号', "deal.pack_total", "derived"),
    (r'单据种类|份数|单据名称', "deal.documents_clause", "derived"),
    (r'付款指示|托收方式', "deal.payment", "derived"),
    # ——— 日期兜底
    (r'日期|时间', "deal.contract_date", "source"),
    (r'有效期|截止', "deal.contract_date", "source"),
    # ——— 信用证细节
    (r'信用证金额|开证金额', "deal.amount", "derived"),
    (r'汇票|付款人|受款人', "deal.payment", "derived"),
]


DOC_RULE = {
    "投保单": {"actor": "term in ('CIF','CIP') ? 'seller' : 'buyer'",
              "cond": "所有术语都需要投保，只是执行方不同",
              "note": "CIF/CIP 由出口商投保；FOB/FCA/CFR/CPT 由进口商投保，且须在出口商订舱完成后、货物出运前尽早办理"},
    "商业发票": {"actor": "seller"}, "装箱单": {"actor": "seller"},
    "合同（外销合同）": {"actor": "seller", "note": "合同只能由出口商起草"},
    "出口货物报关单": {"actor": "seller"}, "进口货物报关单": {"actor": "buyer"},
    "国际海运委托书": {"actor": "seller", "cond": "transport=='海运'"},
    "国际空运委托书": {"actor": "seller", "cond": "transport=='空运'"},
    "托收委托书": {"actor": "seller", "cond": "payment in ('D/P','D/A')"},
    "汇票": {"actor": "seller", "cond": "payment in ('L/C','D/P','D/A')"},
    "出口押汇申请书": {"actor": "seller", "cond": "选择押汇（与仅交单二选一）"},
    "不可撤销信用证开证申请书": {"actor": "buyer", "cond": "payment=='L/C'"},
    "信用证修改申请书": {"actor": "buyer", "cond": "payment=='L/C' 且需修改"},
    "境外汇款申请书": {"actor": "buyer", "cond": "payment=='T/T'"},
    "境内汇款申请书": {"actor": "seller 付运费 / buyer 国内付款", "cond": ""},
    "出境货物检验检疫申请": {"actor": "seller"}, "入境货物检验检疫申请": {"actor": "buyer"},
    "一般原产地证": {"actor": "seller", "cond": "进口国要求一般原产地证（如美国）"},
    "普惠制产地证": {"actor": "seller", "cond": "进口国可享普惠制"},
    "申请鉴定表": {"actor": "seller", "cond": "商品需做货物运输条件鉴定（21001/40001/40002/06002）"},
    "索赔申请书": {"actor": "buyer", "cond": "货物出险"},
}


DOC_OVERRIDE = [
    # (单据, 正则, 目标)
    ("境内汇款申请书", r'收款人|收款单位', "deal.freight_forwarder"),
    ("境内汇款申请书", r'汇款人|付款人', "seller"),
    ("出口押汇申请书", r'押汇金额|融资金额', "deal.amount"),
]


def classify(zh, en, doc=""):
    for d, pat, tgt in DOC_OVERRIDE:
        if d == doc and re.search(pat, zh):
            return tgt, "source", None
    if PREPRINTED.match(zh):
        return None, "preprinted", None
    for pat, const, note in CONST:
        if re.search(pat, zh):
            return const, "const", note
    for pat, tgt, kind in MAP:
        if re.search(pat, zh, re.I) or (en and re.search(pat, en, re.I)):
            return tgt, kind, None
    return None, "manual", None


def main():
    rows = list(csv.DictReader(open(os.path.join(S, "字段总览.csv"), encoding="utf-8-sig")))
    out, stat = [], Counter()
    manual = defaultdict(list)
    for r in rows:
        zh, en, doc = r["中文字段名"], r["英文名"], r["单证"]
        tgt, kind, note = classify(zh, en, doc)
        rec = {"doc": doc, "side": r["方向"], "section": r["章节"], "field": r["字段原文"],
               "field_zh": zh, "field_en": en, "target": tgt, "kind": kind}
        if note:
            rec["const_note"] = note
        if doc in DOC_RULE:
            rec["doc_rule"] = DOC_RULE[doc]
        out.append(rec)
        stat[kind] += 1
        if kind == "manual":
            manual[doc].append(zh)

    json.dump({"schema": {"deal_profile": SCHEMA}, "doc_rules": DOC_RULE},
              open(os.path.join(M, "deal_profile.schema.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(M, "field_map.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    total = len(out)
    auto = total - stat["manual"] - stat["preprinted"]
    names = {"subject": "主体档案整块带入", "source": "取交易条件原值",
             "derived": "由源头计算/拼接", "const": "平台固定值",
             "preprinted": "单据预印，无需填", "manual": "需人工判断"}
    L = ["# 字段映射覆盖率", "",
         "| 类型 | 数量 | 占比 | 含义 |", "|---|---|---|---|"]
    for k in ("subject", "source", "derived", "const", "preprinted", "manual"):
        L.append("| %s | %d | %.1f%% | %s |" % (k, stat[k], 100 * stat[k] / total, names[k]))
    L += ["| **合计** | **%d** | | |" % total, "",
          "**程序可自动处理：%d / %d = %.0f%%**（不含 preprinted 与 manual）" %
          (auto, total, 100 * auto / total), "",
          "## 仍需人工判断的字段（按单证）", ""]
    for doc, items in sorted(manual.items(), key=lambda x: -len(x[1])):
        L += ["### %s（%d）" % (doc, len(items)), "", "、".join(items), ""]
    open(os.path.join(S, "字段映射覆盖率.md"), "w", encoding="utf-8").write("\n".join(L))
    print("total", total, dict(stat), "auto %.0f%%" % (100 * auto / total))


if __name__ == "__main__":
    main()
