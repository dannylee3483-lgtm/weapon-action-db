// ─── State ───────────────────────────────────────────────────────
let allWeapons = [];
let filteredWeapons = [];
let selectedTags = new Set();
let combineSet = new Set();
let combineMode = false;
let currentView = 'grid';

const CATEGORY_ICONS = {
  '대검': '⚔️', '카타나': '🗡️', '쌍검': '⚔️', '창': '🔱',
  '도끼': '🪓', '낫': '🌙', '해머': '🔨', '채찍': '〰️',
  '권투': '👊', '활': '🏹', '1H검': '🗡️', '마법': '✨',
  '방패': '🛡️',
};

const STARTUP_LABEL = {
  'very-fast': '⚡ 매우 빠름', 'fast': '⚡ 빠름', 'medium': '⏱ 보통',
  'slow': '🐢 느림', 'very-slow': '🐢 매우 느림'
};
const RANGE_LABEL = {
  'short': '근거리', 'short-medium': '근-중거리', 'medium': '중거리',
  'medium-long': '중-장거리', 'long': '장거리', 'very-long': '매우 긴 사거리'
};
const STAGGER_LABEL = {
  'very-low': '극소', 'low': '낮음', 'medium': '보통',
  'high': '높음', 'very-high': '매우 높음', 'continuous': '지속'
};
const MOTION_LABEL = {
  'slash': '참격', 'thrust': '찌르기', 'overhead': '오버헤드',
  'sweep': '횡격', 'spin': '회전', 'charge': '차지',
  'dodge-cancel': '회피 캔슬', 'parry': '패리', 'counter': '카운터',
  'throw': '투척', 'combo': '콤보', 'leap': '도약',
  'aerial': '공중', 'block-counter': '블록 카운터',
};
const COMBO_ROLE_LABEL = {
  'opener': '오프너', 'extender': '연장기', 'finisher': '피니셔',
  'launcher': '런처', 'ender': '종결기', 'punish': '패니시',
};

const ELEMENT_LABEL = {
  '없음': '無', '불': '🔥 불', '얼음': '❄️ 얼음', '번개': '⚡ 번개',
  '어둠': '🌑 어둠', '신성': '✨ 신성', '독': '☠️ 독', '출혈': '🩸 출혈',
  '중력': '🌀 중력', '비전': '🔮 비전', '바람': '💨 바람',
  '땅': '🪨 땅', '물': '💧 물', '기타': '? 기타',
};

// CSS class name for each element (used by style.css)
const ELEMENT_CSS = {
  '없음': 'el-none', '불': 'el-fire', '얼음': 'el-ice', '번개': 'el-lightning',
  '어둠': 'el-dark', '신성': 'el-holy', '독': 'el-poison', '출혈': 'el-bleed',
  '중력': 'el-gravity', '비전': 'el-arcane', '바람': 'el-wind',
  '땅': 'el-earth', '물': 'el-water', '기타': 'el-other',
};

// ─── 유튜브 유틸 ──────────────────────────────────────────────────
function extractYouTubeId(url) {
  if (!url) return null;
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);
  return m ? m[1] : null;
}

function isYouTubeSearch(url) {
  return url && url.includes('youtube.com/results');
}

function hasMedia(w) {
  const ml = w.mediaLinks;
  if (!ml) return false;
  return !!(ml.youtube || (ml.images && ml.images.length > 0) || ml.wiki || ml.gif);
}

function mediaFlags(w) {
  const ml = w.mediaLinks || {};
  const flags = [];
  if (ml.youtube)                             flags.push({ icon: '🎥', label: '유튜브', type: 'yt' });
  if (ml.wiki)                                flags.push({ icon: '📖', label: '위키', type: 'wiki' });
  if (ml.images && ml.images.length > 0)      flags.push({ icon: '🖼️', label: `이미지 ${ml.images.length}`, type: 'img' });
  if (ml.gif)                                 flags.push({ icon: '🎞️', label: 'GIF', type: 'gif' });
  return flags;
}

// ─── Init ─────────────────────────────────────────────────────────
async function init() {
  try {
    const res = await fetch('data/weapons.json');
    const data = await res.json();
    allWeapons = data.weapons;
    filteredWeapons = [...allWeapons];
    populateFilters();
    populateTagCloud();
    render();
    updateStats();
  } catch (e) {
    console.error('DB 로드 실패:', e);
    document.getElementById('cards').innerHTML =
      `<div class="empty-state"><div class="emoji">⚠️</div><h3>데이터 로드 실패</h3><p>data/weapons.json 파일을 확인하세요</p></div>`;
  }
}

// ─── Filters Population ───────────────────────────────────────────
function populateFilters() {
  const categories = [...new Set(allWeapons.map(w => w.weaponCategory))].sort();
  const games      = [...new Set(allWeapons.map(w => w.game))].sort();
  const motions    = [...new Set(allWeapons.flatMap(w => w.motionType))].sort();
  const elements   = [...new Set(allWeapons.map(w => w.element?.type).filter(Boolean))].sort();
  populateSelect('filter-category', categories, '전체 무기');
  populateSelect('filter-game', games, '전체 게임');
  const motionSel = document.getElementById('filter-motion');
  motionSel.innerHTML = '<option value="">전체 모션</option>';
  motions.forEach(m => { motionSel.innerHTML += `<option value="${m}">${MOTION_LABEL[m] || m}</option>`; });
  const elemSel = document.getElementById('filter-element');
  if (elemSel) {
    elemSel.innerHTML = '<option value="">전체 속성</option>';
    elements.forEach(el => { elemSel.innerHTML += `<option value="${el}">${ELEMENT_LABEL[el] || el}</option>`; });
  }
}

function populateSelect(id, options, placeholder) {
  const el = document.getElementById(id);
  el.innerHTML = `<option value="">${placeholder}</option>`;
  options.forEach(o => { el.innerHTML += `<option value="${o}">${o}</option>`; });
}

function populateTagCloud() {
  const tagCount = {};
  allWeapons.forEach(w => w.tags.forEach(t => { tagCount[t] = (tagCount[t] || 0) + 1; }));
  const topTags = Object.entries(tagCount).sort((a, b) => b[1] - a[1]).slice(0, 24).map(([t]) => t);
  const cloud = document.getElementById('tag-cloud');
  cloud.innerHTML = '';
  topTags.forEach(tag => {
    const btn = document.createElement('button');
    btn.className = 'tag-btn';
    btn.textContent = tag;
    btn.dataset.tag = tag;
    btn.onclick = () => toggleTagFilter(tag);
    cloud.appendChild(btn);
  });
}

// ─── Filter Logic ─────────────────────────────────────────────────
function applyFilters() {
  const search  = document.getElementById('search').value.toLowerCase().trim();
  const category = document.getElementById('filter-category').value;
  const game    = document.getElementById('filter-game').value;
  const motion  = document.getElementById('filter-motion').value;
  const startup = document.getElementById('filter-startup').value;
  const element = document.getElementById('filter-element')?.value || '';
  const mediaOnly = document.getElementById('filter-media')?.checked;

  filteredWeapons = allWeapons.filter(w => {
    if (search) {
      const searchable = [
        w.actionName, w.description, w.game, w.designNotes,
        w.weaponCategory, w.weaponSubtype, w.actionType,
        w.element?.type || '',
        ...(w.tags || []), ...(w.motionType || [])
      ].join(' ').toLowerCase();
      if (!searchable.includes(search)) return false;
    }
    if (category && w.weaponCategory !== category) return false;
    if (game && w.game !== game) return false;
    if (motion && !(w.motionType || []).includes(motion)) return false;
    if (startup && w.mechanics.startupSpeed !== startup) return false;
    if (element && w.element?.type !== element) return false;
    if (mediaOnly && !hasMedia(w)) return false;
    if (selectedTags.size > 0) {
      if (![...selectedTags].every(t => (w.tags || []).includes(t))) return false;
    }
    return true;
  });

  render();
  updateStats();
}

function toggleTagFilter(tag) {
  if (selectedTags.has(tag)) selectedTags.delete(tag);
  else selectedTags.add(tag);
  document.querySelectorAll('.tag-btn').forEach(btn => {
    btn.classList.toggle('active', selectedTags.has(btn.dataset.tag));
  });
  applyFilters();
}

function resetFilters() {
  document.getElementById('search').value = '';
  document.getElementById('filter-category').value = '';
  document.getElementById('filter-game').value = '';
  document.getElementById('filter-motion').value = '';
  document.getElementById('filter-startup').value = '';
  if (document.getElementById('filter-element')) document.getElementById('filter-element').value = '';
  if (document.getElementById('filter-media')) document.getElementById('filter-media').checked = false;
  selectedTags.clear();
  document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
  filteredWeapons = [...allWeapons];
  render();
  updateStats();
}

// ─── Render ───────────────────────────────────────────────────────
function render() {
  const container = document.getElementById('cards');
  container.className = `cards-grid ${currentView === 'list' ? 'list-view' : ''}`;

  if (filteredWeapons.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="emoji">🔍</div>
        <h3>레퍼런스를 찾을 수 없습니다</h3>
        <p>다른 검색어나 필터를 시도해보세요</p>
      </div>`;
    return;
  }

  container.innerHTML = '';
  filteredWeapons.forEach(w => container.appendChild(createCard(w)));
}

function createCard(w) {
  const div = document.createElement('div');
  div.className = `card ${combineSet.has(w.id) ? 'selected' : ''}`;
  div.dataset.category = w.weaponCategory;
  div.dataset.cardId = w.id;

  const icon         = CATEGORY_ICONS[w.weaponCategory] || '⚔️';
  const startupLabel = STARTUP_LABEL[w.mechanics.startupSpeed] || w.mechanics.startupSpeed;
  const rangeLabel   = RANGE_LABEL[w.mechanics.range] || w.mechanics.range;
  const staggerLabel = STAGGER_LABEL[w.mechanics.staggerPower] || w.mechanics.staggerPower;
  const tagsHtml     = (w.tags || []).slice(0, 5).map(t => `<span class="tag">${t}</span>`).join('');
  const elemType     = w.element?.type;
  const elemBadge    = (elemType && elemType !== '없음')
    ? `<span class="element-badge ${ELEMENT_CSS[elemType] || 'el-other'}">${ELEMENT_LABEL[elemType] || elemType}</span>`
    : '';

  // 미디어 배지 행
  const flags    = mediaFlags(w);
  const mediaRow = flags.length > 0
    ? `<div class="card-media-row">
        ${flags.map(f => `<span class="media-badge media-badge--${f.type}">${f.icon} ${f.label}</span>`).join('')}
       </div>`
    : '';

  // 유튜브 썸네일 미리보기 (특정 영상 URL인 경우만)
  const ytId = extractYouTubeId(w.mediaLinks?.youtube);
  const thumbHtml = ytId
    ? `<div class="card-thumb" onclick="event.stopPropagation(); openModal(allWeapons.find(x=>x.id==='${w.id}'))">
        <img src="https://img.youtube.com/vi/${ytId}/mqdefault.jpg"
             alt="thumbnail" loading="lazy"
             onerror="this.parentElement.style.display='none'">
        <div class="card-thumb-play">▶</div>
       </div>`
    : '';

  div.innerHTML = `
    ${combineMode ? '<div class="combine-check">✓</div>' : ''}
    ${thumbHtml}
    <div class="card-header">
      <div class="weapon-icon">${icon}</div>
      <div class="card-title-area">
        <div class="action-name">${w.actionName}</div>
        <div class="game-name">${w.game} · ${w.developer || ''}</div>
      </div>
      <div class="card-badges">
        <span class="category-badge">${w.weaponCategory}</span>
        ${elemBadge}
      </div>
    </div>
    <div class="description">${w.description}</div>
    <div class="card-meta">
      <span class="meta-pill startup">${startupLabel}</span>
      <span class="meta-pill range">${rangeLabel}</span>
      <span class="meta-pill stagger">경직 ${staggerLabel}</span>
    </div>
    <div class="tags-row">${tagsHtml}</div>
    ${mediaRow}`;

  div.onclick = () => {
    if (combineMode) toggleCombineSelect(w.id, div);
    else openModal(w);
  };

  return div;
}

function updateStats() {
  document.getElementById('total-count').textContent = allWeapons.length;
  document.getElementById('filtered-count').textContent = filteredWeapons.length;
  document.getElementById('result-label').textContent = `${filteredWeapons.length}개 레퍼런스`;
}

// ─── View Toggle ──────────────────────────────────────────────────
function setView(mode) {
  currentView = mode;
  document.querySelectorAll('.view-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.view === mode));
  render();
}

// ─── Combine Mode ─────────────────────────────────────────────────
function toggleCombineMode() {
  combineMode = !combineMode;
  document.getElementById('combine-mode-btn').classList.toggle('active', combineMode);
  if (!combineMode) { combineSet.clear(); updateCombineBar(); }
  render();
}

function toggleCombineSelect(id, cardEl) {
  if (combineSet.has(id)) { combineSet.delete(id); cardEl.classList.remove('selected'); }
  else { combineSet.add(id); cardEl.classList.add('selected'); }
  updateCombineBar();
}

function updateCombineBar() {
  const bar  = document.getElementById('combine-bar');
  const list = document.getElementById('combine-selected-list');
  if (combineSet.size === 0) { bar.classList.remove('visible'); return; }
  bar.classList.add('visible');
  list.innerHTML = '';
  combineSet.forEach(id => {
    const w = allWeapons.find(x => x.id === id);
    if (!w) return;
    const chip = document.createElement('div');
    chip.className = 'combine-chip';
    chip.innerHTML = `
      ${CATEGORY_ICONS[w.weaponCategory] || '⚔️'}
      <span>${w.weaponCategory} · ${w.actionName.split('(')[0].trim()}</span>
      <span class="remove-chip" onclick="removeCombine('${id}')">×</span>`;
    list.appendChild(chip);
  });
}

function removeCombine(id) { combineSet.delete(id); updateCombineBar(); render(); }
function clearCombine()    { combineSet.clear();  updateCombineBar(); render(); }

function openCombineResult() {
  if (combineSet.size < 2) { alert('2개 이상 선택해주세요'); return; }
  const selected  = [...combineSet].map(id => allWeapons.find(x => x.id === id));
  const tagSets   = selected.map(w => new Set(w.tags));
  const commonTags = [...tagSets[0]].filter(t => tagSets.every(s => s.has(t)));
  const allProps  = [...new Set(selected.flatMap(w => w.mechanics.specialProperties || []))];
  const allRoles  = [...new Set(selected.flatMap(w => w.mechanics.comboRole || []))];

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-header">
      <div class="modal-icon">⚗️</div>
      <div class="modal-title">
        <h2>조합 분석 결과</h2>
        <div class="subtitle">${selected.length}개 레퍼런스 조합</div>
      </div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body">
      <div class="modal-section">
        <h4>선택된 레퍼런스</h4>
        <div class="combine-result">
          ${selected.map(w => `
            <div class="combine-entry">
              <strong>${CATEGORY_ICONS[w.weaponCategory]} ${w.weaponCategory} — ${w.actionName}</strong>
              <span>${w.game} · ${w.actionType}</span>
            </div>`).join('')}
        </div>
      </div>
      ${commonTags.length > 0 ? `
      <div class="modal-section">
        <h4>공통 특성 (조합의 핵심 아이덴티티)</h4>
        <div class="props-list">
          ${commonTags.map(t => `<span class="prop-tag" style="color:var(--accent)">${t}</span>`).join('')}
        </div>
      </div>` : ''}
      <div class="modal-section">
        <h4>통합 특수 속성</h4>
        <div class="props-list">
          ${allProps.map(p => `<span class="prop-tag">${p}</span>`).join('')}
        </div>
      </div>
      <div class="modal-section">
        <h4>가능한 콤보 역할 범위</h4>
        <div class="props-list">
          ${allRoles.map(r => `<span class="prop-tag" style="color:var(--blue)">${COMBO_ROLE_LABEL[r] || r}</span>`).join('')}
        </div>
      </div>
      <div class="modal-section">
        <h4>설계 제안</h4>
        <div class="design-note">${generateDesignSuggestion(selected)}</div>
      </div>
      <div class="modal-section">
        <h4>수집 명령어 예시</h4>
        <div class="code-block">python collect.py -q "${selected.map(w => w.actionName.split('(')[0].trim()).join(' + ')} 조합 메카닉" -n 3</div>
      </div>
    </div>`;

  document.getElementById('modal').classList.add('visible');
}

function generateDesignSuggestion(weapons) {
  const categories  = [...new Set(weapons.map(w => w.weaponCategory))];
  const hasFast     = weapons.some(w => ['very-fast', 'fast'].includes(w.mechanics.startupSpeed));
  const hasSlow     = weapons.some(w => ['slow', 'very-slow'].includes(w.mechanics.startupSpeed));
  const hasCounter  = weapons.some(w => (w.motionType || []).some(m => ['counter', 'parry'].includes(m)));
  const hasRange    = weapons.some(w => ['long', 'very-long'].includes(w.mechanics.range));
  const hasAoe      = weapons.some(w => (w.mechanics.specialProperties || []).some(p => p.includes('aoe') || p.includes('360')));
  const suggestions = [];
  if (hasFast && hasSlow) suggestions.push('빠른 연속기로 게이지를 쌓은 뒤 느리지만 강한 피니셔로 마무리하는 <strong>2단 리듬 콤보</strong> 설계를 고려하세요.');
  if (hasCounter)          suggestions.push('<strong>카운터-어택 체인</strong>: 패리/카운터 성공 후 조합된 액션이 자동으로 이어지는 입력 버퍼 설계.');
  if (hasRange && categories.length > 1) suggestions.push('원거리로 약화 후 근접으로 마무리하는 <strong>레인지-갭클로즈 루프</strong>.');
  if (hasAoe)              suggestions.push('<strong>군중 제어 + 단일 딜</strong>: 광역으로 모은 뒤 집중 딜링.');
  if (categories.length > 1) suggestions.push(`선택된 무기(${categories.join(', ')})를 통합하는 <strong>폼 체인지 시스템</strong> 또는 트릭 무기 설계.`);
  if (suggestions.length === 0) suggestions.push('핵심 모션을 기반으로 무브셋을 설계해보세요. 수집 기능으로 추가 레퍼런스를 가져올 수 있습니다.');
  return suggestions.join('<br><br>');
}

// ─── Media Section Builder ────────────────────────────────────────
function buildMediaSection(ml) {
  if (!ml) return '';
  const parts = [];

  // YouTube
  if (ml.youtube) {
    const ytId = extractYouTubeId(ml.youtube);
    if (ytId) {
      // 인라인 임베드 플레이어
      parts.push(`
        <div class="media-yt-embed">
          <iframe
            src="https://www.youtube.com/embed/${ytId}?rel=0&modestbranding=1"
            title="YouTube video player"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
            loading="lazy"
          ></iframe>
        </div>`);
    } else if (isYouTubeSearch(ml.youtube)) {
      // 검색 URL
      parts.push(`
        <a class="media-link-btn media-link-btn--yt" href="${ml.youtube}" target="_blank" rel="noopener">
          🎥 유튜브에서 검색
        </a>`);
    }
  }

  // GIF
  if (ml.gif) {
    parts.push(`
      <div class="media-gif-card">
        <img src="${ml.gif}" alt="GIF 레퍼런스" loading="lazy"
             onerror="this.parentElement.innerHTML='<span style=color:var(--text-dim)>GIF 로드 실패</span>'">
      </div>`);
  }

  // 이미지 갤러리
  if (ml.images && ml.images.length > 0) {
    const imgs = ml.images.map(url => `
      <a href="${url}" target="_blank" rel="noopener" class="media-img-item">
        <img src="${url}" alt="레퍼런스 이미지" loading="lazy"
             onerror="this.parentElement.style.display='none'">
      </a>`).join('');
    parts.push(`<div class="media-img-grid">${imgs}</div>`);
  }

  // Wiki
  if (ml.wiki) {
    parts.push(`
      <a class="media-link-btn media-link-btn--wiki" href="${ml.wiki}" target="_blank" rel="noopener">
        📖 위키에서 상세 정보 보기
      </a>`);
  }

  if (parts.length === 0) return '';

  return `
    <div class="modal-section">
      <h4>미디어 레퍼런스</h4>
      <div class="media-section">${parts.join('')}</div>
    </div>`;
}

// ─── Modal ────────────────────────────────────────────────────────
function openModal(w) {
  const icon       = CATEGORY_ICONS[w.weaponCategory] || '⚔️';
  const frame      = w.mechanics.frameApprox || {};
  const props      = w.mechanics.specialProperties || [];
  const applicable = w.applicableWeapons || [];

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-header">
      <div class="modal-icon">${icon}</div>
      <div class="modal-title">
        <h2>${w.actionName}</h2>
        <div class="subtitle">${w.game} · ${w.developer || ''} · ${w.actionType}</div>
      </div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body">

      ${buildMediaSection(w.mediaLinks)}

      <div class="modal-section">
        <h4>설명</h4>
        <p>${w.description}</p>
      </div>

      <div class="modal-section">
        <h4>메카닉 정보</h4>
        <div class="frame-grid">
          <div class="frame-box">
            <div class="label">발동 속도</div>
            <div class="value" style="font-size:12px">${STARTUP_LABEL[w.mechanics.startupSpeed] || w.mechanics.startupSpeed}</div>
          </div>
          <div class="frame-box">
            <div class="label">사정거리</div>
            <div class="value" style="font-size:12px">${RANGE_LABEL[w.mechanics.range] || w.mechanics.range}</div>
          </div>
          <div class="frame-box">
            <div class="label">경직 파워</div>
            <div class="value" style="font-size:12px">${STAGGER_LABEL[w.mechanics.staggerPower] || w.mechanics.staggerPower}</div>
          </div>
        </div>
      </div>

      ${(frame.startup || frame.active || frame.recovery) ? `
      <div class="modal-section">
        <h4>프레임 데이터 (참고치)</h4>
        <div class="frame-grid">
          <div class="frame-box"><div class="label">선입력</div><div class="value">${frame.startup || '-'}</div></div>
          <div class="frame-box"><div class="label">판정</div><div class="value">${frame.active || '-'}</div></div>
          <div class="frame-box"><div class="label">후딜</div><div class="value">${frame.recovery || '-'}</div></div>
        </div>
      </div>` : ''}

      ${props.length > 0 ? `
      <div class="modal-section">
        <h4>특수 속성</h4>
        <div class="props-list">${props.map(p => `<span class="prop-tag">${p}</span>`).join('')}</div>
      </div>` : ''}

      ${w.element && w.element.type ? `
      <div class="modal-section">
        <h4>속성 & 이펙트</h4>
        <div class="element-detail">
          <span class="element-badge ${ELEMENT_CSS[w.element.type] || 'el-other'} el-lg">${ELEMENT_LABEL[w.element.type] || w.element.type}</span>
          ${(w.element.effectColor && w.element.effectColor.length > 0) ? `
          <div class="element-colors">
            ${w.element.effectColor.map(c => `<span class="color-chip" style="background:${c}" title="${c}"></span>`).join('')}
            <span class="color-labels">${w.element.effectColor.join(', ')}</span>
          </div>` : ''}
          ${(w.element.effectStyle && w.element.effectStyle.length > 0) ? `
          <div class="props-list" style="margin-top:6px">
            ${w.element.effectStyle.map(s => `<span class="prop-tag prop-tag--style">${s}</span>`).join('')}
          </div>` : ''}
        </div>
      </div>` : ''}

      <div class="modal-section">
        <h4>콤보 역할</h4>
        <div class="props-list">
          ${(w.mechanics.comboRole || []).map(r => `<span class="prop-tag" style="color:var(--blue)">${COMBO_ROLE_LABEL[r] || r}</span>`).join('')}
        </div>
      </div>

      <div class="modal-section">
        <h4>디자인 노트</h4>
        <div class="design-note">${w.designNotes}</div>
      </div>

      ${applicable.length > 0 ? `
      <div class="modal-section">
        <h4>적용 가능한 무기 유형</h4>
        <div class="applicable-list">
          ${applicable.map(a => `<span class="applicable-tag">${a}</span>`).join('')}
        </div>
      </div>` : ''}

      <div class="modal-section">
        <h4>태그</h4>
        <div class="tags-row">
          ${(w.tags || []).map(t => `<span class="tag" style="cursor:pointer" onclick="filterByTag('${t}')">${t}</span>`).join('')}
        </div>
      </div>

      <div class="modal-section" style="display:flex;gap:10px;align-items:center">
        <div>
          <h4>리소스 비용</h4>
          <p style="margin-top:4px">${w.mechanics.resourceCost || '없음'}</p>
        </div>
        <div style="margin-left:auto;font-size:11px;color:var(--text-dim)">ID: ${w.id} · ${w.addedDate || ''}</div>
      </div>

    </div>`;

  document.getElementById('modal').classList.add('visible');
}

function closeModal() {
  document.getElementById('modal').classList.remove('visible');
}

function filterByTag(tag) {
  closeModal();
  selectedTags.add(tag);
  document.querySelectorAll('.tag-btn').forEach(btn => {
    btn.classList.toggle('active', selectedTags.has(btn.dataset.tag));
  });
  applyFilters();
  const btn = [...document.querySelectorAll('.tag-btn')].find(b => b.dataset.tag === tag);
  if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ─── Collect Panel ────────────────────────────────────────────────
let collectAbortCtrl = null;

async function openCollect() {
  try {
    const res  = await fetch('/api/categories');
    const data = await res.json();
    const sel  = document.getElementById('col-category');
    sel.innerHTML = '<option value="">전체</option>';
    (data.categories || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c; opt.textContent = c;
      sel.appendChild(opt);
    });
  } catch (_) {}
  document.getElementById('collect-panel').classList.add('visible');
  document.getElementById('collect-overlay').classList.add('visible');
}

function closeCollect() {
  document.getElementById('collect-panel').classList.remove('visible');
  document.getElementById('collect-overlay').classList.remove('visible');
  if (collectAbortCtrl) { collectAbortCtrl.abort(); collectAbortCtrl = null; }
}

function clearConsole() {
  document.getElementById('collect-console').innerHTML =
    '<div class="collect-idle-msg"><span class="idle-icon">🔬</span>위 옵션을 설정하고 수집을 시작하세요.</div>';
}

function appendLine(text, cls) {
  const el   = document.getElementById('collect-console');
  const line = document.createElement('div');
  line.className   = cls;
  line.textContent = text;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

async function startCollect() {
  const btn      = document.getElementById('collect-submit-btn');
  const consoleEl = document.getElementById('collect-console');

  // 수집 중이면 중단
  if (collectAbortCtrl) {
    collectAbortCtrl.abort();
    return;
  }

  const cat    = document.getElementById('col-category').value.trim();
  const game   = document.getElementById('col-game').value.trim();
  const mech   = document.getElementById('col-mechanic').value.trim();
  const query  = document.getElementById('col-query').value.trim();
  const totalCount = parseInt(document.getElementById('col-count').value, 10);
  const model      = document.getElementById('col-model')?.value || '';
  const dryRun     = document.getElementById('col-dry-run').checked;

  const payload = { totalCount };
  if (cat)    payload.category = cat;
  if (game)   payload.game     = game;
  if (mech)   payload.mechanic = mech;
  if (query)  payload.query    = query;
  if (model)  payload.model    = model;
  if (dryRun) payload.dryRun   = true;

  consoleEl.innerHTML = '';
  btn.classList.add('running');
  btn.textContent = '■ 중단';

  if (collectAbortCtrl) collectAbortCtrl.abort();
  collectAbortCtrl = new AbortController();

  // ── 로딩 & 프리뷰 상태
  let loadingVisible = false;
  let lastDetailEl   = null;   // 마지막 프리뷰 카드의 게임/카테고리 텍스트 노드

  function showLoading() {
    if (loadingVisible) return;
    loadingVisible = true;
    const el = document.createElement('div');
    el.id = 'collect-loading-el';
    el.className = 'collect-loading';
    el.innerHTML = `
      <div class="loading-sword-wrap">
        <span class="loading-sword">⚔️</span>
        <span class="loading-sparkle s1">✦</span>
        <span class="loading-sparkle s2">✧</span>
        <span class="loading-sparkle s3">✦</span>
      </div>
      <div class="loading-text">레퍼런스 열심히 수집 중<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span></div>
      <div class="loading-sub">Claude가 게임을 탐색하고 있어요 🎮</div>`;
    consoleEl.appendChild(el);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function hideLoading() {
    document.getElementById('collect-loading-el')?.remove();
    loadingVisible = false;
  }

  function addPreviewCard(id, name) {
    const card = document.createElement('div');
    card.className = 'collect-preview-item';
    card.innerHTML = `
      <div class="preview-item-name"><span class="preview-sparkle">✨</span>${name}</div>
      <div class="preview-item-meta"><span class="preview-item-id">${id}</span><span class="preview-item-detail"></span></div>`;
    consoleEl.appendChild(card);
    consoleEl.scrollTop = consoleEl.scrollHeight;
    lastDetailEl = card.querySelector('.preview-item-detail');
  }

  try {
    const res = await fetch('/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: collectAbortCtrl.signal,
    });
    if (!res.ok || !res.body) { appendLine(`서버 오류: ${res.status}`, 'cl-error'); return; }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let done   = false;

    while (!done) {
      const { done: streamDone, value } = await reader.read();
      if (streamDone) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop();

      for (const chunk of chunks) {
        let eventType = 'message', data = '';
        for (const line of chunk.split('\n')) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          else if (line.startsWith('data: ')) data = line.slice(6);
        }
        if (!data) continue;

        if (eventType === 'collect-done') {
          hideLoading();
          const banner = document.createElement('div');
          banner.className = 'cl-done-banner';
          const addedCount = parseInt(data, 10);
          const countStr = (!dryRun && addedCount > 0) ? ` · ${addedCount}개 추가` : '';
          banner.innerHTML = `✓ 수집 완료!${countStr}${dryRun ? ' (미리보기)' : ''}<button class="reload-btn" onclick="init()">DB 갱신</button>`;
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          if (!dryRun) setTimeout(init, 800);
          done = true; break;
        } else if (eventType === 'collect-error') {
          hideLoading();
          const banner = document.createElement('div');
          banner.className = 'cl-error-banner';
          banner.textContent = `✗ 수집 실패 (종료 코드: ${data})`;
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          done = true; break;
        } else if (eventType === 'wait') {
          appendLine(data, 'cl-wait');
          showLoading();
        } else if (eventType === 'ok') {
          hideLoading();
          const m = data.match(/✓\s*\[([^\]]+)\]\s*(.*)/);
          if (m) {
            addPreviewCard(m[1], m[2].replace(/\*+/g, '').trim());
          } else {
            appendLine(data, 'cl-ok');
            lastDetailEl = null;
          }
        } else if (eventType === 'log') {
          // 게임 / 카테고리 / 타입 detail 라인 → 마지막 카드에 추가
          const stripped = data.trim();
          if (lastDetailEl && stripped.includes(' / ') && !/^[🎥📖🖼️🎞️]/.test(stripped)) {
            lastDetailEl.textContent = ' · ' + stripped;
            lastDetailEl = null;
          }
          // 나머지 log (미디어 URL 등)는 콘솔에 표시하지 않음
        } else if (eventType === 'start') {
          appendLine(data, 'cl-start');
        } else if (eventType === 'batch-done') {
          liveUpdate();
        } else if (eventType === 'batch') {
          hideLoading();
          lastDetailEl = null;
          appendLine(data, 'cl-batch');
        } else if (eventType === 'sep') {
          appendLine(data, 'cl-sep');
        } else if (eventType === 'error') {
          hideLoading();
          appendLine(data, 'cl-error');
        } else if (eventType === 'done-line') {
          hideLoading();
          appendLine(data, 'cl-done-line');
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') appendLine('수집 중단됨', 'cl-batch');
    else appendLine(`연결 오류: ${e.message}`, 'cl-error');
  } finally {
    btn.classList.remove('running');
    btn.textContent = '▶ 수집 시작';
    collectAbortCtrl = null;
  }
}

// ── 실시간 그리드 업데이트 (배치 완료 시마다 호출)
async function liveUpdate() {
  try {
    const res = await fetch('/data/weapons.json', {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    });
    if (!res.ok) return;
    const db = await res.json();

    const prevIds = new Set(allWeapons.map(w => w.id));
    const newOnes = db.weapons.filter(w => !prevIds.has(w.id));
    if (newOnes.length === 0) return;

    allWeapons = db.weapons;

    // 필터 드롭다운·태그클라우드 갱신 (현재 선택값 유지)
    const savedCat  = document.getElementById('filter-category').value;
    const savedGame = document.getElementById('filter-game').value;
    populateFilters();
    document.getElementById('filter-category').value = savedCat;
    document.getElementById('filter-game').value     = savedGame;
    populateTagCloud();

    applyFilters(); // 필터 유지하며 그리드 재렌더

    // 새 카드 하이라이트 + 첫 카드로 스크롤
    let scrolled = false;
    newOnes.forEach(w => {
      const el = document.querySelector(`[data-card-id="${w.id}"]`);
      if (el) {
        el.classList.add('card-new');
        if (!scrolled) { scrolled = true; el.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
        setTimeout(() => el.classList.remove('card-new'), 2500);
      }
    });
  } catch (e) {
    console.error('[liveUpdate]', e);
  }
}

// ── 무한 수집 토글
let infiniteRunning = false;

async function toggleInfinite() {
  const btn       = document.getElementById('infinite-btn');
  const submitBtn = document.getElementById('collect-submit-btn');
  const consoleEl = document.getElementById('collect-console');

  // 실행 중 → 중단
  if (infiniteRunning) {
    if (collectAbortCtrl) { collectAbortCtrl.abort(); collectAbortCtrl = null; }
    return;
  }

  infiniteRunning = true;
  btn.classList.add('running');
  btn.textContent = '■ 중단';
  submitBtn.disabled = true;
  consoleEl.innerHTML = '';

  if (collectAbortCtrl) collectAbortCtrl.abort();
  collectAbortCtrl = new AbortController();

  const model  = document.getElementById('col-model')?.value || '';
  const dryRun = document.getElementById('col-dry-run').checked;
  const payload = { infinite: true };
  if (model)  payload.model  = model;
  if (dryRun) payload.dryRun = true;

  // 로딩 & 프리뷰 상태
  let loadingVisible = false;
  let lastDetailEl   = null;

  function showLoading() {
    if (loadingVisible) return;
    loadingVisible = true;
    const el = document.createElement('div');
    el.id = 'collect-loading-el';
    el.className = 'collect-loading';
    el.innerHTML = `
      <div class="loading-sword-wrap">
        <span class="loading-sword">⚔️</span>
        <span class="loading-sparkle s1">✦</span>
        <span class="loading-sparkle s2">✧</span>
        <span class="loading-sparkle s3">✦</span>
      </div>
      <div class="loading-text">무한 수집 중<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span></div>
      <div class="loading-sub">전 카테고리를 순환합니다 ∞</div>`;
    consoleEl.appendChild(el);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function hideLoading() {
    loadingVisible = false;
    const el = document.getElementById('collect-loading-el');
    if (el) el.remove();
  }

  function addPreviewCard(id, name) {
    const card = document.createElement('div');
    card.className = 'collect-preview-item';
    card.innerHTML = `
      <div class="preview-item-name"><span class="preview-sparkle">✨</span>${name}</div>
      <div class="preview-item-meta"><span class="preview-item-id">${id}</span><span class="preview-item-detail"></span></div>`;
    consoleEl.appendChild(card);
    lastDetailEl = card.querySelector('.preview-item-detail');
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function appendLine(text, cls) {
    const el = document.createElement('div');
    el.className = cls;
    el.textContent = text;
    consoleEl.appendChild(el);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  try {
    const resp = await fetch('/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: collectAbortCtrl.signal,
    });

    const reader = resp.body.getReader();
    const dec    = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const blocks = buf.split('\n\n');
      buf = blocks.pop();

      for (const block of blocks) {
        let eventType = 'message', data = '';
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim();
          else if (line.startsWith('data:')) data = line.slice(5).trim();
        }

        if (eventType === 'batch-done') {
          liveUpdate();
        } else if (eventType === 'collect-done') {
          hideLoading();
          const banner = document.createElement('div');
          banner.className = 'cl-done-banner';
          banner.innerHTML = `■ 무한 수집 중단 · ${data}개 추가됨<button class="reload-btn" onclick="init()">DB 갱신</button>`;
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          if (!dryRun) setTimeout(init, 800);
          break;
        } else if (eventType === 'collect-error') {
          hideLoading();
          const banner = document.createElement('div');
          banner.className = 'cl-error-banner';
          banner.textContent = `✗ 오류 발생`;
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          break;
        } else if (eventType === 'wait') {
          appendLine(data, 'cl-wait');
          showLoading();
        } else if (eventType === 'ok') {
          hideLoading();
          const m = data.match(/✓\s*\[([^\]]+)\]\s*(.*)/);
          if (m) addPreviewCard(m[1], m[2].replace(/\*+/g, '').trim());
          else appendLine(data, 'cl-ok');
        } else if (eventType === 'log') {
          const stripped = data.trim();
          if (lastDetailEl && stripped.includes(' / ') && !/^[🎥📖🖼️🎞️]/.test(stripped)) {
            lastDetailEl.textContent = ' · ' + stripped;
            lastDetailEl = null;
          }
        } else if (eventType === 'start') {
          appendLine(data, 'cl-start');
        } else if (eventType === 'batch') {
          hideLoading();
          lastDetailEl = null;
          appendLine(data, 'cl-batch');
        } else if (eventType === 'sep') {
          appendLine(data, 'cl-sep');
        } else if (eventType === 'error') {
          hideLoading();
          appendLine(data, 'cl-error');
        } else if (eventType === 'done-line') {
          hideLoading();
          appendLine(data, 'cl-done-line');
        }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      const el = document.createElement('div');
      el.className = 'cl-error';
      el.textContent = '연결 종료';
      consoleEl.appendChild(el);
    }
  } finally {
    infiniteRunning = false;
    btn.classList.remove('running');
    btn.textContent = '∞ 무한 수집';
    submitBtn.disabled = false;
    collectAbortCtrl = null;
  }
}

async function startLogin() {
  const btn       = document.getElementById('login-btn');
  const consoleEl = document.getElementById('collect-console');

  // 수집 중이면 중단
  if (collectAbortCtrl) { collectAbortCtrl.abort(); collectAbortCtrl = null; }
  collectAbortCtrl = new AbortController();

  consoleEl.innerHTML = '';
  btn.disabled = true;
  btn.textContent = '⏳ 로그인 중...';

  const CLASS_MAP = {
    ok: 'cl-ok', error: 'cl-error', wait: 'cl-wait',
    sep: 'cl-sep', start: 'cl-start', log: 'cl-log',
  };

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
      signal: collectAbortCtrl.signal,
    });
    if (!res.ok || !res.body) { appendLine(`서버 오류: ${res.status}`, 'cl-error'); return; }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop();

      for (const chunk of chunks) {
        let eventType = 'message', data = '';
        for (const line of chunk.split('\n')) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          else if (line.startsWith('data: ')) data = line.slice(6);
        }
        if (!data) continue;

        if (eventType === 'login-done') {
          const banner = document.createElement('div');
          banner.className = 'cl-done-banner';
          banner.innerHTML = '🔑 터미널 창이 열렸습니다.<br><strong>/login</strong> 입력 → 브라우저 로그인 완료 후 수집을 시작하세요.';
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          break;
        } else if (eventType === 'login-error') {
          const banner = document.createElement('div');
          banner.className = 'cl-error-banner';
          banner.textContent = `✗ 터미널 창 열기 실패. 직접 터미널에서 claude를 실행한 뒤 /login을 입력하세요.`;
          consoleEl.appendChild(banner);
          consoleEl.scrollTop = consoleEl.scrollHeight;
          break;
        } else {
          appendLine(data, CLASS_MAP[eventType] || 'cl-log');
        }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') appendLine(`연결 오류: ${e.message}`, 'cl-error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔑 로그인';
    collectAbortCtrl = null;
  }
}

// ─── Keyboard Shortcuts ───────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeModal(); closeCollect(); }
  if (e.key === '/' && !e.target.matches('input')) {
    e.preventDefault();
    document.getElementById('search').focus();
  }
});

document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});

// ─── Boot ─────────────────────────────────────────────────────────
init();
