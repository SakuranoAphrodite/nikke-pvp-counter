#!/usr/bin/env python3
"""接收瀏覽器匯出的 synergy-raw.json 的本機伺服器。

nikke-synergy 擋程式抓取，角色表要在瀏覽器裡用 synergy_export.js 匯出；手動操作時它會直接下載檔案。
Claude 用內建瀏覽器匯出時，那個瀏覽器既不能下載也不能寫系統剪貼簿，所以改由這個伺服器接收：
  1. python build/synergy_receive.py          （或 .claude/launch.json 的 synergy-receiver；預設 port 8766，只聽 127.0.0.1）
  2. 在 nikke-synergy 頁面先設 window.SYNERGY_RECEIVER = "http://localhost:8766/save"，再執行 synergy_export.js，
     腳本就會把 JSON 以表單 POST 送到這裡而不是下載
  3. 這裡確認是含 rows 的合法 JSON 後寫入 build/data/synergy-raw.json，回應寫入筆數與原文的 SHA-256（可和頁面端算的核對）
收到一筆後仍繼續跑，Ctrl+C 結束。
"""
import hashlib, json, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "synergy-raw.json"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8766


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, msg):
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._reply(204, "")

    def do_GET(self):
        self._reply(200, f"synergy-raw.json 接收伺服器在跑，會寫入 {OUT}。在 nikke-synergy 頁面設 window.SYNERGY_RECEIVER 後執行 synergy_export.js。")

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
        if "application/x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
            raw = urllib.parse.parse_qs(raw).get("data", [""])[0]
        try:
            d = json.loads(raw)
            if not isinstance(d.get("rows"), list) or not d["rows"]:
                raise ValueError("沒有 rows")
        except Exception as e:
            self._reply(400, f"不是合法的匯出資料：{e}")
            return
        OUT.write_text(json.dumps(d, ensure_ascii=False, indent=0) + chr(10), encoding="utf-8")
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        msg = f"已寫入 {OUT}：{len(d['rows'])} 名角色，匯出日 {d.get('exported')}，版本 {d.get('version')}，原文 {len(raw)} 字元，SHA-256 {sha}"
        print(msg, flush=True)
        self._reply(200, msg)

    def log_message(self, fmt, *args):
        print(self.address_string(), fmt % args, flush=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"synergy-raw.json 接收伺服器：POST http://localhost:{PORT}/save → {OUT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
