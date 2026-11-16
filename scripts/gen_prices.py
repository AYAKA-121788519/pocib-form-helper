# -*- coding: utf-8 -*-
"""把 prices.json 洗成 PNAME + PRICE 两个常量，写进 app/index.html 的标记区间。

用法：python scripts/gen_prices.py
"""
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "model", "prices.json")
APP = os.path.join(ROOT, "app", "index.html")
BEGIN = "/* __PRICE_DATA_BEGIN__ */"
END = "/* __PRICE_DATA_END__ */"

# 截图里美国工厂表被截断的最后三行（34002 蓝莓 / 37001 钢笔 / 41003 特效润肤乳）
FIX_ADD = {
    "美国": {"factory": {"34002": ("蓝莓", 3800.00), "37001": ("钢笔", 4.29),
                        "41003": ("特效润肤乳", 3.25)}},
}
CUR_OF = {"俄罗斯": "RUB", "澳大利亚": "AUD", "中国": "RMB", "德国": "EUR", "美国": "USD"}

# OCR 形近字纠错（编号 → 正确名称）。投票只能纠各国不一致的错，全表同错要靠这张表。
NAME_FIX = {
    "01010": "十年陈酿红葡萄酒", "01015": "沙丁鱼罐头", "01019": "巧克力饼干",
    "01020": "黄油饼干", "01021": "牛奶", "02015": "男士牛仔裤",
    "03001": "落地电扇", "04001": "木制茶几", "04002": "木雕-面具",
    "04003": "木雕-娃娃", "04005": "木雕头像", "04006": "欧式木雕壁挂",
    "05006": "剃胡刀", "05011": "两用扳手", "08010": "电子琴玩具",
    "09001": "太阳眼镜", "11001": "4寸2路喇叭", "11010": "6x9寸4路喇叭",
    "12005": "7头茶具", "12007": "10寸圆盘", "14001": "香皂",
    "16008": "竹篮", "17010": "沙滩巾", "22008": "速冻红椒丁",
    "24001": "纪念版雪茄", "24004": "订制版雪茄", "25017": "镶绿松石纯银项链",
    "31001": "钻石戒指", "32002": "阳绿貔貅摆件", "32005": "玉白菜摆件",
    "32007": "巴西天然紫水晶摆件", "36002": "中国油纸伞", "37001": "钢笔",
    "38003": "菠萝", "41003": "特效润肤乳", "42001": "日本防蚊贴",
    "44001": "芭蕾水钻摆件", "50001": "食用盐", "23003": "巴西咖啡(全咖啡豆城市烘焙)",
    "25014": "黄金戒指",
}


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    for v in d.values():                    # 92011 是识别噪声，不是真实商品编号
        for k in ("market", "factory"):
            v[k].pop("92011", None)
    if "RMB" in d:                      # OCR 把人民币认成 RMB，国家键统一成中国
        d["中国"] = d.pop("RMB")
    for cn, add in FIX_ADD.items():
        for k, items in add.items():
            for code, (name, price) in items.items():
                d[cn][k][code] = {"name": name, "price": price,
                                  "cur": CUR_OF[cn], "max": "", "daily": ""}

    # 同一编号在多国出现，名称取出现次数最多的那个（OCR 有错字，投票纠偏）
    names = {}
    for cn, v in d.items():
        for k in ("market", "factory"):
            for code, it in v[k].items():
                names.setdefault(code, Counter())[it["name"]] += 1
    pname = {}
    for code, cnt in names.items():
        ranked = sorted(cnt.items(), key=lambda kv: (-kv[1], -len(kv[0])))
        pname[code] = ranked[0][0]

    price = {}
    for cn, v in d.items():
        cur = CUR_OF.get(cn) or next(iter(v["market"].values()))["cur"]
        m = {c: round(it["price"], 2) for c, it in v["market"].items()}
        f = {c: round(it["price"], 2) for c, it in v["factory"].items()}
        price[cn] = {"cur": cur, "m": m, "f": f}

    pname.update(NAME_FIX)
    for c in pname:
        if not pname[c].strip():
            pname[c] = "（未识别）"

    # 按编号排序输出，体积小、diff 稳定
    lines = [BEGIN]
    lines.append("const PNAME={" + ",".join(
        '"%s":"%s"' % (c, pname[c]) for c in sorted(pname)) + "};")
    for cn in ("俄罗斯", "澳大利亚", "中国", "德国", "美国"):
        v = price[cn]
        mk = ",".join('"%s":%g' % (c, v["m"][c]) for c in sorted(v["m"]))
        fk = ",".join('"%s":%g' % (c, v["f"][c]) for c in sorted(v["f"]))
        lines.append('PRICE["%s"]={cur:"%s",m:{%s},f:{%s}};' % (cn, v["cur"], mk, fk))
    lines.append(END)
    block = "\n".join(x for x in lines if x)

    html = open(APP, encoding="utf-8").read()
    if BEGIN in html:
        html = re.sub(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END), block, html)
    else:
        print("标记区间不存在，先在 index.html 里加：", BEGIN, END)
        return
    open(APP, "w", encoding="utf-8").write(html)
    print("PNAME", len(pname), "条；各国：",
          {k: (len(v["m"]), len(v["f"])) for k, v in price.items()})
    print("写入", APP, len(block) // 1024, "KB")


if __name__ == "__main__":
    main()
