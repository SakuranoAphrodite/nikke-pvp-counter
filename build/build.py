#!/usr/bin/env python3
"""把 template.html 與 data/*.json 合併成單一離線 HTML。

用法：
  python build.py            # 用 data/ 內現有資料產生 ../NIKKE-PVP-解隊助手.html 與 ../index.html
  python build.py --update   # 先抓最新資料、合併角色庫，再產生：
                             #   1. GitHub 上游 nikke-arena-planner 的 characters.json / templates.json（MIT）
                             #   2. nikke-deck.com 的 data.json：上游還沒收錄的新角色由它補進角色庫（充能數值、武器、爆裂…），並產生 deck-speed.json
                             #   3. data/synergy-raw.json（nikke-synergy.com，用瀏覽器匯出，見 synergy.py）：每位角色的出場日期與繁中譯名
                             #   4. nikke.top 的逐幀充能參數（fetch_nikketop.py --refresh）
  python build.py --merge    # 不重抓上游與 nikke-deck（用 data/raw/ 的快取），只重新合併角色庫再產生；
                             # 例如剛換了新的 synergy-raw.json 時用這個

角色庫 = 上游 characters.json（基底，id 與各模板、標籤、綽號相通）＋ nikke-deck 補的新角色 ＋ nikke-synergy 的出場日期。
"""
import json, re, sys, datetime, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nikkedeck, synergy

DATA = HERE / "data"
RAW = DATA / "raw"
OUT = HERE.parent / "NIKKE-PVP-解隊助手.html"
INDEX = HERE.parent / "index.html"
UPSTREAM = "https://raw.githubusercontent.com/williamchong/nikke-arena-planner/master/app/data/"
FILES = ["characters.json", "templates.json"]
# 上游與 nikke-synergy 都沒有繁中名時的手動補充（key 為本工具 id）
NAME_FIX = {
    "scarlet-goddeath": {"zh-TW": "紅蓮:神殺", "zh-CN": "红莲:神杀"},
}


def fetch(name):
    req = urllib.request.Request(UPSTREAM + name, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def read_json(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def update():
    """抓上游的 characters.json（存到 raw/ 當合併基底）與 templates.json，再合併角色庫。"""
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        raw = fetch(name)
        json.loads(raw.decode("utf-8"))  # 先確認是合法 JSON 再覆寫
        dest = RAW / ("upstream_" + name) if name == "characters.json" else DATA / name
        dest.write_bytes(raw)
        print(f"更新 {name}（{len(raw):,} bytes）← {UPSTREAM}")
    merge(refresh=True)


def merge_characters(upstream, deck, syn):
    """回傳 (chars, added, unmapped_synergy)：先把 nikke-deck 有而上游沒有的 SSR 補進來，再用 nikke-synergy 給每位角色出場日期。"""
    chars = [dict(c) for c in upstream]
    by_id = {c["id"]: c for c in chars}
    added, non_ssr = [], set()
    if deck:
        dfind = nikkedeck.matcher(chars)
        syn_lookup = synergy.by_deck_name(syn)
        for n in deck["nikkes"]:
            mid = dfind(n)
            if mid:
                by_id[mid]["deckId"] = n["id"]
                continue
            en = n["name"]["en"]
            if n.get("rarity") != 1:  # 只補 SSR；R／SR 角色上游本來就不收
                non_ssr.add(nikkedeck.norm(en))
                continue
            treasure = bool(n.get("treasure")) or en.endswith(" +")
            base = en[:-2].strip() if en.endswith(" +") else en
            rec = nikkedeck.to_character(n, 0, syn_lookup.get((nikkedeck.norm(base), treasure)))
            if rec["id"] in by_id:  # id 撞到既有角色（英文名略有不同）：不新增，改在 nikkedeck.ALIAS 補對照
                print(f"  略過 nikke-deck {n['id']} {en}：id {rec['id']} 已存在")
                continue
            for k, v in NAME_FIX.get(rec["id"], {}).items():
                rec["name"][k] = v
            added.append(rec)
            by_id[rec["id"]] = rec
        chars += added
    unmapped = []
    if syn:
        find = synergy.matcher(chars)
        for r in syn["rows"]:
            mid = find(r)
            if not mid:
                if nikkedeck.norm(synergy.base_en(r)) not in non_ssr:
                    unmapped.append(r)
                continue
            c = by_id[mid]
            if r.get("releaseDate"):
                c["releaseDate"] = r["releaseDate"]
            c["synergyName"] = r["name"]
            if c.get("source") and not c.get("avatarFile") and r.get("image_public_url"):  # 譯名表還沒有的新角色（例如剛公布的），頭像在這裡補
                c["avatarUrl"] = r["image_public_url"]
                ext = re.search(r"\.(png|jpe?g|webp)(?:\?|$)", r["image_public_url"], re.I)
                c["avatarFile"] = c["id"] + "." + (ext.group(1).lower() if ext else "png")
    if added:  # 補進來的角色排在上游之後，依出場日期給 releaseOrder
        base_order = max((c.get("releaseOrder") or 0) for c in upstream) if upstream else 0
        added.sort(key=lambda c: (c.get("releaseDate") or "9999-99-99", c["name"]["en"]))
        for i, c in enumerate(added):
            c["releaseOrder"] = base_order + 1 + i
    return chars, added, unmapped


def merge(refresh=False):
    up_file = RAW / "upstream_characters.json"
    if up_file.exists():
        upstream = read_json(up_file)
    else:  # 沒有上游快取（例如剛 clone）：以現有角色庫裡非本工具補進的角色為底
        upstream = [c for c in read_json(DATA / "characters.json", []) if not c.get("source")]
        print("沒有 data/raw/upstream_characters.json，以現有 characters.json 為合併基底")
    try:
        deck = nikkedeck.fetch(refresh)
    except Exception as e:
        print("nikke-deck 抓取失敗，這次不補新角色：", e)
        deck = read_json(RAW / "deck_data.json")
    syn = synergy.load()
    if not syn:
        print("沒有 data/synergy-raw.json：角色不會有出場日期。匯出方法見 build/synergy.py 開頭說明")
    chars, added, unmapped = merge_characters(upstream, deck, syn)
    (DATA / "characters.json").write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dated = sum(1 for c in chars if c.get("releaseDate"))
    print(f"角色庫：上游 {len(upstream)} 名 + nikke-deck 補 {len(added)} 名 = {len(chars)} 名，{dated} 名有出場日期"
          + (f"（synergy 匯出於 {syn['exported']}）" if syn else ""))
    if added:
        print("  新增：" + "、".join(f"{c['name']['zh-TW']}（{c['name']['en']}，{c.get('releaseDate') or '日期不明'}）" for c in added))
    if unmapped:
        print("  synergy 對不到的角色（可在 synergy.py 的 OVERRIDE 補）：" + "、".join(f"{r['name']}={r.get('en') or '?'}" for r in unmapped))
    if deck:
        nikkedeck.write_speed(deck, chars)
    ver = read_json(DATA / "version.json", {})
    today = datetime.date.today().isoformat()
    ver.update({"fetched": today, "deck": (deck or {}).get("lastUpdated"), "synergy": (syn or {}).get("exported")})
    if refresh:
        ver["planner"] = today
    (DATA / "version.json").write_text(json.dumps(ver, ensure_ascii=False), encoding="utf-8")
    try:  # nikke.top 的逐幀參數要在角色庫合併後才能把新角色對上
        import fetch_nikketop
        fetch_nikketop.main(refresh)
    except Exception as e:
        print("nikke.top 更新失敗（速度計算會退回 nikke-deck／arena-planner 的數值）：", e)


def build():
    chars = read_json(DATA / "characters.json")
    tpls = read_json(DATA / "templates.json")
    extra = read_json(DATA / "templates-extra.json", [])  # 本工具自行補充的模板（獨立嵌入，線上更新上游模板後再合併）
    extra = extra + read_json(DATA / "templates-mined.json", [])  # 由 mine_templates.py 從冠軍競技場資料挖出的模板
    extra = extra + read_json(DATA / "templates-community.json", [])  # 由 community_templates.py 從社群隊伍清單轉成的模板
    ver = read_json(DATA / "version.json", {}).get("fetched") or datetime.date.today().isoformat()
    html = (HERE / "template.html").read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    refs = read_json(HERE.parent / "references.json", {"updated": "", "items": []})
    pry = read_json(DATA / "prydwen-pvp.json", {"updated": "", "tiers": {}})  # Prydwen PVP 階級（瀏覽器抓取 → prydwen_map.py）
    nick = read_json(DATA / "nicknames.json", {})  # 角色綽號（搜尋用）
    known = {c["id"] for c in chars}
    nick = {k: v for k, v in nick.items() if k in known and isinstance(v, list)}
    arena = read_json(DATA / "arena-stats.json", {"teams": [], "beatenBy": {}, "arch": {}, "archVs": {}, "charPos": {}, "names": {}, "rounds": 0})
    deck = read_json(DATA / "deck-speed.json", {"units": {}, "quantumLv7": 4.66})
    top = read_json(DATA / "nikketop.json", {"units": {}, "keyPoints": []})  # nikke.top 逐幀充能參數（fetch_nikketop.py）
    top.pop("unmatched", None)
    html = (html.replace("__CHARACTERS__", dump(chars))
                .replace("__TEMPLATES__", dump(tpls))
                .replace("__TEMPLATES_EXTRA__", dump(extra))
                .replace("__REFERENCES__", dump(refs))
                .replace("__NICKNAMES__", dump(nick))
                .replace("__PRYDWEN__", dump(pry))
                .replace("__ARENA__", dump(arena))
                .replace("__DECK__", dump(deck))
                .replace("__NIKKETOP__", dump(top))
                .replace("__DATA_DATE__", ver))
    OUT.write_text(html, encoding="utf-8")
    INDEX.write_text(html, encoding="utf-8")  # GitHub Pages 用的同內容副本
    print(f"已產生 {OUT} 與 {INDEX.name}（{OUT.stat().st_size:,} bytes，{len(chars)} 名角色，{len(tpls)}+{len(extra)} 個模板，資料日期 {ver}）")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--update" in sys.argv:
        update()
    elif "--merge" in sys.argv:
        merge(refresh=False)
    build()
