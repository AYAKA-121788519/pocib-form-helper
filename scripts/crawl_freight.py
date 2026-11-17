# -*- coding: utf-8 -*-
"""抓 POCIB 国际货运公司的「航线及运费查询」运价表 → data/freight.json

海运：/institutions/company/14/vehicleline.aspx?id=S0113&country=<国>
      /institutions/company/14/vehiclelinedetail.aspx?id1=<航线>&id2=<船公司>
空运：/institutions/company/14/AirLineForm.aspx?id=S0123&country=<国>
      /institutions/company/14/vehicleairlinedetail.aspx?id1=<航线>&id2=<航空公司>

用法：python scripts/crawl_freight.py [--base http://192.168.150.135:5015]
"""
import argparse
import html as H
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "freight.json")
BASE = "http://192.168.150.135:5015"
COUNTRIES = ["China", "Japan", "Russia", "Germany", "UK",
             "Brazil", "Australia", "America", "Cuba", "South Africa"]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url, tries=3):
    url = url.replace(" ", "%20")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                       # 本地服务偶尔抽风，重试
            if i == tries - 1:
                print("  ! %s  %s" % (url, e), file=sys.stderr)
                return ""
            time.sleep(0.6)


def cells(s):
    """把一段 HTML 的表格拆成 [[单元格纯文本...], ...]"""
    rows = []
    for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", s, re.I):
        tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I)
        out = []
        for td in tds:
            t = re.sub(r"<br\s*/?>", " ", td, flags=re.I)
            t = re.sub(r"<[^>]+>", "", t)
            t = H.unescape(t).replace("\u00a0", " ")
            out.append(re.sub(r"\s+", " ", t).strip())
        if out:
            rows.append(out)
    return rows


def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s or "")
    return float(m.group()) if m else None


def list_routes(mode, country):
    """航线列表：返回 [(航线, 起运港, 起运国, 目的港, 目的国, 航行, 明细url)]"""
    if mode == "sea":
        url = "%s/institutions/company/14/vehicleline.aspx?id=S0113&country=%s" % (
            BASE, urllib.parse.quote(country))
        det = "vehiclelinedetail.aspx"
    else:
        url = "%s/institutions/company/14/AirLineForm.aspx?id=S0123&country=%s" % (
            BASE, urllib.parse.quote(country))
        det = "vehicleairlinedetail.aspx"
    s = get(url)
    out = []
    for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", s, re.I):
        tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I)
        if len(tds) < 6:
            continue
        txt = [re.sub(r"<[^>]+>", "", x).strip() for x in tds]
        m = re.search(r'href="(%s\?[^"]+)"' % det, tds[-1])
        if not m or "-" not in txt[0]:
            continue
        route = H.unescape(txt[0])
        out.append((route, txt[1], txt[2], txt[3], txt[4], txt[5],
                    BASE + "/institutions/company/14/" + H.unescape(m.group(1))))
    return out


def parse_sea_detail(s):
    rows = cells(s)
    d = {}
    for r in rows:
        if not r:
            continue
        head = r[0]
        if head.startswith("通用干货箱"):
            d["dry"] = {"c20": num(r[1]), "c40": num(r[2]), "c40h": num(r[3]),
                        "mtq": num(r[4]), "tne": num(r[5]) if len(r) > 5 else None}
        elif head.startswith("冷藏集装箱"):
            d["rf"] = {"c20": num(r[1]), "c40": num(r[2]), "c40h": num(r[3]),
                       "mtq": num(r[4]), "tne": num(r[5]) if len(r) > 5 else None}
        elif head.startswith("平台集装箱"):
            d["flat"] = {"c20": num(r[1]), "c40": num(r[2]) if len(r) > 2 else None}
        elif head.startswith("汽车集装箱"):
            d["car"] = [num(x) for x in r[1:] if re.search(r"\d", x)]
        elif head.startswith("时间"):
            d["h"] = num(r[1]) if len(r) > 1 else None
    # 汽车集装箱那行是「单层 0.00 / 双层 0.00」挤在单元格里
    if "car" not in d:
        for r in rows:
            if r and r[0].startswith("汽车"):
                nums = [num(x) for x in r[1:] for _ in [0] if num(x) is not None]
                d["car"] = nums
    return d


def parse_air_detail(s):
    rows = cells(s)
    tiers = {}
    h = None
    for r in rows:
        if not r:
            continue
        head = r[0]
        if head.startswith("时间") and len(r) > 1:
            h = num(r[1])
        if {"Minimum", "Normal"} & set(r):
            keys = [x for x in r if x in ("Minimum", "Normal", "45kgs", "100kgs",
                                          "300kgs", "500kgs", "1000kgs")]
            # 表头与取值可能在同一行也可能下一行
            vals = [x for x in r[r.index(keys[-1]) + 1:] if x]
            if len(vals) < len(keys):
                for nr in rows[rows.index(r) + 1:]:
                    vals += [x for x in nr if x]
                    if len(vals) >= len(keys):
                        break
            for k, v in zip(keys, vals):
                tiers[k] = num(v)
    return {"tiers": tiers, "h": h}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    ap.add_argument("--sleep", type=float, default=0.05)
    a = ap.parse_args()
    global BASE
    BASE = a.base or BASE

    data = {"meta": {"source": BASE + "/institutions/company/14/",
                     "crawled": time.strftime("%Y-%m-%d %H:%M")},
            "sea": {}, "air": {}}
    seen = {"sea": set(), "air": set()}

    for mode in ("sea", "air"):
        for c in COUNTRIES:
            routes = list_routes(mode, c)
            print("%s / %-12s %d 条" % (mode, c, len(routes)))
            for (route, o, oc, dd, dc, hrs, url) in routes:
                if route in seen[mode]:
                    continue
                seen[mode].add(route)
                s = get(url)
                info = parse_sea_detail(s) if mode == "sea" else parse_air_detail(s)
                if not info or (mode == "sea" and not info.get("dry")):
                    print("  ! 空表 %s" % route, file=sys.stderr)
                    continue
                info.update({"o": o, "oc": oc, "d": dd, "dc": dc})
                if info.get("h") is None:
                    info["h"] = num(hrs)
                data[mode][route] = info
                time.sleep(a.sleep)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              indent=1, sort_keys=True)
    print("\n海运 %d 条 / 空运 %d 条 → %s" % (len(data["sea"]), len(data["air"]), OUT))


if __name__ == "__main__":
    main()
