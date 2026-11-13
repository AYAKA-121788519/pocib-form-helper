# -*- coding: utf-8 -*-
"""解析器自测：不依赖截图，用构造的 OCR 行结果验证字段映射。

运行：python self_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse as P


def mkres(lines, width=1000, height=800):
    """lines: [(text, x, y, w, h)]"""
    return {"ok": True, "width": width, "height": height,
            "lines": [{"text": t, "x": x, "y": y, "w": w, "h": h, "score": 0.95, "words": []}
                      for (t, x, y, w, h) in lines]}


GOODS_PAGE = [
    ("商品基本资料", 380, 20, 120, 22),
    ("商品编号：26006", 30, 70, 130, 18),
    ("商品名称（中文）：德国咖啡机", 30, 100, 220, 18),
    ("商品名称（英文）：GERMAN COFFEE MACHINE", 30, 130, 330, 18),
    ("商品属类：电器", 30, 160, 120, 18),
    ("H.S.编码：8516711000", 30, 190, 180, 18),
    ("型号：9751G", 30, 220, 110, 18),
    ("销售单位（中文）：件", 30, 250, 160, 18),
    ("销售单位（英文）：PC", 30, 280, 170, 18),
    ("包装单位：CARTON", 30, 310, 150, 18),
    ("单位换算：1 CARTON = 10 PC", 30, 340, 220, 18),
    ("毛重（KG/包装单位）：22", 30, 370, 210, 18),
    ("净重（KG/包装单位）：20", 30, 400, 210, 18),
    ("体积（CBM/包装单位）：0.23239", 30, 430, 230, 18),
    ("运输方式：海运", 30, 460, 130, 18),
    ("规格型号（中文）：额定功率：1000-1200瓦，额定电压：220-240伏", 30, 490, 430, 18),
    ("规格型号（英文）：RATED POWER:1000-1200W,NOMINAL VOLTAGE:220-240V", 30, 520, 430, 18),
]

GOODS_EXPECT = {
    "code": "26006",
    "name_zh": "德国咖啡机",
    "name_en": "GERMAN COFFEE MACHINE",
    "cat": "电器",
    "hs": "8516711000",
    "model": "9751G",
    "unit_zh": "件",
    "unit": "PC",
    "pack": "CARTON",
    "gw": "22",
    "nw": "20",
    "vol": "0.23239",
    "transport": "海运",
}

COMPANY_PAGE = [
    ("基本资料", 430, 20, 90, 20),
    ("账号：202405110116", 328, 98, 137, 17),
    ("国家：Germany", 508, 97, 95, 19),
    ("开户行（中）：德国德意志银行", 29, 143, 162, 24),
    ("本币账号：6101000014043", 375, 149, 157, 17),
    ("报检登记号：32000001404", 750, 149, 153, 17),
    ("开户行（英）：Deutsche Bank", 29, 173, 164, 24),
    ("税务登记号：32010300001404", 367, 175, 178, 19),
    ("统一社会信用代码：913320010000014040", 585, 176, 243, 18),
    ("公司全称（中）：马哈鱼科技有限公司", 22, 228, 197, 20),
    ("公司简称（中）：马哈鱼科技", 622, 230, 150, 20),
    ("公司全称（英）：Shanghai Mihayou Network Technology Co.,Ltd", 21, 260, 350, 20),
    ("公司简称（英）：MIHOYO CO.,LTD", 622, 261, 188, 20),
    ("法人代表（中）：鹤与白鹭", 21, 287, 139, 20),
    ("法人代表（英）：Kamisato Ayaka", 622, 289, 174, 20),
    ("公司地址（中）：上海市徐汇区钦州路100号一号楼", 24, 320, 264, 20),
    ("公司地址（英）：Building 1, No. 100 Qinzhou Road, Xuhui District, Shanghai", 22, 345, 409, 20),
    ("电话：121788519", 67, 372, 110, 18),
    ("传真：111168271", 348, 375, 104, 18),
    ("邮政编码：200233", 645, 373, 111, 18),
]

COMPANY_EXPECT = {
    "account": "202405110116", "country": "Germany",
    "bank_zh": "德国德意志银行", "bank_en": "Deutsche Bank",
    "account_no": "6101000014043", "reg_inspection": "32000001404",
    "reg_tax": "32010300001404", "credit_code": "913320010000014040",
    "name_zh": "马哈鱼科技有限公司", "short_zh": "马哈鱼科技",
    "name_en": "Shanghai Mihayou Network Technology Co.,Ltd",
    "legal_zh": "鹤与白鹭", "legal_en": "Kamisato Ayaka",
    "address_zh": "上海市徐汇区钦州路100号一号楼",
    "tel": "121788519", "fax": "111168271", "postcode": "200233",
}


def check(name, page, expect, kind):
    out = P.extract(mkres(page), kind)
    got = {f["key"]: f["value"] for f in out["fields"]}
    bad = []
    for k, v in expect.items():
        g = (got.get(k) or "").replace(" ", "")
        if g != v.replace(" ", ""):
            bad.append("%s: 期望 %r 实得 %r" % (k, v, got.get(k)))
    print("[%s] 解析 %d 项，期望 %d 项" % (name, len(got), len(expect)))
    if bad:
        print("   ✗ 不一致：")
        for b in bad:
            print("     " + b)
    else:
        print("   ✓ 全部命中")
    miss = [k for k in expect if k not in got]
    if miss:
        print("   缺字段：" + ", ".join(miss))
    return not bad


if __name__ == "__main__":
    ok1 = check("商品档案", GOODS_PAGE, GOODS_EXPECT, "goods")
    print()
    ok2 = check("公司档案", COMPANY_PAGE, COMPANY_EXPECT, "company")
    print()
    print("结果：" + ("全部通过" if (ok1 and ok2) else "有偏差，需要调解析规则"))
