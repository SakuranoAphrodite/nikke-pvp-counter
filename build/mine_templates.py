#!/usr/bin/env python3
"""從 nikkeari 的冠軍競技場回合資料「挖」隊伍模板。

做法：
1. 讀 build/data/raw/ari_matchups_*.json（需先跑 fetch_arena_stats.py），把每回合的雙方隊伍對應成本工具 id（含珍藏）。
2. 找出場次多、勝率高的「核心組合」（2～3 人同時出現），以核心代表一個體系。
3. 對每個核心：統計其餘位置最常搭配的角色（彈性位人選）、每位角色最常站的位置（burstSlots 與站位）、
   以及核心之間的對位勝負（counters / counteredBy）。
4. 輸出 build/data/templates-mined.json，格式與上游 templates.json 相同，archetype 以 "mined-" 開頭。

這些模板是統計結果，不是人工驗證的打法；名稱會標示「（資料挖掘）」。
"""
import json, re, sys, itertools, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
MIN_MATCHES = 80       # 核心至少出場回合數
MIN_WIN = 0.56         # 核心整體勝率下限
MAX_TEMPLATES = 24
TREASURE_ALIAS = {"laplace": "laplace-ultimate-hero"}


def norm(s):
    return re.sub(r"[\s:：・･·\-_＋+()（）]", "", s or "").lower()


def main():
    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in chars}
    my_ids = set(by_id)
    ari_chars = json.loads((RAW / "ari_characters.json").read_text(encoding="utf-8"))
    by_ja = {}
    for c in chars:
        by_ja.setdefault(norm(c["name"]["ja"]), c["id"])
        by_ja.setdefault(norm(c["name"]["en"]), c["id"])
    ari2my = {a["id"]: by_ja.get(norm(a["name"])) for a in ari_chars}

    def resolve(ari_ids, cols):
        out = []
        for i, col in zip(ari_ids, list(cols or []) + [None] * 5):
            m = ari2my.get(i)
            if not m:
                return None
            if str(col or "").startswith("treasure"):
                t = TREASURE_ALIAS.get(m, m + "-treasure")
                if t in my_ids:
                    m = t
            out.append(m)
        return out if len(out) == 5 else None

    rounds = []  # (ordered_team, won, server)
    for f in RAW.glob("ari_matchups_*.json"):
        server = f.stem.split("_")[-1]
        for r in json.loads(f.read_text(encoding="utf-8")).get("matchups", []):
            a = resolve(r["attacker_team"], r.get("attacker_collections"))
            d = resolve(r["defender_team"], r.get("defender_collections"))
            if not a or not d:
                continue
            att_won = r["winner_player_id"] == r["attacker_player_id"]
            rounds.append((a, att_won, d, server))
            rounds.append((d, not att_won, a, server))
    print(f"可用回合 {len(rounds)//2}")

    # 2. 核心組合（2 人與 3 人）統計
    pair_stats = collections.defaultdict(lambda: [0, 0])
    for team, won, _, _ in rounds:
        for k in (2, 3):
            for combo in itertools.combinations(sorted(team), k):
                s = pair_stats[combo]
                s[0] += 1; s[1] += won
    cands = [(combo, m, w / m) for combo, (m, w) in pair_stats.items() if m >= MIN_MATCHES and w / m >= MIN_WIN]
    # 偏好 3 人核心；若 3 人核心涵蓋了某 2 人核心的大部分場次就以 3 人為準
    cands.sort(key=lambda x: (-len(x[0]), -x[1] * x[2]))
    chosen = []
    for combo, m, wr in cands:
        # 與已選核心共用 2 人以上就視為同一家族（例如 阿妮斯/桑迪珍藏/拉普拉斯/索達/特蕾娜 的各種三人組）
        if any(len(set(c[0]) & set(combo)) >= 2 for c in chosen):
            continue
        chosen.append((combo, m, wr))
        if len(chosen) >= MAX_TEMPLATES:
            break
    print(f"核心組合 {len(chosen)}")

    # 3. 每個核心的彈性位、站位、對位
    def detect(team):
        return [i for i, (combo, _, _) in enumerate(chosen) if set(combo) <= set(team)]

    tpls = json.loads((DATA / "templates.json").read_text(encoding="utf-8"))
    extra_file = DATA / "templates-extra.json"
    if extra_file.exists():
        tpls += json.loads(extra_file.read_text(encoding="utf-8"))
    def detect_arch(team):
        s = set(team)
        return sorted({t["archetype"] for t in tpls if all(r in s for r in t["required"])})
    templates = []
    core_vs = collections.defaultdict(lambda: [0, 0])  # (i, j) -> [games, wins of i]
    core_vs_arch = collections.defaultdict(lambda: [0, 0])  # (i, arch) -> [games, wins of i]
    for i, (combo, m, wr) in enumerate(chosen):
        pos_count = collections.defaultdict(collections.Counter)  # unit -> Counter(position)
        others = collections.Counter()
        atk = [0, 0]; dfn = [0, 0]
        for team, won, opp, server in rounds:
            if not set(combo) <= set(team):
                continue
            for p, u in enumerate(team):
                pos_count[u][p] += 1
            for u in team:
                if u not in combo:
                    others[u] += 1
            for j in detect(opp):
                if j != i:
                    core_vs[(i, j)][0] += 1
                    core_vs[(i, j)][1] += won
            for a in detect_arch(opp):
                core_vs_arch[(i, a)][0] += 1
                core_vs_arch[(i, a)][1] += won
        # 核心角站位：取各自最常站的位置，衝突時依出場數讓位
        slots = [None] * 5
        for u in sorted(combo, key=lambda u: -sum(pos_count[u].values())):
            for p, _ in pos_count[u].most_common():
                if slots[p] is None:
                    slots[p] = u; break
        # 彈性位：剩下的位置，人選取該位置最常出現的非核心角（最多 6 位）
        flex = []
        for p in range(5):
            if slots[p] is not None:
                continue
            cnt = collections.Counter()
            for u, c in others.items():
                cnt[u] += pos_count[u][p]
            opts = [u for u, n in cnt.most_common(8) if n > 0 and u in by_id]
            if not opts:
                opts = [u for u, _ in others.most_common(6) if u in by_id]
            flex.append({"slot": p, "options": opts[:6]})
        burst = []
        for p in range(5):
            u = slots[p] or (flex and next((f["options"][0] for f in flex if f["slot"] == p and f["options"]), None))
            burst.append(by_id[u]["burst"] if u and u in by_id else "II")
        zh = "＋".join(by_id[u]["name"]["zh-TW"] for u in combo if u in by_id)
        en = " + ".join(by_id[u]["name"]["en"] for u in combo if u in by_id)
        templates.append({
            "id": f"mined-{i}",
            "name": {"en": f"{en} (data-mined)", "zh-TW": f"{zh}（資料挖掘）", "zh-CN": f"{zh}（数据挖掘）", "ja": f"{en}（データ）"},
            "archetype": f"mined-{i}",
            "mode": "both",
            "required": [u for u in combo if u in by_id],
            "flex": flex,
            "burstSlots": burst,
            "preferredSpeed": "3RL",
            "counters": [], "counteredBy": [],
            "priority": 2,
            "_stats": {"matches": m, "winRate": round(wr * 100, 1)},
            "notes": {"en": f"Data-mined from {m} Champion Arena rounds, win rate {wr*100:.0f}%. Flex options are the most common teammates per position.",
                      "zh-TW": f"由 nikkeari 冠軍競技場 {m} 回合統計而來（整體勝率 {wr*100:.0f}%）；核心角站位取最常見位置，彈性位人選是該位置最常搭配的角色。這是統計結果，不是人工驗證的打法。",
                      "zh-CN": f"数据挖掘：{m} 回合，胜率 {wr*100:.0f}%。", "ja": f"データ：{m}回合、勝率 {wr*100:.0f}%。"},
        })
    # 對位：i 對 j 至少 30 場且勝率 >= 60% → i counters j
    for (i, j), (g, w) in core_vs.items():
        if g >= 30 and w / g >= 0.6:
            templates[i]["counters"].append(f"mined-{j}")
            templates[j]["counteredBy"].append(f"mined-{i}")
            templates[i]["_stats"].setdefault("vs", []).append({"vs": f"mined-{j}", "games": g, "win": round(w / g * 100)})
    for (i, a), (g, w) in core_vs_arch.items():
        if g >= 30 and w / g >= 0.6:
            templates[i]["counters"].append(a)
            templates[i]["_stats"].setdefault("vsArch", []).append({"vs": a, "games": g, "win": round(w / g * 100)})
        elif g >= 30 and w / g <= 0.4:
            templates[i]["counteredBy"].append(a)
    # 排序：場次×勝率
    templates.sort(key=lambda t: -t["_stats"]["matches"] * t["_stats"]["winRate"])
    (DATA / "templates-mined.json").write_text(json.dumps(templates, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in templates:
        print(f"{t['name']['zh-TW']:40s} {t['_stats']['matches']:5d} 場 {t['_stats']['winRate']:5.1f}%  克 {len(t['counters'])} 被克 {len(t['counteredBy'])}  站位 {t['burstSlots']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
