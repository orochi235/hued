(function () {
  'use strict';
  const token = new URLSearchParams(location.search).get('t') || '';
  const api = (path, params) => {
    const q = new URLSearchParams(Object.assign({ t: token }, params || {}));
    return path + '?' + q;
  };
  const getJSON = (path, params) => fetch(api(path, params)).then(r => {
    if (!r.ok) throw new Error(path + ' answered ' + r.status);
    return r.json();
  });
  const $ = id => document.getElementById(id);

  // picks holds only the slots changed on this page; the server fills in the rest from .hued.
  const state = { data: null, band: 'any', click: null, clicked: [], slot: 'background', picks: {},
                  view: null, results: [], finished: false };
  const glyphs = {}, tinted = {}, asked = new Set(), takenBy = {};

  const cv = $('map'), ctx = cv.getContext('2d');
  const gx = 96, gw = 60, px = 196, pw = cv.width - px - 30, py = 30, ph = cv.height - 90;
  const place = p => [p.gray ? gx + gw / 2 : px + p.h / 360 * pw, py + (1 - p.l) * ph];
  const images = {};

  function image(src) {
    return new Promise(done => {
      const img = new Image();
      img.onload = () => done(img);
      img.onerror = () => done(null);
      img.src = src;
    });
  }

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function glyph(name) {
    const g = el('span', 'glyph' + (glyphs[name] ? '' : ' none'));
    if (glyphs[name]) g.style.setProperty('--g', 'url(data:image/png;base64,' + glyphs[name] + ')');
    return g;
  }

  // Glyphs arrive after the first draw: the helper that draws them takes a moment to start.
  function wantGlyphs(names) {
    if (!state.data.symbols.glyphs) return;
    const need = names.filter(n => n && !asked.has(n));
    if (!need.length) return;
    need.forEach(n => asked.add(n));
    getJSON('/glyphs', { names: need.join(',') }).then(got => Promise.all(Object.keys(got).map(name => {
      glyphs[name] = got[name];
      return image('data:image/png;base64,' + got[name]).then(img => {
        if (!img) return;
        ['#000', '#fff'].forEach(col => {
          const s = 40, off = document.createElement('canvas');
          off.width = off.height = s;
          const c = off.getContext('2d'), k = Math.min(s / img.width, s / img.height);
          c.drawImage(img, (s - img.width * k) / 2, (s - img.height * k) / 2, img.width * k, img.height * k);
          c.globalCompositeOperation = 'source-in';
          c.fillStyle = col;
          c.fillRect(0, 0, s, s);
          tinted[name + col] = off;
        });
      });
    }))).then(render).catch(() => {});
  }

  function caption(s, x, y, align) {
    ctx.font = '22px ui-monospace, Menlo, monospace';
    ctx.fillStyle = '#9a9aa0';
    ctx.textAlign = align || 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(s, x, y);
  }
  function outline(dashed) {
    ctx.setLineDash(dashed ? [7, 5] : []);
    ctx.lineWidth = 5; ctx.strokeStyle = '#000a'; ctx.stroke();
    ctx.lineWidth = 2.5; ctx.strokeStyle = '#fff'; ctx.stroke();
    ctx.setLineDash([]);
  }
  function disc(p, r) {
    const [x, y] = place(p);
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = p.hex;
    ctx.fill();
    return [x, y];
  }
  function draw() {
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (images.field) ctx.drawImage(images.field, px, py, pw, ph);
    if (images.grays) ctx.drawImage(images.grays, gx, py, gw, ph);
    caption('grays', gx + gw / 2, py + ph + 28, 'center');
    caption('hue →', px + pw / 2, py + ph + 28, 'center');
    caption('light', 4, py + 14);
    caption('dark', 4, py + ph - 14);
    if (!state.data) return;
    state.data.repos.forEach(p => {
      const mark = tinted[p.sfkey + (p.light ? '#000' : '#fff')];
      const [x, y] = disc(p, mark ? 19 : 12);
      outline();
      if (mark) ctx.drawImage(mark, x - 12, y - 12, 24, 24);
    });
    state.data.gaps[state.band].forEach((p, i) => {
      const [x, y] = disc(p, 19);
      outline(true);
      ctx.font = 'bold 20px ui-monospace, Menlo, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = p.light ? '#000' : '#fff';
      ctx.fillText(i + 1, x, y + 1);
    });
    if (state.click) {
      const [x, y] = state.click;
      ctx.beginPath();
      ctx.moveTo(x - 26, y); ctx.lineTo(x + 26, y);
      ctx.moveTo(x, y - 26); ctx.lineTo(x, y + 26);
      outline();
    }
    const sel = state.view && state.view.colors[state.slot];
    if (sel) {
      const [x, y] = place(sel);
      ctx.beginPath();
      ctx.arc(x, y, 27, 0, 2 * Math.PI);
      outline();
    }
  }

  function swatch(p) {
    const s = el('div', 'swatch' + (state.picks[state.slot] === p.hex ? ' sel' : ''));
    s.setAttribute('role', 'button');
    s.tabIndex = 0;
    s.style.setProperty('--c', p.hex);
    const meta = el('div', 'meta'), n = p.neighbors[0];
    meta.append(el('div', 'hex', p.hex), el('div', '', p.tag));
    if (n) meta.append(el('div', 'who' + (n.close ? ' warn' : ''), (n.close ? 'close to ' : 'nearest ') + n.name));
    s.append(el('div', 'block'), meta);
    const go = () => choose(p.hex);
    s.addEventListener('click', go);
    s.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
    });
    return s;
  }

  function symbol() { return $('sym').value.trim(); }
  function slug() { return $('slug').value.trim(); }
  // Only what is filled in: an empty field leaves the file's own value alone.
  function texts() { return Object.assign({}, symbol() ? { sfkey: symbol() } : {}, slug() ? { slug: slug() } : {}); }

  function renderSymbols() {
    const name = symbol(), box = $('syms'), note = $('symnote');
    note.className = 'note' + (takenBy[name] ? ' warn' : '');
    note.textContent = takenBy[name] ? 'taken: ' + takenBy[name] : '';
    box.replaceChildren(...state.results.map(r => {
      const row = el('div', 'row pick' + (r.name === name ? ' on' : ''));
      row.append(glyph(r.name), el('span', 'name', r.name));
      if (r.taken) row.append(el('span', 'end warn', 'taken: ' + r.taken));
      row.addEventListener('click', () => { $('sym').value = r.name; render(); });
      return row;
    }));
  }

  function choose(hex) {
    state.picks[state.slot] = hex;
    refresh();
  }

  let asking = 0;
  function refresh() {
    const ask = ++asking;
    const params = Object.assign({}, state.picks, texts());
    getJSON('/preview', params).then(got => {
      if (ask !== asking) return;
      state.view = got;
      render();
    }).catch(err => { $('note').textContent = String(err.message || err); });
  }

  function slotRow() {
    const box = $('slots'), first = box.querySelector('.custom');
    if (!box.querySelector('.slot')) {
      state.data.slots.forEach(key => {
        const label = el('label', 'slot'), input = el('input');
        input.type = 'radio';
        input.name = 'slot';
        input.value = key;
        input.addEventListener('change', () => {
          state.slot = key;
          const c = state.view && state.view.colors[key];
          if (c) near(c, false); else render();
        });
        label.dataset.slot = key;
        label.append(input, el('span', 'chipdot'), el('span', '', key), el('span', 'ratio'));
        box.insertBefore(label, first);
      });
    }
    const colors = state.view ? state.view.colors : {};
    box.querySelectorAll('.slot').forEach(label => {
      const key = label.dataset.slot, c = colors[key], dot = label.querySelector('.chipdot');
      label.querySelector('input').checked = key === state.slot;
      dot.classList.toggle('unset', !c);
      if (c) dot.style.setProperty('--c', c.hex); else dot.style.removeProperty('--c');
      const ratio = label.querySelector('.ratio');
      ratio.className = 'ratio' + (c && c.low ? ' warn' : '');
      ratio.textContent = c && c.contrast != null ? c.contrast.toFixed(1) + ':1' : '';
    });
    const now = colors[state.slot];
    if (now) $('custom').value = now.hex;
    if (document.activeElement !== $('hex')) $('hex').value = now ? now.hex : '';
    $('revert').disabled = !(state.slot in state.picks);
  }

  function tint(e, hex) {
    if (hex) { e.classList.add('tint'); e.style.setProperty('--t', hex); }
    return e;
  }

  function render() {
    if (state.finished) return;
    const data = state.data, view = state.view;
    $('gaps').replaceChildren(...data.gaps[state.band].map(swatch));
    if (state.clicked.length) $('clicked').replaceChildren(...state.clicked.map(swatch));
    slotRow();
    renderSymbols();
    draw();
    if (!view) return;
    const c = view.colors, hex = key => c[key] && c[key].hex, term = $('term'), name = symbol();
    if (hex('background')) term.style.setProperty('--c', hex('background'));
    else term.style.removeProperty('--c');
    term.style.setProperty('--f', view.text);
    term.replaceChildren();
    // Only the command is selectable, so copying the pane copies something to paste.
    const who = el('span', 'deco');
    if (glyphs[name]) who.append(glyph(name), ' ');
    who.append(slug() || data.name || '~');
    const branch = el('span', 'deco', '\nOn branch ');
    branch.append(tint(el('span', '', 'main'), hex('accent2')), '\n');
    term.append(tint(who, hex('accent')), branch,
      tint(el('span', 'deco', '$ '), hex('accent3')),
      view.command ? el('span', '', view.command) : el('span', 'deco', '# nothing changed yet'));
    $('near').replaceChildren(...view.neighbors.map(n => {
      const row = el('div', 'row'), dot = el('span', 'chipdot');
      dot.style.setProperty('--c', n.hex);
      row.append(dot, glyph(n.sfkey), el('span', 'name', n.name),
        el('span', 'end' + (n.close ? ' warn' : ''), n.distance.toFixed(2)));
      return row;
    }));
    $('use').disabled = !view.writes.length;
    $('copy').disabled = !view.command;
    $('note').className = 'note';
    $('note').textContent = !view.writes.length ? '' : data.target
      ? 'Writes these lines to ' + data.target + '/.hued. Other keys keep their values.'
      : 'Prints these lines in the terminal.';
  }

  function pointer(e) {
    const r = cv.getBoundingClientRect(), s = cv.width / r.width;
    return [(e.clientX - r.left) * s, (e.clientY - r.top) * s];
  }

  cv.addEventListener('click', e => {
    const [mx, my] = pointer(e);
    if (my < py || my > py + ph) return;
    const gray = mx >= gx && mx <= gx + gw;
    if (!gray && (mx < px || mx > px + pw)) return;
    near({ h: gray ? 0 : (mx - px) / pw * 360, l: 1 - (my - py) / ph, gray }, true);
  });

  // Offer the swatches around a spot on the map; `pick` also takes the first one.
  function near(spot, pick) {
    state.click = place(spot);
    draw();
    getJSON('/near', { h: spot.h, l: spot.l, gray: spot.gray ? 1 : 0 })
      .then(got => {
        state.clicked = got.swatches;
        if (pick) choose(got.swatches[0].hex); else render();
      })
      .catch(err => { $('note').textContent = String(err.message || err); });
  }

  cv.addEventListener('mousemove', e => {
    if (!state.data) return;
    const [mx, my] = pointer(e);
    let hit = null, best = 26;
    state.data.repos.forEach(p => {
      const [x, y] = place(p), d = Math.hypot(x - mx, y - my);
      if (d < best) { best = d; hit = p; }
    });
    $('readout').textContent = hit ? hit.name + '  ' + hit.hex + (hit.sfkey ? '  ' + hit.sfkey : '') : '';
  });

  document.querySelectorAll('input[name=band]').forEach(input => input.addEventListener('change', () => {
    state.band = input.value;
    render();
  }));

  let pending = 0;
  $('custom').addEventListener('input', e => choose(e.target.value.toLowerCase()));
  $('hex').addEventListener('input', e => {
    const v = e.target.value.trim().toLowerCase().replace(/^#?/, '#');
    if (/^#[0-9a-f]{6}$/.test(v)) choose(v);
  });
  $('hex').addEventListener('blur', render);
  $('revert').addEventListener('click', () => {
    delete state.picks[state.slot];
    refresh();
  });

  $('copy').addEventListener('click', () => {
    navigator.clipboard.writeText(state.view.command).then(() => {
      $('note').textContent = 'Copied. Paste it in any directory to set these there.';
    }, err => { $('note').textContent = String(err.message || err); });
  });

  $('slug').addEventListener('input', refresh);
  $('sym').addEventListener('input', () => {
    refresh();
    if (!state.data.symbols.search) return;
    clearTimeout(pending);
    pending = setTimeout(() => {
      const query = symbol();
      getJSON('/symbols', { q: query }).then(got => {
        if (query !== symbol()) return;
        state.results = got.names;
        wantGlyphs(got.names.map(n => n.name));
        renderSymbols();
      }).catch(() => {});
    }, 150);
  });

  $('use').addEventListener('click', () => {
    $('use').disabled = true;
    const body = Object.assign({}, state.picks, texts());
    fetch(api('/use'), { method: 'POST', body: JSON.stringify(body) })
      .then(r => r.ok ? r.json() : r.text().then(t => { throw new Error(t.trim() || 'write failed'); }))
      .then(got => {
        state.finished = true;
        const done = el('div', 'done');
        done.append(el('h1', '', got.path ? 'Written to ' + got.path : 'Sent to the terminal'),
          el('pre', '', got.written.join('\n')),
          el('p', 'sub', 'You can close this tab.'));
        $('main').replaceChildren(done);
      })
      .catch(err => {
        $('use').disabled = false;
        const note = $('note');
        note.className = 'note warn';
        note.textContent = String(err.message || err);
      });
  });

  addEventListener('pagehide', () => {
    if (!state.finished) navigator.sendBeacon(api('/bye'));
  });

  Promise.all([getJSON('/data'), image(api('/field.png')), image(api('/grays.png'))])
    .then(([data, field, grays]) => {
      state.data = data;
      images.field = field;
      images.grays = grays;
      data.repos.forEach(r => { if (r.sfkey && !takenBy[r.sfkey]) takenBy[r.sfkey] = r.name; });
      if (data.target) {
        document.title = 'hued map — ' + data.name;
        $('target').textContent = data.name;
      } else {
        document.title = 'hued pick';
        $('title').textContent = 'Pick colors';
        $('use').textContent = 'Print these';
      }
      const how = 'Choose what you are picking below, then a swatch, or click the map.';
      $('sub').textContent = !data.root ? how
        : data.repos.length
          ? 'Dots are the backgrounds in use under ' + data.root + '. Dashed rings are the widest gaps. ' + how
          : 'No .hued backgrounds found under ' + data.root + ', so every color is free. ' + how;
      if (data.current.sfkey) $('sym').value = data.current.sfkey;
      if (data.current.slug) $('slug').value = data.current.slug;
      if (data.name) $('slug').placeholder = data.name;
      if (!data.symbols.search) $('sym').placeholder = 'SF Symbol name, e.g. leaf';
      render();
      refresh();
      wantGlyphs(data.repos.map(r => r.sfkey).concat(data.current.sfkey || []));
    })
    .catch(err => { $('sub').textContent = 'Could not load: ' + String(err.message || err); });
})();
