let KEY = null, INDEX = null;
const CACHE = {};
const ORDER = {Important: 0, Normal: 1, Promotional: 2};
const main = document.getElementById('main');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const fmtDate = d => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
const sortE = l => [...l].sort((a, b) =>
  ORDER[a.importance] - ORDER[b.importance] ||
  (a.category === 'Newsletters') - (b.category === 'Newsletters') ||
  b.received.localeCompare(a.received));
const b64 = s => Uint8Array.from(atob(s.trim()), c => c.charCodeAt(0));

async function deriveKey(pass) {
  const r = await fetch('data/salt.txt', {cache: 'no-store'});
  if (!r.ok) throw new Error('no salt');
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({name: 'PBKDF2', salt: b64(await r.text()), iterations: 600000, hash: 'SHA-256'},
    base, {name: 'AES-GCM', length: 256}, false, ['decrypt']);
}
async function dec(file) {
  const r = await fetch('data/' + file, {cache: 'no-store'});
  if (!r.ok) throw new Error('missing ' + file);
  const raw = b64(await r.text());
  const pt = await crypto.subtle.decrypt({name: 'AES-GCM', iv: raw.slice(0, 12)}, KEY, raw.slice(12));
  return JSON.parse(new TextDecoder().decode(pt));
}
async function getDay(d) { return CACHE[d] || (CACHE[d] = await dec(d + '.enc')); }
async function allEmails() {
  const out = [];
  for (const x of INDEX.days) (await getDay(x.date)).emails.forEach(e => out.push({...e, _d: x.date}));
  return out;
}

function entry(e, i, date) {
  const act = [e.action && 'Action: ' + e.action, e.deadline && 'Deadline: ' + e.deadline, e.reply_required && 'Reply required'].filter(Boolean);
  return `<div class="item"><span class="num">${i}.</span><div class="body">
    <a class="t" href="#" data-toggle>${esc(e.subject)}</a>
    <div class="meta">${esc(e.sender_name)} | ${date ? esc(date) + ' ' : ''}${e.received.slice(11, 16)} IST | ${esc(e.category)} |
      <span class="${e.importance === 'Important' ? 'imp' : ''}">${esc(e.importance)}</span> | <a href="#" data-toggle>details</a></div>
    <div class="sum">${esc(e.summary)}</div>
    ${act.length ? `<div class="act">${esc(act.join(' | '))}</div>` : ''}
    <div class="more" hidden>
      <p><b>From:</b> ${esc(e.sender_name)} &lt;${esc(e.sender_email)}&gt;</p>
      <p><b>Key points:</b> ${esc(e.details || 'None')}</p>
      <p><a href="https://mail.google.com/mail/u/0/#all/${encodeURIComponent(e.id)}" target="_blank" rel="noopener">open in Gmail</a></p>
    </div></div></div>`;
}

function dayView(d, b) {
  const E = sortE(b.emails);
  const imp = E.filter(e => e.importance === 'Important').length;
  const act = E.filter(e => e.action || e.deadline || e.reply_required).length;
  const cats = new Set(E.map(e => e.category)).size;
  return `<div class="head"><b>Briefing for ${fmtDate(d)}</b><br>${E.length} emails | ${imp} important | ${act} need action | ${cats} categories
    ${b.failed ? `<br><span class="imp">${b.failed} email(s) could not be processed.</span>` : ''}
    ${b.partial ? `<br><span class="imp">Incomplete: only part of this day was processed.</span>` : ''}</div>` +
    (E.length ? E.map((e, i) => entry(e, i + 1)).join('') : '<p class="empty">No emails received on this day.</p>');
}

async function route() {
  const h = location.hash.slice(1) || 'today';
  const days = INDEX.days;
  let html;
  try {
    if (h === 'today') html = days.length ? dayView(days[0].date, await getDay(days[0].date)) : '<p class="empty">No briefings yet.</p>';
    else if (h === 'past') html = '<div class="head"><b>Past briefings</b></div>' +
      days.map(d => `<div class="row"><a href="#d-${d.date}">${fmtDate(d.date)}</a> <span class="meta">${d.emails} emails</span></div>`).join('');
    else if (h.startsWith('d-') && days.some(d => d.date === h.slice(2))) html = dayView(h.slice(2), await getDay(h.slice(2)));
    else if (h === 'categories') {
      const c = {};
      (await allEmails()).forEach(e => c[e.category] = (c[e.category] || 0) + 1);
      html = '<div class="head"><b>Categories</b> (all days)</div>' +
        Object.keys(c).sort().map(k => `<div class="row"><a href="#c-${slug(k)}">${esc(k)}</a> <span class="meta">${c[k]}</span></div>`).join('');
    } else if (h.startsWith('c-')) {
      const list = sortE((await allEmails()).filter(e => slug(e.category) === h.slice(2)));
      html = `<div class="head"><b>${esc(list[0]?.category || 'Unknown category')}</b></div>` +
        list.map((e, i) => entry(e, i + 1, e._d)).join('');
    } else if (h === 'about') html = '<div class="head"><b>About</b></div><p>Daily Brief shows AI-generated summaries of yesterday\'s email. Summaries can be wrong; open the original in Gmail before acting on anything important.</p>';
    else html = '<p class="empty">Page not found.</p>';
  } catch (err) { html = '<p class="empty">Could not load this page.</p>'; }
  main.innerHTML = html;
  window.scrollTo(0, 0);
}

document.addEventListener('click', ev => {
  const a = ev.target.closest('[data-toggle]');
  if (!a) return;
  ev.preventDefault();
  a.closest('.body').querySelector('.more').hidden = a.closest('.body').querySelector('.more').hidden ? false : true;
});
window.addEventListener('hashchange', () => { if (KEY) route(); });
document.getElementById('gate').addEventListener('submit', async ev => {
  ev.preventDefault();
  const msg = document.getElementById('msg'), input = document.getElementById('pass');
  msg.textContent = 'Decrypting...';
  try {
    KEY = await deriveKey(input.value);
    INDEX = await dec('index.enc');
    input.value = '';
    document.getElementById('gate').hidden = true;
    document.getElementById('nav').hidden = false;
    route();
  } catch (err) { KEY = null; msg.textContent = 'Wrong passphrase, or data not available.'; }
});
