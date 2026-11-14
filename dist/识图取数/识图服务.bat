@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title POCIB 识图服务
echo.
echo   ==========================================
echo    POCIB 识图服务 - 网页里一键截取公司/商品信息
echo   ==========================================
echo.
set "PY="
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
if not defined PY (
  echo.
  echo   [X] 没有找到 Python 3
  echo       你用的是精简版：需要本机装 Python 3.9+（https://www.python.org/downloads/，
  echo       安装第一步勾选 "Add python.exe to PATH"）。
  echo       或者下载「绿色版」，它自带运行时，什么都不用装。
  echo.
  pause
  exit /b 1
)
if not defined BUNDLED (
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

echo.
%PY% "%~dp0serve.py" !ENG! --open %*
echo.
echo   服务已停止。要重新开始，再双击本文件。
pause
