#!/usr/bin/env python3
"""把 template.html 與 data/*.json 合併成單一離線 HTML。

用法：
  python build.py            # 用 data/ 內現有資料產生 ../NIKKE-PVP-解隊助手.html
  python build.py --update   # 先從 GitHub 抓最新 characters.json / templates.json 再產生

資料來源：https://github.com/williamchong/nikke-arena-planner （MIT 授權）
"""
import json, sys, datetime, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE.parent / "NIKKE-PVP-解隊助手.html"
INDEX = HERE.parent / "index.html"
RAW = "https://raw.githubusercontent.com/williamchong/nikke-arena-planner/master/app/data/"
FILES = ["characters.json", "templates.json"]


def fetch(name: str) -> bytes:
    req = urllib.request.Request(RAW + name, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def update():
    for name in FILES:
        raw = fetch(name)
        json.loads(raw.decode("utf-8"))  # 先確認是合法 JSON 再覆寫
        (DATA / name).write_bytes(raw)
        print(f"更新 {name}（{len(raw):,} bytes）")
    (DATA / "version.json").write_text(
        json.dumps({"fetched": datetime.date.today().isoformat()}, ensure_ascii=False), encoding="utf-8")


def build():
    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    tpls = json.loads((DATA / "templates.json").read_text(encoding="utf-8"))
    extra_file = DATA / "templates-extra.json"  # 本工具自行補充的模板（獨立嵌入，線上更新上游模板後再合併）
    extra = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else []
    mined_file = DATA / "templates-mined.json"  # 由 mine_templates.py 從冠軍競技場資料挖出的模板
    if mined_file.exists():
        extra = extra + json.loads(mined_file.read_text(encoding="utf-8"))
    community_file = DATA / "templates-community.json"  # 由 community_templates.py 從社群隊伍清單轉成的模板
    if community_file.exists():
        extra = extra + json.loads(community_file.read_text(encoding="utf-8"))
    ver_file = DATA / "version.json"
    ver = json.loads(ver_file.read_text(encoding="utf-8"))["fetched"] if ver_file.exists() else datetime.date.today().isoformat()
    html = (HERE / "template.html").read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    refs_file = HERE.parent / "references.json"
    refs = json.loads(refs_file.read_text(encoding="utf-8")) if refs_file.exists() else {"updated": "", "items": []}
    pry_file = DATA / "prydwen-pvp.json"  # Prydwen PVP 階級（瀏覽器抓取 → prydwen_map.py）
    pry = json.loads(pry_file.read_text(encoding="utf-8")) if pry_file.exists() else {"updated": "", "tiers": {}}
    nick_file = DATA / "nicknames.json"  # 角色綽號（搜尋用）
    nick = json.loads(nick_file.read_text(encoding="utf-8")) if nick_file.exists() else {}
    known = {c["id"] for c in chars}
    nick = {k: v for k, v in nick.items() if k in known and isinstance(v, list)}
    arena_file, deck_file = DATA / "arena-stats.json", DATA / "deck-speed.json"
    arena = json.loads(arena_file.read_text(encoding="utf-8")) if arena_file.exists() else {"teams": [], "beatenBy": {}, "arch": {}, "archVs": {}, "charPos": {}, "names": {}, "rounds": 0}
    deck = json.loads(deck_file.read_text(encoding="utf-8")) if deck_file.exists() else {"units": {}, "quantumLv7": 4.66}
    top_file = DATA / "nikketop.json"  # nikke.top 逐幀充能參數（fetch_nikketop.py）
    top = json.loads(top_file.read_text(encoding="utf-8")) if top_file.exists() else {"units": {}, "keyPoints": []}
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
    if "--update" in sys.argv:
        update()
    build()
