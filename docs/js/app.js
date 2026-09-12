(function() {
  'use strict';

  let notesIndex = null;
  let currentNote = null;
  let supabaseClient = null;
  let userName = '';
  let tocScrollHandler = null;

  const SUPABASE_URL = 'https://firvfvkadexbdrsfuzpk.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_VGm4obXnBc10xM6vsUUb4w_78Df8Qxt';

  async function init() {
    if (SUPABASE_URL && SUPABASE_KEY && window.supabase) {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    }
    loadUserName();
    try {
      const resp = await fetch('notes/index.json');
      if (resp.ok) notesIndex = await resp.json();
      else notesIndex = { specialties: [] };
    } catch { notesIndex = { specialties: [] }; }
    buildSidebar();
    buildWelcome();
    setupRouting();
    setupMobileMenu();
    setupHighlightToolbar();
  }

  // ── User identity ──
  function loadUserName() {
    try { userName = localStorage.getItem('mn-username') || ''; } catch {}
  }

  function promptUserName() {
    return new Promise(resolve => {
      if (userName) { resolve(userName); return; }
      const overlay = document.createElement('div');
      overlay.className = 'user-prompt-overlay';
      overlay.innerHTML = `<div class="user-prompt-box">
        <h2>Welcome!</h2>
        <p>Enter your name for shared highlights and notes</p>
        <input type="text" id="userNameInput" placeholder="Your name" maxlength="20">
        <br><button id="userNameBtn">Start</button>
      </div>`;
      document.body.appendChild(overlay);
      const input = document.getElementById('userNameInput');
      const btn = document.getElementById('userNameBtn');
      input.focus();
      function submit() {
        const name = input.value.trim() || 'Anonymous';
        userName = name;
        try { localStorage.setItem('mn-username', name); } catch {}
        overlay.remove();
        resolve(name);
      }
      btn.addEventListener('click', submit);
      input.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
    });
  }

  // ── Sidebar & Welcome ──
  function buildSidebar() {
    const nav = document.getElementById('navContent');
    if (!notesIndex.specialties.length) {
      nav.innerHTML = '<p style="padding:1.25rem;color:var(--text-muted);font-size:0.85rem;">No notes yet.</p>';
      return;
    }
    let html = '';
    for (const spec of notesIndex.specialties) {
      const specId = slugify(spec.name);
      html += '<div class="nav-section">';
      html += `<div class="nav-specialty" data-spec="${specId}" onclick="toggleSpec(this)">`;
      html += `<span class="arrow">&#9654;</span>${spec.name} (${spec.diseases.length})`;
      html += '</div>';
      html += `<div class="nav-diseases" id="diseases-${specId}">`;
      for (const d of spec.diseases)
        html += `<a class="nav-disease" data-id="${d.id}" onclick="loadNote('${d.id}')">${d.name}</a>`;
      html += '</div></div>';
    }
    nav.innerHTML = html;
  }

  function buildWelcome() {
    const grid = document.getElementById('specialtyGrid');
    if (!notesIndex.specialties.length) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:2rem;"><p style="color:var(--text-muted);">No notes yet.</p></div>';
      return;
    }
    let html = '';
    for (const spec of notesIndex.specialties) {
      html += `<div class="specialty-card" onclick="expandSpecialty('${slugify(spec.name)}')">`;
      html += `<h3>${spec.name}</h3><span class="count">${spec.diseases.length} topics</span></div>`;
    }
    grid.innerHTML = html;
  }

  function setupRouting() {
    const hash = window.location.hash.slice(1);
    if (hash) loadNote(hash);
    window.addEventListener('hashchange', () => {
      const id = window.location.hash.slice(1);
      if (id) loadNote(id);
    });
  }

  function setupMobileMenu() {
    document.getElementById('menuToggle').addEventListener('click', () =>
      document.getElementById('sidebar').classList.toggle('open'));
    document.getElementById('mainContent').addEventListener('click', () =>
      document.getElementById('sidebar').classList.remove('open'));
  }

  window.toggleSpec = function(el) {
    const specId = el.dataset.spec;
    el.classList.toggle('expanded');
    document.getElementById('diseases-' + specId).classList.toggle('show');
  };

  window.expandSpecialty = function(specId) {
    const el = document.querySelector(`.nav-specialty[data-spec="${specId}"]`);
    if (el && !el.classList.contains('expanded')) {
      el.classList.add('expanded');
      document.getElementById('diseases-' + specId).classList.add('show');
    }
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  // ── Note Loading & Rendering ──
  window.loadNote = async function(noteId) {
    window.location.hash = noteId;
    document.getElementById('welcomePage').style.display = 'none';
    const notePage = document.getElementById('notePage');
    notePage.style.display = 'block';
    notePage.innerHTML = '<p style="color:var(--text-muted);padding:2rem;">Loading...</p>';

    document.querySelectorAll('.nav-disease.active').forEach(el => el.classList.remove('active'));
    const navEl = document.querySelector(`.nav-disease[data-id="${noteId}"]`);
    if (navEl) {
      navEl.classList.add('active');
      const specEl = navEl.closest('.nav-section').querySelector('.nav-specialty');
      if (specEl && !specEl.classList.contains('expanded')) {
        specEl.classList.add('expanded');
        specEl.nextElementSibling.classList.add('show');
      }
    }

    try {
      const resp = await fetch(`notes/${noteId}.json`);
      if (!resp.ok) throw new Error('Not found');
      currentNote = await resp.json();
      renderNote(currentNote);
      await restoreHighlights();
      await loadAndShowAnnotations();
    } catch {
      notePage.innerHTML = '<p style="color:var(--text-muted);padding:2rem;">Note not found.</p>';
    }

    document.getElementById('sidebar').classList.remove('open');
    window.scrollTo(0, 0);
  };

  function renderNote(note) {
    const page = document.getElementById('notePage');
    let html = '<div class="note-header">';
    html += `<h1>${esc(note.title)}</h1><div class="note-meta">`;
    if (note.specialty) html += `<span>${esc(note.specialty)}</span>`;
    if (note.sources) html += `<span>Sources: ${esc(note.sources.join(', '))}</span>`;
    if (note.generated) html += `<span>${esc(note.generated)}</span>`;
    html += '</div></div>';

    html += buildToc(note);

    note.sections.forEach((sec, idx) => {
      html += `<div class="note-section" data-sec="${idx}" id="sec-${idx}">`;
      html += `<h2>${esc(sec.title)}</h2>`;
      html += renderContent(sec.content);
      html += '</div>';
    });

    if (note.related && note.related.length) {
      html += '<div class="related-notes"><h3>Related Notes</h3>';
      for (const r of note.related) {
        const id = typeof r === 'string' ? r : r.id;
        const name = typeof r === 'string' ? r : r.name;
        html += `<a class="related-link" onclick="loadNote('${id}')">${esc(name)}</a>`;
      }
      html += '</div>';
    }
    page.innerHTML = html;
    setupTocIds();
    setupScrollSpy(note);
  }

  function buildToc(note) {
    let sectionsHtml = '';
    note.sections.forEach((sec, idx) => {
      sectionsHtml += `<a class="toc-link" data-sec="${idx}" onclick="tocJump('sec-${idx}',event)">${esc(sec.title)}</a>`;
    });
    return `<nav class="note-toc" id="noteToc"><div class="toc-sections">${sectionsHtml}</div><div class="toc-sub" id="tocSub"></div></nav>`;
  }

  function setupTocIds() {
    document.querySelectorAll('.note-section').forEach(sec => {
      let hIdx = 0;
      sec.querySelectorAll('h3').forEach(h3 => {
        h3.id = sec.id + '-h-' + hIdx;
        hIdx++;
      });
    });
  }

  function setupScrollSpy(note) {
    const sections = document.querySelectorAll('.note-section');
    const tocLinks = document.querySelectorAll('.toc-link');
    if (!tocLinks.length) return;

    if (tocScrollHandler) window.removeEventListener('scroll', tocScrollHandler);
    let lastActive = -1;
    tocScrollHandler = function() {
      const tocH = document.getElementById('noteToc');
      const offset = tocH ? tocH.offsetHeight + 16 : 60;
      let activeIdx = 0;
      for (let i = sections.length - 1; i >= 0; i--) {
        if (sections[i].getBoundingClientRect().top <= offset) { activeIdx = i; break; }
      }
      if (activeIdx === lastActive) return;
      lastActive = activeIdx;
      tocLinks.forEach(l => l.classList.remove('active'));
      const active = tocLinks[activeIdx];
      if (active) {
        active.classList.add('active');
        active.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
      updateSubHeadings(note, activeIdx);
    };
    window.addEventListener('scroll', tocScrollHandler, { passive: true });
    tocLinks[0].classList.add('active');
    updateSubHeadings(note, 0);
  }

  function updateSubHeadings(note, secIdx) {
    const sub = document.getElementById('tocSub');
    if (!sub) return;
    const sec = note.sections[secIdx];
    if (!sec) { sub.innerHTML = ''; return; }
    const headings = (Array.isArray(sec.content) ? sec.content : []).filter(b => b && b.type === 'heading');
    if (!headings.length) { sub.innerHTML = ''; return; }
    let html = '';
    headings.forEach((h, hIdx) => {
      html += `<a class="toc-sublink" onclick="tocJump('sec-${secIdx}-h-${hIdx}',event)">${esc(h.text)}</a>`;
    });
    sub.innerHTML = html;
  }

  window.tocJump = function(id, e) {
    if (e) e.preventDefault();
    const el = document.getElementById(id);
    if (!el) return;
    const tocH = document.getElementById('noteToc');
    const offset = tocH ? tocH.offsetHeight + 8 : 0;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo(0, top);
    window.dispatchEvent(new Event('scroll'));
  };

  function renderContent(content) {
    if (typeof content === 'string') return renderMarkdown(content);
    if (Array.isArray(content)) return content.map(renderBlock).join('');
    return '';
  }

  function renderBlock(block) {
    if (typeof block === 'string') return renderMarkdown(block);
    if (!block || !block.type) return '';
    switch (block.type) {
      case 'callout':
        return `<div class="callout callout-${esc(block.style || 'logic')}"><span class="callout-icon">${calloutIcon(block.style)}</span>${renderMarkdown(block.text)}</div>`;
      case 'collapsible':
        return `<details class="collapsible"><summary>${esc(block.summary)}</summary><div class="content">${renderMarkdown(block.text)}</div></details>`;
      case 'table': return renderTable(block);
      case 'heading': return `<h3>${esc(block.text)}</h3>`;
      case 'list': {
        const tag = block.ordered ? 'ol' : 'ul';
        const items = (block.items || []).map(i => `<li>${renderMarkdown(i)}</li>`).join('');
        return `<${tag} style="padding-left:1.25rem;margin:0.5rem 0;">${items}</${tag}>`;
      }
      case 'source':
        return `<span class="source-tag">${esc(block.book)} p.${esc(block.pages)}</span>`;
      default: return block.text ? renderMarkdown(block.text) : '';
    }
  }

  function renderTable(block) {
    if (!block.headers || !block.rows) return '';
    let html = '<div style="overflow-x:auto;"><table class="note-table"><thead><tr>';
    for (const h of block.headers) html += `<th>${esc(h)}</th>`;
    html += '</tr></thead><tbody>';
    for (const row of block.rows) {
      html += '<tr>';
      for (const cell of row) html += `<td>${esc(cell)}</td>`;
      html += '</tr>';
    }
    return html + '</tbody></table></div>';
  }

  function renderMarkdown(text) {
    if (!text) return '';
    let s = esc(text);
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
    s = s.replace(/`(.+?)`/g, '<code style="background:var(--bg-sidebar);padding:0.1rem 0.3rem;border-radius:3px;font-size:0.85em;">$1</code>');
    s = s.replace(/\n/g, '<br>');
    return `<p style="margin:0.4rem 0;">${s}</p>`;
  }

  function calloutIcon(style) {
    return { guideline: '\u{1F4CC}', logic: '\u{1F4A1}', trap: '⚠️' }[style] || '\u{1F4A1}';
  }

  function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function slugify(text) {
    return text.replace(/[^\w一-鿿]+/g, '-').replace(/^-|-$/g, '');
  }

  // ── Highlight System ──
  function setupHighlightToolbar() {
    const toolbar = document.getElementById('highlightToolbar');
    let hideTimer = null;

    document.addEventListener('mouseup', () => {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !document.getElementById('notePage').contains(sel.anchorNode)) {
        hideTimer = setTimeout(() => { toolbar.style.display = 'none'; }, 200);
        return;
      }
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      toolbar.style.left = Math.max(0, rect.left + rect.width / 2 - 80) + 'px';
      toolbar.style.top = (rect.top - 44) + 'px';
      toolbar.style.display = 'flex';
    });

    toolbar.querySelectorAll('.hl-btn').forEach(btn => {
      btn.addEventListener('mousedown', async (e) => {
        e.preventDefault();
        const color = btn.dataset.color;
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) return;

        const anchor = getTextAnchor(sel);
        const range = sel.getRangeAt(0).cloneRange();

        if (color === 'none') {
          await removeHighlight(sel);
        } else if (color === 'annotate') {
          sel.removeAllRanges();
          if (!userName) await promptUserName();
          await addAnnotationFromSelection(anchor);
        } else {
          if (!userName) await promptUserName();
          await applyHighlightFromRange(range, anchor, color);
        }
        toolbar.style.display = 'none';
      });
    });
  }

  function getTextAnchor(sel) {
    const range = sel.getRangeAt(0);
    const text = sel.toString().trim();
    if (!text) return null;

    const section = range.startContainer.parentElement.closest('.note-section');
    const secIdx = section ? parseInt(section.dataset.sec) : -1;

    const sectionText = section ? section.textContent : '';
    const selStart = sectionText.indexOf(text);
    const prefix = selStart > 0 ? sectionText.slice(Math.max(0, selStart - 30), selStart).trim() : '';
    const suffix = sectionText.slice(selStart + text.length, selStart + text.length + 30).trim();

    return { text, prefix, suffix, secIdx };
  }

  async function applyHighlightFromRange(range, anchor, color) {
    if (!anchor || anchor.secIdx < 0) return;

    const span = document.createElement('span');
    span.className = 'highlight-' + color;
    span.title = userName;
    try { range.surroundContents(span); }
    catch { const c = range.extractContents(); span.appendChild(c); range.insertNode(span); }
    window.getSelection().removeAllRanges();

    if (supabaseClient) {
      await supabaseClient.from('highlights').insert({
        note_id: currentNote.id,
        section_idx: anchor.secIdx,
        anchor_text: anchor.text.slice(0, 500),
        anchor_prefix: anchor.prefix.slice(0, 100),
        anchor_suffix: anchor.suffix.slice(0, 100),
        color: color,
        user_name: userName,
      });
    }
  }

  async function removeHighlight(sel) {
    const node = sel.anchorNode.parentElement;
    if (node && node.className && node.className.startsWith('highlight-')) {
      const text = node.textContent;
      const parent = node.parentNode;
      while (node.firstChild) parent.insertBefore(node.firstChild, node);
      parent.removeChild(node);

      if (supabaseClient && currentNote) {
        await supabaseClient.from('highlights')
          .delete()
          .eq('note_id', currentNote.id)
          .eq('anchor_text', text.slice(0, 500));
      }
    }
    sel.removeAllRanges();
  }

  async function restoreHighlights() {
    if (!supabaseClient || !currentNote) return;
    try {
      const { data } = await supabaseClient.from('highlights')
        .select('*')
        .eq('note_id', currentNote.id);
      if (!data || !data.length) return;

      for (const hl of data) {
        const section = document.querySelector(`.note-section[data-sec="${hl.section_idx}"]`);
        if (!section) continue;
        highlightTextInNode(section, hl.anchor_text, hl.color, hl.user_name);
      }
    } catch {}
  }

  function highlightTextInNode(root, text, color, user) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while (node = walker.nextNode()) {
      const idx = node.textContent.indexOf(text);
      if (idx === -1) continue;
      if (node.parentElement.className && node.parentElement.className.startsWith('highlight-')) continue;

      const range = document.createRange();
      range.setStart(node, idx);
      range.setEnd(node, idx + text.length);
      const span = document.createElement('span');
      span.className = 'highlight-' + color;
      span.title = user || '';
      range.surroundContents(span);
      return true;
    }
    return false;
  }

  // ── Annotation System (right sidebar) ──
  function showAnnotationInput(quoteText) {
    return new Promise(resolve => {
      const overlay = document.createElement('div');
      overlay.className = 'user-prompt-overlay';
      overlay.innerHTML = `<div class="user-prompt-box">
        <h2>Add Note</h2>
        <p style="font-style:italic;color:var(--text-muted);font-size:0.8rem;max-height:2.4em;overflow:hidden;margin-bottom:0.5rem;">"${esc(quoteText.slice(0, 80))}"</p>
        <textarea id="annInput" rows="3" placeholder="Your note..." style="width:100%;padding:0.5rem 0.75rem;border:1px solid var(--border);border-radius:4px;font-size:0.9rem;font-family:var(--font-sans);resize:vertical;margin-bottom:0.75rem;"></textarea>
        <br><button id="annSaveBtn" style="padding:0.5rem 1.5rem;border:none;border-radius:4px;background:var(--accent);color:#fff;cursor:pointer;font-size:0.9rem;margin-right:0.5rem;">Save</button>
        <button id="annCancelBtn" style="padding:0.5rem 1.5rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-card);cursor:pointer;font-size:0.9rem;">Cancel</button>
      </div>`;
      document.body.appendChild(overlay);
      const input = document.getElementById('annInput');
      input.focus();
      document.getElementById('annSaveBtn').addEventListener('click', () => {
        const val = input.value.trim();
        overlay.remove();
        resolve(val || null);
      });
      document.getElementById('annCancelBtn').addEventListener('click', () => {
        overlay.remove();
        resolve(null);
      });
    });
  }

  async function addAnnotationFromSelection(anchor) {
    if (!anchor || anchor.secIdx < 0) return;

    const body = await showAnnotationInput(anchor.text);
    if (!body) return;

    if (supabaseClient) {
      await supabaseClient.from('annotations').insert({
        note_id: currentNote.id,
        section_idx: anchor.secIdx,
        anchor_text: anchor.text.slice(0, 500),
        anchor_prefix: anchor.prefix.slice(0, 100),
        anchor_suffix: anchor.suffix.slice(0, 100),
        body: body.trim(),
        user_name: userName,
      });
    }
    await loadAndShowAnnotations();
  }

  async function loadAndShowAnnotations() {
    let panel = document.getElementById('annotationPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'annotationPanel';
      panel.className = 'annotation-panel';
      document.body.appendChild(panel);
    }

    if (!supabaseClient || !currentNote) {
      panel.innerHTML = '<h3>Notes</h3><p style="font-size:0.78rem;color:var(--text-muted);">Select text and click the note button to add annotations.</p>';
      return;
    }

    try {
      const { data } = await supabaseClient.from('annotations')
        .select('*')
        .eq('note_id', currentNote.id)
        .order('created_at', { ascending: true });

      let html = '<h3>Notes (' + (data ? data.length : 0) + ')</h3>';
      if (!data || !data.length) {
        html += '<p style="font-size:0.78rem;color:var(--text-muted);">Select text, then click the note button (speech bubble) to add annotations.</p>';
      } else {
        for (const ann of data) {
          html += `<div class="ann-card" data-sec="${ann.section_idx}" onclick="scrollToSection(${ann.section_idx})">`;
          if (userName === ann.user_name) {
            html += `<button class="ann-delete" onclick="event.stopPropagation();deleteAnnotation(${ann.id})" title="Delete">&times;</button>`;
          }
          html += `<div class="ann-quote">${esc(ann.anchor_text.slice(0, 80))}</div>`;
          html += `<div class="ann-body">${esc(ann.body)}</div>`;
          html += `<div class="ann-meta">${esc(ann.user_name)} &middot; ${new Date(ann.created_at).toLocaleDateString()}</div>`;
          html += '</div>';
        }
      }
      panel.innerHTML = html;
    } catch {
      panel.innerHTML = '<h3>Notes</h3><p style="font-size:0.78rem;color:var(--text-muted);">Could not load annotations.</p>';
    }
  }

  window.scrollToSection = function(secIdx) {
    const sec = document.querySelector(`.note-section[data-sec="${secIdx}"]`);
    if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  window.deleteAnnotation = async function(annId) {
    if (!supabaseClient) return;
    await supabaseClient.from('annotations').delete().eq('id', annId);
    await loadAndShowAnnotations();
  };

  init();
})();
