#!/usr/bin/env python3
"""把所有模板的 counters / counteredBy 宣稱拿去和 nikkeari 冠軍競技場資料對照。
A counters B：找「含 A 必要角」的隊 vs「含 B 必要角」的隊（珍藏與一般版視為同一人）的勝負。
輸出 data/counter-audit.json（每條宣稱的場數與勝率）並印出與實戰相反的宣稱。"""
import json, sys, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
DATA = Path(__file__).resolve().parent / "data"
A = json.loads((DATA / "arena-stats.json").read_text(encoding="utf-8"))
teams = [t[0].split(",") for t in A["teams"]]
nt = lambda x: x[:-9] if x.endswith("-treasure") else x
teams_nt = [set(map(nt, t)) for t in teams]
beaten = {int(k): v for k, v in A["beatenBy"].items()}

tpls = []
for f in ("templates.json", "templates-extra.json", "templates-mined.json", "templates-community.json"):
    p = DATA / f
    if p.exists():
        tpls += json.loads(p.read_text(encoding="utf-8"))
by_arch = collections.defaultdict(list)
for t in tpls:
    by_arch[t["archetype"]].append(t)

def match(req):
    r = set(map(nt, req))
    return {i for i, s in enumerate(teams_nt) if r <= s}

def record(sa, sb):
    w = l = 0
    for e in sb:
        for j, n, *_ in beaten.get(e, []):
            if j in sa and j not in sb: w += n
    for m in sa:
        for j, n, *_ in beaten.get(m, []):
            if j in sb and j not in sa: l += n
    return w, l

cache = {}
def arch_record(a, b):
    """A 體系（任一模板的必要角）對 B 體系：各模板組合加總。"""
    key = (a, b)
    if key in cache: return cache[key]
    w = l = 0
    for ta in by_arch.get(a, []):
        sa = match(ta["required"])
        for tb in by_arch.get(b, []):
            sb = match(tb["required"])
            ww, ll = record(sa, sb); w += ww; l += ll
    cache[key] = (w, l); return cache[key]

out = []; bad = []
for t in tpls:
    for kind, lst in (("counters", t.get("counters", [])), ("counteredBy", t.get("counteredBy", []))):
        for other in lst:
            if other not in by_arch: continue
            w, l = arch_record(t["archetype"], other)
            n = w + l; wr = w / n if n else None
            row = {"tpl": t["id"], "arch": t["archetype"], "kind": kind, "vs": other, "games": n, "win": round(wr * 100) if n else None}
            out.append(row)
            if n >= 30 and ((kind == "counters" and wr <= 0.45) or (kind == "counteredBy" and wr >= 0.55)):
                bad.append(row)
(DATA / "counter-audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
name = {t["id"]: t["name"]["zh-TW"] for t in tpls}
aname = {}
for t in tpls: aname.setdefault(t["archetype"], t["name"]["zh-TW"])
checked = [r for r in out if r["games"] >= 30]
print(f"宣稱總數 {len(out)}，有 30 場以上實戰可對照 {len(checked)}，與實戰相反 {len(bad)}")
for r in sorted(bad, key=lambda r: -r["games"]):
    print(f"  {r['kind']:11s} {name[r['tpl']][:28]:30s} → {aname.get(r['vs'], r['vs'])[:28]:30s} {r['games']:5d} 場 勝率 {r['win']}%")
