/* FinAtlas vanilla JS SPA
 * Handles Supabase Auth + MFA, dashboard navigation, screenings, cases and batches.
 */

const env = window.__ENV__ || {};
let supabaseClient = null;
let session = null;
let lastProcessedAccessToken = null;
let currentScreeningId = null;
let sampleRecords = [];
let allScreenings = [];
let allCases = [];

function el(id) {
  return document.getElementById(id);
}

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function initSupabase() {
  const url = env.supabaseUrl || window.localStorage.getItem('sb_url');
  const key = env.supabaseKey || window.localStorage.getItem('sb_key');
  if (!url || !key) {
    console.warn('Supabase URL/key missing');
    return null;
  }
  if (window.supabase && window.supabase.createClient) {
    return window.supabase.createClient(url, key, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    });
  }
  if (typeof createClient !== 'undefined') {
    return createClient(url, key, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    });
  }
  console.warn('Supabase client library not loaded');
  return null;
}

function decodeAal(token) {
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4);
    const json = JSON.parse(atob(padded.replace(/-/g, '+').replace(/_/g, '/')));
    return json.aal || null;
  } catch (e) {
    return null;
  }
}

function showToast(message, type = 'info') {
  const toast = el('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 4000);
}

function setLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
  const original = button.dataset.originalHtml;
  if (loading) {
    if (!button.dataset.originalHtml) button.dataset.originalHtml = button.innerHTML;
    button.innerHTML = '<span class="spinner"></span> Please wait...';
  } else if (original) {
    button.innerHTML = original;
  }
}

function showElement(idOrEl, show) {
  const element = typeof idOrEl === 'string' ? el(idOrEl) : idOrEl;
  if (!element) return;
  if (show) element.classList.remove('hidden');
  else element.classList.add('hidden');
}

function showView(viewName) {
  qsa('.view').forEach((v) => v.classList.add('hidden'));
  const target = el(`${viewName}-view`);
  if (target) target.classList.remove('hidden');

  qsa('.nav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.view === viewName);
  });

  const titles = {
    dashboard: 'Dashboard',
    screenings: 'Screenings',
    cases: 'Cases',
    batches: 'Batches',
    screen: 'New Screening',
    api: 'API Reference',
    auth: 'Sign in',
    mfa: 'MFA Setup',
    'mfa-challenge': 'MFA Challenge',
    'mfa-error': 'MFA Setup',
  };
  const titleEl = el('page-title');
  if (titleEl) titleEl.textContent = titles[viewName] || 'FinAtlas';

  if (viewName === 'dashboard') loadDashboard();
  if (viewName === 'screenings') loadScreenings();
  if (viewName === 'cases') loadCases();
  if (viewName === 'batches') loadBatches();
}

function showAuth() {
  showElement('sidebar', false);
  const main = el('main');
  if (main) {
    main.classList.remove('hidden');
    main.classList.add('auth-mode');
  }
  showView('auth');
}

function showAuthFlowView(viewName) {
  showElement('sidebar', false);
  const main = el('main');
  if (main) {
    main.classList.remove('hidden');
    main.classList.add('auth-mode');
  }
  showView(viewName);
}

function showApp() {
  showElement('sidebar', true);
  const main = el('main');
  if (main) {
    main.classList.remove('hidden', 'auth-mode');
  }
  showView('dashboard');
}

async function completeSignIn() {
  showApp();
  await loadDashboard();
}

async function onSessionReady() {
  if (!session) {
    showAuth();
    return;
  }

  if (session.access_token === lastProcessedAccessToken) return;
  lastProcessedAccessToken = session.access_token;

  const userEmail = session.user?.email || 'Investigator';
  const userEmailEl = el('user-email');
  if (userEmailEl) userEmailEl.textContent = userEmail;

  if (!env.requireAuth || !env.requireMfa) {
    await completeSignIn();
    return;
  }

  const aal = decodeAal(session.access_token);
  if (aal === 'aal2') {
    updateMfaBadge(true);
    await completeSignIn();
    return;
  }

  try {
    const prepared = await prepareMfaStep();
    if (prepared.type === 'challenge') {
      await challengeMfa(prepared.factorId);
    } else {
      await enrollMfa();
    }
  } catch (err) {
    console.error('MFA flow failed:', err);
    lastProcessedAccessToken = null;
    showMfaError(err);
  }
}

function showMfaError(error) {
  const message = error?.message || 'MFA setup failed. Please try again.';
  const errorMessage = el('mfa-error-message');
  if (errorMessage) errorMessage.textContent = message;
  showAuthFlowView('mfa-error');
}

async function retryMfaSetup() {
  lastProcessedAccessToken = null;
  await onSessionReady();
}

function updateMfaBadge(verified) {
  const badge = el('mfa-badge');
  if (!badge) return;
  badge.textContent = verified ? 'MFA On' : 'MFA';
  badge.classList.toggle('verified', verified);
}

async function cleanupStaleMfaFactors() {
  const { data, error } = await supabaseClient.auth.mfa.listFactors();
  if (error) throw error;

  const unverified = (data?.totp || []).filter((f) => f.status === 'unverified');
  for (const factor of unverified) {
    const { error: unenrollError } = await supabaseClient.auth.mfa.unenroll({
      factorId: factor.id,
    });
    if (unenrollError) {
      throw new Error(
        `Could not remove the unfinished MFA setup (${unenrollError.message}). Retry MFA setup or sign out and contact support.`
      );
    }
    console.info('Removed stale unverified MFA factor:', factor.id);
  }
}

async function prepareMfaStep() {
  const { data: factorsData, error } = await supabaseClient.auth.mfa.listFactors();
  if (error) throw error;

  const allTotp = factorsData.totp || [];
  const verified = allTotp.filter((f) => f.status === 'verified');

  if (verified.length > 0) {
    return { type: 'challenge', factorId: verified[0].id };
  }

  await cleanupStaleMfaFactors();

  const { data: refreshedFactors, error: refreshedError } = await supabaseClient.auth.mfa.listFactors();
  if (refreshedError) throw refreshedError;

  const remainingVerified = (refreshedFactors?.totp || []).filter((f) => f.status === 'verified');
  if (remainingVerified.length > 0) {
    return { type: 'challenge', factorId: remainingVerified[0].id };
  }

  return { type: 'enroll' };
}

async function enrollMfa() {
  let { data, error } = await supabaseClient.auth.mfa.enroll({ factorType: 'totp' });
  if (error && isExistingMfaFactorError(error)) {
    await cleanupStaleMfaFactors();
    const prepared = await prepareMfaStep();
    if (prepared.type === 'challenge') {
      await challengeMfa(prepared.factorId);
      return;
    }
    ({ data, error } = await supabaseClient.auth.mfa.enroll({ factorType: 'totp' }));
  }
  if (error) throw error;
  renderMfaQr(data);
}

function isExistingMfaFactorError(error) {
  const message = (error?.message || '').toLowerCase();
  return (
    message.includes('already exists') ||
    message.includes('unverified') ||
    /factor.{0,30}(exists|already)/.test(message) ||
    /already.{0,30}factor/.test(message)
  );
}

function renderMfaQr(data) {
  el('mfa-factor-id').value = data.id;
  const qrContainer = el('mfa-qr');
  if (qrContainer && data.totp?.qr_code) {
    qrContainer.innerHTML = `<div class="qr-wrap">${data.totp.qr_code}</div>`;
  }
  showAuthFlowView('mfa');
}

async function challengeMfa(factorId) {
  el('mfa-challenge-factor-id').value = factorId;
  showAuthFlowView('mfa-challenge');
}

async function verifyMfaEnrollment(event) {
  event.preventDefault();
  const btn = event.submitter;
  setLoading(btn, true);

  try {
    const factorId = el('mfa-factor-id').value;
    const code = el('mfa-code').value.trim();
    const { data, error } = await supabaseClient.auth.mfa.challengeAndVerify({
      factorId,
      code,
    });
    if (error) throw error;

    updateMfaBadge(true);
    await completeSignIn();
  } catch (err) {
    console.error('MFA verify failed:', err);
    showToast(err.message || 'Invalid MFA code. Please try again.', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function verifyMfaChallenge(event) {
  event.preventDefault();
  const btn = event.submitter;
  setLoading(btn, true);

  try {
    const factorId = el('mfa-challenge-factor-id').value;
    const code = el('mfa-challenge-code').value.trim();
    const { data: challenge, error: challengeError } = await supabaseClient.auth.mfa.challenge({
      factorId,
    });
    if (challengeError) throw challengeError;

    const { data, error } = await supabaseClient.auth.mfa.verify({
      factorId,
      challengeId: challenge.id,
      code,
    });
    if (error) throw error;

    updateMfaBadge(true);
    await completeSignIn();
  } catch (err) {
    console.error('MFA challenge failed:', err);
    showToast(err.message || 'Invalid MFA code. Please try again.', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function handleSignIn(event) {
  event.preventDefault();
  const form = event.target;
  const btn = event.submitter;
  setLoading(btn, true);

  try {
    const email = form.email.value.trim();
    const password = form.password.value;
    const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) throw error;

    session = data.session;
    await onSessionReady();
  } catch (err) {
    console.error('Sign in failed:', err);
    showToast(err.message || 'Sign in failed. Check your email and password.', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function handleSignUp(event) {
  event.preventDefault();
  const form = event.target;
  const btn = event.submitter;
  setLoading(btn, true);

  try {
    const email = form.email.value.trim();
    const password = form.password.value;
    const { data, error } = await supabaseClient.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: window.location.origin,
      },
    });
    if (error) throw error;

    const notice = el('auth-notice');
    if (data.session) {
      session = data.session;
      notice.textContent = 'Account created. Please check your email to confirm your address, then set up MFA.';
      notice.classList.remove('hidden');
      await onSessionReady();
    } else {
      notice.textContent = 'Confirmation email sent. Please check your inbox and click the link before signing in.';
      notice.classList.remove('hidden');
    }
  } catch (err) {
    console.error('Sign up failed:', err);
    showToast(err.message || 'Sign up failed. Please try again.', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function handleSignOut() {
  await supabaseClient.auth.signOut();
  session = null;
  lastProcessedAccessToken = null;
  showAuth();
}

function devSkipAuth() {
  env.requireAuth = false;
  env.requireMfa = false;
  completeSignIn();
}

function switchTab(tabName) {
  qsa('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === tabName));
  showElement('signin-form', tabName === 'signin');
  showElement('signup-form', tabName === 'signup');
  const notice = el('auth-notice');
  if (notice) notice.classList.add('hidden');
}

function authHeader() {
  if (session?.access_token) return { Authorization: `Bearer ${session.access_token}` };
  return {};
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...authHeader(),
      ...(options.headers || {}),
    },
  });
  return response;
}

function formatDate(iso) {
  if (!iso) return '–';
  return new Date(iso).toLocaleString();
}

function classificationPill(classification) {
  const text = classification || 'Unknown';
  let cls = 'pill-low';
  if (text.includes('High')) cls = 'pill-high';
  else if (text.includes('Medium')) cls = 'pill-medium';
  return `<span class="pill ${cls}">${text}</span>`;
}

async function loadDashboard() {
  try {
    const response = await apiFetch('/api/screenings/stats');
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      showToast(data.error || 'Failed to load dashboard stats', 'error');
      return;
    }
    const data = await response.json();
    renderDashboard(data);
  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Failed to load dashboard', 'error');
  }
}

function renderDashboard(data) {
  const dist = data.risk_distribution || {};
  const high = dist['Definite Match / High Risk'] || 0;
  const medium = dist['Potential Match / Medium Risk'] || 0;
  const low = dist['No Match / Low Risk'] || 0;
  const total = data.total_screenings || 0;

  el('kpi-total').textContent = total;
  el('kpi-high').textContent = high;
  el('kpi-medium').textContent = medium;
  el('kpi-low').textContent = low;
  el('kpi-cases').textContent = data.open_cases || 0;
  el('kpi-disagreements').textContent = data.alert_disagreements || 0;

  renderRiskChart(dist, total);
  renderRecentScreenings(data.recent_screenings || []);
  renderDisagreements(data.disagreement_screenings || [], data.alert_disagreements || 0);
}

function renderRiskChart(dist, total) {
  const container = el('risk-chart');
  if (!container) return;
  if (total === 0) {
    container.innerHTML = '<p class="text-muted">No screenings yet.</p>';
    return;
  }

  const rows = [
    { label: 'High Risk', key: 'Definite Match / High Risk', cls: 'high' },
    { label: 'Medium Risk', key: 'Potential Match / Medium Risk', cls: 'medium' },
    { label: 'Low Risk', key: 'No Match / Low Risk', cls: 'low' },
  ];

  container.innerHTML = rows
    .map((row) => {
      const value = dist[row.key] || 0;
      const pct = total ? Math.round((value / total) * 100) : 0;
      return `
        <div class="bar-row">
          <span class="bar-label">${row.label}</span>
          <div class="bar-track"><div class="bar-fill ${row.cls}" style="width: ${pct}%"></div></div>
          <span class="bar-value">${value}</span>
        </div>
      `;
    })
    .join('');
}

function renderRecentScreenings(screenings) {
  const container = el('recent-screenings');
  if (!container) return;
  if (!screenings.length) {
    container.innerHTML = '<p class="text-muted">No screenings yet.</p>';
    return;
  }

  container.innerHTML = screenings
    .map((s) => {
      const tx = s.transaction_data || {};
      return `
        <div class="recent-item" data-id="${s.id}">
          <div class="recent-meta">
            <span class="recent-id">${tx.transactionId || s.transaction_id || 'N/A'}</span>
            <span class="recent-date">${formatDate(s.created_at)}</span>
          </div>
          ${classificationPill(s.classification)}
        </div>
      `;
    })
    .join('');

  qsa('.recent-item', container).forEach((item) => {
    item.addEventListener('click', () => openScreeningDetail(item.dataset.id));
  });
}

function renderDisagreements(disagreements, count) {
  const summary = el('disagreement-summary');
  const list = el('disagreement-list');
  if (!summary || !list) return;

  if (!count) {
    summary.textContent = 'No alert disagreements found.';
    list.innerHTML = '';
    return;
  }

  summary.textContent = `${count} screening(s) where Gemini disagreed with deterministic classification.`;
  list.innerHTML = disagreements
    .map((s) => {
      const tx = s.transaction_data || {};
      const gemini = s.gemini_result || {};
      return `
        <div class="disagreement-item" data-id="${s.id}">
          <div class="disagreement-header">
            <div class="disagreement-meta">
              <strong>${tx.transactionId || s.transaction_id || 'N/A'}</strong>
              <span class="text-muted">Deterministic: ${Number(s.deterministic_score).toFixed(3)} → Final: ${Number(s.final_score).toFixed(3)}</span>
            </div>
            <div class="disagreement-shift">${classificationPill(s.classification)}</div>
          </div>
          <p class="disagreement-reason">${gemini.reasoning || 'No explanation available.'}</p>
        </div>
      `;
    })
    .join('');

  qsa('.disagreement-item', list).forEach((item) => {
    item.addEventListener('click', () => openScreeningDetail(item.dataset.id));
  });
}

async function loadScreenings() {
  try {
    const response = await apiFetch('/api/screenings');
    if (!response.ok) {
      showToast('Failed to load screenings', 'error');
      return;
    }
    const data = await response.json();
    allScreenings = data.screenings || [];
    renderScreenings();
  } catch (err) {
    console.error('Screenings load error:', err);
    showToast('Failed to load screenings', 'error');
  }
}

function renderScreenings() {
  const tbody = el('screenings-body');
  if (!tbody) return;

  const filter = (el('screenings-filter')?.value || '').toLowerCase();
  const filtered = allScreenings.filter((s) => {
    const tx = s.transaction_data || {};
    const text = `${tx.transactionId || ''} ${s.transaction_id || ''} ${s.classification || ''}`.toLowerCase();
    return text.includes(filter);
  });

  tbody.innerHTML = filtered
    .map((s) => {
      const tx = s.transaction_data || {};
      return `
        <tr data-id="${s.id}">
          <td>${s.id.slice(0, 8)}</td>
          <td>${tx.transactionId || s.transaction_id || 'N/A'}</td>
          <td>${Number(s.deterministic_score).toFixed(3)}</td>
          <td>${Number(s.final_score).toFixed(3)}</td>
          <td>${classificationPill(s.classification)}</td>
          <td>${formatDate(s.created_at)}</td>
          <td><button class="btn btn-sm btn-secondary view-detail">View</button></td>
        </tr>
      `;
    })
    .join('');

  qsa('.view-detail', tbody).forEach((btn) => {
    btn.addEventListener('click', () => openScreeningDetail(btn.closest('tr').dataset.id));
  });
}

async function openScreeningDetail(id) {
  try {
    const response = await apiFetch(`/api/screenings/${id}`);
    if (!response.ok) {
      showToast('Screening not found', 'error');
      return;
    }
    const screening = await response.json();
    currentScreeningId = screening.id;
    renderScreeningDetail(screening);
    showElement('detail-modal', true);
  } catch (err) {
    console.error('Screening detail error:', err);
    showToast('Failed to load screening detail', 'error');
  }
}

function renderScreeningDetail(s) {
  const tx = s.transaction_data || {};
  const gemini = s.gemini_result || {};
  const hits = s.sanctions_hits || [];
  const rules = s.rules || [];

  el('modal-title').textContent = `Screening: ${tx.transactionId || s.transaction_id || 'N/A'}`;

  const hitsHtml = hits.length
    ? `<ul>${hits.map((h) => `<li><strong>${h.list}</strong> — ${h.entity_id} (${h.field})</li>`).join('')}</ul>`
    : '<p class="text-muted">No sanctions hits.</p>';

  const rulesHtml = rules.length
    ? `<ul>${rules.map((r) => `<li>${r.rule.replace(/_/g, ' ')} (+${r.weight}) → ${r.cumulative_score}</li>`).join('')}</ul>`
    : '<p class="text-muted">No deterministic rules triggered.</p>';

  el('modal-body').innerHTML = `
    <div class="detail-section">
      <h4>Transaction</h4>
      <p><strong>Date:</strong> ${tx.transactionDate || '–'}</p>
      <p><strong>Type:</strong> ${tx.transactionType || '–'}</p>
      <p><strong>Amount:</strong> ${tx.amount || 0} ${tx.currency || 'USD'}</p>
      <p><strong>Sender:</strong> ${tx.senderName || '–'} (${tx.senderCountry || '–'})</p>
      <p><strong>Receiver:</strong> ${tx.receiverName || '–'} (${tx.receiverCountry || '–'})</p>
    </div>
    <div class="detail-section">
      <h4>Scores</h4>
      <p><strong>Deterministic:</strong> ${Number(s.deterministic_score).toFixed(3)}</p>
      <p><strong>Final:</strong> <span class="score-pill">${Number(s.final_score).toFixed(3)}</span> ${classificationPill(s.classification)}</p>
      <p><strong>Gemini reviewed:</strong> ${s.gemini_result ? 'Yes' : 'No'}</p>
    </div>
    <div class="detail-section">
      <h4>Deterministic rules</h4>
      ${rulesHtml}
    </div>
    <div class="detail-section">
      <h4>Sanctions hits</h4>
      ${hitsHtml}
    </div>
    ${s.gemini_result ? `
    <div class="detail-section">
      <h4>Gemini reasoning</h4>
      <p>${gemini.reasoning || '–'}</p>
      <p><strong>Confidence:</strong> ${gemini.confidence ?? '–'}</p>
      <p><strong>False positive assessment:</strong> ${gemini.false_positive_assessment || '–'}</p>
    </div>` : ''}
  `;
}

async function createCaseFromModal() {
  if (!currentScreeningId) return;
  try {
    const response = await apiFetch('/api/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ screening_id: currentScreeningId, status: 'open', notes: '' }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      showToast(data.error || 'Failed to create case', 'error');
      return;
    }
    showToast('Case created successfully', 'success');
    showElement('detail-modal', false);
    if (!el('cases-view')?.classList.contains('hidden')) loadCases();
  } catch (err) {
    console.error('Create case error:', err);
    showToast('Failed to create case', 'error');
  }
}

async function loadCases() {
  try {
    const response = await apiFetch('/api/cases');
    if (!response.ok) {
      showToast('Failed to load cases', 'error');
      return;
    }
    const data = await response.json();
    allCases = data.cases || [];
    renderCases();
  } catch (err) {
    console.error('Cases load error:', err);
    showToast('Failed to load cases', 'error');
  }
}

function renderCases() {
  const tbody = el('cases-body');
  if (!tbody) return;

  const filter = el('cases-status-filter')?.value || '';
  const filtered = filter ? allCases.filter((c) => c.status === filter) : allCases;

  tbody.innerHTML = filtered
    .map((c) => {
      const screening = c.screenings || {};
      return `
        <tr data-id="${c.id}">
          <td>${c.id.slice(0, 8)}</td>
          <td>${screening.transaction_id || c.screening_id?.slice(0, 8) || 'N/A'}</td>
          <td><span class="pill ${statusPillClass(c.status)}">${c.status.replace(/_/g, ' ')}</span></td>
          <td>${c.notes || '–'}</td>
          <td>${formatDate(c.created_at)}</td>
          <td>
            <select class="case-status-select" data-id="${c.id}">
              <option value="open" ${c.status === 'open' ? 'selected' : ''}>Open</option>
              <option value="in_review" ${c.status === 'in_review' ? 'selected' : ''}>In review</option>
              <option value="resolved" ${c.status === 'resolved' ? 'selected' : ''}>Resolved</option>
              <option value="closed" ${c.status === 'closed' ? 'selected' : ''}>Closed</option>
            </select>
          </td>
        </tr>
      `;
    })
    .join('');

  qsa('.case-status-select', tbody).forEach((select) => {
    select.addEventListener('change', async (e) => {
      await updateCaseStatus(e.target.dataset.id, e.target.value);
    });
  });
}

function statusPillClass(status) {
  if (status === 'open') return 'pill-high';
  if (status === 'in_review') return 'pill-medium';
  if (status === 'resolved') return 'pill-low';
  return 'pill-low';
}

async function updateCaseStatus(caseId, status) {
  try {
    const response = await apiFetch(`/api/cases/${caseId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) {
      showToast('Failed to update case', 'error');
      loadCases();
      return;
    }
    showToast('Case updated', 'success');
  } catch (err) {
    console.error('Update case error:', err);
    showToast('Failed to update case', 'error');
  }
}

async function loadBatches() {
  try {
    const response = await apiFetch('/api/screen/batches');
    if (!response.ok) {
      showToast('Failed to load batches', 'error');
      return;
    }
    const data = await response.json();
    renderBatches(data.batches || []);
  } catch (err) {
    console.error('Batches load error:', err);
    showToast('Failed to load batches', 'error');
  }
}

function renderBatches(batches) {
  const tbody = el('batches-body');
  if (!tbody) return;

  tbody.innerHTML = batches
    .map((b) => {
      const pct = b.total ? Math.round((b.processed / b.total) * 100) : 0;
      return `
        <tr data-id="${b.id}">
          <td>${b.id.slice(0, 8)}</td>
          <td><span class="pill ${statusPillClass(b.status)}">${b.status}</span></td>
          <td>${b.processed}/${b.total} (${pct}%)</td>
          <td>${b.succeeded}</td>
          <td>${b.failed}</td>
          <td>${formatDate(b.created_at)}</td>
        </tr>
      `;
    })
    .join('');
}

async function handleSingleScreen(event) {
  event.preventDefault();
  const form = event.target;
  const btn = event.submitter;
  setLoading(btn, true);

  try {
    const tx = Object.fromEntries(new FormData(form).entries());
    tx.amount = parseFloat(tx.amount);

    const response = await apiFetch('/api/screen/single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tx),
    });
    const data = await response.json();
    const box = el('single-result');
    box.classList.remove('hidden');
    if (!response.ok) {
      box.innerHTML = `<pre class="error">${data.error || 'Screening failed'}</pre>`;
      return;
    }
    box.innerHTML = `<pre class="success">${JSON.stringify(data, null, 2)}</pre>`;
    loadDashboard();
  } catch (err) {
    console.error('Single screen error:', err);
    showToast('Screening request failed', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function handleBatchScreen(event) {
  event.preventDefault();
  const form = event.target;
  const btn = event.submitter;
  setLoading(btn, true);

  const asyncMode = el('batch-async')?.checked ?? true;
  const formData = new FormData(form);

  try {
    const response = await apiFetch(`/api/screen/batch?async=${asyncMode}`, {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    const box = el('batch-result');
    box.classList.remove('hidden');
    if (!response.ok) {
      box.innerHTML = `<pre class="error">${data.error || 'Batch screening failed'}</pre>`;
      return;
    }

    if (asyncMode && data.batch_id) {
      box.innerHTML = `<pre class="success">Batch accepted: <strong>${data.batch_id}</strong><br>${data.message}</pre>`;
      showElement('batch-progress', true);
      pollBatch(data.batch_id);
    } else {
      box.innerHTML = `<pre class="success">${JSON.stringify(data, null, 2)}</pre>`;
      loadDashboard();
    }
  } catch (err) {
    console.error('Batch screen error:', err);
    showToast('Batch screening request failed', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function pollBatch(batchId) {
  const progressEl = el('batch-progress');
  const fillEl = el('batch-progress-fill');
  const textEl = el('batch-progress-text');

  const interval = setInterval(async () => {
    try {
      const response = await apiFetch(`/api/screen/batch/${batchId}`);
      if (!response.ok) {
        clearInterval(interval);
        return;
      }
      const batch = await response.json();
      const pct = batch.total ? Math.round((batch.processed / batch.total) * 100) : 0;
      fillEl.style.width = `${pct}%`;
      textEl.textContent = `${pct}%`;

      if (['completed', 'failed'].includes(batch.status)) {
        clearInterval(interval);
        showToast(`Batch ${batch.status}`, batch.status === 'completed' ? 'success' : 'error');
        loadBatches();
      }
    } catch (err) {
      console.error('Batch poll error:', err);
      clearInterval(interval);
    }
  }, 2000);
}

async function loadSampleData() {
  try {
    const response = await apiFetch('/api/import/sample');
    if (!response.ok) {
      showToast('Failed to load sample data', 'error');
      return;
    }
    const data = await response.json();
    sampleRecords = data.records || [];
    el('sample-result').classList.remove('hidden');
    el('sample-result').textContent = `${sampleRecords.length} sample records loaded.`;
    el('screen-sample').disabled = sampleRecords.length === 0;
  } catch (err) {
    console.error('Sample load error:', err);
    showToast('Failed to load sample data', 'error');
  }
}

async function screenSampleData() {
  if (!sampleRecords.length) return;
  const btn = el('screen-sample');
  setLoading(btn, true);

  try {
    const response = await apiFetch('/api/screen/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sampleRecords),
    });
    const data = await response.json();
    el('sample-result').textContent = JSON.stringify(data, null, 2);
    loadDashboard();
  } catch (err) {
    console.error('Sample screen error:', err);
    showToast('Sample screening failed', 'error');
  } finally {
    setLoading(btn, false);
  }
}

function setupNavigation() {
  qsa('.nav-link').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      if (view) {
        window.location.hash = view;
        showView(view);
      }
      if (window.innerWidth <= 768) {
        el('sidebar').classList.remove('open');
      }
    });
  });

  el('menu-toggle')?.addEventListener('click', () => {
    el('sidebar').classList.toggle('open');
  });

  el('refresh-btn')?.addEventListener('click', () => {
    const active = qs('.nav-link.active')?.dataset.view || 'dashboard';
    if (active === 'dashboard') loadDashboard();
    if (active === 'screenings') loadScreenings();
    if (active === 'cases') loadCases();
    if (active === 'batches') loadBatches();
  });

  window.addEventListener('hashchange', () => {
    const view = window.location.hash.replace('#', '') || 'dashboard';
    showView(view);
  });
}

function setupAuthForms() {
  el('signin-form')?.addEventListener('submit', handleSignIn);
  el('signup-form')?.addEventListener('submit', handleSignUp);
  el('mfa-form')?.addEventListener('submit', verifyMfaEnrollment);
  el('mfa-challenge-form')?.addEventListener('submit', verifyMfaChallenge);
  el('sign-out-btn')?.addEventListener('click', handleSignOut);
  el('dev-skip-btn')?.addEventListener('click', devSkipAuth);
  el('mfa-retry-btn')?.addEventListener('click', retryMfaSetup);
  el('mfa-error-sign-out-btn')?.addEventListener('click', handleSignOut);

  qsa('.tab').forEach((tab) => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
}

function setupScreeningForms() {
  el('single-form')?.addEventListener('submit', handleSingleScreen);
  el('batch-form')?.addEventListener('submit', handleBatchScreen);
  el('load-sample')?.addEventListener('click', loadSampleData);
  el('screen-sample')?.addEventListener('click', screenSampleData);
  el('batches-refresh')?.addEventListener('click', loadBatches);
  el('screenings-filter')?.addEventListener('input', renderScreenings);
  el('cases-status-filter')?.addEventListener('change', renderCases);

  el('modal-close')?.addEventListener('click', () => showElement('detail-modal', false));
  el('detail-modal')?.querySelector('.modal-backdrop')?.addEventListener('click', () => showElement('detail-modal', false));
  el('create-case-btn')?.addEventListener('click', createCaseFromModal);
}

async function handleAuthRedirect() {
  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const errorDescription =
    params.get('error_description') || hashParams.get('error_description');
  if (errorDescription) {
    showAuth();
    const notice = el('auth-notice');
    if (notice) {
      notice.textContent = `Email confirmation failed: ${errorDescription}`;
      notice.classList.remove('hidden');
    }
    window.history.replaceState({}, document.title, window.location.pathname);
    return true;
  }

  const code = params.get('code');
  if (code && supabaseClient) {
    try {
      const { data, error } = await supabaseClient.auth.exchangeCodeForSession(code);
      if (error) throw error;
      session = data.session;
      window.history.replaceState({}, document.title, window.location.pathname);
      await onSessionReady();
    } catch (err) {
      console.error('Could not complete email confirmation:', err);
      showAuth();
      const notice = el('auth-notice');
      if (notice) {
        notice.textContent = err.message || 'Email confirmation could not be completed. Request a new confirmation email and try again.';
        notice.classList.remove('hidden');
      }
    }
    return true;
  }
  return false;
}

async function bootstrap() {
  supabaseClient = initSupabase();

  // Dev mode: show skip button and bypass auth if configured.
  if (env.requireAuth === false || env.requireAuth === 'false') {
    el('dev-skip-btn')?.classList.remove('hidden');
  }

  setupAuthForms();
  setupNavigation();
  setupScreeningForms();

  if (!supabaseClient) {
    showToast('Supabase is not configured. Some features will not work.', 'error');
    if (env.requireAuth === false || env.requireAuth === 'false') {
      devSkipAuth();
    } else {
      showAuth();
      const notice = el('auth-notice');
      if (notice) {
        notice.textContent = 'Authentication is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.';
        notice.classList.remove('hidden');
      }
    }
    return;
  }

  // Hook up API keys UI
  el('create-api-key')?.addEventListener('click', async () => {
    setLoading(el('create-api-key'), true);
    try {
      const resp = await apiFetch('/api/api-keys', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) {
        showToast(data.error || 'Unable to create API key', 'error');
      } else {
        showToast('API key created. It is shown once — copy it now.', 'success');
        renderApiKeys([data, ...(await fetchApiKeys())]);
      }
    } catch (err) {
      console.error('Create API key error', err);
      showToast('Failed to create API key', 'error');
    } finally {
      setLoading(el('create-api-key'), false);
    }
  });

  fetchApiKeys().then((keys) => renderApiKeys(keys)).catch((e) => console.error(e));

  // Listen for auth state changes (login, logout, token refresh).
  supabaseClient.auth.onAuthStateChange((_event, newSession) => {
    session = newSession;
    if (newSession) {
      // Defer Supabase Auth calls until its auth-state callback has returned.
      window.setTimeout(() => {
        onSessionReady().catch((error) => {
          console.error('Auth state handling failed:', error);
          showMfaError(error);
        });
      }, 0);
    } else {
      lastProcessedAccessToken = null;
      showAuth();
    }
  });

  // Handle email confirmation / magic link redirect with ?code=...
  const handledRedirect = await handleAuthRedirect();
  if (handledRedirect) return;

  // Otherwise load the existing session from storage.
  const { data, error } = await supabaseClient.auth.getSession();
  if (error) {
    console.error('Get session error:', error);
  }
  session = data.session;
  await onSessionReady();
}

function showStartupError(error) {
  console.error('Application startup failed:', error);
  showElement('sidebar', false);
  showElement('main', false);
  showElement('startup-view', true);

  const message = el('startup-message');
  if (message) {
    message.textContent = 'FinAtlas could not finish loading. Check your configuration and try again.';
  }

  const spinner = qs('.startup-spinner');
  if (spinner) spinner.classList.add('hidden');
  showElement('startup-retry', true);
}

async function startApp() {
  showElement('startup-view', false);
  showElement('startup-retry', false);
  try {
    await bootstrap();
  } catch (error) {
    showStartupError(error);
  }
}

document.addEventListener('DOMContentLoaded', startApp);

async function fetchApiKeys() {
  try {
    const resp = await apiFetch('/api/api-keys');
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.keys || [];
  } catch (err) {
    return [];
  }
}

function renderApiKeys(keys) {
  const container = el('api-keys-container');
  if (!container) return;
  if (!keys.length) {
    container.innerHTML = '<div class="text-muted">No API keys. Create one to use the REST API without a Supabase session.</div>';
    return;
  }

  container.innerHTML = keys
    .map((k) => `
      <div class="api-key-item card" style="margin-top:0.5rem; padding:0.85rem; display:flex; align-items:center; justify-content:space-between; gap:0.8rem">
        <div style="flex:1">
          <div style="font-weight:700;">${k.id.slice(0,8)}${k.revoked ? ' (revoked)' : ''}</div>
          <div style="font-size:0.85rem; color:var(--text-muted);">Created: ${formatDate(k.created_at)}</div>
        </div>
        <div style="display:flex; gap:0.5rem; align-items:center">
          <button class="btn btn-sm btn-secondary copy-key" data-key="${k.key_text || ''}">Copy</button>
          <button class="btn btn-sm btn-ghost revoke-key" data-id="${k.id}">Revoke</button>
          <button class="btn btn-sm btn-ghost rotate-key" data-id="${k.id}">Rotate</button>
        </div>
      </div>`)
    .join('');

  qsa('.copy-key', container).forEach((btn) => {
    btn.addEventListener('click', async () => {
      const key = btn.dataset.key || '';
      if (!key) {
        showToast('This key value is not available to copy. Create a new key to reveal its value.', 'info');
        return;
      }
      try {
        await navigator.clipboard.writeText(key);
        showToast('API key copied to clipboard', 'success');
      } catch (err) {
        showToast('Could not copy key to clipboard', 'error');
      }
    });
  });

  qsa('.revoke-key', container).forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Revoke this API key? This will disable it immediately.')) return;
      setLoading(btn, true);
      try {
        const id = btn.dataset.id;
        const resp = await apiFetch(`/api/api-keys/${id}/revoke`, { method: 'POST' });
        if (!resp.ok) {
          const d = await resp.json().catch(() => ({}));
          showToast(d.error || 'Failed to revoke key', 'error');
        } else {
          showToast('API key revoked', 'success');
          const keys = await fetchApiKeys();
          renderApiKeys(keys);
        }
      } catch (err) {
        console.error('Revoke key error', err);
        showToast('Failed to revoke API key', 'error');
      } finally {
        setLoading(btn, false);
      }
    });
  });

  qsa('.rotate-key', container).forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Rotate this API key? The previous key will be revoked and a new key created.')) return;
      setLoading(btn, true);
      try {
        const id = btn.dataset.id;
        const resp = await apiFetch(`/api/api-keys/${id}/rotate`, { method: 'POST' });
        const d = await resp.json();
        if (!resp.ok) {
          showToast(d.error || 'Failed to rotate key', 'error');
        } else {
          showToast('API key rotated. Copy the new key now.', 'success');
          // The rotate endpoint returns the new key object; it may include key_text
          const keys = await fetchApiKeys();
          // Place the new key first
          renderApiKeys([d, ...keys.filter((k) => k.id !== d.id)]);
        }
      } catch (err) {
        console.error('Rotate key error', err);
        showToast('Failed to rotate API key', 'error');
      } finally {
        setLoading(btn, false);
      }
    });
  });
}
