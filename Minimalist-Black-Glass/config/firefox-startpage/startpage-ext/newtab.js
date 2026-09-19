
(function () {
  var DEFAULTS = [
    { k: 'Reddit', u: 'https://www.reddit.com/' },
    { k: 'GitHub', u: 'https://github.com/' },
    { k: 'YouTube', u: 'https://www.youtube.com/' },
    { k: 'Amazon', u: 'https://www.amazon.com/' },
    { k: 'Arch Docs', u: 'https://wiki.archlinux.org/' },
    { k: 'Hyprland', u: 'https://wiki.hyprland.org/' },
    { k: 'Hypr Forums', u: 'https://forum.hyprland.org/' }
  ];
  var storeKey = 'sp_custom';
  var custom = [];
  var scsEl = document.getElementById('scs');
  var editor = document.getElementById('editor');
  var inName = document.getElementById('inName');
  var inUrl = document.getElementById('inUrl');

  function store() {
    try { localStorage.setItem(storeKey, JSON.stringify(custom)); } catch (e) {}
  }
  function loadCustom() {
    try {
      var v = localStorage.getItem(storeKey);
      if (v) { var a = JSON.parse(v); if (Array.isArray(a)) return a; }
    } catch (e) {}
    return [];
  }
  function domain(u) {
    var m = u.match(/^https?:\/\/([^\/]+)/i);
    return m ? m[1] : u;
  }
  function render() {
    scsEl.innerHTML = '';
    DEFAULTS.concat(custom).forEach(function (s) {
      var a = document.createElement('a');
      a.className = 'sc';
      a.href = s.u;
      var img = document.createElement('img');
      img.src = 'https://www.google.com/s2/favicons?domain=' + encodeURIComponent(domain(s.u)) + '&sz=64';
      img.loading = 'lazy';
      img.alt = '';
      a.appendChild(img);
      var k = document.createElement('span');
      k.className = 'k';
      k.textContent = s.k;
      a.appendChild(k);
      if (custom.indexOf(s) >= 0) {
        var x = document.createElement('button');
        x.className = 'x';
        x.textContent = '\u00d7';
        x.addEventListener('click', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          custom = custom.filter(function (c) { return c !== s; });
          store();
          render();
        });
        a.appendChild(x);
      }
      scsEl.appendChild(a);
    });
    var add = document.createElement('button');
    add.className = 'sc sc-add';
    add.id = 'addBtn';
    add.textContent = '+';
    add.addEventListener('click', function () {
      inName.value = '';
      inUrl.value = '';
      editor.classList.add('open');
      inName.focus();
    });
    scsEl.appendChild(add);
  }

  function normalizeUrl(u) {
    u = u.trim();
    if (!u) return '';
    if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
    return u;
  }
  function addShortcut() {
    var n = inName.value.trim();
    var u = normalizeUrl(inUrl.value);
    if (!n || !u) return;
    if (custom.length >= 24) return;
    if (!/^https?:\/\//i.test(u) || !/\.[a-z]/i.test(u)) return;
    custom.push({ k: n, u: u });
    store();
    render();
    editor.classList.remove('open');
  }
  function closeEditor() { editor.classList.remove('open'); }

  document.getElementById('edOk').addEventListener('click', addShortcut);
  document.getElementById('edCancel').addEventListener('click', closeEditor);
  editor.addEventListener('click', function (e) { if (e.target === editor) closeEditor(); });
  inUrl.addEventListener('keydown', function (e) { if (e.key === 'Enter') addShortcut(); });
  inName.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); inUrl.focus(); } });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && editor.classList.contains('open')) closeEditor();
  });

  custom = loadCustom();
  render();

  function tickClock() {
    var d = new Date();
    var h = d.getHours() % 12; if (h === 0) h = 12;
    var m = d.getMinutes().toString().padStart(2, '0');
    var ampm = d.getHours() < 12 ? 'AM' : 'PM';
    var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    var el = document.getElementById('clock');
    if (el) el.innerHTML = '<div class="ctime">' + h + ':' + m + ' ' + ampm + '</div>'
      + '<div class="cdate">' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear() + '</div>';
  }
  tickClock();
  setInterval(tickClock, 1000);

  var qEl = document.getElementById('q');
  var suggEl = document.getElementById('sugs');
  var cbName = 'startpageCb';
  var cbSeq = 0;
  var deb = null;
  var typeTimer = null;
  var items = [];
  var active = -1;

  var enginesEl = document.getElementById('engines');
  var GOOGLE_JSONP = 'https://suggestqueries.google.com/complete/search?client=firefox&hl=en&callback={cb}&q={q}';
  var ENGINES = [
    { key: 'google', name: 'Google',
      url: 'https://www.google.com/search?q={q}',
      suggest: { jsonp: GOOGLE_JSONP } },
    { key: 'ddg', name: 'DuckDuckGo',
      url: 'https://duckduckgo.com/?q={q}',
      suggest: { json: 'https://duckduckgo.com/ac/?q={q}&type=list', fallbackJsonp: GOOGLE_JSONP } },
    { key: 'bing', name: 'Bing',
      url: 'https://www.bing.com/search?q={q}',
      suggest: { jsonp: 'https://api.bing.com/osjson.aspx?JsonType=callback&JsonCallback={cb}&query={q}' } },
    { key: 'searxng', name: 'SearXNG',
      url: 'https://searx.be/search?q={q}',
      suggest: { json: 'https://searx.be/autocompleter?q={q}', fallbackJsonp: GOOGLE_JSONP } },
    { key: 'brave', name: 'Brave',
      url: 'https://search.brave.com/search?q={q}',
      suggest: { json: 'https://search.brave.com/api/suggest?q={q}', fallbackJsonp: GOOGLE_JSONP } },
    { key: 'startpage', name: 'Startpage',
      url: 'https://www.startpage.com/sp/search?query={q}',
      suggest: { jsonp: GOOGLE_JSONP } }
  ];
  var engine = ENGINES[0];

  function parseSuggestions(data) {
    if (data && Array.isArray(data[1])) return data[1].map(String);
    if (Array.isArray(data)) {
      return data.map(function (o) {
        return typeof o === 'string' ? o : (o && (o.phrase || o.q)) || '';
      }).filter(Boolean).filter(function (s) { return s !== (data[0] || ''); });
    }
    return [];
  }
  function renderEngines() {
    enginesEl.innerHTML = '';
    var lbl = document.createElement('span');
    lbl.className = 'eng-lbl';
    lbl.textContent = 'SEARCH:';
    enginesEl.appendChild(lbl);
    ENGINES.forEach(function (e) {
      var b = document.createElement('button');
      b.className = 'eng' + (e.key === engine.key ? ' active' : '');
      b.type = 'button';
      b.textContent = e.name;
      b.addEventListener('click', function () { selectEngine(e.key); });
      enginesEl.appendChild(b);
    });
  }
  function selectEngine(key) {
    var found = ENGINES.filter(function (e) { return e.key === key; })[0];
    if (!found) return;
    engine = found;
    try { localStorage.setItem('sp_engine', key); } catch (e) {}
    typePlaceholder();
    clearSuggestions();
    renderEngines();
    qEl.focus();
  }
  try {
    var savedEng = localStorage.getItem('sp_engine');
    if (savedEng) {
      var f = ENGINES.filter(function (e) { return e.key === savedEng; })[0];
      if (f) engine = f;
    }
  } catch (e) {}
  typePlaceholder();
  renderEngines();

  function openSuggestions() {
    suggEl.innerHTML = '';
    items.forEach(function (s, i) {
      var d = document.createElement('div');
      d.className = 'sug' + (i === active ? ' active' : '');
      d.textContent = s;
      d.addEventListener('mousedown', function (e) { e.preventDefault(); go(s); });
      d.addEventListener('mouseenter', function () { setActive(i); });
      suggEl.appendChild(d);
    });
    suggEl.classList.add('open');
  }
  function setActive(i) {
    active = i;
    var kids = suggEl.children;
    for (var kk = 0; kk < kids.length; kk++) kids[kk].className = 'sug' + (kk === active ? ' active' : '');
    if (active >= 0 && kids[active]) kids[active].scrollIntoView({ block: 'nearest' });
  }
  function showSuggestions(list) {
    items = list;
    active = -1;
    if (items.length) openSuggestions(); else clearSuggestions();
  }
  function clearSuggestions() {
    items = [];
    active = -1;
    suggEl.innerHTML = '';
    suggEl.classList.remove('open');
  }
  function typePlaceholder() {
    if (typeTimer) { clearTimeout(typeTimer); typeTimer = null; }
    var full = 'Search ' + engine.name + '...';
    var i = 0;
    function typeStep() {
      if (qEl.value.length > 0) { qEl.placeholder = full; typeTimer = null; return; }
      qEl.placeholder = full.slice(0, i++);
      if (i <= full.length) typeTimer = setTimeout(typeStep, 55);
      else typeTimer = null;
    }
    typeStep();
  }
  function jsonpRequest(tpl, q1, eng) {
    var cb = cbName + (++cbSeq);
    window[cb] = function (data) {
      try { delete window[cb]; } catch (e) { window[cb] = undefined; }
      if (qEl.value.trim() !== q1 || engine.key !== eng.key) return;
      showSuggestions(parseSuggestions(data));
    };
    var s = document.createElement('script');
    s.src = tpl.replace('{cb}', cb).replace('{q}', encodeURIComponent(q1)) + '&_=' + Date.now();
    s.onerror = function () { s.remove(); };
    s.onload = function () { s.remove(); };
    document.body.appendChild(s);
  }
  function fetchSuggestions(q1) {
    if (deb) { clearTimeout(deb); deb = null; }
    var eng = engine;
    var cfg = eng.suggest;
    if (!cfg) { clearSuggestions(); return; }
    deb = setTimeout(function () {
      deb = null;
      if (cfg.json) {
        fetch(cfg.json.replace('{q}', encodeURIComponent(q1)))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (qEl.value.trim() !== q1 || engine.key !== eng.key) return;
            showSuggestions(parseSuggestions(data));
          })
          .catch(function () {
            if (cfg.fallbackJsonp) jsonpRequest(cfg.fallbackJsonp, q1, eng);
            else if (qEl.value.trim() === q1 && engine.key === eng.key) clearSuggestions();
          });
      } else {
        jsonpRequest(cfg.jsonp, q1, eng);
      }
    }, 180);
  }
  function go(text) {
    clearSuggestions();
    if (text) window.location.href = engine.url.replace('{q}', encodeURIComponent(text.trim()));
  }
  qEl.addEventListener('input', function () {
    var v = qEl.value.trim();
    if (v.length >= 1) fetchSuggestions(v); else clearSuggestions();
  });
  function selectOrGo(e) {
    e.preventDefault();
    if (active >= 0 && items[active]) go(items[active]);
    else go(qEl.value);
  }
  qEl.addEventListener('keydown', function (e) {
    var open = suggEl.classList.contains('open');
    if (e.key === 'ArrowDown') { e.preventDefault(); if (!open) openSuggestions(); else setActive(Math.min(active + 1, items.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (open) setActive(Math.max(active - 1, -1)); }
    else if (e.key === 'Enter') { selectOrGo(e); }
    else if (e.key === 'Escape') { clearSuggestions(); }
  });
  qEl.addEventListener('blur', function () { setTimeout(clearSuggestions, 200); });

  var ringRect = document.getElementById('ringRect');
  var ringVisible = false;

  function ringGeometry() {
    var w = qEl.offsetWidth, h = qEl.offsetHeight;
    var rw = Math.max(0, w - 2), rh = Math.max(0, h - 2);
    ringRect.setAttribute('x', 1);
    ringRect.setAttribute('y', 1);
    ringRect.setAttribute('width', rw);
    ringRect.setAttribute('height', rh);
    return 2 * (rw + rh);
  }
  function ringDraw() {
    var P = ringGeometry();
    ringVisible = true;
    ringRect.style.transition = 'none';
    ringRect.style.strokeDasharray = P + ' ' + P;
    ringRect.style.strokeDashoffset = P;
    void ringRect.getBoundingClientRect();
    ringRect.style.transition = 'stroke-dashoffset .55s ease';
    ringRect.style.strokeDashoffset = 0;
  }
  function ringClear() {
    if (!ringVisible) return;
    ringVisible = false;
    var P = ringGeometry();
    ringRect.style.transition = 'stroke-dashoffset .3s ease';
    ringRect.style.strokeDashoffset = -P;
  }

  qEl.addEventListener('focus', ringDraw);
  qEl.addEventListener('blur', ringClear);
  window.addEventListener('resize', function () {
    if (!ringVisible) return;
    var P = ringGeometry();
    ringRect.style.transition = 'none';
    ringRect.style.strokeDasharray = P + ' ' + P;
    ringRect.style.strokeDashoffset = 0;
  });

  /* --- GitHub stats widget --- */
  var ghBody = document.getElementById('ghBody');
  var ghStoreKey = 'sp_gh';

  function ghSet(msg) {
    ghBody.innerHTML = '';
    if (!msg) return;
    var d = document.createElement('div');
    d.className = 'gh-msg';
    d.textContent = msg;
    ghBody.appendChild(d);
  }
  function ghStat(num, label) {
    var box = document.createElement('div');
    box.className = 'gh-stat';
    var b = document.createElement('b');
    b.textContent = (typeof num === 'number') ? num.toLocaleString() : num;
    var s = document.createElement('span');
    s.textContent = label;
    box.appendChild(b);
    box.appendChild(s);
    return box;
  }
  function ghRender(d) {
    ghBody.innerHTML = '';
    var card = document.createElement('div');
    card.className = 'gh-card';
    if (d.avatar_url) {
      var img = document.createElement('img');
      img.className = 'gh-avatar';
      img.src = d.avatar_url;
      img.alt = '';
      card.appendChild(img);
    }
    var info = document.createElement('div');
    info.className = 'gh-info';
    var nm = document.createElement('div');
    nm.className = 'gh-name';
    nm.textContent = d.name || d.login;
    var lg = document.createElement('div');
    lg.className = 'gh-login';
    lg.textContent = '@' + d.login;
    info.appendChild(nm);
    info.appendChild(lg);
    card.appendChild(info);
    var stats = document.createElement('div');
    stats.className = 'gh-stats';
    stats.appendChild(ghStat(d.public_repos, 'REPOS'));
    stats.appendChild(ghStat(d.followers, 'FOLLOWERS'));
    stats.appendChild(ghStat(d.following, 'FOLLOWING'));
    card.appendChild(stats);
    ghBody.appendChild(card);
  }
  function ghLoad(u) {
    u = (u || '').trim();
    if (!u) {
      ghSet('');
      try { localStorage.removeItem(ghStoreKey); } catch (e) {}
      return;
    }
    ghSet('LOADING...');
    fetch('https://api.github.com/users/' + encodeURIComponent(u))
      .then(function (r) {
        if (r.status === 404) throw new Error('USER NOT FOUND');
        if (r.status === 403 || r.status === 429) throw new Error('RATE LIMITED');
        if (!r.ok) throw new Error('ERROR ' + r.status);
        return r.json();
      })
      .then(function (d) {
        ghRender(d);
        try { localStorage.setItem(ghStoreKey, d.login); } catch (e) {}
      })
      .catch(function (err) {
        ghSet(String((err && err.message) || err));
      });
  }
  try {
    var savedGh = localStorage.getItem(ghStoreKey);
    if (savedGh) { ghLink.textContent = '󰊤 ' + savedGh; ghLoad(savedGh); }
    else ghSet('CONFIGURE A USERNAME BELOW TO ENABLE');
  } catch (e) {}

  var ghSetBox = document.getElementById('ghSet');
  var ghUserEl = document.getElementById('ghUser');
  var ghSetMsg = document.getElementById('ghSetMsg');

  function ghOpen() {
    ghUserEl.value = '';
    try { ghUserEl.value = localStorage.getItem(ghStoreKey) || ''; } catch (e) {}
    ghSetMsg.textContent = '';
    ghSetBox.classList.add('open');
    ghUserEl.focus();
  }
  function ghClose() { ghSetBox.classList.remove('open'); }

  function ghSave() {
    var u = ghUserEl.value.trim().replace(/^@/, '');
    if (!u) { ghSetMsg.textContent = 'ENTER A USERNAME'; return; }
    ghSetMsg.textContent = 'CHECKING...';
    fetch('https://api.github.com/users/' + encodeURIComponent(u))
      .then(function (r) {
        if (r.status === 404) throw new Error('USER NOT FOUND');
        if (r.status === 403 || r.status === 429) throw new Error('RATE LIMITED');
        if (!r.ok) throw new Error('ERROR ' + r.status);
        return r.json();
      })
      .then(function () {
        try { localStorage.setItem(ghStoreKey, u); } catch (e) {}
        ghClose();
        ghLink.textContent = '󰊤 ' + u;
        ghLoad(u);
      })
      .catch(function (err) {
        ghSetMsg.textContent = String((err && err.message) || err);
      });
  }
  function ghClear() {
    try { localStorage.removeItem(ghStoreKey); } catch (e) {}
    ghClose();
    ghLink.textContent = '󰊤 CONFIGURE';
    ghSet('');
  }

  ghLink.addEventListener('click', function (e) { e.preventDefault(); ghOpen(); });
  document.getElementById('ghOk').addEventListener('click', ghSave);
  document.getElementById('ghClear').addEventListener('click', ghClear);
  document.getElementById('ghCancel').addEventListener('click', ghClose);
  ghSetBox.addEventListener('click', function (e) { if (e.target === ghSetBox) ghClose(); });
  ghUserEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') ghSave(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && ghSetBox.classList.contains('open')) ghClose();
  });
})();

// Private-browsing accent: same page, purple accents instead of white.
(function () {
  if (typeof browser === 'undefined' || !browser.windows || !browser.windows.getCurrent) return;
  browser.windows.getCurrent().then(function (w) {
    if (w && w.incognito) document.documentElement.classList.add('private');
  }).catch(function () {});
})();
