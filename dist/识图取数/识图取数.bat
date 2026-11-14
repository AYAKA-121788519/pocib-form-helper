@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title POCIB 识图取数
echo.
echo   ==========================================
echo    POCIB 识图取数 - 截窗口自动认字（单次）
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
