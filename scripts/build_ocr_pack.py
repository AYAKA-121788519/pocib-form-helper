# -*- coding: utf-8 -*-
"""单独打「识图服务 + 模型」包：不含填单助手网页，只把截窗口取数这件事做完整。

    python scripts/build_ocr_pack.py            # 装配 + 打包
    python scripts/build_ocr_pack.py assemble   # 只装配到 build/ocr_pack/
    python scripts/build_ocr_pack.py pack       # 只压 zip
    python scripts/build_ocr_pack.py verify     # 自检：导入依赖 + 解析规则自测

产物：dist/POCIB识图服务-独立包.zip
结构（解压后一个文件夹，双击根上的 bat 即可）：
    POCIB识图服务/
        识图服务.bat      起本机服务，网页里一键取数
        识图取数.bat      单次识别，结果进剪贴板
        ocr/              py 源码 + 两个原始 bat + 说明.md
        runtime/          自带 Python 3.13 + numpy/onnxruntime/cv2/rapidocr + PP-OCR 模型
        使用说明.txt
"""
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_RT = os.path.join(ROOT, "build", "portable", "runtime")   # 绿色版已装好的运行时
OCR_SRC = os.path.join(ROOT, "scripts", "ocr")
PACK = os.path.join(ROOT, "build", "ocr_pack")
TOP = os.path.join(PACK, "POCIB识图服务")
OUT = os.path.join(ROOT, "dist", "POCIB识图服务-独立包.zip")

SKIP_DIR = {"__pycache__", "tests", "test", "docs", "doc", "examples"}
SKIP_EXT = (".pyc", ".bak", ".whl")

# 根目录两个入口：转发到 ocr/ 下的原版 bat，逻辑只有一份
ROOT_BAT = r'''@echo off
chcp 65001 >nul
title POCIB 识图服务
call "%~dp0ocr\{inner}" %*
'''

GUIDE = """POCIB 识图服务 · 独立包
============================

这个包只做一件事：把 POCIB 客户端窗口上的公司资料 / 商品资料认成可填的数据。
填单助手网页不在包里，识图能力和中文模型是自带齐的，不用装 Python、不用联网。

一、怎么用

  1. 双击「识图服务.bat」。黑窗口出现「POCIB 识图服务已启动 127.0.0.1:17861」就好了，
     第一次会预热模型，等它打出「模型已就绪」再操作。
  2. 把 POCIB 客户端切到「基本资料」或「商品信息」页面，窗口别最小化。
  3. 打开填单助手网页，点左栏「📷 截图识别公司信息」/「📷 截图识别商品」，
     2～4 秒出结果：左边是截到的画面，右边是逐项识别值。
  4. 核对着改一改，选「填入到哪」，点「填入选中的项」。
  5. 用完直接关掉黑窗口，服务就停了，内存随之释放。

  把「POCIB填单助手.html」放进本文件夹根目录，启动服务时会自动打开它。

二、不想开服务（只认一次）

  双击「识图取数.bat」，自动找 POCIB 窗口 → 识别 → 结果进剪贴板；
  回网页点「📷 截图识别」→「手动方式：粘贴 / 拖入识别结果」→ Ctrl+V。

  常用参数（命令行里跑）：
    识图取数.bat --list              列出当前能识别的窗口
    识图取数.bat --hwnd 123456       指定窗口句柄
    识图取数.bat --kind goods        强制按商品档案解析
    识图取数.bat --file 截图.png      直接认一张图（Win+Shift+S 存的 PNG）
    识图取数.bat --clip              认剪贴板里的截图
    识图取数.bat --engine win        用 Windows 自带 OCR（万一模型起不来时的备胎）
    识图取数.bat --out 结果.json      另存一份 json（默认不留文件）

三、目录

  ocr\\          识图源码：serve.py（本机接口）extract.py（主流程）ocrlib.py（截图/OCR）
                parse.py（版面还原与字段匹配）说明.md（更细的文档）
  runtime\\      自带 Python 3.13 + 依赖 + PP-OCRv3 中文模型，别删、别改名

四、接口（只监听 127.0.0.1，本机才能访问）

  /ping      服务状态          /windows   可识别窗口列表
  /capture   截取并识别        /lastshot  上一次的截图

五、精度与隐私

  - 账号、税号、海关登记号、信用代码、电话传真邮编、银行名称、地址：实测基本全对。
  - 公司介绍、规格型号这类长段落，换行归位偶尔会串栏，核对时留意。
  - 认不准的字段留空或标「低」置信且默认不勾选，不会瞎填。
  - 币别有时认不出（软件里那行字太小），会按国家推导并标「推导」。
  - 全程本机完成：截图走 PrintWindow 后台渲染，不抢焦点、不动鼠标，不联网、不落文件。
  - 模型常驻内存约 300MB，关掉黑窗口即释放。

六、起不来怎么办

  - 提示端口被占：说明已经开着一个了，看看任务栏有没有旧的cmd窗口。
  - 认不出：窗口最小化过、或当前不是基本资料/商品信息页；先点开窗口再试。
  - 黑窗口一闪就没了：右键编辑「识图服务.bat」把最后的 pause 留着再运行，看清楚报错。
"""


def say(*a):
    print(*a, flush=True)


def assemble():
    if not os.path.isfile(os.path.join(SRC_RT, "python.exe")):
        say("缺少运行时：%s" % SRC_RT)
        say("先跑一次 python scripts/build_portable.py prepare 把运行时装出来。")
        sys.exit(1)
    if os.path.isdir(PACK):
        shutil.rmtree(PACK)
    os.makedirs(TOP)
    ocr_dst = os.path.join(TOP, "ocr")
    os.makedirs(ocr_dst)
    n = 0
    for name in sorted(os.listdir(OCR_SRC)):
        if name.endswith((".py", ".bat", ".ps1", ".md")) and name != "make_bats.py":
            shutil.copyfile(os.path.join(OCR_SRC, name), os.path.join(ocr_dst, name))
            n += 1
    say("源码 %d 个 → ocr/" % n)

    say("复制运行时（282MB，稍等）…")
    shutil.copytree(SRC_RT, os.path.join(TOP, "runtime"),
                    ignore=shutil.ignore_patterns(*SKIP_DIR, "*.pyc", ".dist-info",
                                                  "opencv_videoio_ffmpeg*"))
    # 目录名从「识图取数」改成「ocr」，_pth 里的相对路径要跟着改
    with open(os.path.join(TOP, "runtime", "python313._pth"), "w", newline="\r\n") as f:
        f.write("python313.zip\nLib\\site-packages\n..\\ocr\n.\n")

    for inner in ("识图服务.bat", "识图取数.bat"):
        with open(os.path.join(TOP, inner), "w", encoding="utf-8", newline="\r\n") as f:
            f.write(ROOT_BAT.format(inner=inner))
    with open(os.path.join(TOP, "使用说明.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(GUIDE)
    say("装配完成：", TOP)


def pack():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n = total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for base, dirs, files in os.walk(PACK):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR and not d.endswith(".dist-info")]
            for f in sorted(files):
                if f.endswith(SKIP_EXT) or f.startswith("opencv_videoio_ffmpeg"):
                    continue
                p = os.path.join(base, f)
                z.write(p, os.path.relpath(p, PACK))
                n += 1
                total += os.path.getsize(p)
    say("打包完成：%s" % OUT)
    say("  文件数 %d，解压后 %.0f MB，压缩后 %.1f MB"
        % (n, total / 1e6, os.path.getsize(OUT) / 1e6))


def verify():
    py = os.path.join(TOP, "runtime", "python.exe")
    ocr = os.path.join(TOP, "ocr")
    code = (
        "import sys;print('python', sys.version.split()[0]);print('exe', sys.executable);"
        "import numpy, cv2, onnxruntime, rapidocr_onnxruntime as R;"
        "print('numpy', numpy.__version__);print('cv2', cv2.__version__);"
        "print('onnxruntime', onnxruntime.__version__);"
        "print('rapidocr', R.__file__);"
        "import ocrlib;print('rapid ok', ocrlib.rapid_available())"
    )
    r = subprocess.run([py, "-c", code], cwd=ocr, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    say(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        say("!! 依赖导入失败")
        sys.exit(1)
    r2 = subprocess.run([py, "self_test.py"], cwd=ocr, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    tail = (r2.stdout or r2.stderr).strip().splitlines()
    say("\n".join(tail[-6:]))
    if r2.returncode != 0:
        say("!! 解析自测没过")
        sys.exit(1)


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    if a in ("assemble", "all"):
        assemble()
    if a in ("pack", "all"):
        pack()
    if a in ("verify", "all"):
        verify()


if __name__ == "__main__":
    main()
