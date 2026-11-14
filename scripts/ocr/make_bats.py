# -*- coding: utf-8 -*-
"""生成两个双击入口的 .bat（UTF-8 + CRLF）。

绿色版（带 runtime/）优先用自带的 python.exe，别人不用装 Python。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PY_DETECT = r'''set "PY="
set "BUNDLED="
if exist "%~dp0..\runtime\python.exe" (
  set "PY=%~dp0..\runtime\python.exe"
  set "BUNDLED=1"
)
if not defined PY (
  python -c "import sys" >nul 2>nul && set "PY=python"
)
if not defined PY (
  py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
)
'''

NO_PY_MSG = r'''if not defined PY (
  echo.
  echo   [X] 没有找到 Python 3
  echo       你用的是精简版：需要本机装 Python 3.9+（https://www.python.org/downloads/，
  echo       安装第一步勾选 "Add python.exe to PATH"）。
  echo       或者下载「绿色版」，它自带运行时，什么都不用装。
  echo.
  pause
  exit /b 1
)
'''

# 只有非绿色版才需要检查 / 安装模型
MODEL_CHECK = r'''if not defined BUNDLED (
  %PY% -c "import rapidocr_onnxruntime" >nul 2>nul
  if errorlevel 1 (
    echo.
    echo   [!] 第一次使用，要装中文识别模型（约 120MB，只装这一次）
    echo       正在从清华镜像安装，请稍等...
    echo.
    %PY% -m pip install rapidocr-onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
    %PY% -c "import rapidocr_onnxruntime" >nul 2>nul
    if errorlevel 1 (
      echo.
      echo   [X] 模型没装上，退回系统自带 OCR（中文精度会差些）
      echo.
      set "ENG=--engine win"
    ) else (
      set "ENG="
    )
  ) else (
    set "ENG="
  )
) else (
  set "ENG="
)
'''

HEAD = r'''@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
'''

SERVE_BAT = HEAD + r'''title POCIB 识图服务
echo.
echo   ==========================================
echo    POCIB 识图服务 - 网页里一键截取公司/商品信息
echo   ==========================================
echo.
''' + PY_DETECT + NO_PY_MSG + MODEL_CHECK + r'''
echo.
%PY% "%~dp0serve.py" !ENG! --open %*
echo.
echo   服务已停止。要重新开始，再双击本文件。
pause
'''

CLI_BAT = HEAD + r'''title POCIB 识图取数
echo.
echo   ==========================================
echo    POCIB 识图取数 - 截窗口自动认字（单次）
echo   ==========================================
echo.
''' + PY_DETECT + NO_PY_MSG + MODEL_CHECK + r'''
%PY% "%~dp0extract.py" !ENG! %*
set RC=%errorlevel%
echo.
if "%RC%"=="0" (
  echo   结果已复制到剪贴板。回网页点「截图识别」，Ctrl+V 粘贴即可。
) else (
  echo   没成功，常见原因：
  echo     - POCIB 窗口最小化了：先点开窗口再运行
  echo     - 当前页面不是「基本资料」或「商品信息」
)
echo.
echo   提示：双击「识图服务.bat」后，网页里可以直接一键截取，不用粘贴。
pause
'''

for name, body in (("识图服务.bat", SERVE_BAT), ("识图取数.bat", CLI_BAT)):
    p = os.path.join(HERE, name)
    with open(p, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(body)
    print(name, os.path.getsize(p), "bytes")
