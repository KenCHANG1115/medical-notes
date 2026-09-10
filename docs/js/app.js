(function() {
  'use strict';

  let notesIndex = null;
  let currentNote = null;
  let supabaseClient = null;

  const SUPABASE_URL = 'https://firvfvkadexbdrsfuzpk.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_VGm4obXnBc10xM6vsUUb4w_78Df8Qxt';

  async function init() {
    if (SUPABASE_URL && SUPABASE_KEY && window.supabase) {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
    }
    try {
      const resp = await fetch('notes/index.json');
      if (resp.ok) {
        notesIndex = await resp.json();
      } else {
        notesIndex = { specialties: [] };
      }
    } catch {
      notesIndex = { specialties: [] };
    }
    buildSidebar();
    buildWelcome();
    setupRouting();
    setupMobileMenu();
    setupHighlightToolbar();
    setupAnnotations();
  }

  function buildSidebar() {
    const nav = document.getElementById('navContent');
    if (!notesIndex.specialties.length) {
      nav.innerHTML = '<p style="padding:1.25rem;color:var(--text-muted);font-size:0.85rem;">No notes yet. Generate notes using the CLI tool.</p>';
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
      for (const d of spec.diseases) {
        html += `<a class="nav-disease" data-id="${d.id}" onclick="loadNote('${d.id}')">${d.name}</a>`;
      }
      html += '</div></div>';
    }
    nav.innerHTML = html;
  }

  function buildWelcome() {
    const grid = document.getElementById('specialtyGrid');
    if (!notesIndex.specialties.length) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:2rem;">
          <p style="color:var(--text-muted);font-size:0.95rem;line-height:1.8;">
            No notes have been generated yet.<br>
            Use the note generation script to create notes:<br>
            <code style="background:var(--bg-sidebar);padding:0.2rem 0.5rem;border-radius:4px;font-size:0.85rem;">
              python scripts/generate_note.py "Disease Name"
            </code>
          </p>
        </div>`;
      return;
    }
    let html = '';
    for (const spec of notesIndex.specialties) {
      html += `<div class="specialty-card" onclick="expandSpecialty('${slugify(spec.name)}')">`;
      html += `<h3>${spec.name}</h3>`;
      html += `<span class="count">${spec.diseases.length} topics</span>`;
      html += '</div>';
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
    const btn = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    btn.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.getElementById('mainContent').addEventListener('click', () => {
      sidebar.classList.remove('open');
    });
  }

  window.toggleSpec = function(el) {
    const specId = el.dataset.spec;
    const diseases = document.getElementById('diseases-' + specId);
    el.classList.toggle('expanded');
    diseases.classList.toggle('show');
  };

  window.expandSpecialty = function(specId) {
    const el = document.querySelector(`.nav-specialty[data-spec="${specId}"]`);
    if (el && !el.classList.contains('expanded')) {
      el.classList.add('expanded');
      document.getElementById('diseases-' + specId).classList.add('show');
    }
    el && el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

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
    } catch {
      notePage.innerHTML = '<p style="color:var(--text-muted);padding:2rem;">Note not found.</p>';
    }

    document.getElementById('sidebar').classList.remove('open');
    window.scrollTo(0, 0);
  };

  function renderNote(note) {
    const page = document.getElementById('notePage');
    let html = '<div class="note-header">';
    html += `<h1>${esc(note.title)}</h1>`;
    html += '<div class="note-meta">';
    if (note.specialty) html += `<span>${esc(note.specialty)}</span>`;
    if (note.sources) html += `<span>Sources: ${esc(note.sources.join(', '))}</span>`;
    if (note.generated) html += `<span>${esc(note.generated)}</span>`;
    html += '</div></div>';

    for (const sec of note.sections) {
      html += '<div class="note-section">';
      html += `<h2>${esc(sec.title)}</h2>`;
      html += renderContent(sec.content);
      html += '</div>';
    }

    if (note.related && note.related.length) {
      html += '<div class="related-notes">';
      html += '<h3>Related Notes</h3>';
      for (const r of note.related) {
        html += `<a class="related-link" onclick="loadNote('${r.id}')">${esc(r.name)}</a>`;
      }
      html += '</div>';
    }

    page.innerHTML = html;
  }

  function renderContent(content) {
    if (typeof content === 'string') {
      return renderMarkdown(content);
    }
    if (Array.isArray(content)) {
      return content.map(renderBlock).join('');
    }
    return '';
  }

  function renderBlock(block) {
    if (typeof block === 'string') return renderMarkdown(block);
    if (!block || !block.type) return '';

    switch (block.type) {
      case 'callout':
        return `<div class="callout callout-${esc(block.style || 'logic')}">
          <span class="callout-icon">${calloutIcon(block.style)}</span>${renderMarkdown(block.text)}
        </div>`;

      case 'collapsible':
        return `<details class="collapsible">
          <summary>${esc(block.summary)}</summary>
          <div class="content">${renderMarkdown(block.text)}</div>
        </details>`;

      case 'table':
        return renderTable(block);

      case 'heading':
        return `<h3>${esc(block.text)}</h3>`;

      case 'list':
        const tag = block.ordered ? 'ol' : 'ul';
        const items = (block.items || []).map(i => `<li>${renderMarkdown(i)}</li>`).join('');
        return `<${tag} style="padding-left:1.25rem;margin:0.5rem 0;">${items}</${tag}>`;

      case 'source':
        return `<span class="source-tag">${esc(block.book)} p.${esc(block.pages)}</span>`;

      default:
        return block.text ? renderMarkdown(block.text) : '';
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
    html += '</tbody></table></div>';
    return html;
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
    const icons = { guideline: '\u{1F4CC}', logic: '\u{1F4A1}', trap: '⚠️' };
    return icons[style] || '\u{1F4A1}';
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

  // Highlight toolbar
  function setupHighlightToolbar() {
    const toolbar = document.getElementById('highlightToolbar');
    document.addEventListener('mouseup', (e) => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !document.getElementById('notePage').contains(sel.anchorNode)) {
        setTimeout(() => { toolbar.style.display = 'none'; }, 200);
        return;
      }
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      toolbar.style.left = (rect.left + rect.width / 2 - 70) + 'px';
      toolbar.style.top = (rect.top - 40 + window.scrollY) + 'px';
      toolbar.style.display = 'flex';
    });

    toolbar.querySelectorAll('.hl-btn').forEach(btn => {
      btn.addEventListener('mousedown', (e) => {
        e.preventDefault();
        const color = btn.dataset.color;
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) return;
        if (color === 'none') {
          removeHighlight(sel);
        } else {
          applyHighlight(sel, color);
        }
        toolbar.style.display = 'none';
      });
    });
  }

  function applyHighlight(sel, color) {
    const range = sel.getRangeAt(0);
    const span = document.createElement('span');
    span.className = 'highlight-' + color;
    span.dataset.hlId = Date.now().toString(36);
    try {
      range.surroundContents(span);
    } catch {
      const contents = range.extractContents();
      span.appendChild(contents);
      range.insertNode(span);
    }
    sel.removeAllRanges();
    saveHighlights();
  }

  function removeHighlight(sel) {
    const node = sel.anchorNode.parentElement;
    if (node && node.className && node.className.startsWith('highlight-')) {
      const parent = node.parentNode;
      while (node.firstChild) parent.insertBefore(node.firstChild, node);
      parent.removeChild(node);
    }
    sel.removeAllRanges();
    saveHighlights();
  }

  function saveHighlights() {
    if (!currentNote) return;
    const noteEl = document.getElementById('notePage');
    const highlights = [];
    noteEl.querySelectorAll('[class^="highlight-"]').forEach(el => {
      highlights.push({
        id: el.dataset.hlId,
        color: el.className.replace('highlight-', ''),
        text: el.textContent,
      });
    });
    try {
      localStorage.setItem('hl-' + currentNote.id, JSON.stringify(highlights));
    } catch {}
    if (supabaseClient && currentNote) {
      supabaseClient.from('highlights').upsert({
        note_id: currentNote.id,
        data: highlights,
        updated_at: new Date().toISOString(),
      }, { onConflict: 'note_id' }).then(() => {});
    }
  }

  // Annotations (margin notes)
  function setupAnnotations() {
    document.getElementById('notePage').addEventListener('dblclick', (e) => {
      const section = e.target.closest('.note-section');
      if (!section || !currentNote) return;
      const sectionTitle = section.querySelector('h2')?.textContent || '';
      showAnnotationDialog(sectionTitle, section);
    });
  }

  function showAnnotationDialog(sectionTitle, sectionEl) {
    let existing = sectionEl.querySelector('.annotation-box');
    if (existing) { existing.focus(); return; }

    const box = document.createElement('div');
    box.className = 'annotation-box';
    box.style.cssText = 'background:var(--bg-card);border:1px solid var(--accent);border-radius:var(--radius);padding:0.75rem;margin:0.75rem 0;';
    box.innerHTML = `
      <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.4rem;">Annotation for "${esc(sectionTitle)}"</div>
      <textarea style="width:100%;min-height:60px;border:1px solid var(--border);border-radius:4px;padding:0.5rem;font-size:0.85rem;font-family:var(--font-sans);resize:vertical;" placeholder="Write your notes here..."></textarea>
      <div style="margin-top:0.4rem;text-align:right;">
        <button onclick="this.closest('.annotation-box').remove()" style="padding:0.3rem 0.6rem;border:1px solid var(--border);border-radius:4px;background:var(--bg-page);cursor:pointer;font-size:0.8rem;margin-right:0.3rem;">Cancel</button>
        <button class="save-annotation" style="padding:0.3rem 0.6rem;border:none;border-radius:4px;background:var(--accent);color:#fff;cursor:pointer;font-size:0.8rem;">Save</button>
      </div>`;
    sectionEl.appendChild(box);

    const textarea = box.querySelector('textarea');
    textarea.focus();

    loadAnnotation(currentNote.id, sectionTitle).then(text => {
      if (text) textarea.value = text;
    });

    box.querySelector('.save-annotation').addEventListener('click', () => {
      const text = textarea.value.trim();
      if (text) {
        saveAnnotation(currentNote.id, sectionTitle, text);
        box.innerHTML = `<div class="margin-note" style="position:relative;right:auto;width:auto;margin:0.5rem 0;">
          <strong style="font-size:0.75rem;">My Note:</strong> ${esc(text)}
        </div>`;
      } else {
        box.remove();
      }
    });
  }

  async function saveAnnotation(noteId, section, text) {
    try {
      localStorage.setItem(`ann-${noteId}-${section}`, text);
    } catch {}
    if (supabaseClient) {
      await supabaseClient.from('annotations').upsert({
        note_id: noteId,
        section: section,
        text: text,
        updated_at: new Date().toISOString(),
      }, { onConflict: 'note_id,section' });
    }
  }

  async function loadAnnotation(noteId, section) {
    if (supabaseClient) {
      try {
        const { data } = await supabaseClient.from('annotations')
          .select('text')
          .eq('note_id', noteId)
          .eq('section', section)
          .single();
        if (data) return data.text;
      } catch {}
    }
    try {
      return localStorage.getItem(`ann-${noteId}-${section}`) || '';
    } catch { return ''; }
  }

  init();
})();
