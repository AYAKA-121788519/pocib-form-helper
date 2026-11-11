# -*- coding: utf-8 -*-
"""抓取 POCIB i+ 百科全站页面，保存原始 HTML 与链接图。"""
import os, re, time, json, urllib.parse, urllib.request

BASE = "http://192.168.150.135:61234/baike/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) pocib-spec-crawler"


def fetch(name):
    url = BASE + urllib.parse.quote(name)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def links(html):
    out = []
    for m in re.finditer(r'<a[^>]*?href=["\']?([^>"\'\s]+)["\']?[^>]*>(.*?)</a>', html, re.I | re.S):
        href, text = m.group(1), m.group(2)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ').strip()
        out.append((href, text))
    return out


def main():
    seen, queue, pages = set(), ["首页.html"], {}
    while queue and len(pages) < 400:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        try:
            data = fetch(name)
        except Exception as e:
            print("FAIL", name, e)
            continue
        html = data.decode("utf-8", "replace")
        pages[name] = html
        fn = name.replace("/", "_").replace("\\", "_")
        with open(os.path.join(RAW, fn), "wb") as f:
            f.write(data)
        for href, _t in links(html):
            if href.startswith(("http://", "https://", "mailto:", "javascript:", "#")):
                continue
            href = href.split("#")[0]
            if not href.endswith(".html"):
                continue
            if href not in seen and href not in queue:
                queue.append(href)
        time.sleep(0.05)
        print("OK", len(pages), name, len(data))

    with open(os.path.join(RAW, "_graph.json"), "w", encoding="utf-8") as f:
        json.dump({p: [{"href": h, "text": t} for h, t in links(pages[p])] for p in pages},
                  f, ensure_ascii=False, indent=1)
    print("TOTAL", len(pages))


if __name__ == "__main__":
    main()
