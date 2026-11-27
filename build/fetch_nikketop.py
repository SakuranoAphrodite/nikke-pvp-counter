#!/usr/bin/env python3
"""抓 nikke.top（NIKKE Arena Tools）的逐幀充能參數 → build/data/nikketop.json

nikke.top 是逐幀（60 fps）模擬競技場充能的網站：每位角色依武器有固定的射擊節奏，
每次命中充能 baseChargeRate × chargeMultiplier，全隊累積到 100 就是「充滿」，
之後 B1 +24 幀、B2 +32 幀、B3 +32 幀開爆裂。網站沒有公開 API，參數寫在前端 JS 裡，
這支腳本把它抓下來、用英文名對應到本工具的角色 id。

該站是 Vite 打包的 SPA，角色表（"global-nikkes"／"china-nikkes" 兩個地區，本工具只用 Global）
放在哪個 chunk 會隨改版搬動（2026-11 從 HomePage-*.js 搬到 TeamBuilder-*.js），所以這裡不寫死檔名：
從首頁找到 index-*.js，再沿著各 chunk 的 import／動態 import 引用鏈搜尋（名字像首頁／組隊的先看、
首頁預載的共用套件最後），找到含角色表的 chunk 就停；每個 chunk 只下載一次並快取在 build/data/raw/。

用法：
  python build/fetch_nikketop.py            # 用 build/data/raw/ 的快取（沒有才下載）
  python build/fetch_nikketop.py --refresh  # 重新下載
"""
import json, re, sys, datetime, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SITE = "https://nikke.top/"
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)"}
WEAPON = {1: "SG", 2: "RL", 3: "SR", 4: "AR", 5: "SMG", 6: "MG"}
TABLE = "global-nikkes"  # 本工具要的是國際服的角色表
# nikke.top 英文名 → 本工具 id（自動對應失敗時的手動對照；" +" 結尾表示珍藏）
OVERRIDE = {"Queen: Makoto": "queen", "Asuka Shikinami Langley": "asuka", "Asuka Shikinami Langley: WILLE": "asuka-wille",
            "Mari Makinami Illustrious": "mari", "Misato Katsuragi": "misato"}
# 一個 chunk 引用到的其他 chunk：靜態 import{...}from"./x.js"、import"./x.js"、動態 import("./x.js")
# 與 Vite 的預載清單 "assets/x.js"
CHUNK_RE = re.compile(r'(?:from\s*|import\s*\(?\s*)["\']\./([A-Za-z0-9_.-]+\.js)["\']|["\']assets/([A-Za-z0-9_.-]+\.js)["\']')
TABLE_RE = re.compile(r'"%s"\s*:\s*JSON\.parse\(\s*' % re.escape(TABLE))
KEY_POINTS_RE = re.compile(r'\[\{frame:\d+,label:"[^"]+"\}(?:,\{frame:\d+,label:"[^"]+"\})*\]')


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def cached(name: str, url: str, refresh: bool) -> str:
    f = RAW / name
    if f.exists() and not refresh:
        return f.read_text(encoding="utf-8")
    raw = get(url)
    f.write_bytes(raw)
    print(f"下載 {url}（{len(raw):,} bytes）")
    return raw.decode("utf-8")


SIMPLE_ESCAPE = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def read_js_string(src: str, start: int) -> str:
    """從 src[start]（引號或反引號）開始讀一個 JS 字串，還原反斜線跳脫（\\n、\\uXXXX、\\xNN、\\u{…}、行接續…）。

    JSON 自己的跳脫在 JS 原始碼裡是雙反斜線（\\\\u00e9），還原後仍是 \\u00e9，交給 json.loads 處理。
    反引號字串裡的 ${…} 插值無法靜態解析，直接報錯。
    """
    q = src[start]
    i, n = start + 1, len(src)
    out = []
    while i < n:
        ch = src[i]
        if ch == "\\":
            e = src[i + 1]
            if e == "u" and src[i + 2] == "{":
                j = src.index("}", i + 3)
                out.append(chr(int(src[i + 3:j], 16)))
                i = j + 1
            elif e == "u":
                out.append(chr(int(src[i + 2:i + 6], 16)))
                i += 6
            elif e == "x":
                out.append(chr(int(src[i + 2:i + 4], 16)))
                i += 4
            elif e in "\r\n":  # 行接續
                i += 2 + (e == "\r" and src[i + 2:i + 3] == "\n")
            else:
                out.append(SIMPLE_ESCAPE.get(e, e))
                i += 2
            continue
        if ch == q:
            # \\uD83D\\uDE00 這類成對的代理字元還原成一個字；孤立的換成 U+FFFD，避免之後寫檔失敗
            return "".join(out).encode("utf-16", "surrogatepass").decode("utf-16", "replace")
        if q == "`" and ch == "$" and src[i + 1:i + 2] == "{":
            raise SystemExit("角色表字串含 ${…} 插值，無法靜態解析")
        out.append(ch)
        i += 1
    raise SystemExit("角色表字串沒有結尾引號")


def extract_table(src: str, key: str):
    m = re.search(r'"%s"\s*:\s*JSON\.parse\(\s*' % re.escape(key), src)
    if not m:
        raise SystemExit(f"找不到 {key}")
    return json.loads(read_js_string(src, m.end()))


def chunk_refs(src: str) -> list:
    """src 引用到的 chunk 檔名，依出現順序、去重。"""
    seen, out = set(), []
    for a, b in CHUNK_RE.findall(src):
        name = a or b
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def find_table_chunk(index_name: str, index_js: str, preloaded: set, refresh: bool):
    """從 index bundle 出發沿引用鏈找含角色表的 chunk。回傳 (檔名, 內容, 這次讀過的所有 chunk 內容)。

    順序：先找名字像首頁／組隊的 chunk，再找其他頁面，首頁就預載的共用套件（mantine、react 等）最後；
    找到就停，所以正常只多抓一兩個檔。
    """
    def rank(name: str):
        low = name.lower()
        return (name in preloaded, not ("home" in low or "team" in low), "page" in low)

    fetched = {index_name: index_js}
    if TABLE_RE.search(index_js):
        return index_name, index_js, fetched
    queue = sorted(chunk_refs(index_js), key=rank)
    seen = set(queue) | {index_name}
    failed = []
    while queue:
        name = queue.pop(0)
        try:
            src = cached("nikketop_" + name, SITE + "assets/" + name, refresh)
        except (urllib.error.URLError, OSError) as e:  # 單一 chunk 抓不到（404、逾時）就跳過，繼續找
            print(f"警告：{name} 下載失敗（{e}），跳過")
            failed.append(name)
            continue
        fetched[name] = src
        if TABLE_RE.search(src):
            return name, src, fetched
        new = [n for n in chunk_refs(src) if n not in seen]
        seen.update(new)
        # 新發現的 chunk 排在隊列前面（先走完首頁那一條鏈），共用套件仍殿後
        queue = sorted(sorted(new, key=rank) + queue, key=lambda n: n in preloaded)
    raise SystemExit(f"沿 import 鏈找不到 {TABLE}（已搜尋 {len(fetched)} 個 chunk：{'、'.join(fetched)}"
                     + (f"；下載失敗：{'、'.join(failed)}" if failed else "") + "）")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main(refresh: bool):
    index = cached("nikketop_index.html", SITE, refresh)
    im = re.search(r'/assets/(index-[A-Za-z0-9_-]+\.js)', index)
    if not im:
        raise SystemExit("首頁找不到 index bundle")
    index_name = im.group(1)
    preloaded = set(re.findall(r'/assets/([A-Za-z0-9_.-]+\.js)', index))  # 首頁 modulepreload 的共用套件
    idx = cached("nikketop_" + index_name, SITE + "assets/" + index_name, refresh)
    # 版本號：index bundle 內的更新紀錄每筆是 X="2.0.6",Y="2026-02-15",Z="minor"，取最大的
    versions = re.findall(r'="(\d+\.\d+\.\d+)",[A-Za-z$_][\w$]*="20\d\d-\d\d-\d\d",[A-Za-z$_][\w$]*="(?:major|minor|patch)"', idx)
    vm = re.search(r'"V(\d+\.\d+\.\d+)"', idx)  # 舊版寫法
    version = max(versions, key=lambda v: [int(x) for x in v.split(".")]) if versions else (vm.group(1) if vm else None)

    chunk_name, src, fetched = find_table_chunk(index_name, idx, preloaded, refresh)
    print(f"角色表在 {chunk_name}（沿 import 鏈讀了 {len(fetched)} 個 chunk）")
    top = extract_table(src, TABLE)

    out_file = DATA / "nikketop.json"
    prev = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else None
    km = KEY_POINTS_RE.search(src) or next((m for m in map(KEY_POINTS_RE.search, fetched.values()) if m), None)
    if km:
        key_points = [{"f": int(f), "label": l} for f, l in re.findall(r'frame:(\d+),label:"([^"]+)"', km.group(0))]
    else:
        key_points = (prev or {}).get("keyPoints", [])
        print("警告：找不到關鍵時間點（1RL、Stun…）的陣列" + ("，沿用上次的" if key_points else ""))

    chars = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    ids = {c["id"] for c in chars}
    by_en = {}
    for c in chars:
        by_en.setdefault(norm(c["name"]["en"]), []).append(c["id"])

    units, unmatched = {}, []
    for t in top:
        en = t["name"]["en"]
        our = OVERRIDE.get(en)
        if not our:
            if en.endswith(" +"):
                cands = [i + "-treasure" for i in by_en.get(norm(en[:-2]), []) if i + "-treasure" in ids]
            else:
                cands = by_en.get(norm(en), [])
            our = cands[0] if len(cands) == 1 else None
        if not our:
            unmatched.append({"id": t["id"], "en": en})
            continue
        units[our] = {
            "top": t["id"], "w": WEAPON[t["weapon"]],
            "rate": t["baseChargeRate"], "mult": t["chargeMultiplier"],
            "hpc": t.get("hitsPerCharacter", 1), "hint": t.get("hintCharactersCount", 1),
            "int": t["attackInterval"],
        }
    # 本工具有珍藏版、nikke.top 沒有「+」版本的角色（珍藏不改充能節奏時該站就不另列）：沿用本體的參數
    for cid in sorted(ids):
        base = cid[:-len("-treasure")] if cid.endswith("-treasure") else None
        if base and cid not in units and base in units:
            units[cid] = dict(units[base], fromBase=True)
    out = {
        "source": f"nikke.top（NIKKE Arena Tools）前端資料" + (f"，版本 V{version}" if version else ""),
        "fetched": datetime.date.today().isoformat(),
        "fps": 60,
        "keyPoints": key_points,
        "units": units,
        "unmatched": unmatched,
    }
    strip = lambda d: {k: v for k, v in d.items() if k != "fetched"}
    if prev and strip(prev) == strip(out):  # 內容沒變就保留原抓取日期：排程每週跑也不會只因日期變動而產生提交
        out["fetched"] = prev["fetched"]
        print("nikketop.json 內容不變，保留抓取日期", prev["fetched"])
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    for f in RAW.glob("nikketop_*.js"):  # 清掉改版後不再引用的舊 chunk 快取
        if f.name[len("nikketop_"):] not in fetched:
            f.unlink()
    print(f"對應 {len(units)} 名角色，{len(unmatched)} 名沒有對應（{', '.join(u['en'] for u in unmatched)}）")
    print(f"寫入 {DATA / 'nikketop.json'}")


if __name__ == "__main__":
    main("--refresh" in sys.argv)
