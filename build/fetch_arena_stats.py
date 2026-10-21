#!/usr/bin/env python3
"""抓取 nikkeari.cc（にけあり！NIKKE 競技場分析器）的冠軍競技場對戰統計，
以及 nikke-deck.com 的充能資料，整理成工具可嵌入的精簡 JSON。

輸出：
  build/data/arena-stats.json   冠軍競技場統計（依本工具的角色 id）
  build/data/deck-speed.json    nikke-deck 的超頻／量子魔方充能變體與 PVP 階級
  build/data/raw/               原始回應（已在 .gitignore，供除錯）

資料來源與授權：
  nikkeari.cc 為個人粉絲站，資料來自志願玩家提供的截圖；本腳本只讀取其公開 API，請勿高頻呼叫。
  nikke-deck.com 的 data.json 為其網站資料檔；僅用來推導超頻／魔方對速度的影響與其階級表。
"""
import json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)", "Referer": "https://nikkeari.cc/zh-CN"}
ARI = "https://nikkeari.cc"
SERVERS = ["GLOBAL", "JP", "KR"]


def cached(name, fetch):
    """有 raw 快取就用快取（避免重複打對方伺服器）；加 --refresh 參數才重抓。"""
    f = RAW / name
    if f.exists() and "--refresh" not in sys.argv:
        return json.loads(f.read_text(encoding="utf-8"))
    d = fetch()
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def get(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(UA)
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s):
    return re.sub(r"[\s:：・･·\-_＋+()（）]", "", s or "").lower()


def main():
    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    tpls = json.loads((DATA / "templates.json").read_text(encoding="utf-8"))

    # ---------- nikkeari 角色對應（日文名） ----------
    ari_chars = cached("ari_characters.json", lambda: get(ARI + "/api/characters"))
    by_ja = {}
    for c in chars:
        by_ja.setdefault(norm(c["name"]["ja"]), c["id"])
        by_ja.setdefault(norm(c["name"]["en"]), c["id"])
    MANUAL = {  # nikkeari 名稱 → 本工具 id（自動對不到時補）
    }
    ari2my, unmapped, extra_names = {}, [], {}
    for a in ari_chars:
        key = norm(a["name"])
        mid = MANUAL.get(a["name"]) or by_ja.get(key)
        if not mid:
            # 寶物版：「○○：宝物」/「○○（宝物）」
            m = re.sub(r"(宝物|珍藏|treasure)", "", key)
            base = by_ja.get(m)
            if base and "宝物" in a["name"] or "treasure" in key:
                cand = base + "-treasure" if base else None
                if cand and any(c["id"] == cand for c in chars):
                    mid = cand
        if mid:
            ari2my[a["id"]] = mid
        else:
            unmapped.append((a["id"], a["name"], a.get("usage_count", 0)))
            if a["name"] != "空枠":  # 空位不算角色；其餘保留原名當替代 id，回合資料不丟
                ari2my[a["id"]] = "ari:" + a["name"]
                extra_names["ari:" + a["name"]] = a["name"]
    print(f"nikkeari 角色 {len(ari_chars)}，對應成功 {len(ari2my)}，未對應 {len(unmapped)}")
    for u in sorted(unmapped, key=lambda x: -x[2])[:40]:
        print("  未對應:", u)

    # ---------- 賽事與對戰 ----------
    tournaments = cached("ari_tournaments.json", lambda: get(ARI + "/api/tournaments"))
    champ_ids = sorted({t["championship_id"] for t in tournaments if t.get("championship_id")})
    latest_champ = max(champ_ids) if champ_ids else None
    seasons = sorted({t["season"] for t in tournaments})

    def detect(ids):
        s = set(ids)
        out = set()
        for t in tpls:
            if all(r in s for r in t["required"]):
                out.add(t["archetype"])
        return sorted(out)

    team_stats = {}   # key -> dict
    arch_stats = {}   # arch -> dict
    arch_vs = {}      # "A>B" -> {m, w}
    beaten_by = {}    # key -> {oppkey: wins}
    char_pos = {}     # my id -> {server: position_stats}
    total_rounds = 0
    per_server = {}

    for server in SERVERS:
        ids = [t["id"] for t in tournaments if t["play_server"] == server]
        if not ids:
            continue
        body = {"tournament_ids": ids, "play_server": server, "championship_id": latest_champ}
        try:
            mu = cached(f"ari_matchups_{server}.json", lambda: get(ARI + "/api/dashboard/cross-tournament/matchups?t=%d" % int(time.time()), body))
        except Exception as e:
            print(server, "matchups 失敗", e)
            continue
        rounds = mu.get("matchups", mu)
        try:
            st = cached(f"ari_stats_{server}.json", lambda: get(ARI + "/api/dashboard/cross-tournament/stats?t=%d" % int(time.time()), body))
            for c in st.get("character_stats", []):
                mid = ari2my.get(c["id"])
                if not mid:
                    continue
                char_pos.setdefault(mid, {})[server] = {
                    "n": c["count"], "players": c.get("player_count"), "m": c["total_matches"], "w": c["win_count"],
                    "pos": [{"p": p["position"], "n": p["count"], "pct": p["pct"], "wr": p["win_rate"]} for p in c.get("position_stats", [])],
                }
        except Exception as e:
            print(server, "stats 失敗", e)
        per_server[server] = {"tournaments": len(ids), "rounds": len(rounds)}
        total_rounds += len(rounds)
        time.sleep(1)

        def key_of(ari_ids):
            mids = [ari2my.get(i) for i in ari_ids]
            if any(m is None for m in mids):
                return None, None
            return ",".join(sorted(mids)), mids

        for r in rounds:
            ak, a_ids = key_of(r["attacker_team"])
            dk, d_ids = key_of(r["defender_team"])
            if not ak or not dk:
                continue
            att_won = r["winner_player_id"] == r["attacker_player_id"]
            for k, ids_, is_att, won in ((ak, a_ids, True, att_won), (dk, d_ids, False, not att_won)):
                t = team_stats.setdefault(k, {"ids": ids_, "m": 0, "w": 0, "am": 0, "aw": 0, "dm": 0, "dw": 0, "servers": {}})
                t["m"] += 1; t["w"] += won
                if is_att: t["am"] += 1; t["aw"] += won
                else: t["dm"] += 1; t["dw"] += won
                t["servers"][server] = t["servers"].get(server, 0) + 1
            winner_k, loser_k = (ak, dk) if att_won else (dk, ak)
            bb = beaten_by.setdefault(loser_k, {})
            bb[winner_k] = bb.get(winner_k, 0) + 1
            a_arch, d_arch = detect(a_ids), detect(d_ids)
            for arch, won, is_att in [(x, att_won, True) for x in a_arch] + [(x, not att_won, False) for x in d_arch]:
                s = arch_stats.setdefault(arch, {"m": 0, "w": 0, "am": 0, "aw": 0, "dm": 0, "dw": 0})
                s["m"] += 1; s["w"] += won
                if is_att: s["am"] += 1; s["aw"] += won
                else: s["dm"] += 1; s["dw"] += won
            for wa in (a_arch if att_won else d_arch):
                for la in (d_arch if att_won else a_arch):
                    v = arch_vs.setdefault(wa + ">" + la, 0)
                    arch_vs[wa + ">" + la] = v + 1

    # 精簡：隊伍只留 3 場以上，改用索引引用；beatenBy 只留前 6
    keep = {k for k, v in team_stats.items() if v["m"] >= 3}
    bb_tmp = {}
    for k, d in beaten_by.items():
        if k not in keep:
            continue
        bb_tmp[k] = sorted(d.items(), key=lambda x: -x[1])[:6]
        for ok, _ in bb_tmp[k]:
            keep.add(ok)
    keys = sorted(keep, key=lambda k: -team_stats[k]["m"])
    index = {k: i for i, k in enumerate(keys)}
    teams_arr = [[k, team_stats[k]["m"], team_stats[k]["w"], team_stats[k]["am"], team_stats[k]["aw"], team_stats[k]["dm"], team_stats[k]["dw"]] for k in keys]
    bb_out = {str(index[k]): [[index[ok], n] for ok, n in lst] for k, lst in bb_tmp.items()}
    # 角色站位統計：各伺服器加總
    pos_out = {}
    for mid, per in char_pos.items():
        agg = {"n": 0, "m": 0, "w": 0, "pos": [[0, 0, 0] for _ in range(5)]}
        for sv in per.values():
            agg["n"] += sv["n"]; agg["m"] += sv["m"]; agg["w"] += sv["w"]
            for p in sv["pos"]:
                if 1 <= p["p"] <= 5:
                    agg["pos"][p["p"] - 1][0] += p["n"]
                    agg["pos"][p["p"] - 1][1] += round((p["wr"] or 0) / 100 * (p["n"] or 0), 3)  # 暫存勝場估計
        pos = []
        for n, wsum, _ in agg["pos"]:
            pos.append([n, round(n / agg["n"] * 100, 1) if agg["n"] else 0, round(wsum / n * 100, 1) if n else None])
        pos_out[mid] = {"n": agg["n"], "m": agg["m"], "w": agg["w"], "pos": pos}
    out = {
        "source": "nikkeari.cc（にけあり！）冠軍競技場統計，志願玩家提供截圖整理；非官方資料",
        "fetched": time.strftime("%Y-%m-%d"),
        "servers": per_server,
        "seasons": seasons,
        "rounds": total_rounds,
        "teams": teams_arr,        # [key, m, w, am, aw, dm, dw]；key 為排序後的角色 id 以逗號相連
        "beatenBy": bb_out,        # 隊伍索引 -> [[打贏它的隊伍索引, 次數], ...]
        "arch": arch_stats,
        "archVs": arch_vs,
        "charPos": pos_out,
        "names": extra_names,
        "unmapped": [u[1] for u in unmapped if u[2] > 0],
    }
    (DATA / "arena-stats.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"arena-stats.json：{len(teams_arr)} 隊、{total_rounds} 回合、{len(arch_stats)} 體系；{per_server}")

    # ---------- nikke-deck 充能變體與階級 ----------
    try:
        deck = get("https://nikke-deck.com/en/assets/data.json")
        (RAW / "deck_data.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        code2my = {}
        for c in chars:
            img = c.get("avatarImg") or ""
            m = re.search(r"si_(c\d+)_", img)
            if m:
                code = m.group(1) + ("treasure" if c["id"].endswith("-treasure") else "")
                code2my[code] = c["id"]
        en2my = {norm(c["name"]["en"]): c["id"] for c in chars}
        speed = {}
        for n in deck["nikkes"]:
            mid = code2my.get(n["id"])
            if not mid:  # 後備：英文名（nikke-deck 寶物版寫成「Helm +」）
                en = norm(n["name"]["en"].replace(" +", " treasure").replace("+", " treasure"))
                mid = en2my.get(en)
            if not mid:
                continue
            entry = {"rank": n.get("rank"), "ol17": False, "s10": None}
            for sp in n.get("specials", []):
                if sp["name"] == "17%":
                    entry["ol17"] = True
                elif sp["name"] == "S10":
                    entry["s10"] = {"gen": sp.get("burstGeneration"), "default": sp.get("default", False)}
            if n.get("burstGeneration"):
                entry["gen"] = n["burstGeneration"]
            speed[mid] = entry
        quantum = next((c for c in deck.get("cubes", []) if "Quantum" in c["name"]["en"]), None)
        (DATA / "deck-speed.json").write_text(json.dumps({
            "source": "nikke-deck.com data.json（" + deck.get("lastUpdated", "") + "）",
            "quantumLv7": quantum["value"] if quantum else None,
            "units": speed,
        }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"deck-speed.json：{len(speed)} 名角色對應（nikke-deck 共 {len(deck['nikkes'])}），量子 Lv7 = {quantum['value'] if quantum else None}")
    except Exception as e:
        print("nikke-deck 抓取失敗", e)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
