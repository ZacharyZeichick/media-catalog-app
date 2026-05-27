// ── State ──────────────────────────────────────────────────────────────────
const state = {
  entries: [],   // full cached dataset from /api/media
  type:    '',
  status:  '',
  genre:   '',
  rewatch: '',
  rated:   '',   // 'rated' | 'unrated' | ''
  sort:    'title-asc',
  query:   '',
  openId:  null,
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const grid        = document.getElementById('card-grid');
const emptyState  = document.getElementById('empty-state');
const overlay     = document.getElementById('overlay');
const drawer      = document.getElementById('detail-drawer');
const detailContent = document.getElementById('detail-content');
const searchInput = document.getElementById('search-input');
const addModal    = document.getElementById('add-modal');

// Custom dropdown refs
const statusSelect  = document.getElementById('status-select');
const genreSelect   = document.getElementById('genre-select');
const rewatchSelect = document.getElementById('rewatch-select');
const sortDropdown  = document.getElementById('sort-dropdown');

// ── API ────────────────────────────────────────────────────────────────────
async function fetchAllMedia() {
  const res = await fetch('/api/media');
  if (!res.ok) throw new Error('fetch failed');
  return res.json();
}

async function fetchEntry(id) {
  const res = await fetch(`/api/media/${id}`);
  if (!res.ok) throw new Error('fetch failed');
  return res.json();
}

// ── Filtering & sorting ────────────────────────────────────────────────────
function applyFilters() {
  let results = state.entries;

  if (state.type)
    results = results.filter(e => e.media_type === state.type);

  if (state.status)
    results = results.filter(e => e.status === state.status);

  if (state.genre)
    results = results.filter(e => e.genres && e.genres.split(',').map(g => g.trim()).includes(state.genre));

  if (state.rewatch)
    results = results.filter(e => e.rewatch_tag === state.rewatch);

  const hasScore = e => e.rating != null;
  if (state.rated === 'rated')
    results = results.filter(hasScore);
  else if (state.rated === 'unrated')
    results = results.filter(e => !hasScore(e));
  else if (state.rated === 'needs-rating')
    results = results.filter(e => !hasScore(e) && (e.status === 'Watched' || e.status === 'Caught Up'));

  if (state.query) {
    const q = state.query.toLowerCase();
    results = results.filter(e => e.title.toLowerCase().includes(q));
  }

  renderSectionHeader(results);
  renderCards(sortEntries(results));
  updateHeroSlides();
}

function updateHeroSlides() {
  // Update hero slides in-place to reflect current entry data
  heroSlides.querySelectorAll('.hero-slide').forEach(slide => {
    const id = Number(slide.dataset.id);
    const entry = state.entries.find(e => e.id === id);
    if (!entry) return;
    const watchedBtn = slide.querySelector('[data-hero-watched]');
    if (watchedBtn && entry.status !== 'Planned') {
      watchedBtn.remove();
    }
  });
}

function sortEntries(entries) {
  const a2b = (a, b, key, fallback = -Infinity) =>
    (b[key] ?? fallback) - (a[key] ?? fallback);

  const sorted = [...entries];
  switch (state.sort) {
    case 'title-asc':    return sorted.sort((a, b) => a.title.localeCompare(b.title));
    case 'title-desc':   return sorted.sort((a, b) => b.title.localeCompare(a.title));
    case 'year-desc':    return sorted.sort((a, b) => a2b(a, b, 'year', 0));
    case 'year-asc':     return sorted.sort((a, b) => (a.year ?? 0) - (b.year ?? 0));
    case 'score-desc':   return sorted.sort((a, b) => a2b(a, b, 'rating'));
    case 'imdb-desc':    return sorted.sort((a, b) => a2b(a, b, 'imdb_rating'));
    case 'rt-desc':      return sorted.sort((a, b) => a2b(a, b, 'rt_tomatometer'));
    case 'rt-aud-desc':  return sorted.sort((a, b) => a2b(a, b, 'rt_audience'));
    case 'mc-desc':      return sorted.sort((a, b) => a2b(a, b, 'metacritic'));
    case 'added-desc':   return sorted.sort((a, b) => new Date(b.date_added) - new Date(a.date_added));
    default:             return sorted;
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function badgeClass(status) {
  return 'badge-' + status.toLowerCase().replace(/\s+/g, '-');
}

const SERVICE_CSS = {
  'Netflix':      'svc-netflix',
  'Max':          'svc-max',
  'Hulu':         'svc-hulu',
  'Peacock':      'svc-peacock',
  'Prime Video':  'svc-prime',
  'Paramount+':   'svc-paramount',
  'Apple TV+':    'svc-appletv',
  'Disney+':      'svc-disney',
};

function streamingHtml(sourcesJson) {
  let services = [];
  try { services = sourcesJson ? JSON.parse(sourcesJson) : []; } catch { /* ignore */ }

  if (!services.length)
    return `<div class="not-streaming">Not on your streaming services</div>`;

  const badges = services.map(s => {
    const cls = SERVICE_CSS[s.service] ?? '';
    return `<span class="service-badge ${cls}">${esc(s.service)}</span>`;
  }).join('');
  return `<div class="streaming-row">${badges}</div>`;
}

function yearRange(entry) {
  if (entry.media_type === 'show') {
    if (entry.year && entry.year_end) return `${entry.year}–${entry.year_end}`;
    if (entry.year)                   return `${entry.year}–`;
  }
  return entry.year ?? '—';
}

function posterHtml(entry, variant) {
  if (entry.poster_url) {
    return `<img src="${esc(entry.poster_url)}" alt="${esc(entry.title)}" loading="lazy">`;
  }
  if (variant === 'detail') {
    return `<div class="detail-ph"><span class="film-icon">🎬</span></div>`;
  }
  return `
    <div class="poster-placeholder">
      <span class="film-icon">🎬</span>
      <span class="ph-title">${esc(entry.title)}</span>
    </div>`;
}

function ratingTile(label, value, suffix = '') {
  const display = value != null
    ? `<div class="rating-tile-value">${value}${suffix}</div>`
    : `<div class="rating-tile-value null">—</div>`;
  return `<div class="rating-tile"><div class="rating-tile-label">${label}</div>${display}</div>`;
}

function scoreHtml(label, value) {
  const display = value != null
    ? `<span class="score-value">${value}<span class="score-suffix">/10</span></span>`
    : `<span class="score-value empty">—</span>`;
  return `<div class="score-item"><span class="score-label">${label}</span>${display}</div>`;
}

// ── Render cards ───────────────────────────────────────────────────────────
function cardPosterUrl(e) {
  if (e.poster_path) return `https://image.tmdb.org/t/p/w400${e.poster_path}`;
  return e.poster_url || '';
}

const CHECK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
const EDIT_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';

function getCardBadge(e) {
  const sort = state.sort;
  if (sort === 'imdb-desc') {
    return e.imdb_rating != null
      ? `<span class="card-score">${e.imdb_rating}</span>`
      : `<span class="card-score card-score-empty">\u2014</span>`;
  }
  if (sort === 'rt-desc') {
    return e.rt_tomatometer != null
      ? `<span class="card-score">${e.rt_tomatometer}%</span>`
      : `<span class="card-score card-score-empty">\u2014</span>`;
  }
  if (sort === 'rt-aud-desc') {
    return e.rt_audience != null
      ? `<span class="card-score">${e.rt_audience}%</span>`
      : `<span class="card-score card-score-empty">\u2014</span>`;
  }
  if (sort === 'mc-desc') {
    return e.metacritic != null
      ? `<span class="card-score">${e.metacritic}</span>`
      : `<span class="card-score card-score-empty">\u2014</span>`;
  }
  // Default: My Score
  return e.rating != null
    ? `<span class="card-score">${e.rating}</span>`
    : '';
}

function buildCardHtml(e, opts = {}) {
  const url = cardPosterUrl(e);
  const img = url
    ? `<img src="${esc(url)}" alt="${esc(e.title)}" loading="lazy">`
    : `<div class="poster-placeholder"><span class="film-icon">🎬</span></div>`;
  const visibleClass = opts.visible ? ' visible' : '';
  return `
  <div class="card${visibleClass}" data-id="${e.id}" role="button" tabindex="0" aria-label="${esc(e.title)}">
    <div class="card-poster">${img}</div>
    <span class="card-dot-wrap" data-tooltip="${esc(e.status)}">
      <span class="card-status-dot" data-status="${esc(e.status)}"></span>
    </span>
    ${getCardBadge(e)}
    <div class="card-actions">
      <button class="card-action-btn" data-action="toggle-watched" data-id="${e.id}" title="${e.status === 'Watched' ? 'Mark Unwatched' : 'Mark Watched'}">${CHECK_SVG}</button>
      <button class="card-action-btn" data-action="open-edit" data-id="${e.id}" title="Edit">${EDIT_SVG}</button>
      <button class="card-action-btn" data-action="add-to-list" data-id="${e.id}" title="Add to List">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
      </button>
      <button class="card-action-btn${watchlistEntryIds.has(e.id) ? ' on-watchlist' : ''}" data-action="toggle-watchlist" data-id="${e.id}" title="${watchlistEntryIds.has(e.id) ? 'Remove from Watchlist' : 'Add to Watchlist'}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      </button>
    </div>
    <div class="card-body">
      <div class="card-title">${esc(e.title)}</div>
      <div class="card-year">${e.year ?? ''}</div>
    </div>
  </div>`;
}

function renderCards(entries) {
  if (entries.length === 0) {
    grid.innerHTML = '';
    if (state.query) {
      emptyState.innerHTML = `
        <div class="lists-empty">
          <div class="lists-empty-text">No results for "${esc(state.query)}"</div>
          <div class="lists-empty-sub">Not in your catalog yet?</div>
          <button class="btn-primary" id="empty-add-btn">+ Add "${esc(state.query)}"</button>
        </div>`;
      emptyState.hidden = false;
      document.getElementById('empty-add-btn')?.addEventListener('click', () => openAddModal(state.query));
    } else {
      emptyState.innerHTML = 'No results.';
      emptyState.hidden = false;
    }
    return;
  }
  emptyState.hidden = true;
  grid.innerHTML = entries.map(e => buildCardHtml(e)).join('');

  const observer = new IntersectionObserver((obs) => {
    obs.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  grid.querySelectorAll('.card').forEach(card => observer.observe(card));
}

// ── Render detail ──────────────────────────────────────────────────────────

const STATUS_DOT_COLORS = {
  'Watched': '#4ade80', 'Caught Up': '#4ade80', 'Watching': '#c4785a',
  'Get Back To': '#f97316', 'On Hold': '#f97316', 'Planned': '#504a44', 'Dropped': '#ef4444',
};

function renderDetail(entry) {
  const directors = entry.people.filter(p => p.role === 'director');
  const writers   = entry.people.filter(p => p.role === 'writer');
  const allPeople = [...directors, ...writers];

  const peopleSection = allPeople.length ? `
    <div class="detail-section">
      <div class="section-label">People</div>
      <div class="people-list">
        ${allPeople.map(p => `
          <div class="person-row">
            <span class="person-role">${esc(p.role)}</span>
            <span class="person-name">${esc(p.name)}</span>
          </div>`).join('')}
      </div>
    </div>` : '';

  const notesItems = [
    entry.notes_what && `<p class="notes-text">${esc(entry.notes_what)}</p>`,
    entry.notes_why  && `<p class="notes-text"><strong>Score reason:</strong> ${esc(entry.notes_why)}</p>`,
    entry.notes_recommend && `<p class="notes-text"><strong>Notes:</strong> ${esc(entry.notes_recommend)}</p>`,
  ].filter(Boolean);

  const notesSection = notesItems.length ? `
    <div class="detail-section">
      <div class="section-label">About</div>
      ${notesItems.join('')}
    </div>` : '';

  // Hero image — prefer backdrop, fall back to poster with blur class
  const hasBackdrop = !!entry.backdrop_path;
  const drawerHeroUrl = entry.backdrop_path
    ? `https://image.tmdb.org/t/p/original${entry.backdrop_path}`
    : (entry.poster_path ? `https://image.tmdb.org/t/p/w500${entry.poster_path}` : entry.poster_url);
  const heroImage = drawerHeroUrl
    ? `<img src="${esc(drawerHeroUrl)}" alt="" class="${hasBackdrop ? '' : 'detail-hero-poster-fallback'}">`
    : `<div class="detail-ph"><span class="film-icon">🎬</span></div>`;

  // Unified pill row: status (with dot), rewatch, mood, streaming
  const statusDotColor = STATUS_DOT_COLORS[entry.status] || '#504a44';
  const pills = [];
  pills.push(`<span class="detail-pill"><span class="detail-pill-dot" style="background:${statusDotColor}"></span>${esc(entry.status)}</span>`);
  if (entry.rewatch_tag) pills.push(`<span class="detail-pill">Rewatch: ${esc(entry.rewatch_tag)}</span>`);
  if (entry.vibe_tags) {
    entry.vibe_tags.split(',').map(t => t.trim()).filter(Boolean).forEach(tag => {
      pills.push(`<span class="detail-pill">${esc(tag)}</span>`);
    });
  }

  let services = [];
  try { services = entry.streaming_sources ? JSON.parse(entry.streaming_sources) : []; } catch {}
  services.forEach(s => {
    const cls = SERVICE_CSS[s.service] || '';
    pills.push(`<span class="detail-pill ${cls}">${esc(s.service)}</span>`);
  });

  const pillsRow = pills.length ? `<div class="detail-pills">${pills.join('')}</div>` : '';

  // Convince Me — only for backlog entries
  const convinceStatuses = ['Planned', 'On Hold', 'Get Back To'];
  const convinceHtml = convinceStatuses.includes(entry.status)
    ? `<div class="convince-section" id="convince-section">
         <button class="convince-btn" id="convince-btn">Convince Me</button>
       </div>`
    : '';

  // Scores — only show categories that have a value
  const scoreItems = [];
  if (entry.rating != null) scoreItems.push(scoreHtml('Rating', entry.rating));

  const scoresSection = scoreItems.length ? `
      <div class="detail-section">
        <div class="section-label">Scores</div>
        <div class="scores-row">${scoreItems.join('')}</div>
        ${entry.legacy_rating != null ? `<div class="legacy-note">Legacy: ${entry.legacy_rating}</div>` : ''}
      </div>` : '';

  // External ratings — only show tiles that have a value
  const ratingTiles = [
    entry.rt_tomatometer != null && ratingTile('RT Tomatometer', entry.rt_tomatometer, '%'),
    entry.rt_audience    != null && ratingTile('RT Audience', entry.rt_audience, '%'),
    entry.imdb_rating    != null && ratingTile('IMDb', entry.imdb_rating),
    entry.metacritic     != null && ratingTile('Metacritic', entry.metacritic),
  ].filter(Boolean);

  const ratingsSection = ratingTiles.length ? `
      <div class="detail-section">
        <div class="section-label">External Ratings</div>
        <div class="ratings-grid">${ratingTiles.join('')}</div>
      </div>` : '';

  const mediaType = entry.media_type === 'show' ? 'TV Show' : 'Movie';

  detailContent.innerHTML = `
    <div class="detail-hero">
      ${heroImage}
      <div class="detail-hero-gradient"></div>
      <div class="detail-hero-actions">
        <button class="btn-ghost" id="enrich-btn" title="Refresh metadata">↻</button>
        <button class="btn-ghost" id="trailer-btn" title="Watch Trailer">▶ Trailer</button>
        <button class="btn-ghost" id="watchlist-toggle-btn">${watchlistEntryIds.has(entry.id) ? '✓ Watchlist' : '+ Watchlist'}</button>
        <button class="btn-ghost" id="edit-btn">Edit</button>
        <button class="close-btn" id="close-btn" aria-label="Close">✕</button>
      </div>
      <div class="detail-hero-content">
        <h1 class="detail-title">${esc(entry.title)}</h1>
        <div class="detail-year">${yearRange(entry)} · ${mediaType}${entry.genres ? ` · ${esc(entry.genres)}` : ''}</div>
      </div>
    </div>
    <div class="detail-body">
      ${pillsRow}
      ${convinceHtml}
      ${scoresSection}
      ${ratingsSection}
      ${notesSection}
      ${peopleSection}
    </div>
  `;

  document.getElementById('close-btn').addEventListener('click', closeDetail);
  document.getElementById('edit-btn').addEventListener('click', () => renderEditForm(entry));

  const convinceSection = document.getElementById('convince-section');
  if (convinceSection) {
    convinceSection.addEventListener('click', async (e) => {
      const btn = e.target.closest('.convince-btn');
      const dismiss = e.target.closest('.convince-dismiss');
      if (dismiss) {
        convinceSection.innerHTML = '<button class="convince-btn">Convince Me</button>';
        return;
      }
      if (!btn) return;
      convinceSection.innerHTML = '<div class="convince-loading">Thinking...</div>';
      try {
        const res = await fetch('/api/recommend/convince', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_id: entry.id }),
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Failed');
        const { pitch } = await res.json();
        convinceSection.innerHTML = `
          <div class="convince-pitch">${esc(pitch)}</div>
          <button class="convince-dismiss">Dismiss</button>`;
      } catch {
        convinceSection.innerHTML = '<div class="convince-error">Couldn\'t generate pitch</div>';
        setTimeout(() => {
          convinceSection.innerHTML = '<button class="convince-btn">Convince Me</button>';
        }, 2000);
      }
    });
  }
  document.getElementById('trailer-btn').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = '…';
    try {
      const res = await fetch(`/api/media/${entry.id}/trailer`);
      if (!res.ok) throw new Error();
      const { url } = await res.json();
      window.open(url, '_blank');
      btn.textContent = '▶ Trailer';
    } catch {
      btn.textContent = 'No trailer';
      setTimeout(() => { btn.textContent = '▶ Trailer'; }, 2000);
    }
    btn.disabled = false;
  });
  document.getElementById('watchlist-toggle-btn').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    await toggleWatchlist(entry.id);
    btn.textContent = watchlistEntryIds.has(entry.id) ? '✓ Watchlist' : '+ Watchlist';
    btn.disabled = false;
  });
  document.getElementById('enrich-btn').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = '…';
    try {
      const res = await fetch(`/api/media/${entry.id}/enrich`, { method: 'POST' });
      if (!res.ok) throw new Error('Enrich failed');
      const updated = await res.json();
      const idx = state.entries.findIndex(e => e.id === updated.id);
      if (idx !== -1) state.entries[idx] = updated;
      applyFilters();
      renderDetail(updated);
    } catch {
      btn.textContent = '✕';
      btn.disabled = false;
    }
  });
}

// ── Edit form ──────────────────────────────────────────────────────────────
const STATUS_OPTIONS  = ['Planned','Watching','Caught Up','Watched','On Hold','Get Back To','Dropped'];
const VIBE_TAG_OPTIONS = ['Funny','Dark','Intense','Heartfelt','Cozy','Creepy','Hype','Easy Watch','Mind-Bending','Emotional Ride','Slow Burn','Bingeable'];
const REWATCH_OPTIONS = ['Never','Rarely','Sometimes','Anytime'];

function selectOptions(options, selected, placeholder) {
  const blank = `<option value="">${placeholder}</option>`;
  return blank + options.map(o =>
    `<option value="${esc(o)}" ${o === selected ? 'selected' : ''}>${esc(o)}</option>`
  ).join('');
}

function renderEditForm(entry) {
  detailContent.innerHTML = `
    <div class="detail-close-row">
      <button class="btn-ghost" id="edit-cancel-btn">Cancel</button>
      <button class="close-btn" id="close-btn" aria-label="Close">✕</button>
    </div>
    <form class="edit-form" id="edit-form">
      <div class="form-field">
        <label>Status</label>
        <select name="status">${selectOptions(STATUS_OPTIONS, entry.status, '—')}</select>
      </div>
      <div class="form-field">
        <label>Rating</label>
        <div class="rating-slider-row">
          <input type="range" id="rating-slider" min="1" max="10" step="0.1"
                 value="${entry.rating ?? 5}" class="rating-slider">
          <input type="number" name="rating" id="rating-input" min="1" max="10" step="0.1"
                 value="${entry.rating ?? ''}" class="rating-number" placeholder="—">
        </div>
      </div>
      <div class="form-field">
        <label>Rewatch</label>
        <select name="rewatch_tag">${selectOptions(REWATCH_OPTIONS, entry.rewatch_tag, 'None')}</select>
      </div>
      <div class="form-field">
        <label>Vibe Tags</label>
        <div class="vibe-tag-picker" id="vibe-tag-picker">
          ${VIBE_TAG_OPTIONS.map(tag => {
            const sel = entry.vibe_tags && entry.vibe_tags.split(',').map(t => t.trim()).includes(tag);
            return `<button type="button" class="vibe-tag-btn${sel ? ' selected' : ''}" data-tag="${esc(tag)}">${esc(tag)}</button>`;
          }).join('')}
        </div>
        <input type="hidden" name="vibe_tags" id="vibe-tags-input" value="${esc(entry.vibe_tags ?? '')}">
      </div>
      <div class="form-field">
        <label>About (1–2 sentences)</label>
        <textarea name="notes_what">${esc(entry.notes_what)}</textarea>
      </div>
      <div class="form-field">
        <label>Score Reason</label>
        <textarea name="notes_why">${esc(entry.notes_why)}</textarea>
      </div>
      <div class="form-field">
        <label>Quick Notes</label>
        <textarea name="notes_recommend">${esc(entry.notes_recommend)}</textarea>
      </div>
      <div class="modal-actions">
        <button type="submit" class="btn-primary" id="edit-save-btn">Save</button>
        <button type="button" class="btn-ghost" id="edit-cancel-btn2">Cancel</button>
      </div>
      <div id="edit-error" class="form-error"></div>
      <div class="edit-danger-zone">
        <button type="button" class="btn-danger" id="edit-delete-btn">Delete Entry</button>
      </div>
    </form>
  `;

  const form = document.getElementById('edit-form');
  const cancelRestore = () => openDetail(entry.id);

  document.getElementById('close-btn').addEventListener('click', closeDetail);
  document.getElementById('edit-cancel-btn').addEventListener('click', cancelRestore);
  document.getElementById('edit-cancel-btn2').addEventListener('click', cancelRestore);

  // Rating slider + number sync
  const ratingSlider = document.getElementById('rating-slider');
  const ratingNumber = document.getElementById('rating-input');
  ratingSlider.addEventListener('input', () => {
    ratingNumber.value = ratingSlider.value;
  });
  ratingNumber.addEventListener('input', () => {
    if (ratingNumber.value) ratingSlider.value = ratingNumber.value;
  });

  // Vibe tag toggle buttons
  const vibeInput = document.getElementById('vibe-tags-input');
  document.querySelectorAll('.vibe-tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('selected');
      const selected = [...document.querySelectorAll('.vibe-tag-btn.selected')].map(b => b.dataset.tag);
      vibeInput.value = selected.join(', ');
    });
  });

  document.getElementById('edit-delete-btn').addEventListener('click', async () => {
    if (!confirm(`Delete "${entry.title}" from your catalog?`)) return;
    try {
      const res = await fetch(`/api/media/${entry.id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      state.entries = state.entries.filter(e => e.id !== entry.id);
      populateGenres(state.entries);
      applyFilters();
      closeDetail();
    } catch (err) {
      document.getElementById('edit-error').textContent = err.message;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('edit-error');
    const saveBtn = document.getElementById('edit-save-btn');
    errEl.textContent = '';
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    const fd = new FormData(form);
    const body = {};
    for (const [key, val] of fd.entries()) {
      if (val === '') continue;
      if (key === 'rating')
        body[key] = parseFloat(val);
      else
        body[key] = val;
    }

    try {
      const res = await fetch(`/api/media/${entry.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      const updated = await res.json();
      // Update cache
      const idx = state.entries.findIndex(e => e.id === updated.id);
      if (idx !== -1) state.entries[idx] = updated;
      applyFilters();
      renderDetail(updated);
    } catch (err) {
      errEl.textContent = err.message;
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
    }
  });
}

// ── Drawer open / close ────────────────────────────────────────────────────
async function openDetail(id) {
  const wasOpen = drawer.classList.contains('open');
  state.openId = id;
  overlay.classList.add('visible');
  drawer.setAttribute('aria-hidden', 'false');

  if (wasOpen) {
    // Crossfade: fade out current content
    detailContent.classList.add('detail-fade-out');
    await new Promise(r => setTimeout(r, 200));
    detailContent.classList.remove('detail-fade-out');
  } else {
    drawer.classList.add('open');
    history.pushState({ view: 'detail', id }, '');
  }

  detailContent.innerHTML = '<div class="drawer-status">Loading…</div>';
  detailContent.classList.add('detail-fade-in');

  try {
    const entry = await fetchEntry(id);
    if (state.openId === id) {
      renderDetail(entry);
      // Re-trigger fade-in on new content
      detailContent.classList.remove('detail-fade-in');
      void detailContent.offsetWidth; // force reflow
      detailContent.classList.add('detail-fade-in');
    }
  } catch {
    detailContent.innerHTML = '<div class="drawer-status error">Failed to load.</div>';
  }

  // Clean up animation class after it finishes
  setTimeout(() => detailContent.classList.remove('detail-fade-in'), 300);
}

function closeDetail() {
  state.openId = null;
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  overlay.classList.remove('visible');
}

// ── Add modal ──────────────────────────────────────────────────────────────
const addTitleInput = document.getElementById('add-title');
const omdbResults   = document.getElementById('omdb-results');
let searchTimer     = null;

function openAddModal(prefill = '') {
  addModal.hidden = false;
  addTitleInput.value = prefill;
  omdbResults.hidden = true;
  document.getElementById('add-status').textContent = '';
  addTitleInput.focus();
  if (prefill.length >= 2) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => searchTMDb(prefill), 100);
  }
}

function closeAddModal() {
  addModal.hidden = true;
  omdbResults.hidden = true;
}

document.getElementById('add-btn').addEventListener('click', () => openAddModal());
document.getElementById('add-cancel-btn').addEventListener('click', closeAddModal);
addModal.addEventListener('click', (e) => { if (e.target === addModal) closeAddModal(); });

// Debounced TMDB search as user types
let addSearchType = 'movie'; // search both by alternating, or use a toggle
addTitleInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  const q = addTitleInput.value.trim();
  if (q.length < 2) { omdbResults.hidden = true; return; }
  searchTimer = setTimeout(() => searchTMDb(q), 350);
});

async function searchTMDb(query) {
  try {
    // Search both movies and shows, merge results
    const [movieRes, showRes] = await Promise.all([
      fetch(`/api/media/tmdb-search?q=${encodeURIComponent(query)}&type=movie`),
      fetch(`/api/media/tmdb-search?q=${encodeURIComponent(query)}&type=show`),
    ]);
    const movies = movieRes.ok ? await movieRes.json() : [];
    const shows = showRes.ok ? await showRes.json() : [];
    // Interleave: first 5 movies, first 5 shows
    const merged = [...movies.slice(0, 5), ...shows.slice(0, 5)];
    renderSearchResults(merged);
  } catch {
    omdbResults.hidden = true;
  }
}

function renderSearchResults(results) {
  if (!results.length) {
    omdbResults.innerHTML = '<div class="omdb-no-results">No results found</div>';
    omdbResults.hidden = false;
    return;
  }
  omdbResults.innerHTML = results.map((r, i) => `
    <div class="omdb-result-item" data-idx="${i}">
      ${r.poster_url
        ? `<img class="omdb-result-poster" src="${esc(r.poster_url)}" alt="">`
        : `<div class="omdb-result-poster-ph">🎬</div>`}
      <div class="omdb-result-info">
        <div class="omdb-result-title">${esc(r.title)}</div>
        <div class="omdb-result-meta">${esc(r.year)} · ${r.media_type === 'show' ? 'TV Show' : 'Movie'}</div>
      </div>
    </div>
  `).join('');
  omdbResults.hidden = false;
  omdbResults._results = results;
}

omdbResults.addEventListener('click', (e) => {
  const item = e.target.closest('.omdb-result-item');
  if (!item) return;
  const idx = Number(item.dataset.idx);
  const picked = omdbResults._results[idx];
  if (picked) addFromSearch(picked);
});

async function addFromSearch(picked) {
  omdbResults.hidden = true;
  const statusEl = document.getElementById('add-status');
  statusEl.textContent = 'Adding…';
  addTitleInput.value = picked.title;

  try {
    const createRes = await fetch('/api/media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title:         picked.title,
        media_type:    picked.media_type,
        year:          picked.year ? parseInt(picked.year) : null,
        tmdb_id:       picked.tmdb_id,
        poster_path:   picked.poster_path,
        backdrop_path: picked.backdrop_path,
        poster_url:    picked.poster_url,
      }),
    });
    if (!createRes.ok) {
      const err = await createRes.json().catch(() => ({}));
      throw new Error(err.detail || 'Create failed');
    }
    const created = await createRes.json();

    // Enrich (uses imdb_id for exact lookup now)
    statusEl.textContent = 'Fetching metadata…';
    let final = created;
    try {
      const enrichRes = await fetch(`/api/media/${created.id}/enrich`, { method: 'POST' });
      if (enrichRes.ok) final = await enrichRes.json();
    } catch { /* use created as-is */ }

    state.entries.push(final);
    populateGenres(state.entries);
    applyFilters();
    closeAddModal();
    openDetail(final.id);
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

// ── Stats bar ──────────────────────────────────────────────────────────


function renderSectionHeader(entries) {
  const el = document.getElementById('section-header');
  const total = entries.length;
  const movies = entries.filter(e => e.media_type === 'movie').length;
  const shows = entries.filter(e => e.media_type === 'show').length;

  el.innerHTML = `<span class="section-header-title">Collection</span> <span class="section-header-counts">· ${total} entries · ${movies} movies · ${shows} shows</span>`;
}

// ── Genre dropdown ─────────────────────────────────────────────────────────
function populateGenres(entries) {
  const genres = new Set();
  for (const e of entries) {
    if (!e.genres) continue;
    for (const g of e.genres.split(',')) {
      const t = g.trim();
      if (t) genres.add(t);
    }
  }
  const menu = document.getElementById('genre-menu');
  menu.innerHTML = `<div class="custom-select-option selected" data-value="">All</div>` +
    [...genres].sort().map(g =>
      `<div class="custom-select-option" data-value="${esc(g)}">${esc(g)}</div>`
    ).join('');
}

// ── Event listeners ────────────────────────────────────────────────────────
document.querySelectorAll('[data-type]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-type]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.type = btn.dataset.type;
    if (currentListId) exitListMode();
    else { applyFilters(); renderHero(); }
  });
});

document.querySelectorAll('[data-rated]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-rated]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.rated = btn.dataset.rated;
    applyFilters();
  });
});

// Custom dropdown logic is below

searchInput.addEventListener('input', () => {
  state.query = searchInput.value.trim();
  applyFilters();
});

function handleCardClick(e) {
  // Add to list
  const listBtn = e.target.closest('[data-action="add-to-list"]');
  if (listBtn) {
    e.stopPropagation();
    showAddToListPopover(listBtn, Number(listBtn.dataset.id));
    return;
  }

  // Edit button — open detail drawer in edit mode
  const editBtn = e.target.closest('[data-action="open-edit"]');
  if (editBtn) {
    e.stopPropagation();
    const id = Number(editBtn.dataset.id);
    openDetail(id).then(() => {
      // Trigger edit mode after detail loads
      const editTrigger = document.getElementById('edit-btn');
      if (editTrigger) editTrigger.click();
    });
    return;
  }

  // Toggle watchlist
  const wlBtn = e.target.closest('[data-action="toggle-watchlist"]');
  if (wlBtn) {
    e.stopPropagation();
    const id = Number(wlBtn.dataset.id);
    toggleWatchlist(id).then(() => {
      const onWl = watchlistEntryIds.has(id);
      wlBtn.classList.toggle('on-watchlist', onWl);
      wlBtn.title = onWl ? 'Remove from Watchlist' : 'Add to Watchlist';
    });
    return;
  }

  // Toggle watched
  const watchBtn = e.target.closest('[data-action="toggle-watched"]');
  if (watchBtn) {
    e.stopPropagation();
    const id = Number(watchBtn.dataset.id);
    const entry = state.entries.find(e => e.id === id);
    const newStatus = (entry && (entry.status === 'Watched' || entry.status === 'Caught Up')) ? 'Planned' : 'Watched';
    fetch(`/api/media/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    }).then(r => r.ok ? r.json() : null).then(updated => {
      if (updated) {
        const idx = state.entries.findIndex(e => e.id === updated.id);
        if (idx !== -1) state.entries[idx] = updated;
        // Auto-remove from watchlist when marking as Watched
        if (newStatus === 'Watched') removeFromWatchlist(id);
        applyFilters();
      }
    });
    return;
  }

  // Default: open detail drawer
  const card = e.target.closest('.card');
  if (card) openDetail(Number(card.dataset.id));
}

grid.addEventListener('click', handleCardClick);

grid.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') {
    const card = e.target.closest('.card');
    if (card) { e.preventDefault(); openDetail(Number(card.dataset.id)); }
  }
});

overlay.addEventListener('click', closeDetail);

// ── Expandable search ─────────────────────────────────────────────────
const topBar = document.getElementById('top-bar');

// Nav glass effect + hero parallax on scroll
let ticking = false;
window.addEventListener('scroll', () => {
  topBar.classList.toggle('scrolled', window.scrollY > 80);

  if (!ticking) {
    requestAnimationFrame(() => {
      const heroEl = document.getElementById('hero-carousel');
      if (heroEl && window.scrollY < heroEl.offsetHeight) {
        const activeBg = heroEl.querySelector('.hero-slide.active .hero-slide-bg');
        if (activeBg) activeBg.style.transform = `translateY(${window.scrollY * 0.3}px) scale(1)`;
      }
      ticking = false;
    });
    ticking = true;
  }
});

document.getElementById('search-open-btn').addEventListener('click', () => {
  topBar.classList.add('search-open');
  searchInput.focus();
});
document.getElementById('search-close-btn').addEventListener('click', () => {
  topBar.classList.remove('search-open');
  searchInput.value = '';
  state.query = '';
  applyFilters();
});
searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    topBar.classList.remove('search-open');
    searchInput.value = '';
    state.query = '';
    applyFilters();
  }
});

// ── Custom dropdown system ────────────────────────────────────────────
const isMobile = () => window.innerWidth <= 768;

function closeMobileSheet() {
  document.querySelectorAll('.mobile-sheet-backdrop, .mobile-sheet').forEach(el => el.remove());
}

function openMobileSheet(menu, trigger, el, onChange) {
  closeMobileSheet();

  const backdrop = document.createElement('div');
  backdrop.className = 'mobile-sheet-backdrop';
  document.body.appendChild(backdrop);

  const sheet = document.createElement('div');
  sheet.className = 'mobile-sheet';
  sheet.innerHTML = menu.innerHTML;
  document.body.appendChild(sheet);

  backdrop.addEventListener('click', closeMobileSheet);

  sheet.addEventListener('click', (e) => {
    const opt = e.target.closest('.custom-select-option');
    if (!opt) return;
    const value = opt.dataset.value;
    const label = opt.textContent;

    menu.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
    const original = menu.querySelector(`[data-value="${value}"]`);
    if (original) original.classList.add('selected');

    const isDefault = value === '';
    trigger.textContent = isDefault ? trigger.dataset.label : label;
    trigger.classList.toggle('active-filter', !isDefault);

    closeMobileSheet();
    el.classList.remove('open');
    onChange(value);
  });
}

function initCustomSelect(el, onChange) {
  const trigger = el.querySelector('.custom-select-trigger');
  const menu = el.querySelector('.custom-select-menu');

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();

    if (isMobile()) {
      openMobileSheet(menu, trigger, el, onChange);
      return;
    }

    // Desktop: toggle inline dropdown
    document.querySelectorAll('.custom-select.open').forEach(s => { if (s !== el) s.classList.remove('open'); });
    el.classList.toggle('open');
  });

  menu.addEventListener('click', (e) => {
    const opt = e.target.closest('.custom-select-option');
    if (!opt) return;
    const value = opt.dataset.value;
    const label = opt.textContent;

    menu.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
    opt.classList.add('selected');

    const isDefault = value === '';
    trigger.textContent = isDefault ? trigger.dataset.label : label;
    trigger.classList.toggle('active-filter', !isDefault);

    el.classList.remove('open');
    onChange(value);
  });

  trigger.dataset.label = trigger.textContent;
}

// Close dropdowns and popovers on outside click
document.addEventListener('click', () => {
  document.querySelectorAll('.custom-select.open').forEach(s => s.classList.remove('open'));
  closeMobileSheet();
});

// Init each dropdown
initCustomSelect(statusSelect, (v) => { state.status = v; applyFilters(); });
initCustomSelect(genreSelect, (v) => { state.genre = v; applyFilters(); });
initCustomSelect(rewatchSelect, (v) => { state.rewatch = v; applyFilters(); });
initCustomSelect(sortDropdown, (v) => { state.sort = v; applyFilters(); });

// ── Recommend modal ────────────────────────────────────────────────────
const recommendModal   = document.getElementById('recommend-modal');
const moodInput        = document.getElementById('mood-input');
const recommendResults = document.getElementById('recommend-results');
const recommendStatus  = document.getElementById('recommend-status');
const recommendSubmit  = document.getElementById('recommend-submit');
const presetChips      = document.getElementById('preset-chips');
let recMode = 'rewatch';
let recMedia = ''; // '' | 'movie' | 'show'
let presets = {};

// Load presets from API
async function loadPresets() {
  try {
    const res = await fetch('/api/recommend/presets');
    if (res.ok) presets = await res.json();
  } catch { /* ignore */ }
}

function renderPresetChips() {
  const keys = presets[recMode] || [];
  presetChips.innerHTML = keys.map(k =>
    `<button class="preset-chip" data-preset="${esc(k)}">${esc(k)}</button>`
  ).join('');
}

function openRecommendModal() {
  recommendModal.hidden = false;
  moodInput.value = '';
  recommendResults.hidden = true;
  recommendResults.innerHTML = '';
  recommendStatus.textContent = '';
  recommendSubmit.disabled = false;
  renderPresetChips();
}

function closeRecommendModal() {
  recommendModal.hidden = true;
}

document.getElementById('recommend-btn').addEventListener('click', openRecommendModal);
document.getElementById('recommend-close').addEventListener('click', closeRecommendModal);
recommendModal.addEventListener('click', (e) => { if (e.target === recommendModal) closeRecommendModal(); });

// Mode tabs
document.querySelectorAll('[data-rec-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-rec-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    recMode = btn.dataset.recMode;
    renderPresetChips();
    recommendResults.hidden = true;
    recommendResults.innerHTML = '';
    recommendStatus.textContent = '';
  });
});

// Media filter toggle
document.querySelectorAll('[data-rec-media]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-rec-media]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    recMedia = btn.dataset.recMedia;
  });
});

// Preset chip click → immediately submit
presetChips.addEventListener('click', (e) => {
  const chip = e.target.closest('.preset-chip');
  if (!chip) return;
  submitRecommend(null, chip.dataset.preset);
});

// Freeform submit
recommendSubmit.addEventListener('click', () => {
  const mood = moodInput.value.trim();
  if (!mood) return;
  submitRecommend(mood, null);
});

moodInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const mood = moodInput.value.trim();
    if (mood) submitRecommend(mood, null);
  }
});

async function submitRecommend(mood, preset) {
  recommendSubmit.disabled = true;
  recommendStatus.innerHTML = '<div class="rec-loading">Thinking...</div>';
  recommendResults.hidden = true;
  recommendResults.innerHTML = '';

  const isDiscover = recMode === 'discover';
  const url = isDiscover ? '/api/recommend/discover' : '/api/recommend';
  const body = isDiscover
    ? { mood, preset, media_filter: recMedia || undefined }
    : { mode: recMode, mood, preset, media_filter: recMedia || undefined };

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Request failed');
    }
    const data = await res.json();
    recommendStatus.textContent = '';
    if (isDiscover) {
      renderDiscoverResults(data.recommendations);
    } else {
      renderRecommendations(data.recommendations);
    }
  } catch (err) {
    recommendStatus.textContent = err.message;
  } finally {
    recommendSubmit.disabled = false;
  }
}

function renderRecommendations(recs) {
  if (!recs.length) {
    recommendStatus.textContent = 'No recommendations found.';
    return;
  }
  recommendResults.innerHTML = `<div class="rec-cards">${recs.map(r => `
    <div class="rec-card" data-id="${r.entry_id}">
      ${r.poster_url
        ? `<img class="rec-card-poster" src="${esc(r.poster_url)}" alt="">`
        : `<div class="rec-card-poster-ph">🎬</div>`}
      <div class="rec-card-info">
        <div class="rec-card-title">${esc(r.title)}</div>
        <div class="rec-card-meta">${r.year ?? ''} ${r.genres ? '· ' + esc(r.genres) : ''}</div>
        <p class="rec-card-explanation">${esc(r.explanation)}</p>
      </div>
    </div>
  `).join('')}</div>`;
  recommendResults.hidden = false;
}

function renderDiscoverResults(recs) {
  if (!recs.length) {
    recommendStatus.textContent = 'No recommendations found.';
    return;
  }
  recommendResults.innerHTML = `<div class="rec-cards">${recs.map((r, i) => `
    <div class="rec-card discover-card" data-idx="${i}">
      <div class="rec-card-poster-ph" data-discover-poster="${i}">🎬</div>
      <div class="rec-card-info">
        <div class="rec-card-title">${esc(r.title)}</div>
        <div class="rec-card-meta">${r.year ?? ''} · ${r.media_type === 'show' ? 'TV Show' : 'Movie'}</div>
        <p class="rec-card-explanation">${esc(r.explanation)}</p>
        <button class="rec-card-add" data-title="${esc(r.title)}" data-year="${r.year ?? ''}" data-type="${esc(r.media_type)}">+ Add to Catalog</button>
      </div>
    </div>
  `).join('')}</div>`;
  recommendResults.hidden = false;

  // Auto-fetch posters from OMDb
  recs.forEach((r, i) => {
    fetchDiscoverPoster(r.title, i);
  });
}

async function fetchDiscoverPoster(title, idx) {
  try {
    const res = await fetch(`/api/media/omdb-search?q=${encodeURIComponent(title)}`);
    if (!res.ok) return;
    const results = await res.json();
    if (!results.length || !results[0].poster_url) return;
    const ph = recommendResults.querySelector(`[data-discover-poster="${idx}"]`);
    if (ph) {
      const img = document.createElement('img');
      img.className = 'rec-card-poster';
      img.src = results[0].poster_url;
      ph.replaceWith(img);
    }
  } catch { /* ignore */ }
}

// Click handlers for rec cards
recommendResults.addEventListener('click', async (e) => {
  // Handle "Add to Catalog" button on discover cards
  const addBtn = e.target.closest('.rec-card-add');
  if (addBtn && !addBtn.disabled && !addBtn.classList.contains('added')) {
    addBtn.disabled = true;
    addBtn.textContent = 'Adding...';
    try {
      const createRes = await fetch('/api/media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: addBtn.dataset.title,
          media_type: addBtn.dataset.type,
        }),
      });
      if (!createRes.ok) throw new Error('Create failed');
      const created = await createRes.json();

      // Enrich
      try {
        const enrichRes = await fetch(`/api/media/${created.id}/enrich`, { method: 'POST' });
        if (enrichRes.ok) {
          const enriched = await enrichRes.json();
          state.entries.push(enriched);

          // Update the card with poster
          const card = addBtn.closest('.rec-card');
          const ph = card.querySelector('.rec-card-poster-ph');
          if (ph && enriched.poster_url) {
            const img = document.createElement('img');
            img.className = 'rec-card-poster';
            img.src = enriched.poster_url;
            ph.replaceWith(img);
          }
          addBtn.dataset.id = enriched.id;
        } else {
          state.entries.push(created);
          addBtn.dataset.id = created.id;
        }
      } catch {
        state.entries.push(created);
        addBtn.dataset.id = created.id;
      }

      populateGenres(state.entries);
      applyFilters();
      addBtn.textContent = 'Added ✓';
      addBtn.classList.add('added');
      addBtn.disabled = false;
    } catch {
      addBtn.textContent = 'Failed';
      addBtn.disabled = false;
    }
    return;
  }

  // Handle clicking an "Added" button → open detail
  if (addBtn && addBtn.classList.contains('added') && addBtn.dataset.id) {
    closeRecommendModal();
    openDetail(Number(addBtn.dataset.id));
    return;
  }

  // Handle clicking a regular rec card → open detail
  const card = e.target.closest('.rec-card');
  if (card && card.dataset.id) {
    closeRecommendModal();
    openDetail(Number(card.dataset.id));
  }
});

// ── Hero carousel ──────────────────────────────────────────────────────
const heroSlides = document.getElementById('hero-slides');
const heroDots   = document.getElementById('hero-dots');
let heroEntries  = [];
let heroIndex    = 0;
let heroTimer    = null;
const TMDB_IMG   = 'https://image.tmdb.org/t/p';

function pickHeroEntries() {
  // Filter to eligible entries with backdrop_path, respect current type filter
  let pool = state.entries.filter(e => e.backdrop_path && e.hero_eligible !== false);
  if (state.type) pool = pool.filter(e => e.media_type === state.type);
  // Shuffle and pick 4
  const shuffled = pool.sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 9);
}

function getScore(e) {
  return e.rating;
}

function buildHeroSlide(entry) {
  const score = getScore(entry);
  const posterUrl = entry.poster_path ? `${TMDB_IMG}/w500${entry.poster_path}` : entry.poster_url;
  const backdropUrl = `${TMDB_IMG}/original${entry.backdrop_path}`;
  const type = entry.media_type === 'show' ? 'TV Show' : 'Movie';

  const metaParts = [entry.year ?? ''];
  metaParts.push(type);
  if (score != null) metaParts.push(`<span class="hero-score">${score}/10</span>`);

  return `
    <div class="hero-slide" data-id="${entry.id}">
      <div class="hero-slide-bg" style="background-image:url('${esc(backdropUrl)}')"></div>
      <div class="hero-slide-gradient"></div>
      <div class="hero-slide-content">
        <div class="hero-spotlight-label">Spotlight</div>
        <h2 class="hero-title">${esc(entry.title)}</h2>
        <div class="hero-meta">${metaParts.join('<span class="hero-sep"> · </span>')}</div>
        <div class="hero-buttons">
          <button class="hero-btn-primary" data-hero-detail="${entry.id}">View Details</button>
          ${entry.status === 'Planned' ? `<button class="hero-btn-ghost" data-hero-watched="${entry.id}">Mark Watched</button>` : ''}
        </div>
      </div>
      ${posterUrl ? `<img class="hero-poster" src="${esc(posterUrl)}" alt="" data-hero-detail="${entry.id}">` : ''}
    </div>
  `;
}

function renderHero() {
  heroEntries = pickHeroEntries();
  if (!heroEntries.length) {
    heroSlides.innerHTML = '';
    heroDots.innerHTML = '';
    return;
  }

  heroSlides.innerHTML = heroEntries.map(e => buildHeroSlide(e)).join('');
  heroDots.innerHTML = heroEntries.map((_, i) =>
    `<button class="hero-dot${i === 0 ? ' active' : ''}" data-hero-idx="${i}"></button>`
  ).join('');

  heroIndex = 0;
  heroSlides.children[0]?.classList.add('active');
  startHeroTimer();
}

function goToHeroSlide(idx) {
  if (idx === heroIndex || idx < 0 || idx >= heroEntries.length) return;
  const slides = heroSlides.querySelectorAll('.hero-slide');
  const dots = heroDots.querySelectorAll('.hero-dot');

  slides[heroIndex]?.classList.remove('active');
  dots[heroIndex]?.classList.remove('active');

  heroIndex = idx;
  slides[heroIndex]?.classList.add('active');
  dots[heroIndex]?.classList.add('active');

  startHeroTimer();
}

function startHeroTimer() {
  clearInterval(heroTimer);
  heroTimer = setInterval(() => {
    const next = (heroIndex + 1) % heroEntries.length;
    goToHeroSlide(next);
  }, 5500);
}

// Dot clicks
heroDots.addEventListener('click', (e) => {
  const dot = e.target.closest('.hero-dot');
  if (dot) goToHeroSlide(Number(dot.dataset.heroIdx));
});

// Hero button clicks
heroSlides.addEventListener('click', (e) => {
  const detailBtn = e.target.closest('[data-hero-detail]');
  if (detailBtn) {
    openDetail(Number(detailBtn.dataset.heroDetail));
    return;
  }
  const watchedBtn = e.target.closest('[data-hero-watched]');
  if (watchedBtn) {
    const id = Number(watchedBtn.dataset.heroWatched);
    fetch(`/api/media/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'Watched' }),
    }).then(res => {
      if (res.ok) return res.json();
    }).then(updated => {
      if (updated) {
        const idx = state.entries.findIndex(e => e.id === updated.id);
        if (idx !== -1) state.entries[idx] = updated;
        applyFilters();
        openDetail(updated.id);
      }
    });
  }
});

// ── Keyboard shortcuts ─────────────────────────────────────────────────
function getVisibleCardIds() {
  return [...grid.querySelectorAll('.card')].map(c => Number(c.dataset.id));
}

document.addEventListener('keydown', (e) => {
  // Don't intercept when typing in inputs
  const tag = e.target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  // Esc — close topmost open thing
  if (e.key === 'Escape') {
    if (!recommendModal.hidden) { closeRecommendModal(); return; }
    if (!addModal.hidden) { closeAddModal(); return; }
    if (state.openId != null) { closeDetail(); return; }
  }

  // Left/Right arrows — navigate entries in drawer
  if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && state.openId != null) {
    const ids = getVisibleCardIds();
    const idx = ids.indexOf(state.openId);
    if (idx === -1) return;
    const next = e.key === 'ArrowRight' ? idx + 1 : idx - 1;
    if (next >= 0 && next < ids.length) {
      e.preventDefault();
      openDetail(ids[next]);
    }
  }

  // / — open search
  if (e.key === '/' && state.openId == null) {
    e.preventDefault();
    topBar.classList.add('search-open');
    searchInput.focus();
  }
});

// ── Lists ──────────────────────────────────────────────────────────────────
const listsPanel = document.getElementById('lists-panel');
const listsOverlay = document.getElementById('lists-overlay');
const listsPanelContent = document.getElementById('lists-panel-content');
const listViewHeader = document.getElementById('list-view-header');
let allLists = [];
let currentListId = null;

function openListsPanel() {
  listsPanel.classList.add('open');
  listsOverlay.classList.add('visible');
  loadLists();
}

function closeListsPanel() {
  listsPanel.classList.remove('open');
  listsOverlay.classList.remove('visible');
}

document.getElementById('lists-open-btn').addEventListener('click', openListsPanel);
listsOverlay.addEventListener('click', closeListsPanel);

async function loadLists() {
  const res = await fetch('/api/lists');
  if (!res.ok) return;
  allLists = await res.json();
  renderListsPanel();
}

function renderListsPanel() {
  if (!allLists.length) {
    listsPanelContent.innerHTML = `
      <div class="lists-empty">
        <div class="lists-empty-icon">📑</div>
        <div class="lists-empty-text">No lists yet</div>
        <div class="lists-empty-sub">Organize your collection into custom lists</div>
        <button class="btn-primary" onclick="openCreateListModal()">+ Create your first list</button>
      </div>`;
    return;
  }

  listsPanelContent.innerHTML = allLists.map(l => {
    const mosaic = [0,1,2,3].map(i => {
      const p = l.poster_paths[i];
      return p ? `<img src="https://image.tmdb.org/t/p/w92${esc(p)}" alt="">` : `<div class="list-card-mosaic-empty"></div>`;
    }).join('');
    return `
    <div class="list-card" data-list-id="${l.id}">
      <div class="list-card-mosaic">${mosaic}</div>
      <div class="list-card-info">
        <div class="list-card-name">${esc(l.name)}</div>
        <div class="list-card-count">${l.entry_count} entries</div>
      </div>
    </div>`;
  }).join('');
}

listsPanelContent.addEventListener('click', (e) => {
  const card = e.target.closest('.list-card');
  if (card) {
    closeListsPanel();
    openListView(Number(card.dataset.listId));
  }
});

// List view
const heroEl = document.getElementById('hero-carousel');
const filterBarEl = document.querySelector('.filter-bar');
const sectionHeaderEl = document.getElementById('section-header');

function enterListMode() {
  heroEl.style.display = 'none';
  filterBarEl.style.display = 'none';
  sectionHeaderEl.style.display = 'none';
  grid.style.display = '';
  listViewHeader.hidden = false;
}

function exitListMode() {
  currentListId = null;
  listViewHeader.hidden = true;
  const descEl = document.getElementById('list-view-desc');
  if (descEl) descEl.hidden = true;
  const hintEl = document.getElementById('list-reorder-hint');
  if (hintEl) hintEl.hidden = true;
  heroEl.style.display = '';
  filterBarEl.style.display = '';
  sectionHeaderEl.style.display = '';
  emptyState.innerHTML = 'No results.';
  emptyState.hidden = true;
  applyFilters();
}

async function openListView(listId) {
  if (inWatchlistMode) exitWatchlistMode();
  if (inDashboardMode) exitDashboardMode();
  currentListId = listId;
  const res = await fetch(`/api/lists/${listId}`);
  if (!res.ok) return;
  const list = await res.json();

  enterListMode();
  history.pushState({ view: 'list', listId }, '');

  document.getElementById('list-view-name').textContent = list.name;
  document.getElementById('list-view-count').textContent = `· ${list.entries.length} entries`;

  // Description
  let descEl = document.getElementById('list-view-desc');
  if (!descEl) {
    descEl = document.createElement('div');
    descEl.id = 'list-view-desc';
    descEl.className = 'list-view-desc';
    grid.parentElement.insertBefore(descEl, grid);
  }
  descEl.textContent = list.description || '';
  descEl.hidden = !list.description;

  // Reorder hint
  let hintEl = document.getElementById('list-reorder-hint');
  if (!hintEl) {
    hintEl = document.createElement('div');
    hintEl.id = 'list-reorder-hint';
    hintEl.className = 'list-reorder-hint';
    hintEl.textContent = 'Drag to reorder';
    grid.parentElement.insertBefore(hintEl, grid);
  }

  const entries = list.entries.map(le => le.entry);
  if (!entries.length) {
    grid.innerHTML = '';
    hintEl.hidden = true;
    emptyState.innerHTML = `
      <div class="lists-empty">
        <div class="lists-empty-icon">📑</div>
        <div class="lists-empty-text">This list is empty</div>
        <div class="lists-empty-sub">Add entries from your collection</div>
      </div>`;
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
    hintEl.hidden = false;
    grid.innerHTML = entries.map(e => buildCardHtml(e, { visible: true })).join('');
    enableDragReorder(grid, (newOrder) => {
      fetch(`/api/lists/${listId}/entries/reorder`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: newOrder }),
      });
    });
  }
}

document.getElementById('list-back-btn').addEventListener('click', exitListMode);

// Also exit list mode when clicking nav logo or type filters
document.querySelector('.nav-logo').addEventListener('click', () => {
  if (currentListId) exitListMode();
  if (inWatchlistMode) exitWatchlistMode();
  if (inDashboardMode) exitDashboardMode();
});

document.getElementById('list-delete-btn').addEventListener('click', async () => {
  if (!currentListId) return;
  const name = document.getElementById('list-view-name').textContent;
  if (!confirm(`Delete list "${name}"?`)) return;
  await fetch(`/api/lists/${currentListId}`, { method: 'DELETE' });
  exitListMode();
});

document.getElementById('list-edit-btn').addEventListener('click', () => {
  if (!currentListId) return;
  const currentName = document.getElementById('list-view-name').textContent;
  const descEl = document.getElementById('list-view-desc');
  const currentDesc = descEl ? descEl.textContent : '';

  // Show inline edit modal
  const modal = document.createElement('div');
  modal.id = 'list-edit-modal';
  modal.className = 'list-edit-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-title">Edit List</div>
      <div class="form-field">
        <label>Name</label>
        <input type="text" id="list-edit-name" value="${esc(currentName)}">
      </div>
      <div class="form-field">
        <label>Description</label>
        <textarea id="list-edit-desc">${esc(currentDesc)}</textarea>
      </div>
      <div class="modal-actions">
        <button class="btn-primary" id="list-edit-save">Save</button>
        <button class="btn-ghost" id="list-edit-cancel">Cancel</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  document.getElementById('list-edit-name').focus();

  const close = () => modal.remove();
  document.getElementById('list-edit-cancel').addEventListener('click', close);
  modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

  document.getElementById('list-edit-save').addEventListener('click', async () => {
    const name = document.getElementById('list-edit-name').value.trim();
    if (!name) return;
    const description = document.getElementById('list-edit-desc').value.trim() || null;
    const res = await fetch(`/api/lists/${currentListId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    if (res.ok) {
      document.getElementById('list-view-name').textContent = name;
      if (descEl) {
        descEl.textContent = description || '';
        descEl.hidden = !description;
      }
      close();
    }
  });
});

// Create list modal
function openCreateListModal() {
  document.getElementById('create-list-modal').hidden = false;
  document.getElementById('new-list-name').value = '';
  document.getElementById('new-list-desc').value = '';
  document.getElementById('new-list-name').focus();
}

function closeCreateListModal() {
  document.getElementById('create-list-modal').hidden = true;
}

document.getElementById('create-list-btn').addEventListener('click', openCreateListModal);
document.getElementById('create-list-cancel').addEventListener('click', closeCreateListModal);

document.getElementById('create-list-submit').addEventListener('click', async () => {
  const name = document.getElementById('new-list-name').value.trim();
  if (!name) return;
  const desc = document.getElementById('new-list-desc').value.trim() || null;
  const res = await fetch('/api/lists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: desc }),
  });
  if (res.ok) {
    closeCreateListModal();
    loadLists();
  }
});

document.getElementById('new-list-name').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('create-list-submit').click();
});

document.getElementById('create-list-modal').addEventListener('click', (e) => {
  if (e.target.id === 'create-list-modal') closeCreateListModal();
});

// Add to list — from card quick-action
const BOOKMARK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>';

// Inject bookmark button into buildCardHtml — patch it
const _origBuildCardHtml = buildCardHtml;

// We need to add the add-to-list button. Let me just update the actions in buildCardHtml.
// Actually, buildCardHtml is already defined above. Let me add the bookmark via a post-render approach.

async function showAddToListPopover(btn, entryId) {
  // Load lists if needed
  if (!allLists.length) {
    const res = await fetch('/api/lists');
    if (res.ok) allLists = await res.json();
  }

  // Check which lists this entry is in
  const memberRes = await fetch(`/api/lists/for-entry/${entryId}`);
  const memberships = memberRes.ok ? await memberRes.json() : [];
  const memberListIds = new Set(memberships.map(m => m.list_id));

  // Build popover
  let popover = btn.querySelector('.add-to-list-popover');
  if (!popover) {
    popover = document.createElement('div');
    popover.className = 'add-to-list-popover';
    btn.appendChild(popover);
  }

  popover.innerHTML = allLists.map(l => `
    <label class="atl-row">
      <input type="checkbox" data-list-id="${l.id}" data-entry-id="${entryId}" ${memberListIds.has(l.id) ? 'checked' : ''}>
      ${esc(l.name)}
    </label>
  `).join('') + `<div class="atl-row atl-new" data-action="create-and-add" data-entry-id="${entryId}">+ New List</div>`;

  popover.classList.toggle('open');

  // Handle checkbox changes
  popover.addEventListener('change', async (e) => {
    const cb = e.target;
    if (!cb.dataset.listId) return;
    const listId = Number(cb.dataset.listId);
    const eId = Number(cb.dataset.entryId);
    if (cb.checked) {
      await fetch(`/api/lists/${listId}/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_id: eId }),
      });
    } else {
      await fetch(`/api/lists/${listId}/entries/${eId}`, { method: 'DELETE' });
    }
  });

  // Handle "New List" click
  popover.addEventListener('click', (e) => {
    const newBtn = e.target.closest('[data-action="create-and-add"]');
    if (newBtn) {
      popover.classList.remove('open');
      openCreateListModal();
    }
  });
}

// ── Watchlist ─────────────────────────────────────────────────────────────
const watchlistViewHeader = document.getElementById('watchlist-view-header');
let watchlistEntryIds = new Set();
let inWatchlistMode = false;

async function loadWatchlistIds() {
  const res = await fetch('/api/watchlist');
  if (!res.ok) return;
  const items = await res.json();
  watchlistEntryIds = new Set(items.map(i => i.entry_id));
}

function enterWatchlistMode() {
  inWatchlistMode = true;
  heroEl.style.display = 'none';
  filterBarEl.style.display = 'none';
  sectionHeaderEl.style.display = 'none';
  grid.style.display = '';
  watchlistViewHeader.hidden = false;
}

function exitWatchlistMode() {
  inWatchlistMode = false;
  watchlistViewHeader.hidden = true;
  const wlList = document.getElementById('watchlist-list');
  if (wlList) wlList.hidden = true;
  grid.style.display = '';
  heroEl.style.display = '';
  filterBarEl.style.display = '';
  sectionHeaderEl.style.display = '';
  emptyState.innerHTML = 'No results.';
  emptyState.hidden = true;
  applyFilters();
}

async function openWatchlistView() {
  if (currentListId) exitListMode();
  if (inDashboardMode) exitDashboardMode();
  const res = await fetch('/api/watchlist');
  if (!res.ok) return;
  const items = await res.json();
  watchlistEntryIds = new Set(items.map(i => i.entry_id));

  enterWatchlistMode();
  history.pushState({ view: 'watchlist' }, '');
  document.getElementById('watchlist-view-count').textContent = `\u00b7 ${items.length} entries`;

  const entries = items.map(i => i.entry);
  if (!entries.length) {
    grid.innerHTML = '';
    emptyState.innerHTML = `
      <div class="lists-empty">
        <div class="lists-empty-icon">\u23f0</div>
        <div class="lists-empty-text">Watchlist is empty</div>
        <div class="lists-empty-sub">Add movies and shows you want to watch next</div>
      </div>`;
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
    grid.style.display = 'none';
    const wlContainer = document.getElementById('watchlist-list') || (() => {
      const el = document.createElement('div');
      el.id = 'watchlist-list';
      el.className = 'wl-container';
      grid.parentElement.insertBefore(el, grid);
      return el;
    })();
    wlContainer.hidden = false;

    const top = entries[0];
    const topPoster = top.poster_path ? `https://image.tmdb.org/t/p/w200${top.poster_path}` : top.poster_url;
    const topType = top.media_type === 'show' ? 'TV Show' : 'Movie';

    let html = `
      <div class="wl-featured" data-id="${top.id}">
        <div class="wl-featured-poster">${topPoster ? `<img src="${esc(topPoster)}" alt="">` : '<div class="wl-featured-ph">🎬</div>'}</div>
        <div class="wl-featured-info">
          <div class="wl-featured-label">Watch Next</div>
          <div class="wl-featured-title">${esc(top.title)}</div>
          <div class="wl-featured-meta">${top.year ?? ''} · ${topType}</div>
        </div>
      </div>
      <div class="wl-rows" id="wl-rows">`;

    entries.slice(1).forEach((e, i) => {
      const poster = e.poster_path ? `https://image.tmdb.org/t/p/w92${e.poster_path}` : e.poster_url;
      const type = e.media_type === 'show' ? 'TV Show' : 'Movie';
      html += `
        <div class="wl-row" data-id="${e.id}" draggable="true">
          <span class="wl-row-num">${i + 2}</span>
          <div class="wl-row-poster">${poster ? `<img src="${esc(poster)}" alt="">` : '<span>🎬</span>'}</div>
          <div class="wl-row-info">
            <div class="wl-row-title">${esc(e.title)}</div>
            <div class="wl-row-meta">${e.year ?? ''} · ${type}</div>
          </div>
          <span class="wl-row-handle">⋮⋮</span>
        </div>`;
    });
    html += '</div>';
    wlContainer.innerHTML = html;

    // Click to open detail
    wlContainer.querySelector('.wl-featured')?.addEventListener('click', () => openDetail(top.id));
    wlContainer.querySelectorAll('.wl-row').forEach(row => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('.wl-row-handle')) return;
        openDetail(Number(row.dataset.id));
      });
    });

    // Drag reorder for rows
    const rowsContainer = document.getElementById('wl-rows');
    if (rowsContainer) {
      let dragRow = null;
      rowsContainer.querySelectorAll('.wl-row').forEach(row => {
        row.addEventListener('dragstart', (e) => {
          dragRow = row;
          row.classList.add('dragging');
          e.dataTransfer.effectAllowed = 'move';
        });
        row.addEventListener('dragend', () => {
          row.classList.remove('dragging');
          rowsContainer.querySelectorAll('.wl-row').forEach(r => r.classList.remove('drag-over'));
          dragRow = null;
        });
        row.addEventListener('dragover', (e) => {
          e.preventDefault();
          if (row !== dragRow) row.classList.add('drag-over');
        });
        row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
        row.addEventListener('drop', (e) => {
          e.preventDefault();
          row.classList.remove('drag-over');
          if (dragRow && dragRow !== row) {
            const allRows = [...rowsContainer.querySelectorAll('.wl-row')];
            const from = allRows.indexOf(dragRow);
            const to = allRows.indexOf(row);
            if (from < to) row.after(dragRow); else row.before(dragRow);
            // Update numbers and save
            const featured = wlContainer.querySelector('.wl-featured');
            const reordered = [
              { entry_id: Number(featured.dataset.id), priority: 0 },
              ...[...rowsContainer.querySelectorAll('.wl-row')].map((r, i) => {
                r.querySelector('.wl-row-num').textContent = i + 2;
                return { entry_id: Number(r.dataset.id), priority: i + 1 };
              }),
            ];
            fetch('/api/watchlist/reorder', {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ items: reordered }),
            });
          }
        });
      });
    }
  }
}

document.getElementById('watchlist-btn').addEventListener('click', openWatchlistView);
document.getElementById('watchlist-back-btn').addEventListener('click', exitWatchlistMode);

async function toggleWatchlist(entryId) {
  if (watchlistEntryIds.has(entryId)) {
    const res = await fetch(`/api/watchlist/${entryId}`, { method: 'DELETE' });
    if (res.ok) {
      watchlistEntryIds.delete(entryId);
      if (inWatchlistMode) openWatchlistView();
    }
    return !res.ok;
  } else {
    const res = await fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId }),
    });
    if (res.ok) {
      watchlistEntryIds.add(entryId);
    }
    return res.ok;
  }
}

async function removeFromWatchlist(entryId) {
  if (watchlistEntryIds.has(entryId)) {
    await fetch(`/api/watchlist/${entryId}`, { method: 'DELETE' });
    watchlistEntryIds.delete(entryId);
  }
}

// ── Drag-to-reorder ───────────────────────────────────────────────────────
let dragSrcEl = null;

function enableDragReorder(container, onReorder) {
  const cards = container.querySelectorAll('.card');
  cards.forEach(card => {
    card.setAttribute('draggable', 'true');

    card.addEventListener('dragstart', (e) => {
      dragSrcEl = card;
      card.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', card.dataset.id);
    });

    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      container.querySelectorAll('.card').forEach(c => c.classList.remove('drag-over'));
      dragSrcEl = null;
    });

    card.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (card !== dragSrcEl) {
        card.classList.add('drag-over');
      }
    });

    card.addEventListener('dragleave', () => {
      card.classList.remove('drag-over');
    });

    card.addEventListener('drop', (e) => {
      e.preventDefault();
      card.classList.remove('drag-over');
      if (dragSrcEl && dragSrcEl !== card) {
        // Determine position: insert before or after based on position
        const allCards = [...container.querySelectorAll('.card')];
        const fromIdx = allCards.indexOf(dragSrcEl);
        const toIdx = allCards.indexOf(card);
        if (fromIdx < toIdx) {
          card.after(dragSrcEl);
        } else {
          card.before(dragSrcEl);
        }
        // Collect new order
        const newOrder = [...container.querySelectorAll('.card')].map((c, i) => ({
          entry_id: Number(c.dataset.id),
          position: i,
        }));
        onReorder(newOrder);
      }
    });
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────
const dashboardViewHeader = document.getElementById('dashboard-view-header');
const dashboardContent = document.getElementById('dashboard-content');
let inDashboardMode = false;

function enterDashboardMode() {
  inDashboardMode = true;
  heroEl.style.display = 'none';
  filterBarEl.style.display = 'none';
  sectionHeaderEl.style.display = 'none';
  grid.style.display = 'none';
  emptyState.hidden = true;
  dashboardViewHeader.hidden = false;
  dashboardContent.hidden = false;
}

function exitDashboardMode() {
  inDashboardMode = false;
  dashboardViewHeader.hidden = true;
  dashboardContent.hidden = true;
  grid.style.display = '';
  heroEl.style.display = '';
  filterBarEl.style.display = '';
  sectionHeaderEl.style.display = '';
  applyFilters();
}

let _topRatedRank = 0;
function buildTopRatedHtml(e) {
  _topRatedRank++;
  const posterUrl = e.poster_path ? `https://image.tmdb.org/t/p/w92${e.poster_path}` : '';
  const img = posterUrl ? `<img src="${esc(posterUrl)}" alt="">` : '<div class="dash-top-ph">🎬</div>';
  return `
    <div class="dash-top-entry" data-id="${e.id}">
      <span class="dash-top-rank">${_topRatedRank}</span>
      ${img}
      <div class="dash-top-info">
        <div class="dash-top-title">${esc(e.title)}</div>
        <div class="dash-top-score">${e.rating}/10</div>
      </div>
    </div>`;
}

function renderDashboard() {
  const entries = state.entries;
  const scored = entries.filter(e => e.rating != null);
  const movies = entries.filter(e => e.media_type === 'movie');
  const shows = entries.filter(e => e.media_type === 'show');

  // Status breakdown
  const statusCounts = {};
  entries.forEach(e => { statusCounts[e.status] = (statusCounts[e.status] || 0) + 1; });

  // Genre breakdown
  const genreCounts = {};
  entries.forEach(e => {
    if (e.genres) e.genres.split(',').map(g => g.trim()).forEach(g => {
      genreCounts[g] = (genreCounts[g] || 0) + 1;
    });
  });
  const topGenres = Object.entries(genreCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const maxGenre = topGenres[0]?.[1] || 1;

  // Rating distribution (buckets 1-10)
  const ratingBuckets = Array(10).fill(0);
  scored.forEach(e => {
    const bucket = Math.min(Math.floor(e.rating) - 1, 9);
    if (bucket >= 0) ratingBuckets[bucket]++;
  });
  const maxBucket = Math.max(...ratingBuckets, 1);

  // Top rated
  const topRated = [...scored].sort((a, b) => b.rating - a.rating).slice(0, 5);

  // Vibe tags
  const vibeCounts = {};
  entries.forEach(e => {
    if (e.vibe_tags) e.vibe_tags.split(',').map(t => t.trim()).filter(Boolean).forEach(t => {
      vibeCounts[t] = (vibeCounts[t] || 0) + 1;
    });
  });
  const topVibes = Object.entries(vibeCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxVibe = topVibes[0]?.[1] || 1;

  // Average rating
  const avgRating = scored.length ? (scored.reduce((s, e) => s + e.rating, 0) / scored.length).toFixed(1) : '—';

  // Status pills with colored dots
  const STATUS_COLORS = {
    'Watched': '#4ade80', 'Caught Up': '#4ade80', 'Watching': '#c4785a',
    'Get Back To': '#f97316', 'On Hold': '#f97316', 'Planned': '#504a44', 'Dropped': '#ef4444',
  };
  const statusOrder = ['Watched', 'Caught Up', 'Watching', 'Planned', 'On Hold', 'Get Back To', 'Dropped'];
  const statusPills = statusOrder
    .filter(s => statusCounts[s])
    .map(s => `<span class="dash-status-pill"><span class="dash-status-dot" style="background:${STATUS_COLORS[s] || '#504a44'}"></span>${s}: ${statusCounts[s]}</span>`)
    .join('');

  // Find the mode (tallest bucket) for histogram highlighting
  const modeBucket = ratingBuckets.indexOf(Math.max(...ratingBuckets));

  dashboardContent.innerHTML = `
    <div class="dash-grid">
      <div class="dash-card dash-overview">
        <div class="dash-card-title">Overview</div>
        <div class="dash-stat-row">
          <div class="dash-stat"><div class="dash-stat-value">${entries.length}</div><div class="dash-stat-label">Total</div></div>
          <div class="dash-stat"><div class="dash-stat-value">${movies.length}</div><div class="dash-stat-label">Movies</div></div>
          <div class="dash-stat"><div class="dash-stat-value">${shows.length}</div><div class="dash-stat-label">Shows</div></div>
          <div class="dash-stat"><div class="dash-stat-value">${scored.length}</div><div class="dash-stat-label">Rated</div></div>
          <div class="dash-stat"><div class="dash-stat-value">${avgRating}</div><div class="dash-stat-label">Avg Rating</div></div>
        </div>
        <div class="dash-status-pills">${statusPills}</div>
      </div>

      <div class="dash-card">
        <div class="dash-card-title">Top Genres</div>
        <div class="dash-bars">
          ${topGenres.map(([g, c]) => `
            <div class="dash-bar-row">
              <span class="dash-bar-label">${esc(g)}</span>
              <div class="dash-bar-track"><div class="dash-bar-fill" style="width:${(c / maxGenre * 100).toFixed(0)}%"></div></div>
              <span class="dash-bar-count">${c}</span>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="dash-card">
        <div class="dash-card-title">Rating Distribution</div>
        <div class="dash-histogram">
          ${ratingBuckets.map((c, i) => `
            <div class="dash-hist-col">
              <div class="dash-hist-bar${i === modeBucket && c > 0 ? ' dash-hist-mode' : ''}" style="height:${c ? (c / maxBucket * 100).toFixed(0) : 0}%"></div>
              <div class="dash-hist-label">${i + 1}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="dash-card">
        <div class="dash-card-title">Top Rated</div>
        <div class="dash-top-rated">
          ${topRated.length ? (() => { _topRatedRank = 0; return topRated.map(e => buildTopRatedHtml(e)).join(''); })() : '<div class="dash-empty">No rated entries yet</div>'}
        </div>
      </div>

      ${topVibes.length ? `
      <div class="dash-card">
        <div class="dash-card-title">Vibe Tags</div>
        <div class="dash-bars">
          ${topVibes.map(([t, c]) => `
            <div class="dash-bar-row">
              <span class="dash-bar-label">${esc(t)}</span>
              <div class="dash-bar-track"><div class="dash-bar-fill" style="width:${(c / maxVibe * 100).toFixed(0)}%"></div></div>
              <span class="dash-bar-count">${c}</span>
            </div>
          `).join('')}
        </div>
      </div>` : ''}
    </div>
  `;

  // Click top rated to open detail
  dashboardContent.querySelectorAll('.dash-top-entry').forEach(el => {
    el.addEventListener('click', () => openDetail(Number(el.dataset.id)));
  });
}

function openDashboard() {
  if (currentListId) exitListMode();
  if (inWatchlistMode) exitWatchlistMode();
  enterDashboardMode();
  renderDashboard();
  history.pushState({ view: 'dashboard' }, '');
}

document.getElementById('dashboard-btn').addEventListener('click', openDashboard);
document.getElementById('dashboard-back-btn').addEventListener('click', exitDashboardMode);

// ── Browser history (back swipe / back button) ───────────────────────────
window.addEventListener('popstate', (e) => {
  const view = e.state?.view;
  if (!view || view === 'catalog') {
    if (currentListId) exitListMode();
    if (inWatchlistMode) exitWatchlistMode();
    if (inDashboardMode) exitDashboardMode();
    if (drawer.classList.contains('open')) closeDetail();
  } else if (view === 'list') {
    if (inWatchlistMode) exitWatchlistMode();
    if (inDashboardMode) exitDashboardMode();
  } else if (view === 'watchlist') {
    if (currentListId) exitListMode();
    if (inDashboardMode) exitDashboardMode();
  } else if (view === 'dashboard') {
    if (currentListId) exitListMode();
    if (inWatchlistMode) exitWatchlistMode();
  }
});

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  history.replaceState({ view: 'catalog' }, '');
  try {
    const [entries] = await Promise.all([fetchAllMedia(), loadPresets(), loadWatchlistIds()]);
    state.entries = entries;
    populateGenres(entries);
    renderSectionHeader(entries);
    renderCards(entries);
    renderHero();
  } catch {
    emptyState.textContent = 'Failed to load catalog.';
    emptyState.hidden = false;
  }
}

init();
