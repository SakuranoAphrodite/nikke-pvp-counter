#!/usr/bin/env python3
"""抓 nikke.top（NIKKE Arena Tools）的逐幀充能參數 → build/data/nikketop.json

nikke.top 是逐幀（60 fps）模擬競技場充能的網站：每位角色依武器有固定的射擊節奏，
每次命中充能 baseChargeRate × chargeMultiplier，全隊累積到 100 就是「充滿」，
之後 B1 +24 幀、B2 +32 幀、B3 +32 幀開爆裂。網站沒有公開 API，參數寫在前端 JS 裡，
這支腳本把它抓下來、用英文名對應到本工具的角色 id。

用法：
  python build/fetch_nikketop.py            # 用 build/data/raw/ 的快取（沒有才下載）
  python build/fetch_nikketop.py --refresh  # 重新下載
"""
import json, re, sys, datetime, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SITE = "https://nikke.top/"
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)"}
WEAPON = {1: "SG", 2: "RL", 3: "SR", 4: "AR", 5: "SMG", 6: "MG"}
# nikke.top 英文名 → 本工具 id（自動對應失敗時的手動對照；" +" 結尾表示珍藏）
OVERRIDE = {}


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


def read_js_string(src: str, start: int) -> str:
    """從 src[start]（引號或反引號）開始讀一個 JS 字串，處理反斜線跳脫。"""
    q = src[start]
    i = start + 1
    out = []
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            out.append(src[i + 1])
            i += 2
            continue
        if ch == q:
            break
        out.append(ch)
        i += 1
    return "".join(out)


def extract_table(src: str, key: str):
    m = re.search(r'"%s"\s*:\s*JSON\.parse\(\s*' % re.escape(key), src)
    if not m:
        raise SystemExit(f"找不到 {key}")
    return json.loads(read_js_string(src, m.end()))


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main(refresh: bool):
    index = cached("nikketop_index.html", SITE, refresh)
    im = re.search(r'/assets/(index-[^"\']+\.js)', index)
    if not im:
        raise SystemExit("首頁找不到 index bundle")
    idx = cached("nikketop_index.js", SITE + "assets/" + im.group(1), refresh)
    vm = re.search(r'"V(\d+\.\d+\.\d+)"', idx)
    version = vm.group(1) if vm else None
    m = re.search(r'(HomePage-[A-Za-z0-9_-]+\.js)', idx)  # HomePage 是 index bundle 動態載入的
    if not m:
        raise SystemExit("index bundle 找不到 HomePage bundle")
    src = cached("nikketop_HomePage.js", SITE + "assets/" + m.group(1), refresh)

    top = extract_table(src, "global-nikkes")
    km = re.search(r'\[\{frame:76,label:"1RL"\}.*?\]', src)
    key_points = [{"f": int(f), "label": l} for f, l in re.findall(r'frame:(\d+),label:"([^"]+)"', km.group(0))] if km else []

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
    (DATA / "nikketop.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"對應 {len(units)} 名角色，{len(unmatched)} 名沒有對應（{', '.join(u['en'] for u in unmatched)}）")
    print(f"寫入 {DATA / 'nikketop.json'}")


if __name__ == "__main__":
    main("--refresh" in sys.argv)
