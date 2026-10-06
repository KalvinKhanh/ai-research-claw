// AutoResearchClaw Phase 1 - Minimalist Dashboard Logic
document.addEventListener('DOMContentLoaded', () => {
  const data = window.AUTORESEARCH_DATA;
  if (!data) {
    console.error('AutoResearchClaw data not loaded');
    return;
  }

  // --- State ---
  let activeTab = 'overview';
  let activeStageKey = 'stage-01';
  let literatureMode = 'shortlist'; // 'shortlist' | 'corpus'
  let literatureSearchQuery = '';
  let currentPage = 1;
  const pageSize = 12;

  // Chart instances
  let charts = {};

  // --- Initializers ---
  initHeader();
  initStepper();
  initTabs();
  initKPIs();
  initCharts();
  initOverviewTable();
  initStageViewer();
  initLiteratureExplorer();
  initModal();

  // Expose switchTab globally for internal buttons
  window.switchTab = switchTab;

  // --- 1. Header & Banner ---
  function initHeader() {
    document.getElementById('header-run-id').textContent = data.run_id;
    document.getElementById('banner-topic').textContent = data.topic;
    document.getElementById('banner-benchmark').textContent = data.benchmark;
    document.getElementById('banner-model').textContent = data.target_model.split('/')[0].trim();
    document.getElementById('banner-gpu').textContent = `${data.hardware.gpu_name || 'NVIDIA GPU'} (${data.hardware.vram_mb || 4096} MB)`;
  }

  // --- 2. Minimalist Stepper ---
  function initStepper() {
    const track = document.getElementById('stepper-track');
    track.innerHTML = '';

    const stagesList = [
      { num: 1, key: 'stage-01', name: 'Topic Scoping' },
      { num: 2, key: 'stage-02', name: 'Problem Tree' },
      { num: 3, key: 'stage-03', name: 'Search Strategy' },
      { num: 4, key: 'stage-04', name: 'Lit Collect' },
      { num: 5, key: 'stage-05', name: 'Lit Screen' },
      { num: 6, key: 'stage-06', name: 'Knowledge Cards' },
      { num: 7, key: 'stage-07', name: 'Synthesis' },
      { num: 8, key: 'stage-08', name: 'Hypotheses' },
    ];

    stagesList.forEach((s) => {
      const btn = document.createElement('button');
      btn.className = `step-node ${s.key === activeStageKey ? 'active' : ''}`;
      btn.id = `step-node-${s.key}`;
      btn.onclick = () => {
        switchTab('stages');
        selectStage(s.key);
      };

      const sec = data.stages[s.key]?.duration_sec;
      const durStr = sec ? `${Math.round(sec)}s` : 'done';

      btn.innerHTML = `
        <div class="step-circle">${s.num}</div>
        <div class="step-label">${s.name}</div>
        <div class="step-dur">${durStr}</div>
      `;
      track.appendChild(btn);
    });
  }

  // --- 3. Tabs ---
  function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        switchTab(tab);
      });
    });
  }

  function switchTab(tabName) {
    activeTab = tabName;
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tabName);
    });
    document.querySelectorAll('.view-section').forEach(sec => {
      sec.classList.toggle('active', sec.id === `view-${tabName}`);
    });

    if (tabName === 'overview') {
      setTimeout(() => {
        Object.values(charts).forEach(c => c && c.resize());
      }, 50);
    }
  }

  // --- 4. KPIs ---
  function initKPIs() {
    const lit = data.literature;
    document.getElementById('kpi-total-candidates').textContent = (lit.total_candidates || 654).toLocaleString();
    document.getElementById('kpi-shortlisted').textContent = data.stages['stage-05']?.shortlist?.length || 16;
    document.getElementById('kpi-cards-count').textContent = data.stages['stage-06']?.cards?.length || 6;
    document.getElementById('kpi-novelty-score').textContent = (data.stages['stage-08']?.novelty_report?.novelty_score || 1.0).toFixed(1);
    
    let totalSec = 0;
    Object.values(data.stages).forEach(s => { totalSec += (s.duration_sec || 0); });
    const mins = (totalSec / 60).toFixed(1);
    document.getElementById('kpi-total-duration').textContent = `${mins}m`;
  }

  // --- 5. Clean Minimalist Charts ---
  function initCharts() {
    if (typeof Chart === 'undefined') return;

    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = '#64748b';

    // Chart 1: Year Distribution
    const ctxYear = document.getElementById('chart-year-dist');
    if (ctxYear) {
      const yearData = data.literature.year_distribution || {};
      const labels = Object.keys(yearData);
      const values = Object.values(yearData);

      charts.year = new Chart(ctxYear, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: labels.map(y => parseInt(y) >= 2024 ? '#0284c7' : '#94a3b8'),
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: '#f1f5f9' }, beginAtZero: true },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // Chart 2: Stage Durations
    const ctxDuration = document.getElementById('chart-stage-durations');
    if (ctxDuration) {
      const stageLabels = ['S1: Topic', 'S2: Tree', 'S3: Queries', 'S4: Collect', 'S5: Screen', 'S6: Cards', 'S7: Synth', 'S8: Hypo'];
      const durations = stageLabels.map((_, idx) => {
        const k = `stage-0${idx + 1}`;
        const sec = data.stages[k]?.duration_sec || 0;
        return parseFloat(sec.toFixed(1));
      });

      charts.duration = new Chart(ctxDuration, {
        type: 'bar',
        data: {
          labels: stageLabels,
          datasets: [{
            data: durations,
            backgroundColor: '#059669',
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: '#f1f5f9' }, beginAtZero: true },
            x: { grid: { display: false } }
          }
        }
      });
    }
  }

  // --- 5.1 Overview Top Papers Table ---
  function initOverviewTable() {
    const tbody = document.getElementById('overview-top-papers-tbody');
    if (!tbody) return;

    let topPapers = [];
    if (data.literature && data.literature.top_cited && data.literature.top_cited.length > 0) {
      topPapers = data.literature.top_cited;
    } else if (data.literature && data.literature.candidates && data.literature.candidates.length > 0) {
      topPapers = [...data.literature.candidates].sort((a, b) => (b.citations || b.citation_count || 0) - (a.citations || a.citation_count || 0)).slice(0, 10);
    }

    if (topPapers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:1.5rem;">Chưa có dữ liệu bài báo.</td></tr>';
      return;
    }

    tbody.innerHTML = topPapers.slice(0, 10).map((p, idx) => {
      const pid = p.id || p.paper_id || `paper-${idx}`;
      const cites = p.citations !== undefined ? p.citations : (p.citation_count || 0);
      return `
        <tr>
          <td style="font-weight:700; color:var(--text-muted);">${idx + 1}</td>
          <td style="font-weight:600; cursor:pointer;" onclick="openPaperModal('${escapeHtml(pid)}')">
            ${escapeHtml(p.title || 'Untitled')}
          </td>
          <td>${p.year || 'N/A'}</td>
          <td style="color:var(--text-muted);">${escapeHtml(p.venue || 'ArXiv / OpenAlex')}</td>
          <td style="text-align:right; font-weight:700; color:#d97706;">★ ${cites.toLocaleString()}</td>
          <td style="text-align:center;">
            <button class="btn" style="padding:2px 10px; font-size:0.75rem; border-radius:999px;" onclick="openPaperModal('${escapeHtml(pid)}')">Xem</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  // --- 6. Stage Viewer (Deep Dive) ---
  function initStageViewer() {
    const navContainer = document.getElementById('stage-nav-list');
    navContainer.innerHTML = '';

    const stages = [
      { key: 'stage-01', num: 1, name: 'Topic Scoping' },
      { key: 'stage-02', num: 2, name: 'Problem Tree' },
      { key: 'stage-03', num: 3, name: 'Search Strategy' },
      { key: 'stage-04', num: 4, name: 'Literature Collect' },
      { key: 'stage-05', num: 5, name: 'Literature Screen' },
      { key: 'stage-06', num: 6, name: 'Knowledge Cards' },
      { key: 'stage-07', num: 7, name: 'Synthesis & Gaps' },
      { key: 'stage-08', num: 8, name: 'Hypotheses & Novelty' },
    ];

    stages.forEach(s => {
      const btn = document.createElement('button');
      btn.className = `stage-menu-btn ${s.key === activeStageKey ? 'active' : ''}`;
      btn.id = `menu-btn-${s.key}`;
      btn.onclick = () => selectStage(s.key);

      btn.innerHTML = `
        <span>Stage ${s.num}: ${s.name}</span>
        <span style="font-family:var(--font-mono); font-size:0.7rem; color:var(--text-subtle);">
          ${data.stages[s.key]?.duration_sec ? Math.round(data.stages[s.key].duration_sec) + 's' : ''}
        </span>
      `;
      navContainer.appendChild(btn);
    });

    renderStageContent(activeStageKey);
  }

  function selectStage(stageKey) {
    activeStageKey = stageKey;

    document.querySelectorAll('.stage-menu-btn').forEach(it => {
      it.classList.toggle('active', it.id === `menu-btn-${stageKey}`);
    });

    document.querySelectorAll('.step-node').forEach(node => {
      node.classList.toggle('active', node.id === `step-node-${stageKey}`);
    });

    renderStageContent(stageKey);
  }

  function renderStageContent(stageKey) {
    const sData = data.stages[stageKey] || {};
    const titleEl = document.getElementById('stage-view-title');
    const descEl = document.getElementById('stage-view-desc');
    const durationEl = document.getElementById('stage-view-duration');
    const bodyEl = document.getElementById('stage-view-body');

    titleEl.textContent = `Stage ${sData.stage_number || stageKey.split('-')[1]}: ${sData.name || stageKey}`;
    durationEl.textContent = `⏱ ${sData.duration_sec ? sData.duration_sec.toFixed(1) + 's' : 'N/A'}`;

    let contentHtml = '';

    if (stageKey === 'stage-01') {
      descEl.textContent = 'Khởi tạo đề tài, benchmark QASPER và mục tiêu SMART.';
      contentHtml = `<div class="markdown-body">${renderMarkdown(sData.goal_md || '')}</div>`;
    } else if (stageKey === 'stage-02') {
      descEl.textContent = 'Phân rã 5 câu hỏi nghiên cứu cốt lõi (SQ1 - SQ5) và ma trận rủi ro.';
      contentHtml = `<div class="markdown-body">${renderMarkdown(sData.problem_tree_md || '')}</div>`;
    } else if (stageKey === 'stage-03') {
      descEl.textContent = '9 câu truy vấn học thuật được tự động tạo lập cho OpenAlex và arXiv.';
      const queries = sData.queries_data?.queries || [];
      contentHtml = `
        <div style="display:flex; flex-direction:column; gap:0.4rem; margin-top:0.5rem;">
          ${queries.map((q, idx) => `
            <div style="padding:0.6rem 0.85rem; background:#f8fafc; border:1px solid var(--border); border-radius:6px; display:flex; align-items:center; gap:0.6rem; font-size:0.85rem;">
              <span style="font-weight:700; color:var(--primary); width:20px;">#${idx+1}</span>
              <code>${q}</code>
            </div>
          `).join('')}
        </div>
      `;
    } else if (stageKey === 'stage-04') {
      descEl.textContent = 'Thu thập 654 bài báo học thuật ứng viên và 654 mục BibTeX.';
      contentHtml = `
        <div style="padding:1rem; background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; font-size:0.85rem; color:#0369a1; margin-bottom:1rem;">
          ✓ Thu thập thành công <strong>654 bài báo</strong> từ OpenAlex (381) và arXiv (273). Toàn bộ danh mục được lưu trong <code>candidates.jsonl</code> và <code>references.bib</code>.
        </div>
        <button class="btn btn-primary" onclick="switchTab('literature')">Mở Kho Bài báo để tìm kiếm chi tiết →</button>
      `;
    } else if (stageKey === 'stage-05') {
      descEl.textContent = 'Cổng kiểm định chất lượng: 16 bài báo có độ tương thích cao nhất.';
      const shortlist = sData.shortlist || [];
      contentHtml = `
        <div style="display:flex; flex-direction:column; gap:0.6rem;">
          ${shortlist.map((p, idx) => `
            <div class="paper-item" onclick="openPaperModal('${p.paper_id}')">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.75rem;">
                <div class="paper-item-title">${idx+1}. ${p.title}</div>
                <div style="display:flex; gap:0.35rem; flex-shrink:0;">
                  <span class="pill-badge green">Rel: ${p.relevance_score}</span>
                  <span class="pill-badge mono">★ ${p.citation_count || 0}</span>
                </div>
              </div>
              <div class="paper-item-meta">
                <span>${p.year}</span> &bull;
                <span>${p.venue || 'ArXiv'}</span> &bull;
                <span>${p.source}</span>
              </div>
              <div class="paper-item-snippet">${p.abstract}</div>
            </div>
          `).join('')}
        </div>
      `;
    } else if (stageKey === 'stage-06') {
      descEl.textContent = '6 Thẻ Tri thức trích xuất sâu về phương pháp và giới hạn.';
      const cards = sData.cards || [];
      contentHtml = `
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:0.85rem;">
          ${cards.map((c, i) => `
            <div style="border:1px solid var(--border); border-radius:8px; padding:1rem; background:#ffffff;">
              <div style="font-weight:700; font-size:0.82rem; color:var(--primary); margin-bottom:0.4rem;">${c.filename}</div>
              <div class="markdown-body" style="font-size:0.8rem;">${renderMarkdown(c.content)}</div>
            </div>
          `).join('')}
        </div>
      `;
    } else if (stageKey === 'stage-07') {
      descEl.textContent = 'Tổng hợp tài liệu: 3 cụm chuyên đề và 3 khoảng trống nghiên cứu.';
      contentHtml = `<div class="markdown-body">${renderMarkdown(sData.synthesis_md || '')}</div>`;
    } else if (stageKey === 'stage-08') {
      descEl.textContent = 'Đánh giá tính mới (Novelty Score: 1.0) và Đề xuất giả thuyết nghiên cứu.';
      const perspectives = sData.perspectives || {};
      contentHtml = `
        <div style="padding:0.85rem 1rem; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; margin-bottom:1rem; font-size:0.85rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong>Điểm tính mới (Novelty Score):</strong> <span style="color:#059669; font-weight:700;">1.0 / 1.0 (High)</span> — 0 bài báo trùng lặp.
          </div>
          <span class="pill-badge green">Khuyến nghị: Tiến hành (Proceed)</span>
        </div>

        <div style="margin-bottom:1.5rem;">
          <h3 style="font-size:1rem; font-weight:700; margin-bottom:0.5rem;">Tóm tắt 3 Góc nhìn Tranh luận (Multi-Perspective Summary)</h3>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:0.75rem; margin-bottom:1rem;">
            <div style="border:1px solid #bbf7d0; background:#f0fdf4; border-radius:6px; padding:0.85rem; font-size:0.8rem;">
              <strong style="color:#059669;">The Innovator:</strong> 1D DNA Barcoding để mã hóa cấu trúc văn bản mà không cần Graph-RAG cồng kềnh.
            </div>
            <div style="border:1px solid #bae6fd; background:#f0f9ff; border-radius:6px; padding:0.85rem; font-size:0.8rem;">
              <strong style="color:#0284c7;">The Pragmatist:</strong> Định tuyến phân luồng câu hỏi bằng DeBERTa, tiết kiệm 40% chi phí và độ trễ trên GPU nhẹ.
            </div>
            <div style="border:1px solid #fecdd3; background:#fff1f2; border-radius:6px; padding:0.85rem; font-size:0.8rem;">
              <strong style="color:#e11d48;">The Contrarian:</strong> Cảnh báo bẫy phức tạp hóa cấu trúc và vòng lặp khuếch đại ảo giác.
            </div>
          </div>
        </div>

        <div class="markdown-body">
          ${renderMarkdown(sData.hypotheses_md || '')}
        </div>
      `;
    }

    bodyEl.innerHTML = contentHtml;
  }

  // --- 7. Literature Explorer ---
  function initLiteratureExplorer() {
    const searchInput = document.getElementById('lit-search-input');
    const toggleBtns = document.querySelectorAll('.lit-pill-btn');

    searchInput.addEventListener('input', (e) => {
      literatureSearchQuery = e.target.value.toLowerCase().trim();
      currentPage = 1;
      renderLiteratureList();
    });

    toggleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        toggleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        literatureMode = btn.getAttribute('data-mode');
        currentPage = 1;
        renderLiteratureList();
      });
    });

    document.getElementById('lit-prev-page').addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        renderLiteratureList();
      }
    });

    document.getElementById('lit-next-page').addEventListener('click', () => {
      currentPage++;
      renderLiteratureList();
    });

    renderLiteratureList();
  }

  function getFilteredLiterature() {
    let pool = literatureMode === 'shortlist' 
      ? (data.stages['stage-05']?.shortlist || []) 
      : (data.literature.candidates || []);

    if (literatureSearchQuery) {
      pool = pool.filter(p => {
        const title = (p.title || '').toLowerCase();
        const abs = (p.abstract || '').toLowerCase();
        const venue = (p.venue || '').toLowerCase();
        return title.includes(literatureSearchQuery) || abs.includes(literatureSearchQuery) || venue.includes(literatureSearchQuery);
      });
    }

    return pool;
  }

  function renderLiteratureList() {
    const listContainer = document.getElementById('lit-papers-list');
    const filtered = getFilteredLiterature();
    const totalItems = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalItems);
    const pageItems = filtered.slice(startIdx, endIdx);

    document.getElementById('lit-count-label').textContent = `Hiển thị ${totalItems} bài báo`;
    document.getElementById('lit-page-info').textContent = `Trang ${currentPage} / ${totalPages} (${totalItems} bài)`;
    document.getElementById('lit-prev-page').disabled = currentPage <= 1;
    document.getElementById('lit-next-page').disabled = currentPage >= totalPages;

    if (pageItems.length === 0) {
      listContainer.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-subtle);">Không tìm thấy bài báo phù hợp từ khóa.</div>';
      return;
    }

    listContainer.innerHTML = pageItems.map((p, idx) => {
      const globalIdx = startIdx + idx + 1;
      const cites = p.citation_count !== undefined ? p.citation_count : (p.citations || 0);

      return `
        <div class="paper-item" onclick="openPaperModal('${p.paper_id || p.id}')">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.75rem;">
            <div class="paper-item-title">${globalIdx}. ${p.title}</div>
            <span class="pill-badge mono">★ ${cites.toLocaleString()}</span>
          </div>
          <div class="paper-item-meta">
            <span>${p.year || 'N/A'}</span> &bull;
            <span>${p.venue || 'ArXiv'}</span> &bull;
            <span>Nguồn: ${p.source || 'ArXiv'}</span>
          </div>
          <div class="paper-item-snippet">${p.abstract || 'Không có tóm tắt.'}</div>
        </div>
      `;
    }).join('');
  }

  // --- 8. Modal ---
  function initModal() {
    const overlay = document.getElementById('paper-modal-overlay');
    const closeBtn = document.getElementById('modal-close-btn');

    closeBtn.addEventListener('click', () => overlay.classList.remove('active'));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('active');
    });
  }

  window.openPaperModal = function(paperId) {
    const overlay = document.getElementById('paper-modal-overlay');
    const modalBody = document.getElementById('paper-modal-body');
    if (!overlay || !modalBody) return;

    let paper = null;
    if (data.stages && data.stages['stage-05'] && data.stages['stage-05'].shortlist) {
      paper = data.stages['stage-05'].shortlist.find(p => p.paper_id === paperId || p.id === paperId);
    }
    if (!paper && data.literature && data.literature.top_cited) {
      paper = data.literature.top_cited.find(p => p.id === paperId || p.paper_id === paperId);
    }
    if (!paper && data.literature && data.literature.candidates) {
      paper = data.literature.candidates.find(p => p.id === paperId || p.paper_id === paperId);
    }
    if (!paper && data.literature && data.literature.candidates) {
      const q = String(paperId).toLowerCase();
      paper = data.literature.candidates.find(p => p.title && (p.title.toLowerCase().includes(q) || q.includes(p.title.toLowerCase())));
    }
    if (!paper && data.literature && data.literature.candidates && data.literature.candidates.length > 0) {
      paper = data.literature.candidates[0];
    }
    if (!paper) return;

    const cites = paper.citation_count !== undefined ? paper.citation_count : (paper.citations || 0);

    modalBody.innerHTML = `
      <div style="margin-bottom:1rem;">
        <span class="pill-badge green">${paper.source || 'ArXiv'}</span>
        <h2 style="font-size:1.15rem; font-weight:700; margin-top:0.4rem; line-height:1.4;">${escapeHtml(paper.title || 'Untitled')}</h2>
      </div>

      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem;">
        <span class="pill-badge mono">★ ${cites.toLocaleString()} trích dẫn</span>
        <span class="pill-badge mono">Năm: ${paper.year || 'N/A'}</span>
        ${paper.relevance_score ? `<span class="pill-badge green">Độ tương thích: ${paper.relevance_score}</span>` : ''}
      </div>

      <div style="background:#f8fafc; border:1px solid var(--border); border-radius:6px; padding:0.75rem 1rem; margin-bottom:1rem; font-size:0.8rem; line-height:1.5;">
        <div><strong>Hội nghị / Nguồn:</strong> ${escapeHtml(paper.venue || 'Không xác định')}</div>
        ${paper.doi ? `<div style="margin-top:2px;"><strong>DOI:</strong> <code>${escapeHtml(paper.doi)}</code></div>` : ''}
        ${paper.url ? `<div style="margin-top:6px;"><a href="${paper.url}" target="_blank" style="color:var(--primary); text-decoration:none; font-weight:600;">Xem bài báo gốc ↗</a></div>` : ''}
      </div>

      <div>
        <div style="font-weight:700; font-size:0.85rem; margin-bottom:0.35rem;">Tóm tắt (Abstract)</div>
        <p style="font-size:0.82rem; line-height:1.6; color:var(--text-muted);">${escapeHtml(paper.abstract || 'Không có tóm tắt.')}</p>
      </div>
    `;

    overlay.classList.add('active');
  };

  // --- 10. Runner Modal & Live Execution ---
  const runnerOverlay = document.getElementById('runner-modal-overlay');
  const runnerCloseBtn = document.getElementById('runner-close-btn');
  let logPollInterval = null;

  if (runnerCloseBtn) {
    runnerCloseBtn.addEventListener('click', () => {
      runnerOverlay.classList.remove('active');
      if (logPollInterval) clearInterval(logPollInterval);
    });
  }

  window.openRunnerModal = function() {
    const input = document.getElementById('runner-topic-input');
    if (input && !input.value.trim()) {
      input.value = data.topic;
    }
    checkBackendHealth();
    runnerOverlay.classList.add('active');
  };

  function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['ngrok-skip-browser-warning'] = 'true';
    options.headers['Bypass-Tunnel-Reminder'] = 'true';
    return fetch(url, options);
  }

  async function checkBackendHealth() {
    const badge = document.getElementById('backend-status-badge');
    const startBtn = document.getElementById('btn-start-pipeline');
    try {
      const res = await apiFetch('/api/status');
      if (res.ok) {
        const status = await res.json();
        if (status.is_running) {
          badge.textContent = 'Đang chạy tác vụ...';
          badge.className = 'pill-badge mono';
          startBtn.disabled = true;
          startLogPolling();
        } else {
          badge.textContent = '● Backend Sẵn sàng (Local/Tunnel)';
          badge.className = 'pill-badge green';
          startBtn.disabled = false;
          // Hiển thị log gần nhất nếu có
          try {
            const lRes = await apiFetch('/api/logs');
            if (lRes.ok) {
              const lData = await lRes.json();
              if (lData.logs && lData.logs.length > 0) {
                const termBox = document.getElementById('runner-terminal-box');
                termBox.innerHTML = lData.logs.map(l => {
                  if (l.includes('❌') || l.includes('FAILED') || l.includes('LỖI')) {
                    return `<div style="color:#f87171;">&gt; ${escapeHtml(l)}</div>`;
                  } else if (l.includes('✓') || l.includes('THÀNH CÔNG') || l.includes('complete')) {
                    return `<div style="color:#34d399;">&gt; ${escapeHtml(l)}</div>`;
                  } else if (l.includes('⚠️')) {
                    return `<div style="color:#fbbf24;">&gt; ${escapeHtml(l)}</div>`;
                  }
                  return `<div>&gt; ${escapeHtml(l)}</div>`;
                }).join('');
                termBox.scrollTop = termBox.scrollHeight;
              }
            }
          } catch(err) {}
        }
      } else {
        throw new Error('No API');
      }
    } catch (e) {
      badge.textContent = '○ Chế độ Tĩnh (Static / Cloudflare Pages)';
      badge.className = 'pill-badge mono';
      startBtn.disabled = true;
      document.getElementById('runner-terminal-box').innerHTML = `
        <div style="color:#f59e0b;">
          [CHẾ ĐỘ TĨNH / READ-ONLY]: Giao diện đang được host dưới dạng web tĩnh (Cloudflare Pages / GitHub Pages).<br><br>
          👉 Để kích hoạt tính năng chạy Phase 1 trực tiếp trên web, bạn hãy kết nối Backend bằng Cloudflare Tunnel (cloudflared). Khi có backend, nút thực thi sẽ tự động được kích hoạt!
        </div>
      `;
    }
  }

  window.submitRunPipeline = async function() {
    const topic = document.getElementById('runner-topic-input').value.trim();
    const apiKey = document.getElementById('runner-apikey-input') ? document.getElementById('runner-apikey-input').value.trim() : '';
    const termBox = document.getElementById('runner-terminal-box');
    const startBtn = document.getElementById('btn-start-pipeline');

    if (!topic) {
      alert('Vui lòng nhập đề tài nghiên cứu!');
      return;
    }

    startBtn.disabled = true;
    termBox.innerHTML = '<div style="color:#38bdf8;">Đang gửi lệnh khởi chạy Phase 1 (Stage 1 – 8)...</div>';

    try {
      const res = await apiFetch('/api/run-phase-1', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic, api_key: apiKey })
      });
      const resData = await res.json();
      if (!res.ok) {
        termBox.innerHTML += `<div style="color:#ef4444;">Lỗi: ${resData.error || 'Không thể bắt đầu'}</div>`;
        startBtn.disabled = false;
        return;
      }

      termBox.innerHTML += '<div style="color:#10b981;">✓ Khởi động thành công! Đang stream tiến độ thực thi...</div>';
      startLogPolling();
    } catch (e) {
      termBox.innerHTML += `<div style="color:#ef4444;">Lỗi kết nối tới Server: ${e.message}</div>`;
      startBtn.disabled = false;
    }
  };

  function startLogPolling() {
    if (logPollInterval) clearInterval(logPollInterval);
    const termBox = document.getElementById('runner-terminal-box');
    const startBtn = document.getElementById('btn-start-pipeline');
    const badge = document.getElementById('backend-status-badge');

    logPollInterval = setInterval(async () => {
      try {
        const [statusRes, logsRes] = await Promise.all([
          apiFetch('/api/status'),
          apiFetch('/api/logs')
        ]);
        const status = await statusRes.json();
        const logsData = await logsRes.json();

        if (logsData.logs && logsData.logs.length > 0) {
          termBox.innerHTML = logsData.logs.map(l => {
            if (l.includes('❌') || l.includes('FAILED') || l.includes('LỖI')) {
              return `<div style="color:#f87171;">&gt; ${escapeHtml(l)}</div>`;
            } else if (l.includes('✓') || l.includes('THÀNH CÔNG')) {
              return `<div style="color:#34d399;">&gt; ${escapeHtml(l)}</div>`;
            } else if (l.includes('⚠️')) {
              return `<div style="color:#fbbf24;">&gt; ${escapeHtml(l)}</div>`;
            }
            return `<div>&gt; ${escapeHtml(l)}</div>`;
          }).join('');
          termBox.scrollTop = termBox.scrollHeight;
        }

        if (!status.is_running) {
          clearInterval(logPollInterval);
          startBtn.disabled = false;

          if (status.error) {
            badge.textContent = '❌ Thất bại';
            badge.className = 'pill-badge mono';
            termBox.innerHTML += `<div style="color:#ef4444; font-weight:700; margin-top:8px;">❌ ${escapeHtml(status.error)}</div>`;
          } else {
            badge.textContent = '● Hoàn thành!';
            badge.className = 'pill-badge green';
            termBox.innerHTML += '<div style="color:#10b981; font-weight:700; margin-top:8px;">=== HOÀN TẤT PHASE 1! Tự động làm mới giao diện sau 3 giây... ===</div>';
            setTimeout(() => { window.location.reload(); }, 3000);
          }
        }
      } catch (e) {
        clearInterval(logPollInterval);
      }
    }, 2000);
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // --- 11. Minimal Markdown Parser ---
  function renderMarkdown(md) {
    if (!md) return '';
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(md);
    }
    return md
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/\n\s*-\s+(.*)/gim, '<ul><li>$1</li></ul>')
      .replace(/<\/ul>\s*<ul>/gim, '')
      .replace(/\n\n/gim, '<p></p>');
  }
});

