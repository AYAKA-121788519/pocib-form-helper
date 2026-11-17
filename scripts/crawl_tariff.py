# -*- coding: utf-8 -*-
"""抓 POCIB 海关「税率查询」全库 → data/tariff.json

页面：/institutions/company/14/SearchHSCodeForm.aspx
      （即「税率查询 - 海关 CUSTOMS」页里嵌的那个 iframe）
用法：python scripts/crawl_tariff.py [--base http://192.168.150.135:5015] [--delay 0.5]

注意：学校服务器有访问频率限制，**不要并发、不要猛刷**。脚本默认每次请求间隔
0.5s（±30% 抖动），并把每个前缀的结果缓存到 build/net/.tariff_cache.json，
中断后重跑会跳过已抓过的前缀，不会白刷一遍。

接口说明
--------
ASP.NET WebForms，必须 POST 带 __VIEWSTATE / __EVENTVALIDATION，
字段 hscode（可为前缀）/ goodsname / bSearch=true / curPageNo / totalCount。
hscode 是**左前缀匹配**：'20' 命中所有 20 开头的编码，'2005' 命中 2005xxxx。
每页 20 条，翻页靠页面里的 JS 提交，直接改 curPageNo 无效；
但前缀足够窄时 total<=20，一页就能取全，所以按「章 → 品目 → 子目」逐位细分递归。
"""
import argparse
import html as H
import json
import os
import random
import re
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "tariff.json")
BASE = "http://192.168.150.135:5015"
FORM = BASE + "/institutions/company/14/SearchHSCodeForm.aspx"
PER = 20

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

_lock = threading.Lock()
_state = {"vs": None}
CACHE = os.path.join(ROOT, "build", "net", ".tariff_cache.json")
_cache = None
_delay = 0.5
CHAPTERS = list(range(1, 98))
_t0 = time.time()
_nreq = 0


def load_cache():
    global _cache
    if _cache is None:
        try:
            with open(CACHE, encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    return _cache


def save_cache():
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(load_cache(), f, ensure_ascii=False)
    os.replace(tmp, CACHE)


def throttle():
    """每次请求之间歇一下，避免被学校服务器当成爬虫"""
    global _nreq
    _nreq += 1
    time.sleep(_delay * random.uniform(0.8, 1.3))
    if _nreq % 60 == 0:                     # 每 60 次歇久一点
        time.sleep(_delay * 3)


def _fetch(url, data=None, tries=3):
    throttle()
    for i in range(tries):
        try:
            hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                   "Referer": FORM,
                   "Accept": "text/html,application/xhtml+xml"}
            req = urllib.request.Request(url, data=data, headers=hdr)
            with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print("  ! %s" % e, file=sys.stderr)
                return ""
            time.sleep(2.0 * (i + 1))      # 出错先退避，别继续撞


def hidden(s, key):
    m = re.search(r'(?:name|id)="%s"[^>]*value="([^"]*)"' % key, s)
    return m.group(1) if m else ""


def viewstate(force=False):
    """取一份可以重复使用的表单状态（ASP.NET 的 ViewState 不是一次性的）"""
    with _lock:
        if force or _state["vs"] is None:
            s = _fetch(FORM)
            _state["vs"] = {
                "__VIEWSTATE": hidden(s, "__VIEWSTATE"),
                "__VIEWSTATEGENERATOR": hidden(s, "__VIEWSTATEGENERATOR"),
                "__EVENTVALIDATION": hidden(s, "__EVENTVALIDATION"),
            }
        return dict(_state["vs"])


def rows_of(page):
    """结果表：海关编码 | 货名 | 进口普通 | 进口优惠 | 出口税 | 增值税 |
               消费税从量 | 消费税从价 | 退税 | 单位 | 监管条件"""
    out = []
    for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", page, re.I):
        if 'bgcolor="ffffff"' not in tr:
            continue
        cells = []
        for td in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I):
            t = re.sub(r"<br\s*/?>", " ", td, flags=re.I)
            t = re.sub(r"<[^>]+>", "", t)
            t = H.unescape(t).replace("\u00a0", " ")
            cells.append(re.sub(r"\s+", " ", t).strip())
        if len(cells) < 11 or not re.fullmatch(r"\d{6,10}", cells[0] or ""):
            continue
        out.append(cells[:11])
    return out


def query(prefix, tries=3):
    """返回 (total, rows)；带磁盘缓存，中断重跑不重复请求"""
    cache = load_cache()
    if prefix in cache:
        c = cache[prefix]
        return c["total"], c["rows"]
    for attempt in range(tries):
        data = viewstate(force=(attempt > 0))
        data.update({
            "curPageNo": "1", "totalCount": "0", "perPageCount": str(PER),
            "hscode": prefix, "goodsname": "", "bSearch": "true",
        })
        body = _fetch(FORM, data=urllib.parse.urlencode(data).encode())
        if body:
            total = int(hidden(body, "totalCount") or 0)
            rows = rows_of(body)
            cache[prefix] = {"total": total, "rows": rows}
            if len(cache) % 15 == 0:
                save_cache()
            return total, rows
        time.sleep(2.0)
    return -1, []


def crawl(verbose=True):
    seen = {}
    dup_full = []          # 细分到 8 位仍然超一页的编码
    stats = {"q": 0}

    def walk(prefix, depth):
        stats["q"] += 1
        total, rows = query(prefix)
        if total < 0:
            print("  !! 查询失败 %s" % prefix, file=sys.stderr)
            return
        if total == 0:
            return
        if total <= PER:
            for c in rows:
                seen[tuple(c)] = c
            if verbose:
                print("  %-10s %4d 条  [%d 次请求 %.0fs]"
                      % (prefix, len(rows), _nreq, time.time() - _t0), flush=True)
            return
        if depth >= 8:
            dup_full.append((prefix, total))
            for c in rows:
                seen[tuple(c)] = c
            print("  ? %s 共 %d 条仍超一页（%d 位已到底）" % (prefix, total, depth),
                  file=sys.stderr)
            return
        for d in "0123456789":
            walk(prefix + d, depth + 1)

    # 从 2 位章号起抓：一共 97 章，比从 1 位起少绕一圈
    for ch in CHAPTERS:
        walk("%02d" % ch, 2)
    save_cache()
    if verbose:
        print("查询 %d 次，用时 %.1fs" % (stats["q"], time.time() - _t0))
    return list(seen.values()), dup_full


def main():
    global BASE, FORM, _delay
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    ap.add_argument("--delay", type=float, default=0.5,
                    help="每次请求之间的基准间隔秒数（默认 0.5，别调到 0.2 以下）")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--chapters", default="", help="只抓这些章，如 20,73（调试用）")
    a = ap.parse_args()
    if a.base:
        BASE = a.base.rstrip("/")
        FORM = BASE + "/institutions/company/14/SearchHSCodeForm.aspx"
    _delay = max(0.15, a.delay)

    if a.chapters:
        global CHAPTERS
        CHAPTERS = [int(x) for x in a.chapters.split(",") if x.strip()]
    rows, dup = crawl(verbose=not a.quiet)
    items = []
    for c in rows:
        def num(x):
            x = (x or "").replace(",", "").strip()
            return float(x) if re.fullmatch(r"-?\d+(\.\d+)?", x) else None
        items.append({
            "hs": c[0],
            "name": c[1],
            "imGen": num(c[2]),      # 进口普通税率 %
            "imPref": num(c[3]),     # 进口优惠税率 %（POCIB 用这个）
            "ex": num(c[4]),         # 出口税率 %
            "vat": num(c[5]),        # 增值税 %
            "csQty": num(c[6]),      # 消费税从量
            "csVal": num(c[7]),      # 消费税从价 %
            "rebate": num(c[8]),     # 退税率 %
            "unit": c[9],
            "ctrl": c[10],           # 监管条件（POCIB 只模拟 AB）
        })
    items.sort(key=lambda x: (x["hs"], x["name"]))
    out = {
        "meta": {
            "source": FORM,
            "count": len(items),
            "dup_full": dup,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print("共 %d 条 → %s" % (len(items), os.path.relpath(OUT, ROOT)))
    if dup:
        print("有 %d 个编码细分到 8 位仍超一页：%s" % (len(dup), dup[:8]))


if __name__ == "__main__":
    main()
