/* FinAtlas frontend SPA */

(function () {
  'use strict';

  const env = window.__ENV__ || {};
  let supabase = null;
  let session = null;
  let devMode = false;
  let currentScreening = null;
  let allScreenings = [];
  let allCases = [];

  const viewTitles = {
    auth: 'Authentication',
    mfa: 'Multi-factor authentication',
    mfaChallenge: 'Multi-factor authentication',
    dashboard: 'Dashboard',
    screenings: 'Screenings',
    cases: 'Cases',
    batches: 'Batches',
    screen: 'New Screening',
    api: 'API reference',
  };

  function el(id) { return document.getElementById(id); }

  function init() {
    if (!env.supabaseUrl || !env.supabaseKey) {
      showToast('Supabase configuration is missing. Check workspace secrets.', 'error');
      showAuth();
      return;
    }

    supabase = window.supabase.createClient(env.supabaseUrl, env.supabaseKey, {
      auth: { persistSession: true, autoRefreshToken: true }
    });

    bindAuth();
    bindNavigation();
    bindForms();
    bindModal();
    bindMobileMenu();

    supabase.auth.getSession().then(({ data }) => {
      session = data.session;
      if (session) {
        onSessionReady();
      } else if (!env.requireAuth) {
        enableDevMode();
      } else {
        showAuth();
      }
    });
  }

  // --- Views ---------------------------------------------------------------

  function showView(name) {
    document.querySelectorAll('.view').forEach((view) => view.classList.add('hidden'));
    const target = el(`${name}-view`);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.nav-link').forEach((link) => {
      link.classList.toggle('active', link.dataset.view === name);
    });

    const titleEl = el('page-title');
    if (titleEl) titleEl.textContent = viewTitles[name] || '';

    const sidebarEl = el('sidebar');
    if (sidebarEl) sidebarEl.classList.remove('open');

    if (name === 'dashboard') loadDashboard();
    if (name === 'screenings') loadScreenings();
    if (name === 'cases') loadCases();
    if (name === 'batches') loadBatches();
  }

  function showAuth() {
    el('sidebar')?.classList.add('hidden');
    el('main')?.classList.remove('hidden');
    const skipBtn = el('dev-skip-btn');
    if (skipBtn) skipBtn.classList.toggle('hidden', env.requireAuth);
    showView('auth');
  }

  function showApp() {
    el('sidebar')?.classList.remove('hidden');
    el('main')?.classList.remove('hidden');
    showView('dashboard');
  }

  function enableDevMode() {
    devMode = true;
    session = null;
    el('user-email').textContent = 'Development mode';
    el('mfa-badge').classList.add('verified');
    el('mfa-badge').textContent = 'No auth';
    showApp();
  }

  // --- Auth ----------------------------------------------------------------

  function bindAuth() {
    document.querySelectorAll('.tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        el('signin-form')?.classList.toggle('hidden', tab.dataset.tab !== 'signin');
        el('signup-form')?.classList.toggle('hidden', tab.dataset.tab !== 'signup');
      });
    });

    el('signin-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = new FormData(e.target);
      const { error } = await supabase.auth.signInWithPassword({
        email: data.get('email'),
        password: data.get('password'),
      });
      if (error) return showToast(error.message, 'error');
      const { data: sessionData } = await supabase.auth.getSession();
      session = sessionData.session;
      onSessionReady();
    });

    el('signup-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = new FormData(e.target);
      const { error } = await supabase.auth.signUp({
        email: data.get('email'),
        password: data.get('password'),
      });
      if (error) return showToast(error.message, 'error');
      showToast('Account created. Please check your email to confirm, then sign in.', 'success');
      document.querySelector('[data-tab="signin"]')?.click();
    });

    el('sign-out-btn')?.addEventListener('click', async () => {
      await supabase.auth.signOut();
      session = null;
      devMode = false;
      showAuth();
    });

    el('dev-skip-btn')?.addEventListener('click', enableDevMode);

    el('mfa-form')?.addEventListener('submit', verifyMfaEnrollment);
    el('mfa-challenge-form')?.addEventListener('submit', verifyMfaChallenge);
  }

  async function onSessionReady() {
    if (!session) {
      showAuth();
      return;
    }
    el('user-email').textContent = session.user.email;

    const { data: factorsData, error } = await supabase.auth.mfa.listFactors();
    if (error) return showToast(error.message, 'error');

    const totpFactors = factorsData.all.filter((f) => f.factor_type === 'totp');
    const aal = decodeAal(session.access_token);

    if (totpFactors.length === 0) {
      await enrollMfa();
    } else if (aal !== 'aal2' && env.requireMfa) {
      await challengeMfa(totpFactors[0].id);
    } else {
      await completeSignIn();
    }
  }

  async function completeSignIn() {
    const me = await apiCall('/api/auth/me');
    if (me.error) {
      showToast(me.error, 'error');
      await supabase.auth.signOut();
      session = null;
      showAuth();
      return;
    }

    const mfaBadge = el('mfa-badge');
    if (me.mfa && me.mfa.verified) {
      mfaBadge.classList.add('verified');
      mfaBadge.textContent = 'MFA verified';
    } else {
      mfaBadge.classList.remove('verified');
      mfaBadge.textContent = env.requireMfa ? 'MFA required' : 'MFA optional';
    }
    showApp();
  }

  function decodeAal(token) {
    try {
      const payload = token.split('.')[1];
      const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
      const json = atob(padded);
      return JSON.parse(json).aal;
    } catch (e) {
      return null;
    }
  }

  async function enrollMfa() {
    const { data, error } = await supabase.auth.mfa.enroll({ factorType: 'totp' });
    if (error) return showToast(error.message, 'error');

    el('mfa-factor-id').value = data.id;
    const qrContainer = el('mfa-qr');
    if (qrContainer) qrContainer.innerHTML = data.totp.qr_code;
    showView('mfa');
  }

  async function verifyMfaEnrollment(e) {
    e.preventDefault();
    const factorId = el('mfa-factor-id').value;
    const code = el('mfa-code').value;

    const { data: challenge, error: challengeError } = await supabase.auth.mfa.challenge({ factorId });
    if (challengeError) return showToast(challengeError.message, 'error');

    const { error: verifyError } = await supabase.auth.mfa.verify({
      factorId,
      challengeId: challenge.id,
      code,
    });
    if (verifyError) return showToast(verifyError.message, 'error');

    const { data: sessionData } = await supabase.auth.getSession();
    session = sessionData.session;
    showToast('MFA enabled successfully', 'success');
    await onSessionReady();
  }

  async function challengeMfa(factorId) {
    el('mfa-challenge-factor-id').value = factorId;
    showView('mfaChallenge');
  }

  async function verifyMfaChallenge(e) {
    e.preventDefault();
    const factorId = el('mfa-challenge-factor-id').value;
    const code = el('mfa-challenge-code').value;

    const { data: challenge, error: challengeError } = await supabase.auth.mfa.challenge({ factorId });
    if (challengeError) return showToast(challengeError.message, 'error');

    const { error: verifyError } = await supabase.auth.mfa.verify({
      factorId,
      challengeId: challenge.id,
      code,
    });
    if (verifyError) return showToast(verifyError.message, 'error');

    const { data: sessionData } = await supabase.auth.getSession();
    session = sessionData.session;
    showToast('Signed in with MFA', 'success');
    await onSessionReady();
  }

  // --- Navigation ----------------------------------------------------------

  function bindNavigation() {
    document.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        showView(link.dataset.view);
      });
    });
    el('refresh-btn')?.addEventListener('click', () => {
      const active = document.querySelector('.nav-link.active');
      showView(active ? active.dataset.view : 'dashboard');
    });
  }

  function bindMobileMenu() {
    const toggle = el('menu-toggle');
    const sidebar = el('sidebar');
    toggle?.addEventListener('click', () => sidebar?.classList.toggle('open'));
  }

  // --- API helpers ---------------------------------------------------------

  async function apiCall(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (session) headers.Authorization = `Bearer ${session.access_token}`;
    const response = await fetch(path, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    data._status = response.status;
    return data;
  }

  function showToast(message, type = 'info') {
    const toast = el('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 4000);
  }

  // --- Dashboard -----------------------------------------------------------

  async function loadDashboard() {
    const stats = await apiCall('/api/screenings/stats');
    if (stats.error) return showToast(stats.error, 'error');

    setText('kpi-total', stats.total_screenings || 0);
    setText('kpi-high', stats.risk_distribution['Definite Match / High Risk'] || 0);
    setText('kpi-medium', stats.risk_distribution['Potential Match / Medium Risk'] || 0);
    setText('kpi-low', stats.risk_distribution['No Match / Low Risk'] || 0);
    setText('kpi-cases', stats.open_cases || 0);
    setText('kpi-disagreements', stats.alert_disagreements || 0);

    renderRiskChart(stats.risk_distribution || {});
    renderRecentScreenings(stats.recent_screenings || []);

    const summary = el('disagreement-summary');
    if (summary) {
      const total = stats.total_screenings || 0;
      const disagreements = stats.alert_disagreements || 0;
      const pct = total ? Math.round((disagreements / total) * 100) : 0;
      summary.textContent = `${disagreements} of ${total} screenings (${pct}%) had a different classification after Gemini review.`;
    }
  }

  function setText(id, value) {
    const node = el(id);
    if (node) node.textContent = value;
  }

  function renderRiskChart(distribution) {
    const container = el('risk-chart');
    if (!container) return;
    const order = [
      { key: 'Definite Match / High Risk', label: 'High risk', cls: 'high' },
      { key: 'Potential Match / Medium Risk', label: 'Medium risk', cls: 'medium' },
      { key: 'No Match / Low Risk', label: 'Low risk', cls: 'low' },
    ];
    const total = Object.values(distribution).reduce((a, b) => a + b, 0) || 1;
    container.innerHTML = order.map((item) => {
      const value = distribution[item.key] || 0;
      const pct = (value / total) * 100;
      return `
        <div class="bar-row">
          <span class="bar-label" title="${item.label}">${item.label}</span>
          <div class="bar-track"><div class="bar-fill ${item.cls}" style="width:${pct}%"></div></div>
          <span class="bar-value">${value}</span>
        </div>
      `;
    }).join('');
  }

  function renderRecentScreenings(screenings) {
    const container = el('recent-screenings');
    if (!container) return;
    if (!screenings.length) {
      container.innerHTML = '<p class="text-muted">No screenings yet.</p>';
      return;
    }
    container.innerHTML = screenings.map((s) => `
      <div class="recent-item" data-id="${s.id}">
        <div class="recent-meta">
          <span class="recent-id">${escapeHtml(s.transaction_id || 'Unknown')}</span>
          <span class="recent-date">${formatDate(s.created_at)}</span>
        </div>
        ${pill(s.classification)}
      </div>
    `).join('');

    container.querySelectorAll('.recent-item').forEach((item) => {
      item.addEventListener('click', () => openScreeningDetail(item.dataset.id));
    });
  }

  // --- Screenings ----------------------------------------------------------

  async function loadScreenings() {
    const data = await apiCall('/api/screenings');
    if (data.error) return showToast(data.error, 'error');
    allScreenings = data.screenings || [];
    renderScreenings(allScreenings);
  }

  function renderScreenings(screenings) {
    const tbody = el('screenings-body');
    if (!tbody) return;
    if (!screenings.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">No screenings found.</td></tr>';
      return;
    }
    tbody.innerHTML = screenings.map((s) => `
      <tr data-id="${s.id}">
        <td><code>${escapeHtml(s.id).slice(0, 8)}</code></td>
        <td>${escapeHtml(s.transaction_id || 'Unknown')}</td>
        <td>${Number(s.deterministic_score).toFixed(3)}</td>
        <td>${Number(s.final_score).toFixed(3)}</td>
        <td>${pill(s.classification)}</td>
        <td>${formatDate(s.created_at)}</td>
        <td><button class="btn btn-secondary btn-sm view-btn">View</button></td>
      </tr>
    `).join('');

    tbody.querySelectorAll('.view-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.target.closest('tr').dataset.id;
        openScreeningDetail(id);
      });
    });
  }

  el('screenings-filter')?.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = allScreenings.filter((s) =>
      (s.transaction_id || '').toLowerCase().includes(term)
    );
    renderScreenings(filtered);
  });

  // --- Cases ---------------------------------------------------------------

  async function loadCases() {
    const data = await apiCall('/api/cases');
    if (data.error) return showToast(data.error, 'error');
    allCases = data.cases || [];
    renderCases(allCases);
  }

  function renderCases(cases) {
    const tbody = el('cases-body');
    if (!tbody) return;
    if (!cases.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">No cases found.</td></tr>';
      return;
    }
    tbody.innerHTML = cases.map((c) => {
      const screening = c.screenings || {};
      return `
        <tr data-id="${c.id}">
          <td><code>${escapeHtml(c.id).slice(0, 8)}</code></td>
          <td>${escapeHtml(screening.transaction_id || c.screening_id || 'Unknown')}</td>
          <td><span class="pill">${escapeHtml(c.status)}</span></td>
          <td>${escapeHtml((c.notes || '').slice(0, 60))}</td>
          <td>${formatDate(c.created_at)}</td>
          <td>
            <select class="case-status-select btn btn-secondary btn-sm" data-id="${c.id}">
              <option value="open" ${c.status === 'open' ? 'selected' : ''}>Open</option>
              <option value="in_review" ${c.status === 'in_review' ? 'selected' : ''}>In review</option>
              <option value="resolved" ${c.status === 'resolved' ? 'selected' : ''}>Resolved</option>
              <option value="closed" ${c.status === 'closed' ? 'selected' : ''}>Closed</option>
            </select>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.case-status-select').forEach((sel) => {
      sel.addEventListener('change', async (e) => {
        const id = e.target.dataset.id;
        const res = await apiCall(`/api/cases/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: e.target.value }),
        });
        if (res.error) showToast(res.error, 'error');
        else showToast('Case updated', 'success');
      });
    });
  }

  el('cases-status-filter')?.addEventListener('change', (e) => {
    const status = e.target.value;
    const filtered = status ? allCases.filter((c) => c.status === status) : allCases;
    renderCases(filtered);
  });

  // --- Batches -------------------------------------------------------------

  async function loadBatches() {
    const data = await apiCall('/api/screen/batches');
    if (data.error) return showToast(data.error, 'error');
    renderBatches(data.batches || []);
  }

  function renderBatches(batches) {
    const tbody = el('batches-body');
    if (!tbody) return;
    if (!batches.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">No batch jobs found.</td></tr>';
      return;
    }
    tbody.innerHTML = batches.map((b) => {
      const pct = b.total ? Math.round((b.processed / b.total) * 100) : 0;
      return `
        <tr data-id="${b.id}">
          <td><code>${escapeHtml(b.id).slice(0, 8)}</code></td>
          <td>${pillStatus(b.status)}</td>
          <td>
            <div class="progress-bar" style="width:140px"><div class="progress-fill" style="width:${pct}%"></div></div>
            <span class="text-muted" style="font-size:0.75rem">${pct}%</span>
          </td>
          <td>${b.succeeded}</td>
          <td>${b.failed}</td>
          <td>${formatDate(b.created_at)}</td>
        </tr>
      `;
    }).join('');
  }

  el('batches-refresh')?.addEventListener('click', loadBatches);

  // --- Screening forms -----------------------------------------------------

  function bindForms() {
    const singleForm = el('single-form');
    singleForm?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const resultBox = el('single-result');
      resultBox.classList.remove('hidden');
      resultBox.innerHTML = '<p class="text-muted">Screening...</p>';
      const payload = formToObject(singleForm);
      const result = await apiCall('/api/screen/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      renderResult(resultBox, result);
    });

    const batchForm = el('batch-form');
    batchForm?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const resultBox = el('batch-result');
      const progress = el('batch-progress');
      const fill = el('batch-progress-fill');
      const text = el('batch-progress-text');

      resultBox.classList.remove('hidden');
      resultBox.innerHTML = '<p class="text-muted">Uploading...</p>';
      const asyncMode = el('batch-async')?.checked;
      const formData = new FormData(batchForm);

      const result = await apiCall(`/api/screen/batch?async=${asyncMode}`, {
        method: 'POST',
        body: formData,
      });
      renderResult(resultBox, result);

      if (asyncMode && result.batch_id) {
        progress?.classList.remove('hidden');
        pollBatch(result.batch_id, progress, fill, text);
      }
    });

    const loadSample = el('load-sample');
    const screenSample = el('screen-sample');
    const sampleResult = el('sample-result');
    let sampleRecords = [];

    loadSample?.addEventListener('click', async () => {
      sampleResult.classList.remove('hidden');
      sampleResult.innerHTML = 'Loading sample...';
      const data = await apiCall('/api/import/sample');
      if (data.error) {
        sampleResult.textContent = data.error;
        return;
      }
      sampleRecords = data.records || [];
      sampleResult.innerHTML = `<p class="text-muted">Loaded ${sampleRecords.length} sample transactions.</p><pre>${escapeHtml(JSON.stringify(sampleRecords, null, 2))}</pre>`;
      screenSample.disabled = sampleRecords.length === 0;
    });

    screenSample?.addEventListener('click', async () => {
      if (!sampleRecords.length) return;
      sampleResult.innerHTML = '<p class="text-muted">Screening sample...</p>';
      const result = await apiCall('/api/screen/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sampleRecords),
      });
      renderResult(sampleResult, result);
    });
  }

  async function pollBatch(batchId, progressEl, fillEl, textEl) {
    const interval = setInterval(async () => {
      const data = await apiCall(`/api/screen/batch/${batchId}`);
      if (data.error) {
        clearInterval(interval);
        progressEl?.classList.add('hidden');
        return showToast(data.error, 'error');
      }

      const pct = data.total ? Math.round((data.processed / data.total) * 100) : 0;
      if (fillEl) fillEl.style.width = `${pct}%`;
      if (textEl) textEl.textContent = `${pct}% (${data.processed}/${data.total})`;

      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(interval);
        showToast(`Batch ${data.status} (${data.succeeded} succeeded, ${data.failed} failed)`, data.status === 'completed' ? 'success' : 'error');
      }
    }, 1500);
  }

  function formToObject(form) {
    const data = new FormData(form);
    const obj = {};
    for (const [key, value] of data.entries()) obj[key] = value;
    return obj;
  }

  function renderResult(element, result) {
    const status = result._status >= 400 ? 'error' : 'success';
    element.innerHTML = `<pre class="${status}">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
  }

  // --- Modal ---------------------------------------------------------------

  function bindModal() {
    el('modal-close')?.addEventListener('click', closeModal);
    document.querySelector('.modal-backdrop')?.addEventListener('click', closeModal);
    el('create-case-btn')?.addEventListener('click', async () => {
      if (!currentScreening) return;
      const res = await apiCall('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screening_id: currentScreening.id, notes: 'Created from dashboard' }),
      });
      if (res.error) showToast(res.error, 'error');
      else {
        showToast('Case created', 'success');
        closeModal();
      }
    });
  }

  async function openScreeningDetail(id) {
    const data = await apiCall(`/api/screenings/${id}`);
    if (data.error) return showToast(data.error, 'error');
    currentScreening = data;
    el('modal-title').textContent = `Screening: ${data.transaction_id || id}`;

    const tx = data.transaction_data || {};
    const gemini = data.gemini_result || {};
    const rules = data.rules || [];
    const hits = data.sanctions_hits || [];

    el('modal-body').innerHTML = `
      <div class="detail-section">
        <h4>Scores</h4>
        <p><span class="score-pill ${scoreClass(data.deterministic_score)}">Deterministic: ${Number(data.deterministic_score).toFixed(3)}</span></p>
        <p><span class="score-pill ${scoreClass(data.final_score)}">Final: ${Number(data.final_score).toFixed(3)}</span></p>
        <p><strong>Classification:</strong> ${pill(data.classification)}</p>
      </div>
      <div class="detail-section">
        <h4>Transaction</h4>
        <p><strong>ID:</strong> ${escapeHtml(tx.transactionId || 'N/A')}</p>
        <p><strong>Amount:</strong> ${tx.amount || 0} ${escapeHtml(tx.currency || '')}</p>
        <p><strong>Sender:</strong> ${escapeHtml(tx.senderName || '')} (${escapeHtml(tx.senderCountry || '')})</p>
        <p><strong>Receiver:</strong> ${escapeHtml(tx.receiverName || '')} (${escapeHtml(tx.receiverCountry || '')})</p>
      </div>
      <div class="detail-section">
        <h4>Rules triggered</h4>
        ${rules.length ? '<ul>' + rules.map((r) => `<li>${escapeHtml(r.rule)} (+${r.weight}) → ${r.cumulative_score}</li>`).join('') + '</ul>' : '<p class="text-muted">None</p>'}
      </div>
      <div class="detail-section">
        <h4>Sanctions hits</h4>
        ${hits.length ? '<ul>' + hits.map((h) => `<li>${escapeHtml(h.list)} — ${escapeHtml(h.entity_id)}</li>`).join('') + '</ul>' : '<p class="text-muted">None</p>'}
      </div>
      ${gemini.reasoning ? `
        <div class="detail-section">
          <h4>Gemini reasoning</h4>
          <p>${escapeHtml(gemini.reasoning)}</p>
          <p><strong>Confidence:</strong> ${gemini.confidence || 'N/A'}</p>
          <p><strong>False positive assessment:</strong> ${escapeHtml(gemini.false_positive_assessment || 'N/A')}</p>
        </div>
      ` : ''}
    `;

    el('detail-modal').classList.remove('hidden');
  }

  function closeModal() {
    el('detail-modal')?.classList.add('hidden');
    currentScreening = null;
  }

  // --- Utilities -----------------------------------------------------------

  function pill(classification) {
    if (!classification) return '<span class="pill">Unknown</span>';
    let cls = 'pill-low';
    if (classification.includes('High')) cls = 'pill-high';
    else if (classification.includes('Medium')) cls = 'pill-medium';
    return `<span class="pill ${cls}">${escapeHtml(classification)}</span>`;
  }

  function pillStatus(status) {
    const map = {
      completed: 'pill-low',
      running: 'pill-medium',
      pending: 'pill-medium',
      failed: 'pill-high',
    };
    return `<span class="pill ${map[status] || ''}">${escapeHtml(status)}</span>`;
  }

  function scoreClass(score) {
    if (score > 0.85) return 'pill-high';
    if (score >= 0.5) return 'pill-medium';
    return 'pill-low';
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDate(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return isNaN(d) ? '–' : d.toLocaleString();
  }

  init();
})();
