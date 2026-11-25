#!/usr/bin/env python3
"""抓取 nikkeari.cc（にけあり！NIKKE 競技場分析器）的冠軍競技場對戰統計，
以及 nikke-deck.com 的充能資料，整理成工具可嵌入的精簡 JSON。

輸出：
  build/data/arena-stats.json   冠軍競技場統計（依本工具的角色 id）
  build/data/deck-speed.json    nikke-deck 的超頻／量子魔方充能變體與 PVP 階級
  build/data/raw/               原始回應（已在 .gitignore，供除錯）
  build/data/arena-rounds-archive.json.gz
                                β31～β40（beta 賽季）的回合封存。nikkeari 的 API 自 2026-11 起只回傳正規賽季（Season 1 起），
                                舊賽季抓不回來了，所以保留當時的回應；每次執行都會把封存併進統計，並標記哪些回合是
                                2026-10-29 攻守目標規則統一之後的「新規則」對局（見 NEW_RULE_FROM）。

資料來源與授權：
  nikkeari.cc 為個人粉絲站，資料來自志願玩家提供的截圖；本腳本只讀取其公開 API，請勿高頻呼叫。
  nikke-deck.com 的 data.json 為其網站資料檔；僅用來推導超頻／魔方對速度的影響與其階級表。
"""
import gzip, io, json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
DATA = HERE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)", "Referer": "https://nikkeari.cc/zh-CN"}
ARI = "https://nikkeari.cc"
SERVERS = ["GLOBAL", "JP", "KR"]
NEW_RULE_FROM = "2026-10-29"  # 攻守目標規則統一（SR 一律打 P5、SG 一律打 P1）；此日之後開打的賽季算「新規則」對局
ARCHIVE = DATA / "arena-rounds-archive.json.gz"  # β 賽季回合封存（API 已不再提供），見檔頭說明
ARCHIVE_KEEP = ("tournament_id", "tournament_name", "stage", "match_id", "round_number", "attacker_player_id",
                "attacker_team", "attacker_collections", "defender_team", "defender_collections", "winner_player_id")


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


def load_archive():
    """β 賽季封存：回傳 {server: {"matchups": [...], "character_stats": [...], "tournaments": [...]}}。
    以 data/arena-rounds-archive.json.gz 為基底；raw/ 裡若有某伺服器的 ari_matchups_<server>.beta.json（舊 API 回應的備份），
    就用它（與同伺服器的 ari_stats_*.beta.json、ari_tournaments.beta.json）取代該伺服器的封存內容，其他伺服器維持封存；
    缺少的部分沿用封存，所以永遠不會把封存「掏空」。內容有變才改寫檔案（gzip 不寫檔名、mtime=0：內容相同時位元組也相同）。
    最後把 raw/ 缺少的 .beta 檔從封存還原出來，讓 mine_templates.py / community_templates.py 用 ari_matchups_*.json 萬用字元也讀得到。"""
    arch = {}
    if ARCHIVE.exists():
        with gzip.open(ARCHIVE, "rt", encoding="utf-8") as g:
            arch = json.load(g)["servers"]
    tf = RAW / "ari_tournaments.beta.json"
    tours = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else None
    from_raw = []
    for s in SERVERS:
        f = RAW / f"ari_matchups_{s}.beta.json"
        if not f.exists():
            continue
        mu = json.loads(f.read_text(encoding="utf-8"))
        sf = RAW / f"ari_stats_{s}.beta.json"
        prev = arch.get(s, {})
        arch[s] = {
            "matchups": [{k: r.get(k) for k in ARCHIVE_KEEP} for r in mu.get("matchups", mu)],
            "character_stats": json.loads(sf.read_text(encoding="utf-8")).get("character_stats", []) if sf.exists() else prev.get("character_stats", []),
            "tournaments": [t for t in tours if t.get("play_server") == s] if tours is not None else prev.get("tournaments", []),
        }
        from_raw.append(s)
    if not arch:
        return {}
    blob = json.dumps({"note": "nikkeari.cc β31～β40 冠軍競技場回合（2026-10-29 規則統一前的舊規則對局）；API 已不再提供，由 fetch_arena_stats.py 封存",
                       "servers": arch}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buf, mode="wb", mtime=0) as g:
        g.write(blob)
    data = buf.getvalue()
    n_rounds = sum(len(v["matchups"]) for v in arch.values())
    if not ARCHIVE.exists() or ARCHIVE.read_bytes() != data:
        ARCHIVE.write_bytes(data)
        print(f"改寫封存 {ARCHIVE.name}：{n_rounds} 回合、{len(data) // 1024} KB（來自 raw：{'、'.join(from_raw) or '無'}）")
    else:
        print(f"β 賽季封存 {ARCHIVE.name}：{n_rounds} 回合，內容不變")
    for s, v in arch.items():  # 還原 raw/ 缺少的 .beta 檔（三種都還原，第二次執行才不會以殘缺的 raw 改寫封存）
        f = RAW / f"ari_matchups_{s}.beta.json"
        if not f.exists():
            f.write_text(json.dumps({"matchups": v["matchups"]}, ensure_ascii=False), encoding="utf-8")
        sf = RAW / f"ari_stats_{s}.beta.json"
        if not sf.exists():
            sf.write_text(json.dumps({"character_stats": v.get("character_stats", [])}, ensure_ascii=False), encoding="utf-8")
    if not tf.exists():
        tf.write_text(json.dumps([t for v in arch.values() for t in v.get("tournaments", [])], ensure_ascii=False), encoding="utf-8")
    return arch


def main():
    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    tpls = json.loads((DATA / "templates.json").read_text(encoding="utf-8"))
    extra_file = DATA / "templates-extra.json"
    if extra_file.exists():
        tpls = tpls + json.loads(extra_file.read_text(encoding="utf-8"))

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
    archive = load_archive()  # API 已不再提供的 β 賽季
    all_tours = {t["id"]: t for v in archive.values() for t in v.get("tournaments", [])}
    all_tours.update({t["id"]: t for t in tournaments})
    t_date = {i: t["date"] for i, t in all_tours.items() if t.get("date")}  # 賽事開打日（沒有日期的不收，統一走名稱備援）
    season_date = {}
    for t in all_tours.values():
        if t.get("date"):
            season_date[t["season"]] = min(season_date.get(t["season"], "9999"), t["date"])
    seasons = sorted({t["season"] for t in all_tours.values()}, key=lambda s: (season_date.get(s, "9999"), s))  # 依開打日期排：β 賽季在前、正規賽季在後、沒日期的最後

    def is_new_rule(r):
        """這回合是否打在 2026-10-29 攻守目標規則統一之後：依賽事開打日；賽事不在清單或沒有日期時以名稱判斷（β 開頭為舊規則）"""
        d = t_date.get(r.get("tournament_id"))
        if not d:
            return not str(r.get("tournament_name") or "").startswith("β")
        return d >= NEW_RULE_FROM

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
    bb_samples = {}   # (loser, winner) -> [出處]
    char_pos = {}     # my id -> {server: position_stats}
    total_rounds = 0
    new_rounds = 0    # 其中新規則（NEW_RULE_FROM 之後開打的賽季）的回合數
    per_server = {}

    for server in SERVERS:
        ids = [t["id"] for t in tournaments if t["play_server"] == server]
        arch_sv = archive.get(server, {})
        if not ids and not arch_sv:
            continue
        body = {"tournament_ids": ids, "play_server": server, "championship_id": latest_champ}
        rounds = []
        if ids:
            try:
                mu = cached(f"ari_matchups_{server}.json", lambda: get(ARI + "/api/dashboard/cross-tournament/matchups?t=%d" % int(time.time()), body))
                rounds = list(mu.get("matchups", mu))
            except Exception as e:
                print(server, "matchups 失敗", e)
        # 併入封存的 β 賽季回合（同一回合若 API 仍有回傳就不重複算）
        seen = {(r.get("tournament_id"), r.get("match_id"), r.get("round_number")) for r in rounds}
        rounds += [r for r in arch_sv.get("matchups", []) if (r.get("tournament_id"), r.get("match_id"), r.get("round_number")) not in seen]
        if not rounds:
            continue
        stats_list = [arch_sv.get("character_stats", [])]
        if ids:
            try:
                st = cached(f"ari_stats_{server}.json", lambda: get(ARI + "/api/dashboard/cross-tournament/stats?t=%d" % int(time.time()), body))
                stats_list.append(st.get("character_stats", []))
            except Exception as e:
                print(server, "stats 失敗", e)
        for src_i, cs in enumerate(stats_list):  # 站位統計：封存（#0）與現行 API（#1）分開存，輸出時各伺服器、各來源加總
            for c in cs:
                mid = ari2my.get(c["id"])
                if not mid:
                    continue
                char_pos.setdefault(mid, {})[f"{server}#{src_i}"] = {
                    "n": c["count"], "players": c.get("player_count"), "m": c["total_matches"], "w": c["win_count"],
                    "pos": [{"p": p["position"], "n": p["count"], "pct": p["pct"], "wr": p["win_rate"]} for p in c.get("position_stats", [])],
                }
        n_new = sum(1 for r in rounds if is_new_rule(r))
        per_server[server] = {"tournaments": len({i for i, t in all_tours.items() if t.get("play_server") == server}), "rounds": len(rounds), "newRule": n_new}
        total_rounds += len(rounds)
        new_rounds += n_new
        time.sleep(1)

        my_ids = {c["id"] for c in chars}
        by_id = {c["id"]: c for c in chars}
        TREASURE_ALIAS = {}  # 珍藏版一律為 <id>-treasure（拉普拉斯珍藏與究極英雄是不同角色）
        def key_of(ari_ids, cols):
            mids = []
            for i, col in zip(ari_ids, list(cols or []) + [None] * 5):
                m = ari2my.get(i)
                if m is None:
                    return None, None
                if str(col or "").startswith("treasure"):  # nikkeari 把珍藏記成收藏等級標記
                    t = TREASURE_ALIAS.get(m, m + "-treasure")
                    if t in my_ids:
                        m = t
                mids.append(m)
            return ",".join(sorted(mids)), mids

        def chain_key(ids_):
            """誰開爆裂：每種爆裂（I/II/III）由站位最前的那位開，Λ 補缺（與工具 chainOf 的主要規則一致）"""
            used = []
            for b in ("I", "II", "III"):
                exact = [u for u in ids_ if u in by_id and by_id[u]["burst"] == b and u not in used]
                lam = [u for u in ids_ if u in by_id and by_id[u]["burst"] == "Λ" and u not in used]
                pick = (exact or lam)[:1]
                used += pick
            return ",".join(sorted(used))
        for r in rounds:
            ak, a_ids = key_of(r["attacker_team"], r.get("attacker_collections"))
            dk, d_ids = key_of(r["defender_team"], r.get("defender_collections"))
            if not ak or not dk:
                continue
            att_won = r["winner_player_id"] == r["attacker_player_id"]
            new = is_new_rule(r)
            for k, ids_, is_att, won in ((ak, a_ids, True, att_won), (dk, d_ids, False, not att_won)):
                t = team_stats.setdefault(k, {"ids": ids_, "m": 0, "w": 0, "am": 0, "aw": 0, "dm": 0, "dw": 0, "nm": 0, "nw": 0, "servers": {}})
                t["m"] += 1; t["w"] += won
                if new: t["nm"] += 1; t["nw"] += won
                ck = chain_key(ids_); c = t.setdefault("ch", {}).setdefault(ck, [0, 0]); c[0] += 1; c[1] += won
                if is_att: t["am"] += 1; t["aw"] += won
                else: t["dm"] += 1; t["dw"] += won
                t["servers"][server] = t["servers"].get(server, 0) + 1
            winner_k, loser_k = (ak, dk) if att_won else (dk, ak)
            bb = beaten_by.setdefault(loser_k, {})
            bb[winner_k] = bb.get(winner_k, 0) + 1
            smp = bb_samples.setdefault((loser_k, winner_k), [])
            if len(smp) < 2:  # 每組最多留 2 筆出處：賽季|輪次|勝方(A 進攻/D 防守)|伺服器
                smp.append(f"{r.get('tournament_name','')}|{r.get('stage','')}|{'A' if att_won else 'D'}|{server[0]}")
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

    # 精簡：隊伍只留 2 場以上，改用索引引用；beatenBy 只留前 6
    keep = {k for k, v in team_stats.items() if v["m"] >= 2}
    bb_tmp = {}
    for k, d in beaten_by.items():
        if k not in keep:
            continue
        bb_tmp[k] = sorted(d.items(), key=lambda x: -x[1])[:6]
        for ok, _ in bb_tmp[k]:
            keep.add(ok)
    keys = sorted(keep, key=lambda k: (-team_stats[k]["m"], k))  # 同場數以 key 決定順序：輸出才不會隨每次執行的 set 迭代順序而變
    index = {k: i for i, k in enumerate(keys)}
    def ch_out(k):  # 這隊各種「開爆裂三人組」的場數與勝場，最多 4 種
        ch = team_stats[k].get("ch", {})
        return [[ck, g, w] for ck, (g, w) in sorted(ch.items(), key=lambda x: -x[1][0])[:4]]
    teams_arr = [[k, team_stats[k]["m"], team_stats[k]["w"], team_stats[k]["am"], team_stats[k]["aw"], team_stats[k]["dm"], team_stats[k]["dw"], ch_out(k), team_stats[k]["nm"], team_stats[k]["nw"]] for k in keys]
    bb_out = {str(index[k]): [[index[ok], n, bb_samples.get((k, ok), [])] if pos < 3 else [index[ok], n] for pos, (ok, n) in enumerate(lst)] for k, lst in bb_tmp.items()}  # 出處只留前 3 組
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
        "newRule": {"from": NEW_RULE_FROM, "rounds": new_rounds, "seasons": [s for s in seasons if season_date.get(s, "") >= NEW_RULE_FROM]},  # 規則統一後開打的賽季（Season 1 起）；沒日期的賽季不列
        "teams": teams_arr,        # [key, m, w, am, aw, dm, dw, chains, nm, nw]；key 為排序後的角色 id 以逗號相連；chains = [[開爆裂三人 key, 場數, 勝場], ...]；nm/nw = 其中新規則賽季的場數與勝場
        "beatenBy": bb_out,        # 隊伍索引 -> [[打贏它的隊伍索引, 次數], ...]
        "arch": arch_stats,
        "archVs": arch_vs,
        "charPos": pos_out,
        "names": extra_names,
        "unmapped": [u[1] for u in unmapped if u[2] > 0],
    }
    (DATA / "arena-stats.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"arena-stats.json：{len(teams_arr)} 隊、{total_rounds} 回合（新規則 {new_rounds}）、{len(arch_stats)} 體系；{per_server}")

    # ---------- nikke-deck 充能變體與階級（共用 nikkedeck.py；build.py --update 也會產生同一份） ----------
    try:
        import nikkedeck
        nikkedeck.write_speed(nikkedeck.fetch("--refresh" in sys.argv), chars)
    except Exception as e:
        print("nikke-deck 抓取失敗", e)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
