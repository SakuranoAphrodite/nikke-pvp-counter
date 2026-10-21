#!/usr/bin/env python3
"""從上游 NIKKE Arena Planner 倉庫下載角色頭像（app/assets/avatars/<id>.webp）到專案根目錄 avatars/。

圖片為遊戲素材（© SHIFT UP / Level Infinite），上游以 MIT 授權的倉庫隨附；本工具僅作粉絲用途展示。
只下載本地沒有的檔案；加 --refresh 全部重抓。
"""
import json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "avatars"
TREE = "https://api.github.com/repos/williamchong/nikke-arena-planner/git/trees/HEAD?recursive=1"
RAW = "https://raw.githubusercontent.com/williamchong/nikke-arena-planner/master/"
UA = {"User-Agent": "Mozilla/5.0 (nikke-pvp-counter fetch script)"}


def main():
    OUT.mkdir(exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(TREE, headers=UA), timeout=60) as r:
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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
