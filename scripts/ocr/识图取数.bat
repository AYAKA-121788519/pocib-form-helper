@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title POCIB 识图取数
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo   ==========================================
echo    POCIB 识图取数  ·  截窗口自动认字
echo   ==========================================
echo.

set "PY="
python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY (
  py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo   [X] 没有找到 Python
  echo       1. 打开 https://www.python.org/downloads/ 下载安装
  echo       2. 安装第一步务必勾选 "Add python.exe to PATH"
  echo       3. 装完重新双击本文件
  echo.
  pause
  exit /b 1
)

%PY% -c "import rapidocr_onnxruntime" >nul 2>nul
if errorlevel 1 (
  echo   [!] 第一次使用，要装中文识别模型（约 120MB，只装这一次）
  echo       正在从清华镜像安装，请稍等...
  echo.
  %PY% -m pip install rapidocr-onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
  %PY% -c "import rapidocr_onnxruntime" >nul 2>nul
  if errorlevel 1 (
     echo.
     echo   [X] 模型没装上，先用系统自带识别顶上（中文精度会差些）
     echo.
     %PY% "%~dp0extract.py" --engine win %*
     echo.
     pause
     exit /b 0
  )
)

%PY% "%~dp0extract.py" %*
set RC=%errorlevel%
echo.
if "%RC%"=="0" (
  echo   下一步：回到 POCIB 填单助手网页，点「截图识别」，
  echo           在输入框里按 Ctrl+V 粘贴，核对后填入。
) else (
  echo   没成功，常见原因：
  echo     - 窗口最小化了：先把 POCIB 窗口点开再运行
  echo     - 当前页面不是「基本资料」或「商品信息」
)
echo.
pause
