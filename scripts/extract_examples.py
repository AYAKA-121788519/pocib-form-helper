# -*- coding: utf-8 -*-
"""从 6 篇操作示例中抽取"履行合同阶段"的分步流程与蓝色可跳转单证链接。"""
import os, re, html, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "parsed")

EXAMPLES = [
    "操作示例：L／C＋FOB＋海运", "操作示例：T／T＋CIF＋海运", "操作示例：T／T＋CPT＋空运",
    "操作示例：T／T＋FCA＋空运", "操作示例：D／P＋CIP＋空运", "操作示例：D／A＋CIF＋海运",
]


def seg_fulfill(h):
    """取'履行合同阶段' H2 到下一个 H2 之间的 HTML（跳过目录里的同名锚点）。"""
    m = re.search(r'<H2[^>]*>[^<]*履行合同阶段[^<]*</H2>', h, re.I)
    if not m:
        return ""
    start = m.start()
    nxt = re.search(r'<H2[^>]*>', h[m.end():])
    end = m.end() + nxt.start() if nxt else len(h)
    return h[start:end]


def steps(seg):
    """切成有序的步骤：以数字编号开头的段落。"""
    # 先把块级标签换成换行
    s = re.sub(r'<(P|LI|TR|BR|DIV|UL|OL)\b[^>]*>', "\n", seg, flags=re.I)
    # 链接保留为 [文本](target)
    s = re.sub(r'<A[^>]*href=["\']?([^>"\'\s]+)["\']?[^>]*>(.*?)</A>',
               lambda m: "{{%s|%s}}" % (re.sub(r'<[^>]+>', '', m.group(2)).strip(), m.group(1)), s,
               flags=re.I | re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')]
    lines = [l for l in lines if l and len(l) > 3]
    out = []
    for l in lines:
        m = re.match(r'^(\d{1,2})[\s\.．、]', l)
        if m:
            out.append({"no": int(m.group(1)), "text": l})
        elif out and l.startswith(('（', '(', '注', '点击', '选择', '输入')):
            out[-1]["text"] += " " + l
    for st in out:
        st["docs"] = re.findall(r'\{\{([^|}]+)\|([^}]+)\}\}', st["text"])
        st["linked"] = [d[0] for d in st["docs"] if d[1].endswith('.html') and '操作示例' not in d[1]]
    return out


def main():
    res = {}
    for name in EXAMPLES:
        p = os.path.join(RAW, name + ".html")
        if not os.path.exists(p):
            print("MISS", name)
            continue
        h = open(p, encoding="utf-8", errors="replace").read()
        st = steps(seg_fulfill(h))
        res[name.replace("操作示例：", "")] = st
        print("%-16s 履行阶段步骤 %d 个，含单证链接的步骤 %d 个" %
              (name.replace("操作示例：", ""), len(st), sum(1 for s in st if s["linked"])))

    txt = os.path.join(ROOT, "spec", "六个操作示例-履行阶段对照.md")
    L = ["# 六种贸易组合 · 履行合同阶段分步对照", "",
         "> 来源：POCIB 百科《操作示例》系列。蓝色可跳转字段即该步骤要填写的单证。", ""]
    for combo, st in res.items():
        L += ["## %s" % combo, ""]
        for s in st:
            docs = "、".join("`%s`" % d for d in s["linked"]) if s["linked"] else "—"
            text = re.sub(r'\{\{([^|}]+)\|[^}]+\}\}', r'\1', s["text"])
            L.append("%2d. %s  \n    → 单据：%s" % (s["no"], text[:200], docs))
        L.append("")
    open(txt, "w", encoding="utf-8").write("\n".join(L))
    json.dump(res, open(os.path.join(OUT, "examples_flow.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n-> spec/六个操作示例-履行阶段对照.md")
    print("-> data/parsed/examples_flow.json")


if __name__ == "__main__":
    main()
