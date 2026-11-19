(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- dil / language
  const I18N = {
    tr: {
      title: 'Masaüstü Düzenleyici', by: 'Desktop Organizer by Lionstone', desktop: 'Masaüstü',
      c_moved: 'Taşınan dosya', c_folders: 'Kullanılan hedef klasör', c_dups: 'Kopyalar’a taşınan',
      c_dups_sub: 'silinmez · alan kazandırmaz', c_bytes: 'Taşınan toplam boyut',
      plan: 'plan', skipped: 'atlanan', files: 'dosya',
      start: 'Başlat', resume_start: 'Kaldığı Yerden Devam Et', pause: 'Duraklat', resume: 'Devam Et',
      stop: 'Durdur', undo: 'Son İşlemi Geri Al', close: 'Panoyu Kapat',
      hint: 'Dosyalar adsız kutularla gösterilir. Adlar, yollar ve küçük resimler bu panoya gelmez.',
      op: (id, n, per) => `İşlem ${id} · ${n} dosya planlandı` + (per > 1 ? ` · her kutu en çok ${per} dosya` : ''),
      start_needs_approval: 'Plan onaylanmadan başlatılamaz',
      st: {
        hazir: 'Onay bekleniyor', hazir_ok: 'Başlatmaya hazır', devam_hazir: 'Devam etmeye hazır',
        calisiyor: 'Düzenleniyor', duraklatiliyor: 'Mevcut dosya bitiriliyor…', duraklatildi: 'Duraklatıldı',
        durduruluyor: 'Durduruluyor…', durduruldu: 'Durduruldu', tamamlandi: 'Tamamlandı',
        geri_aliniyor: 'Geri alınıyor…', geri_alindi: 'Geri alındı', hata: 'Hata', kapandi: 'Pano kapandı',
      },
      n_preview: 'Önizleme. Sohbette “Planı onaylıyorum” yazılıp plan onaylanınca Başlat etkinleşir.',
      n_resume: (k) => `Bu işlem daha önce yarıda kaldı. Taşınmış dosyalara dokunulmaz; kalan ${k} dosya aynı onaylı planla taşınır.`,
      n_running: (s) => `Görsel akış yaklaşık ${s} saniyeye yayılır; kutu yalnızca taşıma doğrulanınca rafa iner.`,
      n_skipped: (k) => `${k} dosya taşınmadı (plandan sonra değişti, kilitli ya da hedef uygun değil). Ayrıntılar terminal özetinde.`,
      n_stopped: 'Durduruldu. Önceden taşınanlar yerinde kaldı; geri almak için düğmeyi kullanabilirsiniz.',
      n_done: 'Tüm planlanan dosyalar doğrulanarak taşındı.',
      n_error: 'Bir hata oluştu.',
      n_closed: 'Pano kapatıldı. Bu sekmeyi kapatabilirsiniz.',
      n_nokey: 'Oturum anahtarı yok. Terminalde yazan pano adresini açın.',
      n_unreachable: (m) => `Sunucuya ulaşılamıyor: ${m}`,
      u_none: 'Geri alınacak işlem yok.',
      u_done: (id, k) => `İşlem ${id}: ${k} dosya eski yerine döndü.`,
      u_conflict: (k) => `${k} dosyanın eski yeri dolu; yerinde bırakıldı.`,
      u_refused: (k) => `${k} dosya taşındıktan sonra değiştiği/taşındığı için zorla geri alınmadı.`,
      u_error: (k) => `${k} hata.`,
      confirm_stop: 'Durdurulsun mu? Devam eden dosya tamamlanır; önceden taşınanlar geri alınmaz.',
      confirm_undo: (id) => `Son işlem (${id}) geri alınacak. Dosyalar eski yerlerine döner; eski yeri dolu olanlar ve sonradan değişenler yerinde bırakılır. Devam edilsin mi?`,
      confirm_close: 'İşlem sürüyor. Devam eden dosya tamamlanıp durdurulacak ve pano kapanacak. Emin misiniz?',
      codes: {
        zaten_baslatildi: 'Bu panoda işlem zaten başlatıldı.', onay_yok: 'Plan onaylanmadı; Başlat pasif.',
        basladi: 'Başladı.', duraklatilacak: 'Mevcut dosya bitince duraklatılacak.', devam: 'Devam ediliyor.',
        calisan_yok: 'Çalışan bir işlem yok.', durdurulacak: 'Mevcut dosya bitince durdurulacak. Taşınanlar geri alınmaz.',
        once_bekle: 'Önce çalışan işlemin bitmesini bekleyin.', geri_alma_basladi: 'Geri alma başladı.',
        kapaniyor: 'Pano kapanıyor.', mesgul: 'Başka bir düzenleme ya da geri alma sürüyor.',
      },
      cats: { '01': 'Görseller', '02': 'YZ Görselleri', '03': 'Ekran Görüntüleri', '04': 'Videolar', '05': 'Ses',
        '06': 'Belgeler', '07': 'Tablolar', '08': 'Sunumlar', '09': 'Web Sayfaları', '10': 'Arşivler',
        '11': 'Kurulum', '12': 'Diğer', '13': 'Kopyalar' },
      shelf: 'rafı', locale: 'tr-TR',
    },
    en: {
      title: 'Desktop Organizer', by: 'by Lionstone', desktop: 'Desktop',
      c_moved: 'Files moved', c_folders: 'Target folders used', c_dups: 'Moved to Duplicates',
      c_dups_sub: 'never deleted · frees no space', c_bytes: 'Total size moved',
      plan: 'plan', skipped: 'skipped', files: 'files',
      start: 'Start', resume_start: 'Resume where it stopped', pause: 'Pause', resume: 'Resume',
      stop: 'Stop', undo: 'Undo last run', close: 'Close dashboard',
      hint: 'Files appear as anonymous boxes. No names, paths or thumbnails reach this dashboard.',
      op: (id, n, per) => `Run ${id} · ${n} files planned` + (per > 1 ? ` · up to ${per} files per box` : ''),
      start_needs_approval: 'The plan must be approved first',
      st: {
        hazir: 'Waiting for approval', hazir_ok: 'Ready to start', devam_hazir: 'Ready to resume',
        calisiyor: 'Organizing', duraklatiliyor: 'Finishing current file…', duraklatildi: 'Paused',
        durduruluyor: 'Stopping…', durduruldu: 'Stopped', tamamlandi: 'Done',
        geri_aliniyor: 'Undoing…', geri_alindi: 'Undone', hata: 'Error', kapandi: 'Dashboard closed',
      },
      n_preview: 'Preview. Start unlocks once the plan is approved in the chat with “Planı onaylıyorum”.',
      n_resume: (k) => `This run was interrupted earlier. Files already moved stay put; the remaining ${k} files follow the same approved plan.`,
      n_running: (s) => `The visual flow spans about ${s} seconds; a box lands on its shelf only after the move is verified.`,
      n_skipped: (k) => `${k} files were not moved (changed after planning, locked, or the target was unsafe). See the terminal summary.`,
      n_stopped: 'Stopped. Files already moved stay where they are; use Undo to move them back.',
      n_done: 'Every planned file was moved and verified.',
      n_error: 'Something went wrong.',
      n_closed: 'Dashboard closed. You can close this tab.',
      n_nokey: 'No session key. Open the dashboard address printed in the terminal.',
      n_unreachable: (m) => `Cannot reach the local server: ${m}`,
      u_none: 'Nothing to undo.',
      u_done: (id, k) => `Run ${id}: ${k} files returned to their original place.`,
      u_conflict: (k) => `${k} files left in place because their original spot is taken.`,
      u_refused: (k) => `${k} files changed or moved after organizing, so they were not forced back.`,
      u_error: (k) => `${k} errors.`,
      confirm_stop: 'Stop now? The current file finishes; files already moved are not moved back.',
      confirm_undo: (id) => `Undo the last run (${id})? Files go back to where they were; files whose spot is taken or that changed are left in place.`,
      confirm_close: 'A run is in progress. The current file will finish, the run stops and the dashboard closes. Continue?',
      codes: {
        zaten_baslatildi: 'This run was already started.', onay_yok: 'The plan is not approved; Start is disabled.',
        basladi: 'Started.', duraklatilacak: 'Pausing after the current file.', devam: 'Resuming.',
        calisan_yok: 'Nothing is running.', durdurulacak: 'Stopping after the current file. Moved files stay moved.',
        once_bekle: 'Wait for the current run to finish first.', geri_alma_basladi: 'Undo started.',
        kapaniyor: 'Closing the dashboard.', mesgul: 'Another organize or undo run is in progress.',
      },
      cats: { '01': 'Images', '02': 'AI Images', '03': 'Screenshots', '04': 'Videos', '05': 'Audio',
        '06': 'Documents', '07': 'Spreadsheets', '08': 'Presentations', '09': 'Web Pages', '10': 'Archives',
        '11': 'Installers', '12': 'Other', '13': 'Duplicates' },
      shelf: 'shelf', locale: 'en-US',
    },
  };

  let LANG = 'tr';
  try {
    LANG = localStorage.getItem('md-lang') || ((navigator.language || '').toLowerCase().startsWith('tr') ? 'tr' : 'en');
  } catch (e) {
    LANG = (navigator.language || '').toLowerCase().startsWith('tr') ? 'tr' : 'en';
  }
  if (!I18N[LANG]) LANG = 'tr';
  const T = () => I18N[LANG];

  // Oturum anahtarı adres çubuğundan alınır, yalnızca bu sekmede tutulur.
  let KEY = new URLSearchParams(location.search).get('k');
  try {
    if (KEY) sessionStorage.setItem('mdk', KEY);
    else KEY = sessionStorage.getItem('mdk');
  } catch (e) { /* depolama kapalı olabilir */ }
  if (KEY) history.replaceState(null, '', '/');

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const BUSY = ['calisiyor', 'duraklatiliyor', 'duraklatildi', 'durduruluyor', 'geri_aliniyor'];
  const PILL = {
    hazir: 'warn', calisiyor: 'run', duraklatiliyor: 'warn', duraklatildi: 'warn', durduruluyor: 'warn',
    durduruldu: 'warn', tamamlandi: 'ok', geri_aliniyor: 'run', geri_alindi: 'ok', hata: 'err',
  };

  let built = false;
  let closed = false;
  let last = null;
  let lastAction = null; // {kod, mesaj, err}
  const groups = [];
  const racks = {};
  const shelves = {};

  function fmtSize(n) {
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let v = n, i = 0;
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    if (i === 0) return `${v} B`;
    const s = v.toFixed(1);
    return `${LANG === 'tr' ? s.replace('.', ',') : s} ${u[i]}`;
  }
  const fmtNum = (n) => n.toLocaleString(T().locale);

  function rng(seedText) {
    let h = 2166136261;
    for (const ch of seedText) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
    return () => {
      h += 0x6D2B79F5;
      let t = h;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  async function api(path, method = 'GET') {
    const r = await fetch(path, {
      method, cache: 'no-store', credentials: 'omit',
      headers: { 'X-Oturum-Anahtari': KEY || '' },
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      const e = new Error(body.mesaj || body.hata || `HTTP ${r.status}`);
      e.kod = body.kod;
      throw e;
    }
    return body;
  }

  function applyStatic() {
    document.documentElement.lang = LANG;
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const v = T()[el.dataset.i18n];
      if (typeof v === 'string') el.textContent = v;
    });
    document.querySelectorAll('.lang button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === LANG)));
    for (const [k, sh] of Object.entries(shelves)) {
      sh.name.textContent = `${k} · ${T().cats[k]}`;
      sh.rack.setAttribute('aria-label', `${T().cats[k]} ${T().shelf}`);
    }
    if (last) render(last);
  }

  function build(s) {
    const box = $('shelves');
    const colors = {};
    for (const c of s.kategoriler) {
      colors[c.k] = c.renk;
      const row = document.createElement('div');
      row.className = 'shelf';
      row.style.setProperty('--c', c.renk);
      row.innerHTML = '<div class="tag"><span class="dot"></span><span class="name"></span><span class="num"></span></div><div class="rack"></div>';
      const name = row.querySelector('.name');
      name.title = c.klasor; // gerçek klasör adı (kategori klasörü; kullanıcı yolu değil)
      shelves[c.k] = { name, num: row.querySelector('.num'), rack: row.querySelector('.rack'), plan: c.plan };
      racks[c.k] = shelves[c.k].rack;
      box.appendChild(row);
    }
    // Çok dosyada kutular gruplanır; sayaçlar yine kesin değerdir.
    const N = s.ogeler.length;
    const per = Math.max(1, Math.ceil(N / 240));
    const byCat = {};
    for (const it of s.ogeler) (byCat[it.k] = byCat[it.k] || []).push(it.id);
    for (const k of Object.keys(byCat)) {
      const ids = byCat[k];
      for (let i = 0; i < ids.length; i += per) {
        const el = document.createElement('div');
        el.className = 'box' + (per > 1 ? ' big' : '');
        el.style.setProperty('--c', colors[k]);
        const chunk = ids.slice(i, i + per);
        el.title = chunk.length > 1 ? `${chunk[0]} … ${chunk[chunk.length - 1]} (${chunk.length})` : chunk[0];
        groups.push({ ids: chunk, k, el, place: 'cloud', hole: null });
      }
    }
    const rand = rng(s.islem);
    const order = groups.slice().sort(() => rand() - 0.5);
    const cloud = $('cloud');
    for (const g of order) {
      g.el.style.rotate = `${Math.round((rand() - 0.5) * 24)}deg`;
      g.el.style.margin = `${Math.round(rand() * 6)}px ${Math.round(rand() * 5)}px`;
      cloud.appendChild(g.el);
    }
    built = true;
    built_per = per;
    applyStatic();
  }
  let built_per = 1;

  function fly(g, to) {
    const el = g.el;
    const first = el.getBoundingClientRect();
    if (to === 'shelf') {
      // Bulutta yer tutucu bırak: diğer kutular kaymasın.
      const hole = el.cloneNode(false);
      hole.style.visibility = 'hidden';
      hole.removeAttribute('title');
      el.replaceWith(hole);
      g.hole = hole;
      el.style.rotate = '0deg';
      racks[g.k].appendChild(el);
    } else {
      if (g.hole) { g.hole.replaceWith(el); g.hole = null; } else { $('cloud').appendChild(el); }
      el.style.rotate = `${Math.round((Math.random() - 0.5) * 24)}deg`;
    }
    g.place = to;
    if (reduceMotion.matches) return;
    const lastR = el.getBoundingClientRect();
    const dx = first.left - lastR.left;
    const dy = first.top - lastR.top;
    el.classList.add('flying');
    const anim = el.animate([
      { transform: `translate(${dx}px, ${dy}px) scale(1.2)` },
      { transform: `translate(${dx * 0.45}px, ${dy * 0.45 - 70}px) scale(1.35)`, offset: 0.45 },
      { transform: 'translate(0, 0) scale(1)' },
    ], { duration: 950, easing: 'cubic-bezier(.3,.7,.2,1)' });
    anim.onfinish = anim.oncancel = () => el.classList.remove('flying');
  }

  function render(s) {
    if (!built) build(s);
    last = s;
    const t = T();
    const state = Object.fromEntries(s.ogeler.map((it) => [it.id, it.d]));

    // Kutular yalnızca doğrulanmış duruma göre hareket eder.
    let inCloud = 0;
    const onShelf = {};
    for (const g of groups) {
      const st = g.ids.map((id) => state[id]);
      const allMoved = st.every((d) => d === 'tasindi');
      const allBack = st.every((d) => d === 'geri_alindi' || d === 'bekliyor');
      const skipped = st.some((d) => d === 'atlandi');
      if (allMoved && g.place !== 'shelf') fly(g, 'shelf');
      else if (allBack && g.place === 'shelf') fly(g, 'cloud');
      g.el.classList.toggle('skip', skipped);
      if (g.place === 'cloud') inCloud += g.ids.length;
    }
    for (const it of s.ogeler) if (it.d === 'tasindi') onShelf[it.k] = (onShelf[it.k] || 0) + 1;
    for (const [k, v] of Object.entries(shelves)) v.num.textContent = `${onShelf[k] || 0} / ${v.plan}`;
    $('cloud-count').textContent = `· ${fmtNum(inCloud)} ${t.files}`;
    $('op').textContent = t.op(s.islem, fmtNum(s.ogeler.length), built_per);

    const c = s.sayaclar;
    $('c-moved').textContent = fmtNum(c.tasinan);
    $('c-moved-sub').textContent = `${t.plan}: ${fmtNum(s.plan_dosya)}` + (c.atlanan ? ` · ${t.skipped}: ${fmtNum(c.atlanan)}` : '');
    $('c-folders').textContent = fmtNum(c.klasor);
    $('c-folders-sub').textContent = `${t.plan}: ${fmtNum(s.kategoriler.length)}`;
    $('c-dups').textContent = fmtNum(c.kopyalara);
    $('c-bytes').textContent = fmtSize(c.boyut);
    $('c-bytes-sub').textContent = `${t.plan}: ${fmtSize(s.plan_boyut)}`;
    const done = s.ogeler.filter((it) => it.d !== 'bekliyor' && it.d !== 'tasiniyor').length;
    $('bar').style.width = s.plan_dosya ? `${(100 * done) / s.plan_dosya}%` : '0%';

    let label = t.st[s.durum] || s.durum;
    let cls = PILL[s.durum] || '';
    if (s.durum === 'hazir' && s.onayli) {
      label = s.devam_edilebilir ? t.st.devam_hazir : t.st.hazir_ok;
      cls = 'ok';
    }
    if (closed) { label = t.st.kapandi; cls = ''; }
    const pill = $('status');
    pill.textContent = label;
    pill.className = `pill ${cls}`;

    const busy = BUSY.includes(s.durum);
    const running = ['calisiyor', 'duraklatiliyor', 'duraklatildi'].includes(s.durum);
    const bs = $('b-start');
    bs.textContent = s.devam_edilebilir ? t.resume_start : t.start;
    bs.disabled = closed || !(s.onayli && s.durum === 'hazir');
    bs.title = s.onayli ? '' : t.start_needs_approval;
    $('b-pause').disabled = closed || !running;
    $('b-pause').textContent = ['duraklatiliyor', 'duraklatildi'].includes(s.durum) ? t.resume : t.pause;
    $('b-stop').disabled = closed || !running;
    $('b-undo').disabled = closed || busy || !s.geri_alinabilir;
    $('b-close').disabled = closed;

    const n = $('notice');
    let msg = '';
    let err = false;
    if (closed) msg = t.n_closed;
    else if (s.durum === 'hata') { msg = `${t.n_error} ${s.mesaj || ''}`.trim(); err = true; }
    else if (lastAction && lastAction.fresh) { msg = lastAction.text(); err = lastAction.err; }
    else if (!s.onayli) msg = t.n_preview;
    else if (s.geri_alma_raporu) msg = undoText(s.geri_alma_raporu);
    else if (s.devam_edilebilir) msg = t.n_resume(fmtNum(s.kalan));
    else if (s.durum === 'tamamlandi' || s.durum === 'durduruldu') {
      msg = c.atlanan ? t.n_skipped(fmtNum(c.atlanan)) : (s.durum === 'durduruldu' ? t.n_stopped : t.n_done);
    } else if (s.durum === 'calisiyor') msg = t.n_running(Math.round(s.sure));
    n.textContent = msg;
    n.classList.toggle('err', err);
  }

  function undoText(r) {
    const t = T();
    if (!r.islem) return t.u_none;
    const parts = [t.u_done(r.islem, fmtNum(r.geri_alinan))];
    if (r.cakisma.length) parts.push(t.u_conflict(r.cakisma.length));
    if (r.reddedilen.length) parts.push(t.u_refused(r.reddedilen.length));
    if (r.hata.length) parts.push(t.u_error(r.hata.length));
    return parts.join(' ');
  }

  async function poll() {
    if (closed) return;
    try {
      render(await api('/api/durum'));
    } catch (e) {
      $('notice').textContent = KEY ? T().n_unreachable(e.message) : T().n_nokey;
      $('notice').classList.add('err');
    }
    setTimeout(poll, 450);
  }

  function showAction(kod, mesaj, err) {
    const a = { kod, mesaj, err, fresh: true, text: () => (T().codes[kod] || mesaj || '') };
    lastAction = a;
    setTimeout(() => { a.fresh = false; }, 4000);
    if (last) render(last);
  }

  async function act(path, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return false;
    try {
      const r = await api(path, 'POST');
      showAction(r.kod, r.mesaj, false);
      return true;
    } catch (e) {
      showAction(e.kod, e.message, true);
      return false;
    }
  }

  document.querySelectorAll('.lang button').forEach((b) => b.addEventListener('click', () => {
    LANG = b.dataset.lang;
    try { localStorage.setItem('md-lang', LANG); } catch (e) { /* yok say */ }
    applyStatic();
  }));
  $('b-start').addEventListener('click', () => act('/api/baslat'));
  $('b-pause').addEventListener('click', () => act('/api/duraklat'));
  $('b-stop').addEventListener('click', () => act('/api/durdur', T().confirm_stop));
  $('b-undo').addEventListener('click', () => act('/api/geri-al', T().confirm_undo(last && last.geri_alinacak_islem)));
  $('b-close').addEventListener('click', async () => {
    const running = last && BUSY.includes(last.durum);
    if (running && !window.confirm(T().confirm_close)) return;
    if (await act('/api/kapat')) {
      closed = true;
      if (last) render(last);
    }
  });

  applyStatic();
  poll();
})();
