# NIKKE 競技場解隊助手

以台港澳服（與國際服同資料）為基準的 PVP 競技場輔助工具。輸入對方防守隊的 5 個角色，工具會分析對方的爆裂速度、爆裂鏈、所屬體系與關鍵威脅，再從你的角色庫挑出能克制對方的隊伍。

## 使用方式

線上版（手機也能用）：<https://sakuranoaphrodite.github.io/nikke-pvp-counter/>

1. 或者直接用瀏覽器打開 `NIKKE-PVP-解隊助手.html`（不需要安裝任何東西，離線可用）。
2. 到「我的角色庫」把你擁有的角色點成擁有，資料只存在瀏覽器本機。
3. 回「解隊」，照對方 P1 到 P5 的順序填入角色，或在快速輸入框直接打中文名，例如 `紅蓮 豺狼 布蘭兒 桑迪 特蕾娜`。
4. 看分析與建議，點「帶入試算」可以再微調自己的隊伍。

頁首的「我方進攻／我方防守」用來切換你是在打別人的防守隊，還是在排自己的防守隊。

## 冠軍競技場實戰數據與進階速度設定

- `build/fetch_arena_stats.py` 會從 [にけあり！NIKKE 競技場分析器](https://nikkeari.cc/zh-CN) 的公開 API 抓冠軍競技場的對戰紀錄（JP／KR／國際服，每回合含進攻隊、防守隊與勝方），整理成 `build/data/arena-stats.json`：每個 5 人組合的場次、勝率、進攻／防守勝率、被哪些隊伍打贏過、含某核心角的隊伍整體勝率、角色常用站位。工具會在「對方分析」顯示這隊（或 4 人相同的相近隊）的實戰戰績，在「解法建議」列出實戰中打贏過它的隊伍並可一鍵帶入。
- 同一支腳本也會抓 [NIKKE DECK](https://nikke-deck.com/en/deck) 的 `data.json`，整理成 `build/data/deck-speed.json`：哪些角色有「充能速度 17%」超頻選項、量子魔方 Lv7 的充能加成，以及它的 PVP 階級（在角色旁以「deck」標籤顯示，作為第二份獨立評價）。
- 「進階」區可以勾選對方或我方角色的超頻 17%／量子魔方 Lv7，速度判定會隨之改變；模型與數值來自 nikke-deck 與 NIKKE Synergy 的機制文章，是估算值。
- 更新：`python build/fetch_arena_stats.py --refresh`（原始回應存在 `build/data/raw/`，不進倉庫），再執行 `python build/build.py`。請勿高頻呼叫對方的 API。

## 軸（誰開爆裂）與再入爆裂

- 每一段爆裂由位置最前、類型符合的角色開；第一輪會開的角色是「軸內」，其餘「軸外」。軸外角色的爆裂技能不會發動，但被動與一般技能照常生效。工具在逐位威脅標出「開 B1／B2／B3」或「軸外」，靠爆裂的核心角在軸外時該體系視為不成立，相關提示略過。
- 角色標籤中含「(被動…)」者為一般技能，軸外也有效；其餘的核爆、無敵、不屈、復活、全體暈眩、全體嘲諷、全隊減傷、再入都需該角色實際開爆裂。標籤來源為 nikke.gg 各角色技能頁。
- 再入爆裂：蒂亞、露菲冬日購物狂、阿維斯塔、仙境兔女郎愛麗絲開完會讓全隊再入 B1（無條件）；超級巨星阿妮斯在隊上另有一般 B1 時再入 B1（被動）；毒蛇珍藏再入 B2；拉毗小紅帽在無一般 B1 時自己變成 B1。再入多一段爆裂，工具把延遲（約 0.5～1.5 秒）換算成速度階計入比較。
- 「自動排軸」：關鍵爆裂角排進軸內、有嘲諷／坦克／減傷標籤的角色放 P1／P5、火力放 P3／P4，並套用社群站位偏好（灰姑娘避開 P1／P2、小美人魚 P4、豺狼與羅珊娜後排）；不會把坦從 P1／P5 換走。

## 建議的依據、參考對局與對戰紀錄

- 每條建議後面都有「依據：…」標籤，連到出處：上游模板對照表（互剋關係）、Prydwen 的 PVP 機制與隊伍原型指南（角色機制、解法）、巴哈組隊心得；標成「本工具推算」的是速度與評分，不是外部依據。
- `references.json`（倉庫根目錄）收錄參考對局與資料，符合當前對手體系的項目會直接顯示在建議裡。格式：

```json
{"title":"標題","url":"連結","source":"YouTube","kind":"影片",
 "enemy":["scarlet-nuke"],"my":["noah-stall"],"units":["scarlet","jackal"],
 "result":"win","note":"一句話說明","date":"2026-10"}
```

`enemy`／`my` 填 `build/data/templates.json` 的 `archetype` id，`units` 填角色 id（命中兩個以上就會顯示），`result` 只在自己打過的對局填 `win` 或 `loss`。線上版會即時讀取倉庫裡的最新檔案；本機版用建置時嵌入的版本。
- 「對戰紀錄」卡可以把每場的對方隊、我方隊與勝負記下來，之後遇到同一隊或同體系會顯示戰績；匯出 JSON 時會一起帶走。冠軍競技場的回放只能在遊戲內看，無法自動匯入。

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
| `build/data/templates.json` | 上游的 23 個主流隊伍模板與互剋關係 |
| `build/data/templates-extra.json` | 本工具補充的 2026 體系模板（超級巨星阿妮斯＋餅乾核心、娜由塔一閃、豺狼＋貝斯蒂不屈、諾雅諾伊斯餅乾灰姑娘），獨立嵌入，線上更新上游模板後仍會合併 |
| `build/data/templates-mined.json` | `build/mine_templates.py` 從 nikkeari 的 24,000 回合挖出的 24 個核心家族：場次、勝率、常見補位、站位、互剋（統計結果，非人工驗證） |
| `build/data/community-teams.json` | 社群明確列出的新人／特殊競技場隊伍（JP wikiwiki、GameWith、Yahoo知恵袋、KR arca／dcinside／ruliweb、Gamemeca，2025-07～2026-10），含來源、日期、站位、速度、打得贏與輸給誰 |
| `build/data/templates-community.json` | `build/community_templates.py` 把上面的隊伍轉成的 36 個模板（名稱標「（社群）」） |
| `build/data/nicknames.json` | 角色綽號／別名（白兔、黑兔、偶像阿妮斯、白雪重武、EMT…），搜尋時與正式名一起比對，可自行增補 |
| `avatars/` | 角色頭像（`build/fetch_avatars.py` 從上游倉庫下載，檔名為角色的 avatarImg 代碼）。圖片為遊戲素材，版權屬 SHIFT UP／Level Infinite，僅作粉絲工具展示 |

模板分四層：上游模板、本工具補充、資料挖掘、社群隊伍；更新流程是 `fetch_arena_stats.py --refresh` → `mine_templates.py` → `community_templates.py` → `build.py`。社群隊伍要新增時直接在 `community-teams.json` 加一筆再跑轉換。

## 哪裡可以找到這類隊伍資料與討論

- 日本：[wikiwiki（NIKKE）アリーナ攻略](https://wikiwiki.jp/fpo2w6pt/（NIKKE）アリーナ攻略)（隊伍、互剋、新手三隊範本，更新最勤）、[GameWith 競技場](https://gamewith.jp/nikke/article/show/379079)、[Yahoo!知恵袋](https://chiebukuro.yahoo.co.jp/)（搜「NIKKE アリーナ」有大量「這隊怎麼打」問答）。
- 韓國：[arca.live 니케 채널](https://arca.live/b/nikketgv)（特殊競技場體系整理、新手配法）、[dcinside 니케 갤러리](https://gall.dcinside.com/mgallery/board/lists/?id=gov)（冠軍競技場環境文、新手攻守指南）、[ruliweb](https://bbs.ruliweb.com/game/86188)。
- 資料統計：[にけあり！nikkeari.cc](https://nikkeari.cc/zh-CN)（冠軍競技場對戰紀錄與勝率）、[NIKKE Synergy](https://nikke-synergy.com/arena-ex_en)（逐幀速度計算，有繁中）、[NIKKE DECK](https://nikke-deck.com/en/deck)（含超頻與魔方的組隊工具、PVP 階級、冠軍競技場規則文）。
- 英文：[Prydwen PVP 指南](https://www.prydwen.gg/nikke/guides/pvp-sp-arena-teams)（需用瀏覽器開）、[nikke.gg](https://nikke.gg/)（角色技能與評測）、[Gamemeca 冠軍競技場月報](https://www.gamemeca.com/en/view.php?gid=1775676)。
- 台港澳：[巴哈姆特妮姬板競技場串](https://forum.gamer.com.tw/C.php?bsn=36390&snA=8237)（2026 年的隊伍討論多以圖片與影片呈現，文字版隊伍少）。
- 簡中：[233乐园](https://www.233leyuan.com/post-detail/2069994974744829952)、GameKee（多為影片與圖片，文字版隊伍少）。

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
