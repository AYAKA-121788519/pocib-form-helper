# -*- coding: utf-8 -*-
"""把 OCR 的行结果还原成「字段 → 取值」。

思路：同一行的词先按纵向聚成行，再按横向空白切成单元格，单元格里遇到冒号就切成
「标签 / 取值」。标签再用模糊匹配对到 POCIB 的字段名上——OCR 会把「（中）」读成
「)」「】」，也会在汉字之间塞空格，所以匹配前统一去掉标点和空格。
"""
import difflib
import os
import re

_DBG = bool(os.environ.get("POCIB_OCR_DEBUG"))

CJK = r"\u4e00-\u9fff"

# ---------------------------------------------------------------- 文本清洗
def squeeze(s):
    """去掉汉字之间被 OCR 塞进来的空格，保留英文单词间空格。"""
    s = s or ""
    s = re.sub(r"(?<=[%s])\s+(?=[%s])" % (CJK, CJK), "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def norm_label(s):
    """标签归一：只留汉字、字母、数字。"""
    s = squeeze(s)
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("：", ":").replace("∶", ":").replace("ˉ", ":")
    s = re.sub(r"[^0-9A-Za-z%s]" % CJK, "", s)
    return s.lower()


def norm_value(s):
    s = squeeze(s)
    s = s.replace("：", ":").replace("，", ",").replace("。", ".")
    return s.strip(" :：·")


def de_space_num(s):
    """账号/电话这类纯数字：去掉 OCR 插入的空格与常见误识字母。"""
    if not s:
        return s
    t = re.sub(r"\s+", "", s)
    if re.fullmatch(r"[0-9A-Za-z\-+()/.]+", t) and sum(c.isdigit() for c in t) >= max(3, len(t) * 0.6):
        return t
    return s


# ---------------------------------------------------------------- 版面还原
def tokens_of(res, min_conf=0.0):
    """把 OCR 结果摊平成词级 token（没有词就退回行级）。"""
    out = []
    for ln in res.get("lines") or []:
        words = ln.get("words") or []
        if words:
            for w in words:
                t = w.get("text") or ""
                if t.strip():
                    out.append({"text": t, "x": w["x"], "y": w["y"],
                                "w": w["w"], "h": w["h"], "score": w.get("score", 1.0)})
        else:
            t = ln.get("text") or ""
            if t.strip():
                out.append({"text": t, "x": ln["x"], "y": ln["y"],
                            "w": ln["w"], "h": ln["h"], "score": ln.get("score", 1.0)})
    return [t for t in out if t["score"] >= min_conf]


def find_gutters(tokens, width, min_gap=26, min_frac=0.45):
    """找出贯穿页面的竖直空白带（用来分栏）。"""
    if not tokens:
        return []
    cover = bytearray(width + 2)
    for t in tokens:
        x0 = max(0, int(t["x"]))
        x1 = min(width, int(t["x"] + t["w"]))
        for x in range(x0, x1):
            cover[x] = 1
    gaps = []
    run = None
    for x in range(width):
        if not cover[x]:
            run = run if run is not None else x
        else:
            if run is not None and x - run >= min_gap:
                gaps.append((run, x))
            run = None
    if run is not None and width - run >= min_gap:
        gaps.append((run, width))
    # 只保留“够空”的带：同一 y 上不横跨太多内容
    keep = []
    for a, b in gaps:
        crossing = sum(1 for t in tokens if t["x"] < a and t["x"] + t["w"] > b)
        if crossing <= len(tokens) * min_frac:
            keep.append((a, b))
    # 丢掉过于靠边的空白（左右留白）
    return [(a, b) for a, b in keep if a > width * 0.12 and b < width * 0.95]


def split_columns(tokens, width):
    gutters = find_gutters(tokens, width)
    if not gutters:
        return [(0, width, tokens)]
    bounds = [0] + [(a + b) // 2 for a, b in gutters] + [width]
    cols = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        part = [t for t in tokens if a <= t["x"] + t["w"] / 2 < b]
        if part:
            cols.append((a, b, part))
    return cols


def group_rows(tokens, tol_ratio=0.62):
    if not tokens:
        return []
    ts = sorted(tokens, key=lambda t: (t["y"] + t["h"] / 2))
    rows = []
    for t in ts:
        cy = t["y"] + t["h"] / 2
        placed = False
        for r in rows:
            if abs(r["cy"] - cy) <= max(t["h"], r["h"]) * tol_ratio:
                r["items"].append(t)
                r["cy"] = sum(i["y"] + i["h"] / 2 for i in r["items"]) / len(r["items"])
                r["h"] = max(r["h"], t["h"])
                placed = True
                break
        if not placed:
            rows.append({"cy": cy, "h": t["h"], "items": [t]})
    for r in rows:
        r["items"].sort(key=lambda t: t["x"])
    rows.sort(key=lambda r: r["cy"])
    return rows


COLONS = (":", "：", "∶", "﹕", "⑩")


def _first_colon(text):
    best = -1
    ch = None
    for c in COLONS:
        i = text.find(c)
        if i >= 0 and (best < 0 or i < best):
            best, ch = i, c
    return best, ch


def split_multi(cell, gap_reset=26):
    """一个单元格里可能塞了「标签:值 标签:值」——按冒号和横向间距拆成多组。
    返回 [(标签, 取值, 取值起始x)]"""
    out = []
    label, value, vx = "", "", None
    started = False
    grp = []

    def flush():
        nonlocal label, value, vx, started, grp
        if started:
            out.append((label.strip(), value.strip(), vx, list(grp)))
        elif grp:
            out.append(("", "".join(t["text"] for t in grp).strip(), None, list(grp)))
        label, value, vx, started, grp = "", "", None, False, []

    prev_x1 = None
    for t in cell:
        txt = t["text"]
        gap = (t["x"] - prev_x1) if prev_x1 is not None else 0
        idx, _c = _first_colon(txt)
        looks_label = bool(txt.strip()) and txt.strip()[-1] in COLONS and len(txt.strip()) <= 14
        if idx >= 0:
            if not started:
                label += txt[:idx]
                value += txt[idx + 1:]
                vx = t["x"] + t["w"] * (idx / max(1, len(txt)))
                started = True
                grp.append(t)
            elif (value and gap > gap_reset) or (looks_label and value):
                # 新的一组「标签:」
                flush()
                label = txt[:idx]
                value = txt[idx + 1:]
                vx = t["x"] + t["w"] * (idx / max(1, len(txt)))
                started = True
                grp.append(t)
            else:
                value += txt
                grp.append(t)
        else:
            if started:
                value += (" " if value and not value.endswith(" ") and txt[:1].isascii() else "") + txt
                grp.append(t)
            else:
                label += txt
                grp.append(t)
        prev_x1 = t["x"] + t["w"]
    flush()
    return out


# ---------------------------------------------------------------- 字段字典
COMPANY = [
    ("account", ["账号", "客户号", "注册号", "登陆账号", "登录账号", "用户名"]),
    ("country", ["国家"]),
    ("country_zh", ["国家中文", "国家(中文)", "国别"]),
    ("bank_zh", ["开户行中", "开户银行中", "银行名称中", "开户行中文", "开户行"]),
    ("bank_en", ["开户行英", "开户银行英", "银行名称英", "开户行英文"]),
    ("account_no", ["本币账号", "银行账号", "账号本币"]),
    ("currency", ["币别", "币种", "结算币种"]),
    ("reg_inspection", ["海关登记号", "报关登记号", "海关备案号", "报关注册登记号"]),
    ("reg_tax", ["税务登记号", "税号", "纳税登记号"]),
    ("credit_code", ["统一社会信用代码", "信用代码", "社会信用代码"]),
    ("name_zh", ["公司全称中", "公司名称中", "企业名称中", "公司全称", "公司名称"]),
    ("name_en", ["公司全称英", "公司名称英", "企业名称英"]),
    ("short_zh", ["公司简称中", "简称中", "公司简称"]),
    ("short_en", ["公司简称英", "简称英"]),
    ("legal_zh", ["法人代表中", "法人中", "法定代表人中", "法人代表", "法定代表人"]),
    ("legal_en", ["法人代表英", "法人英", "法定代表人英"]),
    ("address_zh", ["公司地址中", "地址中", "注册地址中", "公司地址"]),
    ("address_en", ["公司地址英", "地址英", "注册地址英"]),
    ("tel", ["电话", "联系电话", "公司电话"]),
    ("fax", ["传真", "传真号"]),
    ("postcode", ["邮政编码", "邮编"]),
    ("intro_zh", ["公司介绍中", "公司简介中", "公司介绍", "公司简介"]),
    ("intro_en", ["公司介绍英", "公司简介英"]),
]

GOODS = [
    ("code", ["商品编号", "商品代码", "货号"]),
    ("name_zh", ["商品名称中", "品名中", "商品中文名称", "商品名称"]),
    ("name_en", ["商品名称英", "品名英", "商品英文名称"]),
    ("cat", ["商品属类", "商品类别", "所属类别"]),
    ("hs", ["hs编码", "海关编码", "hs", "商品编码"]),
    ("model", ["型号", "规格型号", "model"]),
    ("unit", ["销售单位英", "销售单位", "计量单位英", "单位英"]),
    ("unit_zh", ["销售单位中", "计量单位中", "单位中", "单位"]),
    ("pack", ["包装单位", "包装种类", "包装", "pack"]),
    ("conv", ["单位换算", "换算", "包装换算"]),
    ("gw", ["毛重", "grossweight", "gross"]),
    ("nw", ["净重", "netweight", "net"]),
    ("vol", ["体积", "volume"]),
    ("transport", ["运输方式", "运输"]),
    ("spec_zh", ["规格中", "规格型号中", "规格"]),
    ("spec_en", ["规格英", "规格型号英"]),
]

MULTILINE = {"address_zh", "address_en", "intro_zh", "intro_en", "spec_zh", "spec_en", "name_zh", "name_en"}

LATIN_KEYS = {"country", "bank_en", "name_en", "short_en", "legal_en", "address_en",
              "intro_en", "unit", "pack", "transport"}
DIGIT_KEYS = {"account", "account_no", "reg_inspection", "reg_tax", "credit_code",
              "tel", "fax", "postcode", "hs", "conv", "gw", "nw", "vol", "code"}


def _latin(s):
    return re.fullmatch(r"[a-z. ]+", s) is not None


def _edge_ok(cn, n, at_start):
    """英文候选靠前后缀命中时也要卡词边界：NETWT 不能靠前缀 net 命中。"""
    if not _latin(cn):
        return True
    if at_start:
        return re.match(re.escape(cn) + r"(?![a-z])", n) is not None
    return re.search(r"(?<![a-z])" + re.escape(cn) + r"$", n) is not None


def _word_in(cn, n):
    """英文候选词要按词边界出现（NETWT 里的 net 不算），中文照旧按子串。"""
    if not _latin(cn):
        return cn in n
    return re.search(r"(?<![a-z])" + re.escape(cn) + r"(?![a-z])", n) is not None


def match_label(label, table):
    n = norm_label(label)
    if not n:
        return None, 0.0
    best, score = None, 0.0
    for key, cands in table:
        for c in cands:
            cn = norm_label(c)
            if not cn:
                continue
            if n == cn:
                s = 1.0
            elif n.startswith(cn) and _edge_ok(cn, n, True):
                # 「毛重（KG/包装单位）」这类带单位的标签，靠前缀命中
                s = 0.93 - min(0.08, 0.01 * (len(n) - len(cn)))
            elif n.endswith(cn) and _edge_ok(cn, n, False):
                s = 0.86 - min(0.08, 0.01 * (len(n) - len(cn)))
            elif cn in n:
                # 包含命中要防「水印/正文里的英文片段」误中：候选词太短、标签比候选长太多、
                # 或英文候选只作为更长单词的一部分出现（NETWT 里的 net），都不认
                if len(n) > max(len(cn) + 4, len(cn) * 2.2) or not _word_in(cn, n):
                    s = 0.0
                else:
                    s = 0.78 - min(0.08, 0.01 * (len(n) - len(cn)))
            else:
                s = difflib.SequenceMatcher(None, n, cn).ratio() * 0.85
            # 中文/英文标记必须一致，避免 name_zh 抢走 name_en
            if ("英" in n) != ("英" in norm_label(c)):
                s -= 0.35
            if s > score:
                best, score = key, s
    return (best, score) if score >= 0.62 else (None, score)


def guess_conf(key, value):
    v = value or ""
    if not v:
        return 0.0
    c = 0.62
    if key in DIGIT_KEYS:
        digits = sum(ch.isdigit() for ch in v)
        c = 0.55 + 0.42 * (digits / max(1, len(v)))
        if digits == 0:
            c = 0.2
    elif key in LATIN_KEYS:
        latin = sum(ch.isascii() and ch.isalpha() for ch in v)
        c = 0.5 + 0.4 * (latin / max(1, len(v.replace(" ", ""))))
    else:
        han = sum(1 for ch in v if "\u4e00" <= ch <= "\u9fff")
        c = 0.55 + 0.4 * (han / max(1, len(v.replace(" ", ""))))
    if len(v) <= 1:
        c -= 0.25
    return round(max(0.0, min(1.0, c)), 2)


def _cells_of_row(items, gap=40):
    cells, cur = [], []
    for t in items:
        if cur and t["x"] - (cur[-1]["x"] + cur[-1]["w"]) > gap:
            cells.append(cur)
            cur = []
        cur.append(t)
    if cur:
        cells.append(cur)
    return cells


def _box(tokens):
    x0 = min(t["x"] for t in tokens)
    y0 = min(t["y"] for t in tokens)
    x1 = max(t["x"] + t["w"] for t in tokens)
    y1 = max(t["y"] + t["h"] for t in tokens)
    return [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]


def dedupe(tokens):
    """多通道识别会有重复/被包含的行，按面积从大到小保留，丢掉被包住的碎片。"""
    ts = sorted(tokens, key=lambda t: -(t["w"] * t["h"]))
    keep = []
    for t in ts:
        tx0, ty0, tx1, ty1 = t["x"], t["y"], t["x"] + t["w"], t["y"] + t["h"]
        dup = False
        for k in keep:
            kx0, ky0, kx1, ky1 = k["x"], k["y"], k["x"] + k["w"], k["y"] + k["h"]
            ox = max(0, min(tx1, kx1) - max(tx0, kx0))
            oy = max(0, min(ty1, ky1) - max(ty0, ky0))
            inter = ox * oy
            if inter <= 0:
                continue
            small = min(t["w"] * t["h"], k["w"] * k["h"])
            if small and inter / small > 0.65:
                dup = True
                break
        if not dup:
            keep.append(t)
    keep.sort(key=lambda t: (t["y"], t["x"]))
    return keep


def extract(res, kind="auto", table=None, min_score=0.58):
    """res: ocr 结果；返回 {fields, extras, kind}"""
    width = res.get("width") or 1000
    toks = dedupe(tokens_of(res, min_conf=0.3))
    if not toks:
        return {"fields": [], "extras": [], "kind": kind}

    if table is None:
        table = COMPANY if kind == "company" else GOODS

    fields, extras = [], []
    seen = set()

    def find_target(cell, rowh):
        """续行归属：上一个可换行字段，且左边界对齐（同一栏），纵向紧跟。"""
        cx = cell[0]["x"]
        cy = cell[0]["y"]
        best = None
        for f in fields:
            if f["key"] not in MULTILINE:
                continue
            gap = cy - (f["box"][1] + f["box"][3])
            # 行高偏小的表格里，OCR 框常带上下留白，容差要放到接近一个行高
            if gap < -max(6, rowh * 0.85) or gap > rowh * 2.8:
                continue
            if abs(f["box"][0] - cx) > 120:
                continue
            s = abs(f["box"][0] - cx) + max(0, gap)
            if best is None or s < best[0]:
                best = (s, f)
        return best[1] if best else None

    for _a, _b, col_toks in split_columns(toks, width):
        last_row_h = 20
        for r in group_rows(col_toks):
            for cell in _cells_of_row(r["items"]):
                for label, value, _vx, grp in split_multi(cell):
                    if not label and not value:
                        continue
                    key, score = match_label(label, table)
                    if key and score >= min_score:
                        val = norm_value(de_space_num(value))
                        if key in seen:
                            if val:
                                for f in fields:
                                    if f["key"] == key and not f["value"]:
                                        f["value"] = val
                                        f["conf"] = guess_conf(key, val)
                                        break
                            continue
                        seen.add(key)
                        fields.append({"key": key, "label": squeeze(label), "value": val,
                                       "conf": guess_conf(key, val),
                                       "box": _box(grp or cell), "score": round(score, 2)})
                        last_row_h = r["h"]
                        continue

                    txt = norm_value(label + (" " + value if value else ""))
                    if not txt:
                        continue
                    tgt = find_target(cell, last_row_h)
                    if _DBG:
                        print("[dbg] 无标签 cell x=%d y=%d %r -> %s" %
                              (cell[0]["x"], cell[0]["y"], txt[:24],
                               tgt["key"] if tgt else "extras"), flush=True)
                    if tgt is not None:
                        tgt["value"] = norm_value(tgt["value"] + " " + txt)
                        tgt["conf"] = guess_conf(tgt["key"], tgt["value"]) if tgt["value"] else 0.5
                        tgt["box"][3] = int(r["cy"] + r["h"] / 2 - tgt["box"][1])
                        continue
                    if len(txt) >= 2:
                        # 商品页左边是商品图片，图片上的字认出来也是垃圾，直接丢
                        if kind == "goods" and cell[0]["x"] < width * 0.30:
                            continue
                        extras.append({"text": txt, "box": _box(cell)})
    _polish(fields, kind)
    return {"fields": fields, "extras": extras, "kind": kind}


# ---------- 取值规整 ----------

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _split_zh(s):
    """「TIN（听）」→ ("TIN", "听")；没有括号就返回 (原文, "")。"""
    t = squeeze(s or "")
    m = re.match(r"^([^（(]*)[（(]([^）)]*)[）)]?$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return t, ""


def _first_num(s):
    m = _NUM_RE.search(s or "")
    return m.group(0) if m else ""


def _polish(fields, kind):
    """把客户端的书写习惯转成程序内部口径（单位拆中英、换算只留数字、重量体积只留数值）。"""
    by = {f["key"]: f for f in fields}

    if "unit" in by:
        en, zh = _split_zh(by["unit"]["value"])
        by["unit"]["value"] = en.upper()
        if zh and "unit_zh" not in by:
            fields.append({"key": "unit_zh", "label": "销售单位（中）", "value": zh,
                           "conf": by["unit"]["conf"], "box": list(by["unit"]["box"])})
    if "pack" in by:
        en, _zh = _split_zh(by["pack"]["value"])
        by["pack"]["value"] = en.upper()
    if "conv" in by:
        v = by["conv"]["value"]
        m = re.search(r"[=＝]\s*(\d+)", v)
        if m:
            by["conv"]["value"] = m.group(1)
        else:
            n = _first_num(v)
            if n:
                by["conv"]["value"] = n
    for k in ("gw", "nw", "vol"):
        if k in by:
            n = _first_num(by[k]["value"])
            if n:
                by[k]["value"] = n
    if kind == "goods":
        for k in ("name_en", "spec_en"):
            if k in by:
                # 英文栏里粘上中文（相邻列溢出），切掉
                v = by[k]["value"]
                cut = re.search(r"[\u4e00-\u9fff]", v)
                if cut and cut.start() > 0:
                    by[k]["value"] = v[:cut.start()].strip()
