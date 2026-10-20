@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在從上游專案抓最新資料並重新產生 HTML...
python -X utf8 build\build.py --update
if errorlevel 1 (
  echo.
  echo 更新失敗。請確認已安裝 Python 且網路正常。
) else (
  echo.
  echo 完成，重新打開 NIKKE-PVP-解隊助手.html 即可。
)
pause
