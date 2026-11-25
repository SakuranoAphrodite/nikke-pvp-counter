@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在抓 nikkeari 的冠軍競技場實戰資料、重挖體系模板、轉換社群模板、驗證克制宣稱並重新產生 HTML...
echo （角色庫、階級與充能資料的更新請用 更新資料.bat）
echo.
python -X utf8 build/fetch_arena_stats.py --refresh --no-deck || goto :fail
python -X utf8 build/mine_templates.py || goto :fail
python -X utf8 build/community_templates.py || goto :fail
python -X utf8 build/audit_counters.py > nul || goto :fail
python -X utf8 build/build.py || goto :fail
echo.
echo 完成，重新打開 NIKKE-PVP-解隊助手.html 即可（克制稽核結果在 build/data/counter-audit.json）。要讓線上版也更新，請 commit 並 push（或等每週六的自動排程）。
goto :end
:fail
echo.
echo 更新失敗。請確認已安裝 Python、網路正常，且 nikkeari.cc 連得上。
:end
pause
