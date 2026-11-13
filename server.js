'use strict';
// Personalised-song shop: order wizard + Razorpay + admin dashboard + SongReel video rendering.
const express = require('express'), multer = require('multer'), crypto = require('crypto'), fs = require('fs'), path = require('path');
const { spawn } = require('child_process');
const { DatabaseSync } = require('node:sqlite');

const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const PORT = +process.env.PORT || 3000;
const DATA = process.env.DATA_DIR || path.join(__dirname, 'data');
const PROD = process.env.NODE_ENV === 'production';
const RZP_ID = process.env.RAZORPAY_KEY_ID || '', RZP_SECRET = process.env.RAZORPAY_KEY_SECRET || '', RZP_WH = process.env.RAZORPAY_WEBHOOK_SECRET || '';
const ADMIN_PW = process.env.ADMIN_PASSWORD || (PROD ? '' : 'admin123');
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');
const ENGINE_DIR = process.env.SONGREEL_DIR || path.join(__dirname, 'songreel');
const MOCK = !RZP_ID || !RZP_SECRET;
if (PROD && !ADMIN_PW) { console.error('ADMIN_PASSWORD must be set in production'); process.exit(1); }
if (PROD && MOCK) console.warn('WARNING: Razorpay keys missing; payments are disabled in production.');

fs.mkdirSync(path.join(DATA, 'tmp'), { recursive: true });
const db = new DatabaseSync(path.join(DATA, 'shop.db'));
db.exec(`CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE, status TEXT, plan TEXT, occasion TEXT, recipient TEXT, language TEXT, genre TEXT,
  to_name TEXT, from_name TEXT, pronounce TEXT, story TEXT, cust_name TEXT, phone TEXT, email TEXT, amount INTEGER,
  rzp_order TEXT, rzp_payment TEXT, created_at TEXT, paid_at TEXT, delivered_at TEXT, photos TEXT DEFAULT '[]',
  song_file TEXT, lrc_file TEXT, video_file TEXT, render_status TEXT DEFAULT '', notes TEXT DEFAULT '', revision_note TEXT DEFAULT '')`);

const now = () => new Date().toISOString();
const odir = id => path.join(DATA, 'orders', String(id));
const hmac = (s, k = SESSION_SECRET) => crypto.createHmac('sha256', k).update(s).digest('hex');
const safeEq = (a, b) => { a = Buffer.from(String(a)); b = Buffer.from(String(b)); return a.length === b.length && crypto.timingSafeEqual(a, b); };
const clip = (v, n) => String(v ?? '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').trim().slice(0, n);

const OCCASIONS = ['birthday', 'anniversary', 'wedding', 'love', 'diwali', 'festival', 'devotional', 'friendship', 'thank-you', 'graduation', 'reel', 'other'];
const LANGS = ['en', 'hi', 'kn', 'ta', 'te'];
const RECIPIENTS = ['partner', 'mother', 'father', 'child', 'sibling', 'friend', 'grandparent', 'teacher', 'self', 'other'];
const GENRES = ['soft-melody', 'filmy-romantic', 'classical-folk', 'pop', 'devotional', 'rap-fun', 'acoustic'];
const rate = new Map();
function limited(key, max, ms) { const t = Date.now(), a = (rate.get(key) || []).filter(x => t - x < ms); a.push(t); rate.set(key, a); return a.length > max; }

const app = express();
app.disable('x-powered-by'); app.set('trust proxy', 1);
app.use((req, res, next) => {
  res.set({ 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'strict-origin-when-cross-origin' });
  next();
});

// ---------------- Razorpay webhook (raw body, before json parser)
app.post('/api/razorpay/webhook', express.raw({ type: '*/*', limit: '1mb' }), (req, res) => {
  if (!RZP_WH) return res.status(503).end();
  const sig = req.get('x-razorpay-signature') || '';
  if (!safeEq(hmac(req.body, RZP_WH), sig)) return res.status(400).end();
  try {
    const ev = JSON.parse(req.body.toString('utf8')); const ent = ev.payload?.payment?.entity || ev.payload?.order?.entity;
    const oid = ent?.order_id || ent?.id;
    if (['payment.captured', 'order.paid'].includes(ev.event) && oid) markPaid(oid, ev.payload?.payment?.entity?.id || '');
  } catch (e) { console.error('webhook', e.message); }
  res.json({ ok: true });
});
app.use(express.json({ limit: '100kb' }));

function markPaid(rzpOrder, payId) {
  const o = db.prepare('SELECT * FROM orders WHERE rzp_order=?').get(rzpOrder);
  if (!o || o.status !== 'created') return !!o;
  db.prepare("UPDATE orders SET status='paid', rzp_payment=?, paid_at=? WHERE id=?").run(payId, now(), o.id);
  return true;
}

// ---------------- public API
const upload = multer({ dest: path.join(DATA, 'tmp'), limits: { files: 12, fileSize: 12 * 1024 * 1024, fields: 30 } });
function sniff(file) {
  const b = fs.readFileSync(file, { encoding: null }).subarray(0, 12);
  if (b[0] === 0xff && b[1] === 0xd8) return 'jpg';
  if (b.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return 'png';
  if (b.subarray(0, 4).toString() === 'RIFF' && b.subarray(8, 12).toString() === 'WEBP') return 'webp';
  return null;
}
const rm = fs => fs.forEach(f => { try { require('fs').unlinkSync(f.path); } catch { } });

app.get('/api/config', (req, res) => res.json({
  brand: CFG.brand, prices: CFG.prices, delivery: CFG.deliveryText, whatsapp: CFG.whatsapp, rzpKey: RZP_ID || null, mock: MOCK && !PROD, payReady: !MOCK
}));
app.get('/api/samples', (req, res) => {
  const d = path.join(__dirname, 'public', 'samples');
  try { res.json(fs.readdirSync(d).filter(f => /\.mp4$/i.test(f)).sort().map(f => ({ src: '/samples/' + f, label: f.replace(/\.mp4$/i, '').replace(/[-_]+/g, ' ') }))); } catch { res.json([]); }
});

app.post('/api/orders', (req, res, next) => {
  if (limited('ord:' + req.ip, 12, 3600e3)) return res.status(429).json({ error: 'Too many orders from this network. Please try later.' });
  next();
}, upload.array('photos', 12), async (req, res) => {
  const files = req.files || [];
  if (PROD && MOCK) { rm(files); return res.status(503).json({ error: 'Bookings open very soon. Please check back shortly.' }); }
  try {
    const b = req.body, plan = b.plan === 'video' ? 'video' : b.plan === 'audio' ? 'audio' : null;
    const err = m => { rm(files); return res.status(400).json({ error: m }); };
    if (!plan) return err('Choose a plan.');
    if (!OCCASIONS.includes(b.occasion) || !LANGS.includes(b.language) || !RECIPIENTS.includes(b.recipient) || !GENRES.includes(b.genre)) return err('Please complete all choices.');
    const to = clip(b.to_name, 60), from = clip(b.from_name, 60), story = clip(b.story, 3000), cust = clip(b.cust_name, 80);
    const phone = clip(b.phone, 20).replace(/[^\d+]/g, ''), email = clip(b.email, 120);
    if (!to || !story || story.length < 40) return err('Please write a little more about the person and your memories (at least a few sentences).');
    if (!cust || !/^(\+?91)?[6-9]\d{9}$/.test(phone.replace(/^\+/, ''))) return err('Enter a valid 10-digit Indian WhatsApp number.');
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return err('Email looks incorrect.');
    if (b.consent !== 'yes') return err('Please accept the terms and privacy policy.');
    if (plan === 'video') {
      if (files.length < 3) return err('Add at least 3 photos for the video song.');
      for (const f of files) if (!sniff(f.path)) return err('Photos must be JPG, PNG or WEBP.');
    } else rm(files.splice(0));
    const amount = CFG.prices[plan] * 100, token = crypto.randomBytes(18).toString('hex');
    const r = db.prepare(`INSERT INTO orders(token,status,plan,occasion,recipient,language,genre,to_name,from_name,pronounce,story,cust_name,phone,email,amount,created_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(token, 'created', plan, b.occasion, b.recipient, b.language, b.genre, to, from, clip(b.pronounce, 200), story, cust, phone.replace(/^\+?91/, ''), email, amount, now());
    const id = Number(r.lastInsertRowid); const pd = path.join(odir(id), 'photos'); fs.mkdirSync(pd, { recursive: true });
    const saved = files.map((f, i) => { const n = `${i + 1}.${sniff(f.path)}`; fs.renameSync(f.path, path.join(pd, n)); return n; });
    db.prepare('UPDATE orders SET photos=? WHERE id=?').run(JSON.stringify(saved), id);
    if (MOCK) return res.json({ token, mock: true, amount });
    const rz = await fetch('https://api.razorpay.com/v1/orders', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Basic ' + Buffer.from(RZP_ID + ':' + RZP_SECRET).toString('base64') },
      body: JSON.stringify({ amount, currency: 'INR', receipt: 'ord_' + id, notes: { order: String(id) } })
    });
    const j = await rz.json(); if (!rz.ok) { console.error('rzp', j); return res.status(502).json({ error: 'Payment service error. Please try again.' }); }
    db.prepare('UPDATE orders SET rzp_order=? WHERE id=?').run(j.id, id);
    res.json({ token, rzp: { key: RZP_ID, order_id: j.id, amount, name: CFG.brand, prefill: { name: cust, contact: '91' + phone.replace(/^\+?91/, ''), email } } });
  } catch (e) { console.error(e); rm(files); res.status(500).json({ error: 'Something went wrong. Please try again.' }); }
});

app.post('/api/orders/:token/verify', (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE token=?').get(req.params.token);
  const { razorpay_payment_id: p, razorpay_order_id: oid, razorpay_signature: sig } = req.body || {};
  if (!o || !p || oid !== o.rzp_order || !safeEq(hmac(oid + '|' + p, RZP_SECRET), sig || '')) return res.status(400).json({ error: 'Payment could not be verified.' });
  markPaid(oid, p); res.json({ ok: true });
});
app.post('/api/orders/:token/mock-pay', (req, res) => {
  if (!MOCK || PROD) return res.status(404).end();
  const o = db.prepare('SELECT * FROM orders WHERE token=?').get(req.params.token); if (!o) return res.status(404).end();
  db.prepare("UPDATE orders SET status='paid', paid_at=? WHERE id=? AND status='created'").run(now(), o.id); res.json({ ok: true });
});

const pub = o => ({ plan: o.plan, status: o.status, to: o.to_name, occasion: o.occasion, delivered: o.status === 'delivered', hasAudio: !!o.song_file, hasVideo: !!o.video_file, brand: CFG.brand, delivery: CFG.deliveryText, whatsapp: CFG.whatsapp, id: o.id });
app.get('/api/o/:token', (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE token=?').get(req.params.token); if (!o) return res.status(404).json({ error: 'Not found' }); res.json(pub(o));
});
app.get('/api/o/:token/file/:kind', (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE token=?').get(req.params.token);
  if (!o || o.status !== 'delivered') return res.status(404).end();
  const f = req.params.kind === 'video' ? o.video_file : req.params.kind === 'audio' ? o.song_file : null; if (!f) return res.status(404).end();
  const p = path.join(odir(o.id), f); if (!fs.existsSync(p)) return res.status(410).send('File expired. Please contact us on WhatsApp.');
  const nice = `${CFG.brand.replace(/\W+/g, '-')}-for-${o.to_name.replace(/[^\w]+/g, '-')}${path.extname(f)}`;
  req.query.dl ? res.download(p, nice) : res.sendFile(p);
});
app.post('/api/o/:token/revision', (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE token=?').get(req.params.token); if (!o || o.status !== 'delivered') return res.status(404).end();
  db.prepare('UPDATE orders SET revision_note=? WHERE id=?').run(clip(req.body?.note, 1000), o.id); res.json({ ok: true });
});

// ---------------- admin
const sign = () => { const exp = Date.now() + 12 * 3600e3; return exp + '.' + hmac('adm' + exp); };
const authed = req => { const m = /(?:^|;\s*)adm=([^;]+)/.exec(req.headers.cookie || ''); if (!m) return false; const [exp, sig] = m[1].split('.'); return +exp > Date.now() && safeEq(hmac('adm' + exp), sig || ''); };
const admin = (req, res, next) => authed(req) ? next() : res.status(401).json({ error: 'login' });
app.post('/api/admin/login', (req, res) => {
  if (limited('login:' + req.ip, 6, 600e3)) return res.status(429).json({ error: 'Too many attempts. Wait 10 minutes.' });
  if (!ADMIN_PW || !safeEq(req.body?.password || '', ADMIN_PW)) return res.status(401).json({ error: 'Wrong password' });
  res.set('Set-Cookie', `adm=${sign()}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200${PROD ? '; Secure' : ''}`); res.json({ ok: true });
});
app.post('/api/admin/logout', (req, res) => { res.set('Set-Cookie', 'adm=; HttpOnly; Path=/; Max-Age=0'); res.json({ ok: true }); });
app.get('/api/admin/me', admin, (req, res) => res.json({ ok: true, mock: MOCK, brand: CFG.brand }));
app.get('/api/admin/orders', admin, (req, res) => {
  const rows = db.prepare("SELECT id,token,status,plan,occasion,language,to_name,cust_name,phone,amount,created_at,paid_at,render_status,revision_note FROM orders WHERE status!='created' ORDER BY id DESC LIMIT 300").all(); res.json(rows);
});
app.get('/api/admin/orders/:id', admin, (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE id=?').get(+req.params.id); if (!o) return res.status(404).end();
  o.photos = JSON.parse(o.photos || '[]'); const lf = path.join(odir(o.id), 'render.log'); o.log = fs.existsSync(lf) ? fs.readFileSync(lf, 'utf8').split('\n').slice(-8).join('\n') : ''; res.json(o);
});
app.get('/api/admin/orders/:id/photo/:n', admin, (req, res) => {
  const o = db.prepare('SELECT photos FROM orders WHERE id=?').get(+req.params.id); const list = JSON.parse(o?.photos || '[]'); const n = path.basename(req.params.n);
  if (!list.includes(n)) return res.status(404).end(); const p = path.join(odir(+req.params.id), 'photos', n); fs.existsSync(p) ? res.sendFile(p) : res.status(410).end();
});
app.get('/api/admin/orders/:id/file/:kind', admin, (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE id=?').get(+req.params.id); const f = o && (req.params.kind === 'video' ? o.video_file : o.song_file); if (!f) return res.status(404).end();
  const p = path.join(odir(o.id), f); fs.existsSync(p) ? res.sendFile(p) : res.status(410).end();
});
const sup = multer({ dest: path.join(DATA, 'tmp'), limits: { fileSize: 60 * 1024 * 1024, files: 2 } });
app.post('/api/admin/orders/:id/song', admin, sup.fields([{ name: 'song', maxCount: 1 }, { name: 'lrc', maxCount: 1 }]), (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE id=?').get(+req.params.id); const fl = req.files || {};
  const all = Object.values(fl).flat(); if (!o || !fl.song) { rm(all); return res.status(400).json({ error: 'Song file required' }); }
  const ext = path.extname(fl.song[0].originalname).toLowerCase(); if (!['.mp3', '.wav', '.m4a'].includes(ext)) { rm(all); return res.status(400).json({ error: 'Use mp3, wav or m4a' }); }
  fs.mkdirSync(odir(o.id), { recursive: true }); const sf = 'song' + ext; fs.renameSync(fl.song[0].path, path.join(odir(o.id), sf)); let lf = o.lrc_file;
  if (fl.lrc) { lf = 'lyrics.lrc'; fs.renameSync(fl.lrc[0].path, path.join(odir(o.id), lf)); }
  db.prepare('UPDATE orders SET song_file=?, lrc_file=?, status=CASE WHEN status IN (\'paid\') THEN \'song_ready\' ELSE status END WHERE id=?').run(sf, lf, o.id); res.json({ ok: true });
});
app.post('/api/admin/orders/:id/notes', admin, (req, res) => { db.prepare('UPDATE orders SET notes=? WHERE id=?').run(clip(req.body?.notes, 4000), +req.params.id); res.json({ ok: true }); });

const T = {
  birthday: { en: 'Happy Birthday', hi: 'जन्मदिन मुबारक', kn: 'ಜನ್ಮದಿನದ ಶುಭಾಶಯಗಳು', ta: 'பிறந்தநாள் வாழ்த்துக்கள்', te: 'పుట్టినరోజు శుభాకాంక్షలు' },
  anniversary: { en: 'Happy Anniversary', hi: 'सालगिरह मुबारक', kn: 'ವಿವಾಹ ವಾರ್ಷಿಕೋತ್ಸವದ ಶುಭಾಶಯಗಳು', ta: 'திருமண நாள் வாழ்த்துக்கள்', te: 'వివాహ వార్షికోత్సవ శుభాకాంక్షలు' },
  wedding: { en: 'Congratulations', hi: 'हार्दिक बधाई', kn: 'ಹಾರ್ದಿಕ ಅಭಿನಂದನೆಗಳು', ta: 'இனிய வாழ்த்துக்கள்', te: 'హృదయపూర్వక అభినందనలు' },
  generic: { en: 'A Song For You', hi: 'आपके लिए एक गीत', kn: 'ನಿಮಗಾಗಿ ಒಂದು ಹಾಡು', ta: 'உங்களுக்காக ஒரு பாடல்', te: 'మీ కోసం ఒక పాట' }
};
const SUB = { en: 'A song made just for you', hi: 'सिर्फ़ आपके लिए बना गीत', kn: 'ನಿಮಗಾಗಿ ವಿಶೇಷ ಹಾಡು', ta: 'உங்களுக்காகவே உருவான பாடல்', te: 'మీ కోసమే చేసిన పాట' };
const LOVE = { en: 'With love,', hi: 'प्यार के साथ,', kn: 'ಪ್ರೀತಿಯಿಂದ,', ta: 'அன்புடன்,', te: 'ప్రేమతో,' };
const THEME = { birthday: 'gold', anniversary: 'rose', wedding: 'rose', love: 'rose', diwali: 'saffron', festival: 'saffron', devotional: 'saffron', graduation: 'gold', reel: 'rose' };
let rendering = null;
app.post('/api/admin/orders/:id/render', admin, (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE id=?').get(+req.params.id); const photos = JSON.parse(o?.photos || '[]');
  if (!o || o.plan !== 'video' || !o.song_file || photos.length < 3) return res.status(400).json({ error: 'Needs a video order with song and 3+ photos' });
  if (!fs.existsSync(path.join(ENGINE_DIR, 'songreel.py'))) return res.status(500).json({ error: 'Video engine not found on this server' });
  if (rendering) return res.status(409).json({ error: 'Another video is rendering (#' + rendering + ')' });
  const b = req.body || {}, d = odir(o.id), L = o.language, tt = T[o.occasion] || T.generic;
  const spec = {
    to: o.to_name, from: o.from_name, occasion: o.occasion, language: L, theme: ['gold', 'rose', 'royal', 'saffron'].includes(b.theme) ? b.theme : (THEME[o.occasion] || 'gold'),
    title: clip(b.title, 120) || (tt[L] + '\n' + o.to_name), subtitle: clip(b.subtitle, 100) || SUB[L], header: clip(b.header, 80) || (tt[L] + ' ' + o.to_name).trim(),
    outro_title: LOVE[L] + (o.from_name ? '\n' + o.from_name : ''), brand: CFG.brand, wishes: String(b.wishes || '').split('\n').map(s => clip(s, 90)).filter(Boolean).slice(0, 4),
    photos: photos.map(p => path.join(d, 'photos', p)), audio: path.join(d, o.song_file)
  };
  if (o.lrc_file) spec.lyrics_lrc = path.join(d, o.lrc_file); else if (b.lyrics_text) spec.lyrics_text = clip(b.lyrics_text, 4000);
  fs.writeFileSync(path.join(d, 'order.json'), JSON.stringify(spec)); const out = path.join(d, 'video.mp4'), log = fs.openSync(path.join(d, 'render.log'), 'w');
  rendering = o.id; db.prepare("UPDATE orders SET render_status='rendering' WHERE id=?").run(o.id);
  const p = spawn(process.env.PYTHON || 'python3', ['-I', path.join(ENGINE_DIR, 'songreel.py'), path.join(d, 'order.json'), out], { stdio: ['ignore', log, log] });
  p.on('close', code => {
    rendering = null; const ok = code === 0 && fs.existsSync(out);
    db.prepare('UPDATE orders SET render_status=?, video_file=COALESCE(?,video_file), status=CASE WHEN ? AND status IN (\'paid\',\'song_ready\') THEN \'video_ready\' ELSE status END WHERE id=?').run(ok ? 'done' : 'failed', ok ? 'video.mp4' : null, ok ? 1 : 0, o.id);
  });
  res.json({ ok: true });
});
app.post('/api/admin/orders/:id/deliver', admin, (req, res) => {
  const o = db.prepare('SELECT * FROM orders WHERE id=?').get(+req.params.id); if (!o || !o.song_file || (o.plan === 'video' && !o.video_file)) return res.status(400).json({ error: 'Upload the song' + (o.plan === 'video' ? ' and render the video' : '') + ' first' });
  db.prepare("UPDATE orders SET status='delivered', delivered_at=? WHERE id=?").run(now(), o.id);
  const base = (CFG.domain ? 'https://' + CFG.domain : req.protocol + '://' + req.get('host')) + '/o.html?t=' + o.token;
  const msg = `Namaste ${o.cust_name}! Your personalised song for ${o.to_name} is ready 🎶\nWatch & download: ${base}\n— ${CFG.brand}`;
  res.json({ ok: true, link: base, wa: `https://wa.me/91${o.phone}?text=${encodeURIComponent(msg)}` });
});

// ---------------- static + retention
app.use(express.static(path.join(__dirname, 'public'), { extensions: ['html'], maxAge: PROD ? '1d' : 0, setHeaders: (res, p) => { if (/\.(html|css|js)$/.test(p)) res.setHeader('Cache-Control', 'no-cache'); } }));
function purge() {
  const day = 864e5, rows = db.prepare('SELECT * FROM orders').all();
  for (const o of rows) {
    const dir = odir(o.id); if (!fs.existsSync(dir)) continue;
    const unpaidOld = o.status === 'created' && Date.now() - Date.parse(o.created_at) > 3 * day;
    const delivered = o.status === 'delivered' && Date.now() - Date.parse(o.delivered_at) > CFG.photoRetentionDays * day;
    const files = o.status === 'delivered' && Date.now() - Date.parse(o.delivered_at) > CFG.fileRetentionDays * day;
    if (unpaidOld || files) { fs.rmSync(dir, { recursive: true, force: true }); db.prepare("UPDATE orders SET photos='[]', song_file=NULL, video_file=NULL, lrc_file=NULL WHERE id=?").run(o.id); if (unpaidOld) db.prepare("UPDATE orders SET status='expired', story='' WHERE id=?").run(o.id); }
    else if (delivered) { fs.rmSync(path.join(dir, 'photos'), { recursive: true, force: true }); db.prepare("UPDATE orders SET photos='[]' WHERE id=?").run(o.id); }
  }
  for (const f of fs.readdirSync(path.join(DATA, 'tmp'))) { const p = path.join(DATA, 'tmp', f); if (Date.now() - fs.statSync(p).mtimeMs > day) fs.unlinkSync(p); }
}
setInterval(() => { try { purge(); } catch (e) { console.error('purge', e.message); } }, 6 * 3600e3); setTimeout(() => { try { purge(); } catch { } }, 5000);
db.prepare("UPDATE orders SET render_status='failed' WHERE render_status='rendering'").run();
app.use((err, req, res, next) => { console.error(err.message); res.status(err.code === 'LIMIT_FILE_SIZE' ? 413 : 500).json({ error: err.code === 'LIMIT_FILE_SIZE' ? 'File too large (max 12 MB per photo).' : 'Server error' }); });
app.listen(PORT, () => console.log(`${CFG.brand} on :${PORT} ${MOCK ? '(payments: TEST MODE, no Razorpay keys)' : '(Razorpay live)'}`));
