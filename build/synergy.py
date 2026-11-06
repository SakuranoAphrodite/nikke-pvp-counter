#!/usr/bin/env python3
"""nikke-synergy.com 的角色表（data/synergy-raw.json）：對應到本工具的角色 id，提供出場日期與繁中譯名。

nikke-synergy 擋程式抓取（用 curl／Python 連線會被重設），所以資料要用瀏覽器匯出：
  1. 用瀏覽器打開 https://nikke-synergy.com/index_en ，按 F12 打開 Console
  2. 把 build/synergy_export.js 的內容整段貼進 Console 執行，會下載 synergy-raw.json
  3. 把檔案放到 build/data/synergy-raw.json，執行 python build/build.py --merge（或 --update）
匯出的是該站前端已載入的角色表（名稱、武器、爆裂、職業、企業、屬性、出場日期、彈藥、裝填、蓄力…）與
它的譯名表（日文簡稱 → 英／韓／繁中），不含技能文字；圖片只記網址，不下載。
"""
import json, re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
FILE = DATA / "synergy-raw.json"
# synergy 的日文簡稱 → 本工具 id（英文名與繁中名都對不上時的手動對照）
OVERRIDE = {
    "アヤナミ風": "rei-ayanami-tentative-name",
    "クイーン（真）": "queen",
    "ソルジャーE.G.": "soldier-eg",
    "ソルジャーF.A.": "soldier-fa",
    "ソルジャーО.W.": "soldier-ow",
    "神紅蓮": "scarlet-goddeath",  # 該站譯名表還沒有她
}


def norm(s):
    return re.sub(r"[\s:：・･·\-_＋+()（）]", "", s or "").lower()


def first_date(s):
    """release_date 可能是「2022-11-04」或「2026-10-29~2026-11-19 / 2027-…」（多次復刻），取最早的那個日期＝初次出場。"""
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", s or "")
    return min(dates) if dates else None


def load():
    """讀 synergy-raw.json；沒有檔案時回傳 None。每筆補上 en／ko／zh（來自譯名表）、releaseDate（初次出場日）與 treasure（是否珍藏版）。"""
    if not FILE.exists():
        return None
    d = json.loads(FILE.read_text(encoding="utf-8"))
    names = d.get("names") or {}
    rows = []
    for r in d["rows"]:
        t = names.get(r["name"]) or {}
        r = dict(r)
        for k in ("en", "ko", "zh"):
            r[k] = r.get(k) or t.get(k)
        r["releaseDate"] = first_date(r.get("release_date"))
        r["treasure"] = r.get("treasure_status") == "適用済"
        rows.append(r)
    return {"exported": d.get("exported"), "version": d.get("version"), "rows": rows}


def base_en(r):
    """去掉珍藏標記的英文名。"""
    return re.sub(r"\s*\(Favorite Item\)", "", r.get("en") or "").strip()


def matcher(chars):
    """回傳 find(synergy 角色) → 本工具 id。先查手動對照，再用英文名，最後用繁中名；珍藏版對到 <id>-treasure。"""
    ids = {c["id"] for c in chars}
    by_en, by_zh = {}, {}
    for c in chars:
        by_en.setdefault(norm(c["name"]["en"]), c["id"])
        by_zh.setdefault(norm(c["name"].get("zh-TW")), c["id"])

    def find(r):
        tre = r.get("treasure") or "(Favorite Item)" in (r.get("en") or "")
        mid = OVERRIDE.get(r["name"])
        if not mid and r.get("en"):
            mid = by_en.get(norm(base_en(r)))
        if not mid and r.get("zh"):
            mid = by_zh.get(norm(re.sub(r"\s*\(珍藏品\)", "", r["zh"])))
        if mid and tre and not mid.endswith("-treasure"):
            mid = mid + "-treasure"
        return mid if mid in ids else None
    return find


def by_deck_name(syn):
    """(norm(英文名), 是否珍藏) → synergy 角色，給 nikke-deck 的新角色查繁中名與出場日期用。"""
    out = {}
    if not syn:
        return out
    for r in syn["rows"]:
        if r.get("en"):
            out.setdefault((norm(base_en(r)), bool(r.get("treasure"))), r)
    return out
