/* FinAtlas frontend SPA — Phase 4 (UI, public APIs, Supabase Auth + MFA) */

(function () {
  'use strict';

  const env = window.__ENV__ || {};
  let supabase = null;
  let session = null;
  let devMode = false;
  let currentScreening = null;
  let allScreenings = [];
  let allCases = [];
  let lastProcessedAccessToken = null;

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
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });

    bindAuth();
    bindNavigation();
    bindForms();
    bindModal();
    bindMobileMenu();

    // Handle both redirect-after-confirmation and ordinary sign-ins.
    supabase.auth.onAuthStateChange((event, newSession) => {
      if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
        if (newSession) {
          session = newSession;
          onSessionReady();
        }
      }
      if (event === 'TOKEN_REFRESHED') {
        session = newSession || session;
      }
      if (event === 'SIGNED_OUT') {
        session = null;
        devMode = false;
        lastProcessedAccessToken = null;
        showAuth();
      }
    });

    supabase.auth.getSession().then(({ data, error }) => {
      if (error) {
        showToast(error.message, 'error');
        showAuth();
        return;
      }
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

  function showAuth(message) {
    el('sidebar')?.classList.add('hidden');
    el('main')?.classList.remove('hidden');
    const skipBtn = el('dev-skip-btn');
    if (skipBtn) skipBtn.classList.toggle('hidden', env.requireAuth);
    const notice = el('auth-notice');
    if (notice && message) {
      notice.textContent = message;
      notice.classList.remove('hidden');
    } else if (notice) {
      notice.classList.add('hidden');
    }
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
    const mfaBadge = el('mfa-badge');
    mfaBadge.classList.add('verified');
    mfaBadge.textContent = 'No auth';
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
        el('auth-notice')?.classList.add('hidden');
      });
    });

    el('signin-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector('button[type="submit"]');
      setLoading(btn, true);
      const data = new FormData(e.target);
      try {
        const { error } = await supabase.auth.signInWithPassword({
          email: data.get('email'),
          password: data.get('password'),
        });
        if (error) {
          showToast(error.message, 'error');
          return;
        }
        const { data: sessionData } = await supabase.auth.getSession();
        session = sessionData.session;
        await onSessionReady();
      } catch (err) {
        showToast(err.message || 'Sign in failed', 'error');
      } finally {
        setLoading(btn, false);
      }
    });

    el('signup-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector('button[type="submit"]');
      setLoading(btn, true);
      const data = new FormData(e.target);
      try {
        const { error } = await supabase.auth.signUp({
          email: data.get('email'),
          password: data.get('password'),
          options: {
            emailRedirectTo: window.location.origin,
          },
        });
        if (error) {
          showToast(error.message, 'error');
          return;
        }
        showToast(
          'Account created. Check your inbox and click the confirmation link, then sign in.',
          'success'
        );
        document.querySelector('[data-tab="signin"]')?.click();
      } catch (err) {
        showToast(err.message || 'Sign up failed', 'error');
      } finally {
        setLoading(btn, false);
      }
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
    // Avoid processing the same access token twice (e.g. getSession + onAuthStateChange race).
    if (session.access_token === lastProcessedAccessToken) return;
    lastProcessedAccessToken = session.access_token;

    el('user-email').textContent = session.user.email || 'Investigator';

    if (!env.requireMfa) {
      await completeSignIn();
      return;
    }

    const aal = decodeAal(session.access_token);
    if (aal === 'aal2') {
      await completeSignIn();
      return;
    }

    // AAL1 and MFA is required — either enrol a new factor or challenge an existing one.
    try {
      const prepared = await prepareMfaStep();
      if (prepared.type === 'challenge') {
        await challengeMfa(prepared.factorId);
      } else {
        await enrollMfa();
      }
    } catch (err) {
      showToast(err.message || 'MFA setup failed. Please sign in again.', 'error');
      await supabase.auth.signOut();
      session = null;
      showAuth();
    }
  }

  async function prepareMfaStep() {
    const { data: factorsData, error } = await supabase.auth.mfa.listFactors();
    if (error) throw error;

    const allTotp = factorsData.totp || [];
    const verified = allTotp.filter((f) => f.status === 'verified');
    const unverified = allTotp.filter((f) => f.status === 'unverified');

    if (verified.length > 0) {
      return { type: 'challenge', factorId: verified[0].id };
    }

    // Supabase free tier allows only one TOTP factor per user. Remove stale
    // unverified factors (e.g. from an interrupted enrolment) before enrolling.
    for (const factor of unverified) {
      try {
        await supabase.auth.mfa.unenroll({ factorId: factor.id });
      } catch (err) {
        // If unenroll is not permitted, continue and let enrol fail cleanly.
        console.warn('Could not unenroll stale MFA factor:', err);
      }
    }

    return { type: 'enroll' };
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
    if (error) {
      // If a factor already exists, challenge instead of failing.
      if (error.message && error.message.toLowerCase().includes('already exists')) {
        const prepared = await prepareMfaStep();
        if (prepared.type === 'challenge') {
          await challengeMfa(prepared.factorId);
          return;
        }
        throw new Error('A stale unverified MFA factor exists. Please sign out and sign in again, or contact an administrator.');
      }
      throw error;
    }

    el('mfa-factor-id').value = data.id;
    const qrContainer = el('mfa-qr');
    if (qrContainer) {
      qrContainer.innerHTML = `<div class="qr-wrap">${data.totp.qr_code}</div>`;
    }
    showView('mfa');
  }

  async function verifyMfaEnrollment(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    try {
      const factorId = el('mfa-factor-id').value;
      const code = el('mfa-code').value;
      await verifyMfaCode(factorId, code);
      showToast('MFA enabled successfully', 'success');
      await onSessionReady();
    } catch (err) {
      showToast(err.message || 'Invalid MFA code', 'error');
    } finally {
      setLoading(btn, false);
    }
  }

  async function challengeMfa(factorId) {
    el('mfa-challenge-factor-id').value = factorId;
    showView('mfaChallenge');
  }

  async function verifyMfaChallenge(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    try {
      const factorId = el('mfa-challenge-factor-id').value;
      const code = el('mfa-challenge-code').value;
      await verifyMfaCode(factorId, code);
      showToast('Signed in with MFA', 'success');
      await onSessionReady();
    } catch (err) {
      showToast(err.message || 'Invalid MFA code', 'error');
    } finally {
      setLoading(btn, false);
    }
  }

  async function verifyMfaCode(factorId, code) {
    const { data: challenge, error: challengeError } = await supabase.auth.mfa.challenge({ factorId });
    if (challengeError) throw challengeError;

    const { data: verifyData, error: verifyError } = await supabase.auth.mfa.verify({
      factorId,
      challengeId: challenge.id,
      code,
    });
    if (verifyError) throw verifyError;

    session = (verifyData && verifyData.session) || (await supabase.auth.getSession()).data.session;
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
    setTimeout(() => toast.classList.remove('show'), 5000);
  }

  function setLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
      button.disabled = true;
      button.dataset.originalText = button.dataset.originalText || button.innerHTML;
      button.innerHTML = '<span class="spinner"></span> ' + button.textContent.trim();
    } else {
      button.disabled = false;
      button.innerHTML = button.dataset.originalText || button.innerHTML.replace(/^<span class="spinner"><\/span>\s*/, '');
      delete button.dataset.originalText;
    }
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
    renderDisagreements(stats.disagreement_screenings || [], stats.total_screenings || 0);

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

  function classifyLabel(score) {
    const n = Number(score) || 0;
    if (n > 0.85) return 'Definite Match / High Risk';
    if (n >= 0.5) return 'Potential Match / Medium Risk';
    return 'No Match / Low Risk';
  }

  function renderDisagreements(screenings, total) {
    const container = el('disagreement-list');
    if (!container) return;
    if (!screenings.length) {
      container.innerHTML = '<p class="text-muted">No alert disagreements found.</p>';
      return;
    }
    container.innerHTML = screenings.map((s) => {
      const detClass = classifyLabel(s.deterministic_score);
      const finalClass = classifyLabel(s.final_score);
      const reasoning = (s.gemini_result && s.gemini_result.reasoning) || 'No explanation available.';
      return `
        <div class="disagreement-item" data-id="${s.id}">
          <div class="disagreement-header">
            <div class="disagreement-meta">
              <span class="recent-id">${escapeHtml(s.transaction_id || 'Unknown')}</span>
              <span class="text-muted">${formatDate(s.created_at)}</span>
            </div>
            <div class="disagreement-shift">${pill(detClass)} <span class="text-muted">→</span> ${pill(finalClass)}</div>
          </div>
          <p class="disagreement-reason">${escapeHtml(reasoning)}</p>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.disagreement-item').forEach((item) => {
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
          <td>${caseStatusPill(c.status)}</td>
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
      const btn = e.target.querySelector('button[type="submit"]');
      setLoading(btn, true);
      const resultBox = el('single-result');
      resultBox.classList.remove('hidden');
      resultBox.innerHTML = '<p class="text-muted">Screening...</p>';
      try {
        const payload = formToObject(singleForm);
        const result = await apiCall('/api/screen/single', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        renderResult(resultBox, result);
      } catch (err) {
        resultBox.innerHTML = `<pre class="error">${escapeHtml(err.message)}</pre>`;
      } finally {
        setLoading(btn, false);
      }
    });

    const batchForm = el('batch-form');
    batchForm?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector('button[type="submit"]');
      setLoading(btn, true);
      const resultBox = el('batch-result');
      const progress = el('batch-progress');
      const fill = el('batch-progress-fill');
      const text = el('batch-progress-text');

      resultBox.classList.remove('hidden');
      resultBox.innerHTML = '<p class="text-muted">Uploading...</p>';
      try {
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
      } catch (err) {
        resultBox.innerHTML = `<pre class="error">${escapeHtml(err.message)}</pre>`;
      } finally {
        setLoading(btn, false);
      }
    });

    const loadSample = el('load-sample');
    const screenSample = el('screen-sample');
    const sampleResult = el('sample-result');
    let sampleRecords = [];

    loadSample?.addEventListener('click', async () => {
      const btn = loadSample;
      setLoading(btn, true);
      sampleResult.classList.remove('hidden');
      sampleResult.innerHTML = 'Loading sample...';
      try {
        const data = await apiCall('/api/import/sample');
        if (data.error) {
          sampleResult.innerHTML = `<pre class="error">${escapeHtml(data.error)}</pre>`;
          return;
        }
        sampleRecords = data.records || [];
        sampleResult.innerHTML = `<p class="text-muted">Loaded ${sampleRecords.length} sample transactions.</p><pre>${escapeHtml(JSON.stringify(sampleRecords, null, 2))}</pre>`;
        screenSample.disabled = sampleRecords.length === 0;
      } catch (err) {
        sampleResult.innerHTML = `<pre class="error">${escapeHtml(err.message)}</pre>`;
      } finally {
        setLoading(btn, false);
      }
    });

    screenSample?.addEventListener('click', async () => {
      if (!sampleRecords.length) return;
      const btn = screenSample;
      setLoading(btn, true);
      sampleResult.innerHTML = '<p class="text-muted">Screening sample...</p>';
      try {
        const result = await apiCall('/api/screen/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sampleRecords),
        });
        renderResult(sampleResult, result);
      } catch (err) {
        sampleResult.innerHTML = `<pre class="error">${escapeHtml(err.message)}</pre>`;
      } finally {
        setLoading(btn, false);
      }
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
      const btn = el('create-case-btn');
      setLoading(btn, true);
      try {
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
      } finally {
        setLoading(btn, false);
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

  function caseStatusPill(status) {
    const map = {
      open: 'pill-high',
      in_review: 'pill-medium',
      resolved: 'pill-low',
      closed: '',
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
