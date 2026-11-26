#!/usr/bin/env python3
"""從上游 NIKKE Arena Planner 倉庫下載角色頭像（app/assets/avatars/<id>.webp）到專案根目錄 avatars/。

圖片為遊戲素材（© SHIFT UP / Level Infinite），上游以 MIT 授權的倉庫隨附；本工具僅作粉絲用途展示。
只下載本地沒有的檔案；加 --refresh 全部重抓。
GitHub Actions 裡會帶 GITHUB_TOKEN 呼叫 GitHub API（匿名額度在共用 runner 上常被用完）；上游清單抓不到時略過，仍會補 nikke-synergy 的新角色頭像。
"""
import json, os, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "avatars"
TREE = "https://api.github.com/repos/williamchong/nikke-arena-planner/git/trees/HEAD?recursive=1"
RAW = "https://raw.githubusercontent.com/williamchong/nikke-arena-planner/master/"
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)"}


def upstream():
    api = dict(UA)
    if os.environ.get("GITHUB_TOKEN"):
        api["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(TREE, headers=api), timeout=60) as r:
        tree = json.loads(r.read().decode("utf-8"))["tree"]
    files = [t["path"] for t in tree if t["path"].startswith("app/assets/avatars/") and t["path"].endswith(".webp")]
    done = skipped = 0
    for p in files:
        dest = OUT / Path(p).name
        if dest.exists() and "--refresh" not in sys.argv:
            skipped += 1
            continue
        with urllib.request.urlopen(urllib.request.Request(RAW + p, headers=UA), timeout=60) as r:
            dest.write_bytes(r.read())
        done += 1
    print(f"頭像：下載 {done}，已存在 {skipped}，共 {len(files)}，目錄 {OUT}")


def main():
    OUT.mkdir(exist_ok=True)
    try:
        upstream()
    except Exception as e:
        print(f"上游倉庫的頭像清單抓取失敗，略過：{e}")
    # 上游還沒收錄、由 nikke-deck 補進角色庫的新角色：characters.json 記有 nikke-synergy 的角色圖網址（avatarUrl）與檔名（avatarFile）
    chars = json.loads((HERE / "data" / "characters.json").read_text(encoding="utf-8"))
    extra = 0
    for c in chars:
        url, fn = c.get("avatarUrl"), c.get("avatarFile")
        if not url or not fn:
            continue
        dest = OUT / fn
        if dest.exists() and "--refresh" not in sys.argv:
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                dest.write_bytes(r.read())
            extra += 1
        except Exception as e:
            print(f"  {c['id']} 的頭像下載失敗（{url}）：{e}")
    if extra:
        print(f"新角色頭像：下載 {extra}（來源 nikke-synergy 的角色圖）")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
