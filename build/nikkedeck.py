#!/usr/bin/env python3
"""nikke-deck.com 的角色資料（data.json）：下載、對應到本工具的角色 id、產生 deck-speed.json，
以及把上游 arena-planner 還沒收錄的新角色轉成本工具的角色格式。

nikke-deck 的 data.json 是該站前端的資料檔（含全部角色的每階充能、超頻 17% 變體、PVP 階級），
更新得比 arena-planner 勤。本模組只做讀取與換算，被 build.py --update 與 fetch_arena_stats.py 共用。
"""
import json, re, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
URL = "https://nikke-deck.com/en/assets/data.json"
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)"}

WEAPON = {1: "SG", 2: "RL", 3: "SR", 4: "AR", 5: "SMG", 6: "MG"}
ROLE = {1: "attacker", 2: "defender", 3: "supporter"}
MAKER = {1: "elysion", 2: "missilis", 3: "tetra", 4: "pilgrim", 5: "abnormal"}
ELEMENT = {1: "fire", 2: "wind", 3: "iron", 4: "electric", 5: "water"}
BURST = {1: "I", 2: "II", 3: "III", 0: "Λ"}
# nikke-deck 的五階依序是 2RL、2.5RL、3RL、3.5RL、4RL，對應本工具的速度階名稱
TIERS = ["2RL", "5SG", "3RL", "7SG", "4RL"]
# 超級巨星阿妮斯被動的角色係數（nikke-deck 前端 app-deck-details.getBurstGeneration）
# nikke-deck id → 本工具 id（英文名寫法不同、自動對應會對不上的角色）
ALIAS = {"c870": "queen", "c871": "yukiko", "c23": "delta-ninja-thief"}
RATIO = {"c017": 6, "c821": 4.5, "c232": 8, "c183": 2.5, "c062": 4, "c811": 4.5, "c261": 2, "c290": 1.704, "c582": 1.704,
         "c225": 2, "c230": 2, "c094": 6, "c851": 5, "c302": 1, "c511": 1.5}


def norm(s):
    return re.sub(r"[\s:：・･·\-_＋+()（）]", "", s or "").lower()


def slug(en):
    return re.sub(r"[^a-z0-9]+", "-", en.lower()).strip("-")


def fetch(refresh=False):
    """下載 data.json 到 data/raw/deck_data.json；已有快取且沒要求 refresh 時直接用快取。"""
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / "deck_data.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text(encoding="utf-8"))
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    d = json.loads(raw.decode("utf-8"))
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"下載 {URL}（{len(raw):,} bytes，{len(d.get('nikkes', []))} 名角色）")
    return d


def matcher(chars):
    """回傳 find(deck 角色) → 本工具 id：優先用角色上記的 deckId，其次頭像檔名裡的 si_cXXX 代碼，最後英文名。"""
    code2my, en2my = {}, {}
    for c in chars:
        if c.get("deckId"):
            code2my.setdefault(c["deckId"], c["id"])
        m = re.search(r"si_(c\d+)_", c.get("avatarImg") or "")
        if m:
            code2my.setdefault(m.group(1) + ("treasure" if c["id"].endswith("-treasure") else ""), c["id"])
        en2my.setdefault(norm(c["name"]["en"]), c["id"])

    def find(n):
        mid = ALIAS.get(n["id"]) or code2my.get(n["id"])
        if not mid:  # 後備：英文名（nikke-deck 珍藏版寫成「Helm +」，本工具寫成「Helm: Treasure」）
            mid = en2my.get(norm(n["name"]["en"].replace(" +", " treasure").replace("+", " treasure")))
        return mid
    return find


def gen_of(n):
    """回傳 (gen, hits, gen17, hits17, s10)。nikke-deck 的規則：有標 default 的「S10」版本就是預設充能；
    「17%」是充能速度超頻 17% 的版本。"""
    gen, hits = n.get("burstGeneration") or None, n.get("hitOneTarget") or None
    gen17 = hits17 = s10 = None
    for sp in n.get("specials", []):
        if sp["name"] == "17%":
            gen17 = sp.get("burstGeneration")
            hits17 = sp.get("hitOneTarget") or hits
        elif sp["name"] == "S10":
            s10 = {"gen": sp.get("burstGeneration"), "default": sp.get("default", False)}
            if sp.get("default") or not gen:
                gen = sp.get("burstGeneration")
                hits = sp.get("hitOneTarget") or hits
    return gen, hits, gen17, hits17, s10


def write_speed(deck, chars):
    """產生 data/deck-speed.json：每位角色的每階充能（含超頻 17% 版本）、命中數、PVP 階級、量子魔方 Lv7 加成。"""
    find = matcher(chars)
    speed = {}
    for n in deck["nikkes"]:
        mid = find(n)
        if not mid:
            continue
        gen, hits, gen17, hits17, s10 = gen_of(n)
        entry = {"rank": n.get("rank"), "ol17": gen17 is not None, "s10": s10, "deckId": n["id"],
                 "ratio": RATIO.get(n["id"], 4 if n.get("weapon") == 2 else 1)}
        if gen17 is not None:
            entry["gen17"], entry["hits17"] = gen17, hits17
        if gen:
            entry["gen"] = gen
        if hits:
            entry["hits"] = hits
        speed[mid] = entry
    quantum = next((c for c in deck.get("cubes", []) if "Quantum" in c["name"]["en"]), None)
    (DATA / "deck-speed.json").write_text(json.dumps({
        "source": "nikke-deck.com data.json（" + deck.get("lastUpdated", "") + "）",
        "quantumLv7": quantum["value"] if quantum else None,
        "units": speed,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"deck-speed.json：{len(speed)} 名角色對應（nikke-deck 共 {len(deck['nikkes'])}），量子 Lv7 = {quantum['value'] if quantum else None}")
    return speed


def _r4(x):
    return round(x, 4)


def to_character(n, release_order, syn=None):
    """把 nikke-deck 的一筆 SSR 角色轉成本工具（arena-planner 格式）的角色。
    充能數值由 nikke-deck 的五階（2RL～4RL）換算：1RL 取 2RL 的一半，1.5RL（3SG）火箭筒／狙擊槍與 1RL 相同、其餘取 2RL 的 3/4，
    5RL 以 3RL→4RL 的增量外推；攻守相同。syn 是 nikke-synergy 的同一角色（可為 None），提供繁中名、出場日期、彈藥、裝填等。"""
    en = n["name"]["en"]
    treasure = bool(n.get("treasure")) or en.endswith(" +")
    base_en = en[:-2].strip() if en.endswith(" +") else en
    cid = slug(base_en) + ("-treasure" if treasure else "")
    gen, hits, gen17, hits17, s10 = gen_of(n)
    w = WEAPON.get(n.get("weapon"), "RL")
    bg = {}
    if gen and len(gen) >= 5:
        g = [x / 100 for x in gen]
        one = g[0] / 2
        bg = {"1RL": _r4(one), "2RL": _r4(g[0]), "3SG": _r4(one if w in ("RL", "SR") else g[0] * 0.75), "5SG": _r4(g[1]),
              "3RL": _r4(g[2]), "7SG": _r4(g[3]), "4RL": _r4(g[4]), "5RL": _r4(g[4] + (g[4] - g[2]) / 2)}
    name = {"en": (base_en + ": Treasure") if treasure else en}
    zh = syn.get("zh") if syn else None
    name["zh-TW"] = re.sub(r"\s*\(珍藏品\)", " 珍藏", zh).replace("：", ":") if zh else name["en"]  # 沿用上游寫法：半形冒號、「X 珍藏」
    name["zh-CN"] = name["zh-TW"]
    name["ja"] = n["name"].get("ja") or (syn or {}).get("name") or name["en"]
    if n["name"].get("ko"):
        name["ko"] = n["name"]["ko"]
    rec = {"id": cid, "name": name, "burst": BURST.get(n.get("burst"), "III"), "role": ROLE.get(n.get("class"), "attacker"),
           "element": ELEMENT.get(n.get("element"), "fire"), "manufacturer": MAKER.get(n.get("manufacturer"), "elysion"), "weapon": w}
    if syn:
        if syn.get("ammo"):
            rec["ammo"] = syn["ammo"]
        if syn.get("reload_original"):
            rec["reloadTime"] = float(syn["reload_original"])
        if syn.get("charge_time"):
            rec["chargeTime"] = round(syn["charge_time"] / 60, 2)  # synergy 以 60fps 的幀數記
        if syn.get("charge_multiplier"):
            rec["maxCharge"] = syn["charge_multiplier"]
    rec.update({"burstGen": {"attack": bg, "defense": dict(bg)},
                "burstGenSource": "nikke-deck 的 2RL～4RL；1RL、1.5RL、5RL 為推算",
                "suitability": {"attack": 0, "defense": 0},
                "releaseOrder": release_order, "avatarImg": cid, "deckId": n["id"],
                "source": "nikke-deck" + ("＋nikke-synergy" if syn else "")})
    if syn and syn.get("releaseDate"):
        rec["releaseDate"] = syn["releaseDate"]
    if syn and syn.get("image_public_url"):  # 上游沒有這些角色的頭像；記下 nikke-synergy 的角色圖網址，fetch_avatars.py 會下載成 avatars/<id>.<副檔名>
        rec["avatarUrl"] = syn["image_public_url"]
        ext = re.search(r"\.(png|jpe?g|webp)(?:\?|$)", syn["image_public_url"], re.I)
        rec["avatarFile"] = cid + "." + (ext.group(1).lower() if ext else "png")
    return rec
