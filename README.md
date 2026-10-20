# NIKKE 競技場解隊助手

以台港澳服（與國際服同資料）為基準的 PVP 競技場輔助工具。輸入對方防守隊的 5 個角色，工具會分析對方的爆裂速度、爆裂鏈、所屬體系與關鍵威脅，再從你的角色庫挑出能克制對方的隊伍。

## 使用方式

線上版（手機也能用）：<https://sakuranoaphrodite.github.io/nikke-pvp-counter/>

1. 或者直接用瀏覽器打開 `NIKKE-PVP-解隊助手.html`（不需要安裝任何東西，離線可用）。
2. 到「我的角色庫」把你擁有的角色點成擁有，資料只存在瀏覽器本機。
3. 回「解隊」，照對方 P1 到 P5 的順序填入角色，或在快速輸入框直接打中文名，例如 `紅蓮 豺狼 布蘭兒 桑迪 特蕾娜`。
4. 看分析與建議，點「帶入試算」可以再微調自己的隊伍。

頁首的「我方進攻／我方防守」用來切換你是在打別人的防守隊，還是在排自己的防守隊。

## 讓線上版自動載入角色庫

角色庫預設存在瀏覽器本機，不同裝置不互通。若想讓每個裝置打開線上版都直接有你的角色庫：

1. 在「我的角色庫」按「匯出 JSON」，下載 `roster.json`。
2. 把 `roster.json` 放到專案根目錄（與 `index.html` 同層），commit 後 push。
3. 線上版開啟時會讀取同目錄的 `roster.json`：本機角色庫是空的、或上次也是從倉庫載入的，就自動套用；本機手動改過則不覆蓋，可用「從 GitHub 載入角色庫」按鈕手動同步。

`roster.json` 格式：`{"exported":"2026-10-20","owned":["scarlet","jackal"],"history":[]}`，`owned` 放角色 id（與 `build/data/characters.json` 的 `id` 相同）。

## 檔案結構

| 路徑 | 內容 |
| --- | --- |
| `NIKKE-PVP-解隊助手.html` | 成品，單一檔案 |
| `build/template.html` | 頁面原始碼，含解法規則與威脅標籤 |
| `build/build.py` | 建置腳本，把資料嵌進頁面 |
| `build/data/characters.json` | 209 名角色資料、繁中譯名、充能數值、PVP 階級 |
| `build/data/templates.json` | 23 個主流隊伍模板與互剋關係 |

## 新角色出來怎麼辦

工具有三層更新方式：

1. **自動**：每天第一次打開 HTML 時，若有網路，會向上游專案抓最新的 `characters.json` 與 `templates.json`，暫存在瀏覽器並立即套用。頁首會顯示資料來源（內建／快取／線上）與日期，也有「檢查更新」按鈕可手動觸發。
2. **半自動**：雙擊 `更新資料.bat`，或執行下面的指令，會把最新資料寫回 `build/data/` 並重新產生成品 HTML，離線時也會有新角色：

```bash
python build/build.py --update
```

3. **手動**：若上游停更，可直接編輯 `build/data/characters.json` 新增角色（照既有格式填爆裂類型、武器與各速度階的充能值），再執行 `python build/build.py`。

威脅標籤（`UNIT_TAGS`）、體系中文名（`ARCH_NAME`）與解法規則（`RULES`）在 `build/template.html` 內，是本工具自行整理的知識層，新角色或新體系需要手動補；沒補的角色會顯示為「一般角色」，不影響速度計算。

## 資料來源與授權

角色資料、充能數值與隊伍模板取自開源專案 [NIKKE Arena Planner](https://github.com/williamchong/nikke-arena-planner)（MIT 授權，授權書在 `build/data/LICENSE-nikke-arena-planner.txt`）。該專案的數據整理自 nikke.gg、Prydwen 與左猫猫的充能計算表。解法規則與威脅標籤由本工具自行整理，僅供參考。本工具為非官方粉絲工具，與 Shift Up、Level Infinite 無關。
