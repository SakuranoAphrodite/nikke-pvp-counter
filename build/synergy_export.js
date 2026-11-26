// nikke-synergy.com 角色表匯出：在瀏覽器打開 https://nikke-synergy.com/index_en ，按 F12 → Console，
// 把這整個檔案貼進去按 Enter，會下載 synergy-raw.json；放到 build/data/ 後執行 python build/build.py --merge 。
// 不能下載的環境（例如 Claude 的內建瀏覽器）：先跑 python build/synergy_receive.py，再在 Console 設 window.SYNERGY_RECEIVER = 'http://localhost:8766/save' 後貼本檔，JSON 會 POST 給它寫檔。
// 匯出的只是網站前端已載入到你瀏覽器裡的角色表（名稱、武器、爆裂、出場日期、彈藥…）與譯名表，不含技能文字，不下載圖片。
(async () => {
  const key = Object.keys(localStorage).find(k => /^character_(sim_all_|data_)v/.test(k));
  if (!key) throw new Error('找不到角色資料快取：請先重新整理頁面，等網站載入角色後再執行一次');
  const arr = JSON.parse(localStorage.getItem(key));
  const trUrl = performance.getEntriesByType('resource').map(e => e.name).find(u => /translations\.runtime/.test(u))
    || [...document.scripts].map(s => s.src).find(u => /translations\.runtime/.test(u));
  const names = {};
  if (trUrl) {
    const tr = await fetch(trUrl).then(r => r.text());
    const rx = /(?:"((?:[^"\\]|\\.)+)"|([^\s,{}:"]+)):\{en:"((?:[^"\\]|\\.)*)",ko:"((?:[^"\\]|\\.)*)",zh:"((?:[^"\\]|\\.)*)"\}/g;
    let m;
    while ((m = rx.exec(tr))) {
      const k = m[1] !== undefined ? JSON.parse('"' + m[1] + '"') : m[2];
      if (!(k in names)) names[k] = { en: m[3], ko: m[4], zh: m[5] };
    }
  } else {
    console.warn('找不到譯名表（translations.runtime），匯出的資料會沒有英文／繁中名，build.py 會用英文名對不到的角色列出來');
  }
  const keep = ['id', 'name', 'weapon_type', 'burst_type', 'class_type', 'company', 'code_type', 'release_date', 'treasure_status',
    'gacha_origin', 'is_free', 'has_spare_body', 'ammo', 'charge_multiplier', 'charge_time', 'reload_original', 'burst_cooltime',
    'normal_attack_multiplier', 'core_attack_multiplier', 'image_public_url'];
  const rows = arr.map(r => { const o = {}; for (const k of keep) o[k] = r[k]; const t = names[r.name]; o.en = t ? t.en : null; o.ko = t ? t.ko : null; o.zh = t ? t.zh : null; return o; });
  const out = {
    version: Number((key.match(/_v(\d+)/) || [])[1]) || null,  // 和既有檔案一致，存成數字
    exported: new Date().toISOString().slice(0, 10),
    lang: key.split('_').pop(),
    count: rows.length,
    missingTranslation: rows.filter(r => !r.en).map(r => r.name),
    translationKeys: Object.keys(names).length,
    rows,
    names: Object.fromEntries(rows.filter(r => names[r.name]).map(r => [r.name, names[r.name]])),
  };
  const json = JSON.stringify(out, null, 0);
  if (window.SYNERGY_RECEIVER) {  // 由本機的 build/synergy_receive.py 接收（Claude 用內建瀏覽器匯出時：那個瀏覽器不能下載、也不能寫剪貼簿）
    const f = document.createElement('form'); f.method = 'POST'; f.action = window.SYNERGY_RECEIVER;
    const i = document.createElement('input'); i.type = 'hidden'; i.name = 'data'; i.value = json;
    f.appendChild(i); document.body.appendChild(f); f.submit();
  } else {
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'synergy-raw.json'; a.click();
  }
  console.log('synergy-raw.json：' + rows.length + ' 名角色，譯名 ' + Object.keys(out.names).length + ' 筆，缺譯名：' + (out.missingTranslation.join('、') || '無'));
})();
