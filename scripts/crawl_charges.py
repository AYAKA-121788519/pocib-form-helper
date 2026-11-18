# -*- coding: utf-8 -*-
"""抓 POCIB 各国机构价目 → data/charges.json

邮局「收费标准」寄单费：
    /institutions/company/18/S0180..S0189/4_fuwu/fuwu2.aspx
化学材料测试中心「运输条件鉴定」：
    /institutions/company/21/S00604..S00694/4_fuwu/fuwu1.aspx

两处都是按国家一套，编号与 COUNTRIES 顺序一致（中国→南非）：
    邮局 S0180–S0189（步长 1）、化工 S00604–S00694（步长 10）。
银行「基本费用查询」(08/S0080/6_feiyong/feiyong1.html) 与
海关「费用查询」是全系统同一张价目表，页面里是 <%=money%> 模板占位符，
抓不到渲染值，基准价写在 app/_letters_src.html 的 BANK_EUR / CERT_EUR 里。

用法：
    python scripts/crawl_charges.py            # 抓取并写 data/charges.json
    python scripts/crawl_charges.py --check    # 只校验 json 与页面、代码是否一致
"""
import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "charges.json")
SRC = os.path.join(ROOT, "app", "_letters_src.html")
BASE = "http://192.168.150.135:5015"
COUNTRIES = ["中国", "日本", "俄罗斯", "德国", "英国",
             "巴西", "澳大利亚", "美国", "古巴", "南非"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def postage(idx):
    """邮局：返回 (币种, 金额)"""
    sid = "S%04d" % (180 + idx)
    h = get("%s/institutions/company/18/%s/4_fuwu/fuwu2.aspx" % (BASE, sid))
    m = re.search(r"寄单费用为\s*([A-Z]{3})\s*([\d.]+)", h)
    return (m.group(1), float(m.group(2))) if m else None


def chem(idx):
    """化工：返回 (币种, 金额)"""
    sid = "S%05d" % (604 + idx * 10)
    h = get("%s/institutions/company/21/%s/4_fuwu/fuwu1.aspx" % (BASE, sid))
    m = re.search(r"运输条件鉴定收取的费用为\s*([A-Z]{3})\s*([\d.]+)", h)
    return (m.group(1), float(m.group(2))) if m else None


def crawl():
    data = {"postage": {}, "chem": {}}
    for i, c in enumerate(COUNTRIES):
        for key, fn in (("postage", postage), ("chem", chem)):
            try:
                r = fn(i)
            except Exception as e:                      # 本地服务偶尔抽风
                print("  ! %s %s %s" % (c, key, e), file=sys.stderr)
                r = None
            if not r:
                print("  ! %s %s 抓不到" % (c, key), file=sys.stderr)
                continue
            data[key][c] = {"cur": r[0], "amt": int(r[1]) if r[1] == int(r[1]) else r[1]}
    return data


def consts(text, name):
    """从函电源码里抠出 const NAME = { ... } 的键值（值可能是 {cur:"X",amt:N} 或数字）"""
    i = text.find("const %s = {" % name)
    if i < 0:
        return {}
    j = text.find("\n};", i)
    block = text[i:j]
    out = {}
    for m in re.finditer(r'"([^"]+)":\s*\{cur:"(\w+)",amt:(\d+(?:\.\d+)?)\}', block):
        out[m.group(1)] = {"cur": m.group(2), "amt": float(m.group(3))}
    for m in re.finditer(r'"([^"]+)":\s*(\d+(?:\.\d+)?)', block):
        if m.group(1) not in out:
            out[m.group(1)] = float(m.group(2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if a.check:
        if not os.path.exists(OUT):
            print("缺 data/charges.json，先跑一次不带 --check 的")
            return 1
        data = json.load(open(OUT, encoding="utf-8"))
        text = open(SRC, encoding="utf-8").read()
        bad = 0
        for name, key in (("POSTAGE", "postage"), ("CHEM", "chem")):
            code = consts(text, name)
            for c in COUNTRIES:
                want = data[key].get(c)
                got = code.get(c)
                if not want or not got:
                    print("缺 %s %s" % (name, c)); bad += 1; continue
                if key == "postage":
                    same = got["cur"] == want["cur"] and abs(got["amt"] - want["amt"]) < 1e-9
                else:
                    same = abs(float(got) - float(want["amt"])) < 1e-9
                if not same:
                    print("不一致 %s %s：代码 %s / 页面 %s" % (name, c, got, want)); bad += 1
        print("价目一致" if not bad else "%d 处不一致" % bad)
        return 0 if not bad else 1

    data = crawl()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("邮局 %d 国、化工 %d 国 → %s" % (len(data["postage"]), len(data["chem"]), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
