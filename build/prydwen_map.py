#!/usr/bin/env python3
"""把 Prydwen PVP 階級表（data/prydwen-raw.json，從瀏覽器抓的英文名清單）對應成本工具的角色 id → data/prydwen-pvp.json。
Prydwen 擋程式抓取，所以 raw 檔是用瀏覽器開 https://www.prydwen.gg/nikke/tier-list/ 的 PVP 分頁整理的；更新時換掉 raw 檔再跑本腳本。
同一角色出現多次（小紅帽 B1/B2/B3、拉毗小紅帽）取最高的那個。"""
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
DATA = Path(__file__).resolve().parent / "data"
RANK = {"SSS": 8, "SS": 7, "S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
norm = lambda s: re.sub(r"[\s:：'’\.\-_()（）]", "", s).lower()
chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
by_en = {}
for c in chars:
    by_en.setdefault(norm(c["name"]["en"]), c["id"])
raw = json.loads((DATA / "prydwen-raw.json").read_text(encoding="utf-8"))
out, unmapped = {}, []
for tier, names in raw["lists"].items():
    for n in names:
        if n == "NEW":
            continue
        ALIAS = {"Ada Wong": "Ada", "Mari Makinami Illustrious": "Mari", "Chisato Nishikigi": "Chisato", "Queen (Makoto Niijima)": "Queen",
                 "Takina Inoue": "Takina", "Yukiko Amagi": "Yukiko", "Jill Valentine": "Jill", "Misato Katsuragi": "Misato",
                 "Asuka Shikinami Langley": "Asuka", "Asuka Shikinami Langley: Wille": "Asuka: WILLE"}
        n = ALIAS.get(n, n)
        base = re.sub(r"\s*\(Treasure\)", "", n)
        base = re.sub(r"^Red Hood B[123]$", "Red Hood", base)
        mid = by_en.get(norm(base))
        if mid and "(Treasure)" in n:
            mid = mid + "-treasure" if any(c["id"] == mid + "-treasure" for c in chars) else None
        if not mid:
            unmapped.append(n); continue
        if mid not in out or RANK[tier] > RANK[out[mid]]:
            out[mid] = tier
(DATA / "prydwen-pvp.json").write_text(json.dumps({"updated": raw["updated"], "source": raw["source"], "tiers": out}, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"對應 {len(out)} 名，未對應 {len(unmapped)}：{unmapped}")
