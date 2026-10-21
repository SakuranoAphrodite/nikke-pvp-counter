#!/usr/bin/env python3
"""把 build/data/community-teams.json（社群明確列出的隊伍）轉成模板 build/data/templates-community.json。

規則：
- 英文名對應到 characters.json 的 id；對不到的角色整隊略過並列出。
- required = 階級最高的 2～3 位（SSS/SS 優先），其餘為彈性位，人選只放原角色，缺角時由工具的替補機制處理。
- burstSlots 依來源順序；來源沒給順序時依「坦 P1/P5、火力 P3/P4」粗排。
- preferredSpeed 由來源速度換算（2.5RL→5SG、3.5RL→7SG、unknown→3RL）。
- 模板名稱標示（社群）與來源站，notes 保留原文摘要與打得贏／輸給誰。
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TIER = {"SSS": 8, "SS": 7, "S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
SPEED = {"2RL": "2RL", "2.5RL": "5SG", "3RL": "3RL", "3.5RL": "7SG", "4RL": "4RL", "5RL": "5RL", "unknown": "3RL"}
ALIAS = {"helm": "helm", "siren": "siren", "mihara": "mihara-bonding-chain", "anis": "anis", "centi": "centi", "soda": "soda", "drake": "drake", "moran": "moran", "bay": "bay"}


def norm(s):
    return re.sub(r"[\s:：・･·\-_＋+()（）]", "", s or "").lower()


def host(url):
    m = re.search(r"https?://([^/]+)/", url + "/")
    h = m.group(1) if m else ""
    return {"wikiwiki.jp": "JP wikiwiki", "gamewith.jp": "GameWith", "arca.live": "KR arca", "gall.dcinside.com": "KR dcinside",
            "detail.chiebukuro.yahoo.co.jp": "Yahoo知恵袋", "bbs.ruliweb.com": "KR ruliweb", "www.gamemeca.com": "Gamemeca", "videmoss.com": "videmoss"}.get(h, h)


def main():
    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in chars}
    by_en = {}
    for c in chars:
        by_en[norm(c["name"]["en"])] = c["id"]
    src = json.loads((DATA / "community-teams.json").read_text(encoding="utf-8"))
    out, skipped = [], []
    for n, t in enumerate(src["teams"]):
        ids = []
        for u in t["units"]:
            key = norm(u)
            mid = ALIAS.get(key) or by_en.get(key)
            if not mid and key.endswith("treasure"):
                base = by_en.get(key[:-8])
                if base and base + "-treasure" in by_id:
                    mid = base + "-treasure"
            if not mid or mid not in by_id:
                ids = None; skipped.append((n, u)); break
            ids.append(mid)
        if not ids:
            continue
        if not t.get("ordered"):
            tank = lambda i: by_id[i]["role"] == "defender"
            atk = lambda i: by_id[i]["role"] == "attacker"
            order = [i for i in ids if tank(i)][:1] + [i for i in ids if not tank(i) and not atk(i)] + [i for i in ids if atk(i)] + [i for i in ids if tank(i)][1:]
            seen = set(); ids = [i for i in order if not (i in seen or seen.add(i))]
            if len(ids) == 5 and tank(ids[-1]) is False and sum(tank(i) for i in ids) >= 2:
                pass
        ranked = sorted(ids, key=lambda i: -TIER.get(by_id[i].get("pvpTier"), 0))
        required = ranked[:3] if TIER.get(by_id[ranked[2]].get("pvpTier"), 0) >= 6 else ranked[:2]
        flex = [{"slot": p, "options": [i]} for p, i in enumerate(ids) if i not in required]
        # required 的位置：非 flex 的位置依 ids 順序
        req_slots = [p for p in range(5) if ids[p] in required]
        required_ordered = [ids[p] for p in req_slots]
        zh = "／".join(by_id[i]["name"]["zh-TW"] for i in ids)
        arena = {"rookie": "新人競技場", "special": "特殊競技場", "champion": "冠軍競技場", "any": "通用"}.get(t.get("arena"), "")
        notes_zh = f"{arena}・{host(t['source'])}（{t.get('date','')}）：{t.get('role','')}"
        if t.get("beats"): notes_zh += f"｜打得贏：{'、'.join(t['beats'])}"
        if t.get("losesTo"): notes_zh += f"｜輸給：{'、'.join(t['losesTo'])}"
        if not t.get("ordered"): notes_zh += "｜來源未給站位，順序為工具粗排"
        out.append({
            "id": f"community-{n}",
            "name": {"en": f"{' / '.join(by_id[i]['name']['en'] for i in ids)} (community)", "zh-TW": f"{zh}（社群）", "zh-CN": f"{zh}（社群）", "ja": f"{zh}（コミュニティ）"},
            "archetype": f"community-{n}",
            "mode": t.get("mode", "both"),
            "arena": t.get("arena", "any"),
            "required": required_ordered,
            "flex": flex,
            "burstSlots": [by_id[i]["burst"] for i in ids],
            "preferredSpeed": SPEED.get(t.get("speed", "unknown"), "3RL"),
            "counters": [], "counteredBy": [],
            "priority": 2,
            "source": t["source"], "date": t.get("date", ""),
            "notes": {"en": t.get("role", ""), "zh-TW": notes_zh, "zh-CN": notes_zh, "ja": notes_zh},
        })
    (DATA / "templates-community.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"社群模板 {len(out)}，略過 {len(skipped)}：{skipped}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
