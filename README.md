# NIKKE 競技場解隊助手

以台港澳服（與國際服同資料）為基準的 PVP 競技場輔助工具。輸入對方防守隊的 5 個角色，工具會分析對方的爆裂速度、爆裂鏈、所屬體系與關鍵威脅，再從你的角色庫挑出能克制對方的隊伍。

## 使用方式

線上版（手機也能用）：<https://sakuranoaphrodite.github.io/nikke-pvp-counter/>

1. 或者直接用瀏覽器打開 `NIKKE-PVP-解隊助手.html`（不需要安裝任何東西，離線可用）。
2. 到「我的角色庫」把你擁有的角色點成擁有，資料只存在瀏覽器本機。清單可依「階級」「出場時間」（初次出場日期，來自 NIKKE Synergy）或「衝能速度」排序；衝能速度排的是每位角色一人在所選階段（2RL／2.5RL／3RL／3.5RL／4RL）內充的爆裂能量，數字來自 NIKKE DECK、和該站的「Sort by RL」一致，5 人相加到 100% 的那一階就是隊伍速度；再按一次同一個按鈕會反向。解隊與特殊競技場的選角視窗也有同一組排序按鈕，和角色庫分開記住。
3. 回「解隊」，照對方 P1 到 P5 的順序填入角色，或在快速輸入框直接打中文名，例如 `紅蓮 豺狼 布蘭兒 桑迪 特蕾娜`。
4. 看分析與建議，點「帶入試算」可以再微調自己的隊伍。

頁首的「我方進攻／我方防守」用來切換你是在打別人的防守隊，還是在排自己的防守隊。

- 快速輸入的分隔符可用空格、逗號、頓號、斜線（半形／全形）、直線或加號；「桑迪 珍藏」「海倫 一般」中間有空格也可以。一個詞只對一個角色，不會把一個詞拆成多人；「偶阿」「白重」這類取字首的簡稱也認得。每隊旁邊和每張推薦卡都有「複製」按鈕，複製成「名字／名字／…」文字，貼回快速輸入即可還原。

## 冠軍競技場實戰數據與進階速度設定

- 速度預設採用 [nikke.top](https://nikke.top/)（NIKKE Arena Tools）的逐幀模擬：60 fps，每位角色依武器有固定射擊節奏（火箭筒一輪 76 幀＝1.267 秒），每次命中充能「基礎充能 × 命中倍率」，全隊累積到 100% 那一幀就是「充滿」，之後 B1 +24 幀、B2／B3 各 +32 幀。本工具把該站前端的計算移植進來（含 23 位特殊節奏角色，2026-11-06 補上紅蓮:神殺與長髮公主:聖域、超級巨星阿妮斯被動、紅蓮反擊回充、超頻 17%、量子魔方；不含豺狼連結回充與小紅帽穿透），結果與該站逐幀一致。解隊分頁的「充能時間軸」畫出兩隊的累積充能曲線、1RL～5RL 與暈眩等關鍵時間點、各段爆裂啟動時間，並寫出充滿秒數、等於幾 RL、比 2RL 快或慢多少、兩隊差幾幀，讓 2RL 以下的隊伍也看得出實際多快。參數由 `python build/fetch_nikketop.py` 抓進 `build/data/nikketop.json`（`--refresh` 重抓）。
- 頁首可切換成 nikke-deck.com 的每階充能資料與公式（含技能 10 預設版本、超頻 17% 版本、量子魔方、超級巨星阿妮斯的每擊加成），結果與該站一致；頁首可切換回 nikke-arena-planner 的資料。公式來源：nikke-deck 前端 `app-deck-details.getBurstGeneration`。

- `build/fetch_arena_stats.py` 會從 [にけあり！NIKKE 競技場分析器](https://nikkeari.cc/zh-CN) 的公開 API 抓冠軍競技場的對戰紀錄（JP／KR／國際服，每回合含進攻隊、防守隊與勝方），整理成 `build/data/arena-stats.json`：每個 5 人組合的場次、勝率、進攻／防守勝率、被哪些隊伍打贏過、含某核心角的隊伍整體勝率、角色常用站位。工具會在「對方分析」顯示這隊（或 4 人相同的相近隊）的實戰戰績，在「解法建議」列出實戰中打贏過它的隊伍並可一鍵帶入。判斷勝負時另有「直接對位」：含我方 4 位（不足 20 場放寬到 3 位）相同角色的隊伍對上含對方 4 位（或 3 位）相同角色的隊伍的實戰勝負，珍藏與一般版視為同一人；它和模板寫的克制關係衝突時以實戰為準（例如「娜由塔一閃」模板宣稱克制布蘭兒不屈隊，但對超級巨星阿妮斯＋布蘭兒隊實戰只有約三成，工具就不再給克制加分）。
- 同一支腳本也會抓 [NIKKE DECK](https://nikke-deck.com/en/deck) 的 `data.json`，整理成 `build/data/deck-speed.json`：哪些角色有「充能速度 17%」超頻選項、量子魔方 Lv7 的充能加成，以及它的 PVP 階級（在角色旁以「deck」標籤顯示，作為第二份獨立評價）。
- 「進階」區可以勾選對方或我方角色的超頻 17%／量子魔方 Lv7，速度判定會隨之改變；模型與數值來自 nikke-deck 與 NIKKE Synergy 的機制文章，是估算值。
- 更新：`python build/fetch_arena_stats.py --refresh`（原始回應存在 `build/data/raw/`，不進倉庫），再執行 `python build/build.py`。請勿高頻呼叫對方的 API。

## 特殊競技場（15v15）

「特殊競技場」分頁處理三隊對戰：雙方各擺三隊，我方第 1 隊打對方第 1 隊、第 2 隊打第 2 隊、第 3 隊打第 3 隊，贏兩場即勝，我方三隊角色不可重複。

1. 填入對方三隊（各 5 人，支援一次選整隊與簡稱；三隊間角色不可重複，選角視窗會停用已在其他隊的角色），每隊下方顯示速度階、體系、爆裂鏈、軸外關鍵角與冠軍競技場戰績。
   - 候選隊依估計勝率排序再截斷（每場 8／5／4 名），你手動填的三隊也會一起當候選，推薦不會輸給你的手動組合；手動三隊比推薦高時會提示。推薦仍只搜尋模板組合，不是所有 5 人組合的全域最佳解。
   - 組法可切換：兩勝機率最高（預設）、期望勝場最高、三場求穩（最弱一場勝率最高、不放生）、放生一場、速度優先；每種都標出兩勝機率與預期勝場，從同一批三隊組合裡依不同目標挑。
   - 「③ 我方三隊（手動）」可自己填三隊（選角、快速輸入、自動排軸，三隊角色不重複），每隊顯示對上對方同號隊伍的完整判斷；「把上面的推薦帶入」可拿推薦當底稿修改；「自動配對」會嘗試 6 種出場順序，依兩勝機率重排我方三隊。「儲存這組三隊」會連同當時的對方三隊存起來，之後可載入我方或雙方。
   - 「三隊存到歷史」把對方三隊存成一筆歷史（點擊載入、Shift 點擊刪除），三隊也各自進解隊分頁的對方隊伍歷史；匯出 JSON 會一併帶走特殊競技場的歷史、儲存三隊與紀錄。
   - 「④ 特殊競技場紀錄」記下每場勝負；每一場也會寫進解隊分頁的「對戰紀錄」（標示「特殊」），之後同樣的對手與隊伍會顯示你的戰績並用它估勝率。
2. 工具對每一場先用解隊的反制邏輯挑候選隊，再在六種場次順序下做組合搜尋，確保角色不重複，以「至少兩勝的估計機率」排序。某一場怎麼配都劣勢時自動放生：那場派剩餘角色中最強、爆裂鏈完整的組合（自動排軸），反制核心留給另外兩場。
3. 每場的判斷與解隊分頁共用同一套 `evalMatch`（克制、速度、軸、再入、鏡像、實戰數據、站位檢查）；機率粗估為優勢 75%、五五波 50%、劣勢 25%、湊數隊最高 35%，自己對該對手打過兩場以上時改用對戰紀錄。
4. 每場可「帶入試算」到解隊分頁微調。我方角色的超頻／量子魔方設定沿用解隊分頁的進階設定。

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

## 把角色庫放到 GitHub，換裝置時一鍵載入

角色庫與對戰紀錄只存在各自的瀏覽器本機，不同裝置不互通，任何人第一次打開網頁都是空白的。若想在別的裝置一鍵拿回自己的資料：

1. 在「我的角色庫」按「匯出 JSON」，下載 `roster.json`。
2. 把 `roster.json` 放到專案根目錄（與 `index.html` 同層），commit 後 push。
3. 網頁不會自動讀取這份檔案。到「我的角色庫」按「從 GitHub 載入資料」：角色庫換成倉庫的版本，對戰紀錄、對方隊伍歷史、儲存隊伍與特殊競技場資料一律「合併」進本機（只加入本機沒有的，不刪除、不覆蓋）。想以倉庫或檔案內容完整取代本機資料（還原備份），改按「從 GitHub 完整取代」或「匯入並取代」，會先問一次。

`roster.json` 格式：`{"exported":"2026-10-28","owned":["scarlet","jackal"],"history":[],"records":[],"mySaved":[],"spHistory":[],"spSaved":[],"spRecords":[]}`，`owned` 放角色 id（與 `build/data/characters.json` 的 `id` 相同）；其餘欄位依序是對方隊伍歷史、對戰紀錄、儲存的我方隊伍、特殊競技場的對方三隊歷史、儲存三隊與紀錄，直接用「匯出 JSON」產生即可。對戰紀錄每筆為 `{"date","mode":"attack"|"defense"|"sp","enemy":[5 個 id],"mine":[5 個 id],"result":"win"|"loss","note"}`。

## 檔案結構

| 路徑 | 內容 |
| --- | --- |
| `NIKKE-PVP-解隊助手.html` | 成品，單一檔案 |
| `build/template.html` | 頁面原始碼，含解法規則與威脅標籤 |
| `build/build.py` | 建置腳本：`--update` 抓上游、nikke-deck、nikke.top 並合併角色庫後嵌進頁面；`--merge` 只用快取重新合併 |
| `build/nikkedeck.py` | NIKKE DECK 的 `data.json`：下載、對應角色 id、產生 `deck-speed.json`、把上游沒收錄的 SSR 轉成本工具的角色格式 |
| `build/synergy.py`、`build/synergy_export.js` | NIKKE Synergy 的角色表：瀏覽器 Console 匯出腳本，與把匯出檔對應到角色 id（出場日期、繁中譯名） |
| `build/data/characters.json` | 213 名角色資料、繁中譯名、充能數值、PVP 階級、出場日期（上游 209 名＋nikke-deck 補的 4 名，補的角色有 `source` 欄位） |
| `build/data/synergy-raw.json` | NIKKE Synergy 的角色表匯出檔（227 名，含珍藏版與 R／SR）與譯名表，由 `synergy_export.js` 在瀏覽器產生 |
| `build/data/templates.json` | 上游的 23 個主流隊伍模板與互剋關係 |
| `build/data/templates-extra.json` | 本工具補充的 2026 體系模板（超級巨星阿妮斯＋餅乾核心、娜由塔一閃、豺狼＋貝斯蒂不屈、諾雅諾伊斯餅乾灰姑娘），獨立嵌入，線上更新上游模板後仍會合併 |
| `build/data/templates-mined.json` | `build/mine_templates.py` 從 nikkeari 的 24,000 回合挖出的 24 個核心家族：場次、勝率、常見補位、站位、互剋（統計結果，非人工驗證） |
| `build/data/community-teams.json` | 社群明確列出的新人／特殊競技場隊伍（JP wikiwiki、GameWith、Yahoo知恵袋、KR arca／dcinside／ruliweb、Gamemeca，2025-07～2026-10），含來源、日期、站位、速度、打得贏與輸給誰 |
| `build/data/templates-community.json` | `build/community_templates.py` 把上面的隊伍轉成的 36 個模板（名稱標「（社群）」） |
| `build/data/prydwen-raw.json` → `prydwen-pvp.json` | Prydwen 的 PVP 階級表（2026-10-12）。Prydwen 擋程式抓取，raw 檔是用瀏覽器開 PVP 分頁整理的，`prydwen_map.py` 對應成角色 id。頁面以它為角色的 PVP 階級（上游 arena-planner 的 pvpTier 本來就是各角色加入時抄 Prydwen 的，但沒跟著更新；舊值顯示為「planner X」） |
| `build/data/nicknames.json` | 角色綽號／別名（白兔、黑兔、偶像阿妮斯、白雪重武、EMT…），搜尋時與正式名一起比對，可自行增補 |
| `avatars/` | 角色頭像（`build/fetch_avatars.py` 從上游倉庫下載，檔名為角色的 avatarImg 代碼）。圖片為遊戲素材，版權屬 SHIFT UP／Level Infinite，僅作粉絲工具展示 |

資料挖掘模板除了核心角與站位，還記錄這些對局裡「實際開爆裂的核心角」比例（chainRate／chainCore）：例如桑迪珍藏＋拉普拉斯究極英雄＋特蕾娜那一家，77% 的場次由特蕾娜開 B2、桑迪只有 14%，所以只有特蕾娜在軸內時才算這個體系、才套用它的克制統計；桑迪排在前面搶了 B2 時工具會提醒。克制行會附上對位場數與勝率（例如「311 場、我方勝率 82%」）。

arena-stats.json 的每個隊伍另記錄「實際開爆裂的三位」的場次分布，直接對位會依你的排法（誰開 B2／B3）加權；贏點摘要的「開誰的爆裂」會比較同一隊改由另一位開 B2／B3 時的實戰結果，沒有資料時寫明。每張推薦卡、特殊競技場卡與我方隊伍判斷的最上方有「贏點」摘要：優勢來自哪裡（速度先手、克制、後手鏡像、同型隊實戰勝率）、軸怎麼開（誰開 B1／B2／B3、誰軸外、各自靠什麼）、實戰撐住的是哪幾位（相似隊裡含她的場次百分比）、哪些成員在相似隊裡很少出現因此未驗證。

所有模板寫的克制／被克制關係，工具在使用前都會先拿實戰驗證：找「含我方體系核心角的隊」對上「含對方體系核心角的隊」的勝負（30 場以上才算），實戰相反的宣稱不採用並在判斷依據說明，五五波的不加分，支持的會附上場數。`build/audit_counters.py` 可離線列出所有與實戰相反的宣稱（2026-10-21：298 條可驗證的宣稱中有 44 條相反）。

模板分四層：上游模板、本工具補充、資料挖掘、社群隊伍；更新流程是 `fetch_arena_stats.py --refresh` → `mine_templates.py` → `community_templates.py` → `build.py`。社群隊伍要新增時直接在 `community-teams.json` 加一筆再跑轉換。社群來源沒給站位的隊伍，轉換時會依序用「冠軍競技場同樣 5 人最常用的排法」→「各角色最常站的位置」→ 粗排來決定順序，說明文字會標示用了哪一種。

## 哪裡可以找到這類隊伍資料與討論

- 日本：[wikiwiki（NIKKE）アリーナ攻略](https://wikiwiki.jp/fpo2w6pt/（NIKKE）アリーナ攻略)（隊伍、互剋、新手三隊範本，更新最勤）、[GameWith 競技場](https://gamewith.jp/nikke/article/show/379079)、[Yahoo!知恵袋](https://chiebukuro.yahoo.co.jp/)（搜「NIKKE アリーナ」有大量「這隊怎麼打」問答）。
- 韓國：[arca.live 니케 채널](https://arca.live/b/nikketgv)（特殊競技場體系整理、新手配法）、[dcinside 니케 갤러리](https://gall.dcinside.com/mgallery/board/lists/?id=gov)（冠軍競技場環境文、新手攻守指南）、[ruliweb](https://bbs.ruliweb.com/game/86188)。
- 資料統計：[にけあり！nikkeari.cc](https://nikkeari.cc/zh-CN)（冠軍競技場對戰紀錄與勝率）、[NIKKE Synergy](https://nikke-synergy.com/arena-ex_en)（逐幀速度計算，有繁中）、[NIKKE DECK](https://nikke-deck.com/en/deck)（含超頻與魔方的組隊工具、PVP 階級、冠軍競技場規則文）。
- 英文：[Prydwen PVP 指南](https://www.prydwen.gg/nikke/guides/pvp-sp-arena-teams)（需用瀏覽器開）、[nikke.gg](https://nikke.gg/)（角色技能與評測）、[Gamemeca 冠軍競技場月報](https://www.gamemeca.com/en/view.php?gid=1775676)。
- 台港澳：[巴哈姆特妮姬板競技場串](https://forum.gamer.com.tw/C.php?bsn=36390&snA=8237)（2026 年的隊伍討論多以圖片與影片呈現，文字版隊伍少）。
- 簡中：[233乐园](https://www.233leyuan.com/post-detail/2069994974744829952)、GameKee（多為影片與圖片，文字版隊伍少）。

## 新角色出來怎麼辦

角色庫的基底是上游 [NIKKE Arena Planner](https://github.com/williamchong/nikke-arena-planner) 的 `characters.json`（各模板、威脅標籤、綽號、實戰數據都用它的角色 id），但上游 2026-10 之後沒再更新，所以 `build.py --update` 現在會合併三個來源：

| 來源 | 提供什麼 | 怎麼抓 |
| --- | --- | --- |
| NIKKE Arena Planner（GitHub） | 角色基底、模板 | 自動 |
| [NIKKE DECK](https://nikke-deck.com/en/deck) `data.json` | 上游沒收錄的新 SSR（武器、爆裂、職業、企業、屬性、每階充能、PVP 階級）；所有角色的每階充能與超頻 17% 版本 | 自動 |
| [NIKKE Synergy](https://nikke-synergy.com/index_en) 角色表 | 每位角色的初次出場日期（珍藏版以珍藏品實裝日計）、新角色的繁中譯名、彈藥／裝填／蓄力 | 該站擋程式抓取，要用瀏覽器匯出（下面） |
| [nikke.top](https://nikke.top/) | 逐幀充能參數 | 自動（`fetch_nikketop.py`） |

更新方式：

1. **自動**：每天第一次打開 HTML 時，若有網路，會向本專案的 GitHub 倉庫抓合併後的 `build/data/characters.json` 與 `templates.json`，暫存在瀏覽器並立即套用（線上資料比內建少時不套用）。頁首會顯示資料來源（內建／快取／線上）與日期，也有「檢查更新」按鈕可手動觸發。
2. **半自動**：雙擊 `更新資料.bat`，或執行下面的指令，會抓上游、nikke-deck 與 nikke.top、合併角色庫、寫回 `build/data/` 並重新產生成品 HTML，離線時也會有新角色：

```bash
python build/build.py --update
```

   nikke-deck 補進來的角色會標「新」，繁中名與出場日期取自 `synergy-raw.json`；兩邊都沒有繁中名的角色（例如剛公布、譯名表還沒更新的）可在 `build.py` 的 `NAME_FIX` 手動補，綽號在 `nicknames.json` 補。新角色的頭像上游沒有，執行 `python build/fetch_avatars.py` 會依 `characters.json` 記的 nikke-synergy 角色圖網址下載到 `avatars/`。
3. **更新出場日期（nikke-synergy）**：用瀏覽器打開 <https://nikke-synergy.com/index_en>，按 F12 打開 Console，把 `build/synergy_export.js` 整個貼進去執行，會下載 `synergy-raw.json`（網站前端已載入到瀏覽器裡的角色表與譯名表，不含技能文字與圖片）；放到 `build/data/` 後執行：

```bash
python build/build.py --merge
```

   `--merge` 不重抓上游與 nikke-deck（用 `build/data/raw/` 的快取），只重新合併角色庫再產生 HTML。沒有 `synergy-raw.json` 時一切照常，只是角色沒有出場日期、排序退回上游的 `releaseOrder`。
4. **手動**：可直接編輯 `build/data/characters.json` 新增角色（照既有格式填爆裂類型、武器與各速度階的充能值），再執行 `python build/build.py`；但 `--update`／`--merge` 會從上游快取重新合併，手動加的角色要放進 `templates-extra.json` 那類獨立檔案才不會被蓋掉。

nikke-deck 補的角色，充能數值直接用該站的 2RL～4RL 五階；1RL、1.5RL 與 5RL 是推算值（1RL 取 2RL 的一半、5RL 以 3RL→4RL 的增量外推），記在 `burstGenSource` 欄位。速度計算預設走 nikke.top 的逐幀模擬，該站有收錄的新角色不受這個推算影響。

威脅標籤（`UNIT_TAGS`）、體系中文名（`ARCH_NAME`）與解法規則（`RULES`）在 `build/template.html` 內，是本工具自行整理的知識層，新角色或新體系需要手動補；沒補的角色會顯示為「一般角色」，不影響速度計算。

## 資料來源與授權

角色資料、充能數值與隊伍模板取自開源專案 [NIKKE Arena Planner](https://github.com/williamchong/nikke-arena-planner)（MIT 授權，授權書在 `build/data/LICENSE-nikke-arena-planner.txt`）。該專案的數據整理自 nikke.gg、Prydwen 與左猫猫的充能計算表。該專案沒收錄的新角色由 [NIKKE DECK](https://nikke-deck.com/en/deck) 的資料檔補入（每階充能、武器、爆裂、職業、PVP 階級），角色的出場日期與新角色的繁中譯名來自 [NIKKE Synergy](https://nikke-synergy.com/index_en) 的角色表（用瀏覽器匯出，只取角色基本欄位與譯名，不含技能文字與圖片）；兩者都是粉絲站，本工具只做讀取與換算，請勿高頻抓取。解法規則與威脅標籤由本工具自行整理，僅供參考。本工具為非官方粉絲工具，與 Shift Up、Level Infinite 無關。
