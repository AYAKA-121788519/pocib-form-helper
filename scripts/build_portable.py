# -*- coding: utf-8 -*-
"""打「绿色版」：自带 Python 运行时 + PP-OCR 模型，对方不用装任何东西。

装配（首次需要联网下载，约 5 分钟）：
    python scripts/build_portable.py prepare
打包（产出 dist/POCIB填单助手-绿色版.zip）：
    python scripts/build_portable.py pack

体积说明：解压约 260MB，压缩后约 90MB。大头是 cv2.pyd（74MB，PP-OCR 的
检测后处理要用 findContours/透视变换）、onnxruntime（47MB）、numpy（53MB）。
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "portable")
RT = os.path.join(BUILD, "runtime")
SP = os.path.join(RT, "Lib", "site-packages")
OCR_SRC = os.path.join(ROOT, "scripts", "ocr")
APP = os.path.join(ROOT, "app", "index.html")
GUIDE = os.path.join(ROOT, "dist", "使用说明.txt")
OUT = os.path.join(ROOT, "dist", "POCIB填单助手-绿色版.zip")

PY_URL = "https://mirrors.huaweicloud.com/python/3.13.2/python-3.13.2-embed-amd64.zip"
PKGS = ["numpy", "onnxruntime", "opencv-python-headless", "pyclipper", "shapely",
        "PyYAML", "six", "rapidocr-onnxruntime"]

# 压缩时跳过的东西
SKIP_DIR = {"__pycache__", "tests", "test", "docs", "doc", "examples"}
SKIP_EXT = (".pyc", ".bak", ".whl")


def say(*a):
    print(*a, flush=True)


def prepare():
    os.makedirs(BUILD, exist_ok=True)
    if not os.path.isfile(os.path.join(RT, "python.exe")):
        z = os.path.join(BUILD, "py.zip")
        if not os.path.isfile(z):
            say("下载 Python 嵌入式包…")
            subprocess.run(["curl", "-sL", "-o", z, PY_URL], check=True)
        say("解压运行时…")
        zipfile.ZipFile(z).extractall(RT)
        pth = os.path.join(RT, "python313._pth")
        with open(pth, "w", newline="\r\n") as f:
            f.write("python313.zip\nLib\\site-packages\n..\\识图取数\n.\n")
    if not os.path.isdir(os.path.join(SP, "rapidocr_onnxruntime")):
        say("安装依赖（numpy / onnxruntime / opencv / rapidocr）…")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "--no-warn-script-location", "--target", SP] + PKGS, check=True)
    say("运行时就绪：", RT)


def assemble():
    tools = os.path.join(BUILD, "识图取数")
    os.makedirs(tools, exist_ok=True)
    for name in os.listdir(OCR_SRC):
        if name.endswith((".py", ".bat", ".ps1", ".md")) and name != "make_bats.py":
            shutil.copyfile(os.path.join(OCR_SRC, name), os.path.join(tools, name))
    shutil.copyfile(APP, os.path.join(BUILD, "POCIB填单助手.html"))
    if os.path.isfile(GUIDE):
        shutil.copyfile(GUIDE, os.path.join(BUILD, "使用说明.txt"))
    say("工具就位：", tools)


def pack():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n = 0
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for base, dirs, files in os.walk(BUILD):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR and not d.endswith(".dist-info")]
            for f in sorted(files):
                if f.endswith(SKIP_EXT) or f.startswith("opencv_videoio_ffmpeg"):
                    continue
                p = os.path.join(base, f)
                rel = os.path.relpath(p, BUILD)
                # 只跳过装配目录根上的中间产物（py.zip 之类），runtime 里的 stdlib zip 要保留
                if rel in ("py.zip",) or f.endswith(SKIP_EXT):
                    continue
                if rel.startswith("runtime\\Lib\\site-packages\\cv2\\") and "ffmpeg" in f:
                    continue
                z.write(p, rel)
                n += 1
                total += os.path.getsize(p)
    say("打包完成：%s" % OUT)
    say("  文件数 %d，解压后 %.0f MB，压缩后 %.1f MB"
        % (n, total / 1e6, os.path.getsize(OUT) / 1e6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "assemble", "pack", "all"])
    a = ap.parse_args()
    if a.action in ("prepare", "all"):
        prepare()
    if a.action in ("assemble", "all"):
        assemble()
    if a.action in ("pack", "all"):
        pack()


if __name__ == "__main__":
    main()
