# -*- coding: utf-8 -*-
"""打包：把 app/index.html 和识图取数工具装进 dist/。

用法：python scripts/build_dist.py
"""
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app", "index.html")
OCR = os.path.join(ROOT, "scripts", "ocr")
DIST = os.path.join(ROOT, "dist")
HTML = os.path.join(DIST, "POCIB填单助手.html")
TOOLS = os.path.join(DIST, "识图取数")
README = os.path.join(DIST, "使用说明.txt")
ZIP = os.path.join(DIST, "POCIB填单助手.zip")

KEEP_EXT = (".py", ".ps1", ".bat", ".md")


def main():
    os.makedirs(DIST, exist_ok=True)
    shutil.copyfile(APP, HTML)
    print("HTML  ->", HTML, os.path.getsize(HTML) // 1024, "KB")

    if os.path.isdir(TOOLS):
        shutil.rmtree(TOOLS)
    os.makedirs(TOOLS)
    n = 0
    for name in sorted(os.listdir(OCR)):
        if not name.endswith(KEEP_EXT):
            continue
        shutil.copyfile(os.path.join(OCR, name), os.path.join(TOOLS, name))
        n += 1
    print("工具  ->", TOOLS, n, "个文件")

    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(HTML, os.path.basename(HTML))
        if os.path.exists(README):
            z.write(README, os.path.basename(README))
        for name in sorted(os.listdir(TOOLS)):
            z.write(os.path.join(TOOLS, name), "识图取数/" + name)
    print("ZIP   ->", ZIP, os.path.getsize(ZIP) // 1024, "KB")


if __name__ == "__main__":
    main()
