# -*- coding: utf-8 -*-
"""解析百科 HTML：抽取每页的章节与字段填写说明，输出结构化 JSON。"""
import os, re, html, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "parsed")
os.makedirs(OUT, exist_ok=True)

H2, H3, ST = "\x01H2\x01", "\x01H3\x01", "\x01ST\x01"


def content_of(h):
    m = re.search(r'<DIV[^>]*id=content[^>]*>(.*?)<DIV id=pagebottom', h, re.S | re.I)
    body = m.group(1) if m else h
    return re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S | re.I)


def to_lines(body):
    s = body
    # 标题 -> 带标记的独立行
    s = re.sub(r'<(H[2-6])[^>]*>(.*?)</\1>',
               lambda m: "\n" + (H2 if m.group(1).upper() == 'H2' else H3) + strip(m.group(2)) + "\n",
               s, flags=re.I | re.S)
    # 纯 STRONG 段落 -> 可能是字段标签（排除含站内链接的，那是术语引用不是字段）
    s = re.sub(r'<P[^>]*>\s*(<STRONG>(?:(?!<A\s).){1,80}?</STRONG>)\s*(<SPAN[^>]*>\s*</SPAN>)*\s*(</P>)?',
               lambda m: "\n" + ST + strip(m.group(1)) + "\n", s, flags=re.I | re.S)
    s = re.sub(r'<(P|LI|TR|BR|DIV|UL|OL|TABLE|HR)\b[^>]*>', "\n", s, flags=re.I)
    s = re.sub(r'<T[DH]\b[^>]*>', " | ", s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = s.replace('\xa0', ' ')
    lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')]
    return [l for l in lines if l and l not in ('|',)]


def strip(x):
    return html.unescape(re.sub(r'<[^>]+>', '', x)).strip()


def is_field_line(l):
    """判断一行是否是字段标签（H3 或 短标签、可含英文括号）。"""
    if not (20 <= len(l) <= 60):
        return False
    if l.endswith(('。', '：', ':', '，', ',')) or '。' in l:
        return False
    # 形如 中文名(English) 或 纯短中文
    if re.match(r'^[\u4e00-\u9fa5A-Za-z0-9（）()／/·\-、 ]{2,40}[（(][A-Za-z0-9 .,&/／\'\-]{1,45}[)）]$', l):
        return True
    return False


def parse_page(name, h):
    body = content_of(h)
    m = re.search(r'<H1[^>]*>(.*?)</H1>', body, re.S | re.I)
    title = strip(m.group(1)) if m else name[:-5]
    lines = to_lines(body)
    # 去掉导航噪声
    noise = {'首页', '搜索：', '目录', 'POCIB i+ 百科'}
    lines = [l for l in lines if l not in noise]

    sections, cur_sec, cur_field = [], None, None
    for l in lines:
        if l.startswith(H2):
            cur_sec = {'name': l[len(H2):], 'fields': [], 'paras': []}
            sections.append(cur_sec)
            cur_field = None
        elif l.startswith(H3) or l.startswith(ST):
            label = l[4:] if l.startswith(H3) else l[len(ST):]
            if label.endswith(('：', ':')) or len(label) < 2:
                continue
            # 以"注/注意/这里/说明"开头的其实是说明性注释，归入上一个字段的规则
            if re.match(r'^(注|注意|说明|这里|附注)', label) and cur_field is not None:
                cur_field['rules'].append(label)
                continue
            if cur_sec is None:
                cur_sec = {'name': '正文', 'fields': [], 'paras': []}
                sections.append(cur_sec)
            cur_field = {'label': label, 'rules': []}
            cur_sec['fields'].append(cur_field)
        else:
            if cur_sec is None:
                continue
            if cur_field is not None:
                cur_field['rules'].append(l)
            else:
                cur_sec['paras'].append(l)
    return {'page': name, 'title': title, 'sections': sections}


def main():
    out = {}
    problems = []
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith('.html'):
            continue
        h = open(os.path.join(RAW, fn), encoding='utf-8', errors='replace').read()
        p = parse_page(fn, h)
        out[fn[:-5]] = p
        nf = sum(len(s['fields']) for s in p['sections'])
        if nf == 0 and len(p['sections']) > 0:
            problems.append((fn, len(p['sections'])))
    with open(os.path.join(OUT, 'documents.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('pages', len(out), 'no-field pages', len(problems))
    for x in problems[:20]:
        print('  nofield:', x)


if __name__ == '__main__':
    main()
