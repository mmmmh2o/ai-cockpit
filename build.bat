@echo off
REM AI Cockpit — Windows 本地构建脚本
REM 用法: 双击运行 或 cmd 中执行 build.bat

echo ========================================
echo   AI Cockpit - Windows Build Script
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 未安装，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/5] 安装前端依赖...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] npm install 失败
    pause
    exit /b 1
)

echo [2/5] 构建前端...
call npm run build
if errorlevel 1 (
    echo [ERROR] 前端构建失败
    pause
    exit /b 1
)
cd ..

echo [3/5] 安装后端依赖...
cd backend
pip install pyinstaller -q
pip install -e . -q
if errorlevel 1 (
    echo [ERROR] pip install 失败
    pause
    exit /b 1
)
cd ..

echo [4/5] PyInstaller 打包...
pyinstaller build/ai-cockpit.spec --noconfirm --distpath dist --workpath build\tmp
if errorlevel 1 (
    echo [ERROR] PyInstaller 打包失败
    pause
    exit /b 1
)

echo [5/5] 整理产物...
if exist "dist\ai-cockpit\static" rmdir /s /q "dist\ai-cockpit\static"
mkdir "dist\ai-cockpit\static"
xcopy /e /i /q "frontend\dist\*" "dist\ai-cockpit\static\"
copy /y "config.yaml" "dist\ai-cockpit\"
copy /y "README.md" "dist\ai-cockpit\"

echo.
echo ========================================
echo   ✅ 构建完成！
echo   输出: dist\ai-cockpit\ai-cockpit.exe
echo ========================================
echo.
pause
