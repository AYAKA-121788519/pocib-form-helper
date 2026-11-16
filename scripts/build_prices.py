# -*- coding: utf-8 -*-
"""从 POCIB「购买商品 / 售出商品」截图批量提取价格表。

用法：python scripts/build_prices.py
输出：data/model/prices.json
"""
import glob
import json
import os
import re
import sys

from PIL import Image
from rapidocr_onnxruntime import RapidOCR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.path.expanduser(r"~\AppData\Local\Temp")
OUT = os.path.join(ROOT, "data", "model", "prices.json")

CUR2CN = {"RUB": "俄罗斯", "AUD": "澳大利亚", "CNY": "中国", "EUR": "德国", "USD": "美国"}
UNITS = {"CARTON", "SET", "PC", "BOX", "TIN", "DRUM", "BAG", "MT", "PAIR", "UNIT",
         "BOTTLE", "CAN", "KGS", "KG", "PCS", "DOZEN"}

ocr = RapidOCR()


def recognize(path):
    """切条识别，返回 [(cx, cy, text)]，坐标换算回原图。"""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    out = []
    step, overlap = 900, 60
    y = 0
    while y < H:
        box = (0, y, W, min(y + step, H))
        crop = im.crop(box)
        res, _ = ocr(crop_to_array(crop))
        if res:
            for b, txt, _score in res:
                xs = [p[0] for p in b]
                ys = [p[1] for p in b]
                out.append(((min(xs) + max(xs)) / 2,
                            (min(ys) + max(ys)) / 2 + y,
                            txt.strip()))
        if y + step >= H:
            break
        y += step - overlap
    return out, W, H


def crop_to_array(im):
    import numpy as np
    return np.array(im)


def group_rows(items, tol=14):
    items = sorted(items, key=lambda t: t[1])
    rows, cur = [], []
    for it in items:
        if cur and abs(it[1] - cur[-1][1]) > tol:
            rows.append(cur)
            cur = []
        cur.append(it)
    if cur:
        rows.append(cur)
    return rows


def classify(W):
    """按 x 落点分列。不同截图列宽略有差异，用比例更稳。"""
    def col(cx):
        r = cx / W
        if r < 0.11:
            return "code"
        if r < 0.40:
            return "name"
        if r < 0.52:
            return "price"
        if r < 0.66:
            return "maxqty"
        return "daily"
    return col


def parse(path):
    items, W, H = recognize(path)
    col = classify(W)
    rows = []
    for grp in group_rows(items):
        cells = {"code": "", "name": "", "price": "", "maxqty": "", "daily": ""}
        for cx, cy, txt in sorted(grp, key=lambda t: t[0]):
            k = col(cx)
            cells[k] = (cells[k] + " " + txt).strip()
        if not re.fullmatch(r"\d{5}", cells["code"]):
            continue
        m = re.match(r"([A-Z]{3})\s*([\d,]+\.\d{2})", cells["price"])
        cur = m.group(1) if m else ""
        price = float(m.group(2).replace(",", "")) if m else None
        rows.append({"code": cells["code"], "name": cells["name"],
                     "cur": cur, "price": price,
                     "max": cells["maxqty"], "daily": cells["daily"]})
    return rows, W, H, items


def kind_of(items):
    head = " ".join(t[2] for t in items[:60])
    if "售出商品" in head or "国内市场" in head:
        return "market"
    if "购买商品" in head or "国内工厂" in head:
        return "factory"
    return "?"


def main():
    files = sorted(glob.glob(os.path.join(TEMP, "QQ_2026-11-16_2*.png")))
    data = {}
    for f in files:
        name = os.path.basename(f)
        if os.path.getsize(f) < 20000:
            continue
        rows, W, H, items = parse(f)
        if not rows:
            print("skip", name, "no rows")
            continue
        kind = kind_of(items)
        curs = {}
        for r in rows:
            curs[r["cur"]] = curs.get(r["cur"], 0) + 1
        cur = max(curs, key=curs.get)
        cn = CUR2CN.get(cur, cur)
        key = cn
        data.setdefault(key, {"market": {}, "factory": {}})
        bucket = data[key][kind if kind in ("market", "factory") else "factory"]
        added = 0
        for r in rows:
            if r["price"] is None:
                continue
            if r["code"] not in bucket:
                added += 1
            bucket[r["code"]] = {"name": r["name"], "price": r["price"], "cur": r["cur"],
                                 "max": r["max"], "daily": r["daily"]}
        print("%-28s %-8s %-6s rows=%3d new=%3d H=%d" % (name, kind, cn, len(rows), added, H))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=1)
    for cn, v in data.items():
        print(cn, "市场", len(v["market"]), "工厂", len(v["factory"]))


if __name__ == "__main__":
    main()
