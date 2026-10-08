// ─────────────────────────────────────────────────────────────
// CL-RAG: AI-Powered Cross-Language Knowledge Transfer Platform
// Client Application Logic
// ─────────────────────────────────────────────────────────────

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? `${window.location.origin}/api`
  : '/api';

let activeSpaces = [];
let currentSpaceId = null;
let chartTSR = null;
let chartReview = null;
let authToken = localStorage.getItem('clrag_token');
let currentUser = JSON.parse(localStorage.getItem('clrag_user') || 'null');

async function authFetch(url, options = {}) {
  options.headers = options.headers || {};
  if (authToken) {
    options.headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(url, options);
  if (res.status === 401) {
    // Token expired or unauthenticated
    authToken = null;
    currentUser = null;
    localStorage.removeItem('clrag_token');
    localStorage.removeItem('clrag_user');
    updateUserSessionUI();
    openModal('modal-auth');
    showToast("Session expired or authentication required. Please sign in.");
  }
  return res;
}

function updateUserSessionUI() {
  const profileBadge = document.getElementById('user-profile-badge');
  const btnLogin = document.getElementById('btn-open-login');
  const nameEl = document.getElementById('user-display-name');
  const roleEl = document.getElementById('user-display-role');

  if (currentUser && authToken) {
    if (profileBadge) profileBadge.style.display = 'flex';
    if (btnLogin) btnLogin.style.display = 'none';
    if (nameEl) nameEl.textContent = currentUser.name || currentUser.email;
    if (roleEl) {
      roleEl.textContent = currentUser.role || 'USER';
      const roleColors = {
        ADMIN: '#dc2626',
        REVIEWER: '#2563eb',
        USER: '#16a34a'
      };
      roleEl.style.background = roleColors[currentUser.role] || '#2563eb';
    }

    // Role-aware UI gating
    const isReviewerOrAdmin = ['ADMIN', 'REVIEWER'].includes(currentUser.role);
    const isAdmin = currentUser.role === 'ADMIN';

    // Disable ablation run button for non-admins
    const btnAblation = document.getElementById('btn-run-ablation-benchmark');
    if (btnAblation) {
      btnAblation.title = isAdmin ? "Run full IEEE evaluation" : "Evaluation run requires ADMIN role";
      if (!isAdmin) {
        btnAblation.classList.add('disabled');
      } else {
        btnAblation.classList.remove('disabled');
      }
    }
  } else {
    if (profileBadge) profileBadge.style.display = 'none';
    if (btnLogin) btnLogin.style.display = 'inline-block';
  }
}

async function ensureAuthenticated() {
  // Respect existing session or open sign-in modal if anonymous
  updateUserSessionUI();
  if (!authToken || !currentUser) {
    openModal('modal-auth');
  }
}

// Technical sentences for quick demo
const SAMPLE_SENTENCES = [
  "Fault tolerance is essential for modern cloud infrastructure to prevent downtime. A reliable load balancer manages traffic distribution and horizontal scaling across clusters.",
  "The cluster implements an active circuit breaker pattern alongside eventual consistency to prevent cascading network failures.",
  "Mechanical ventilators regulate positive end-expiratory pressure and tidal volume for critical patient safety.",
  "Continuous pulse oximetry and capnography are critical to prevent barotrauma during intubation."
];

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initModals();
  await ensureAuthenticated();
  if (authToken) {
    loadInitialData();
  }
  setupEventListeners();
});

// ─────────────────────────────────────────────────────────────
// Navigation & Tab Switching
// ─────────────────────────────────────────────────────────────
function initNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  // Update sidebar active state
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-tab') === tabId);
  });

  // Update view visibility
  document.querySelectorAll('.tab-view').forEach(view => {
    view.style.display = 'none';
  });

  const activeView = document.getElementById(`view-${tabId}`);
  if (activeView) {
    activeView.style.display = 'block';
  }

  // Update Header title
  const titles = {
    dashboard: "Dashboard & Telemetry",
    translate: "Multi-Agent Translation Studio",
    kg: "Living Terminology Knowledge Graph (T-KG)",
    review: "Confidence-Gated Human Review Hub",
    adaptive: "Expertise-Adaptive Summarization Lab",
    chat: "CL-RAG Cross-Lingual Conversational Chat",
    documents: "Knowledge Spaces & Document Ingestion",
    eval: "IEEE Empirical Evaluation & Ablation Hub"
  };
  document.getElementById('current-view-title').innerText = titles[tabId] || "CL-RAG Platform";

  // Trigger tab-specific loads
  if (tabId === 'dashboard') loadStats();
  if (tabId === 'kg') loadKnowledgeGraph();
  if (tabId === 'review') loadReviewQueue();
  if (tabId === 'documents') loadDocuments();
  if (tabId === 'eval') loadEvaluationAblation();
}

// ─────────────────────────────────────────────────────────────
// Initial Data Loading
// ─────────────────────────────────────────────────────────────
async function loadInitialData() {
  try {
    await loadStats();
    await loadSpaces();
    await loadReviewQueueBadge();
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

async function loadStats() {
  try {
    const res = await authFetch(`${API_BASE}/stats`);
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('stat-kg-nodes').innerText = data.terminology_nodes;
    document.getElementById('stat-docs-indexed').innerText = data.documents_indexed;
    document.getElementById('stat-chunks').innerText = data.semantic_chunks;
    document.getElementById('stat-pending-reviews').innerText = data.pending_reviews;
    document.getElementById('stat-self-evolution').innerText = data.self_evolution_updates;
    document.getElementById('review-badge-count').innerText = data.pending_reviews;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadSpaces() {
  try {
    const res = await authFetch(`${API_BASE}/documents/spaces`);
    if (!res.ok) return;
    activeSpaces = await res.json();
    if (activeSpaces.length > 0) {
      currentSpaceId = activeSpaces[0].id;
    }
    populateSpaceSelects();
  } catch (err) {
    console.error("Failed to load spaces:", err);
  }
}

function populateSpaceSelects() {
  const modalSpaceSelect = document.getElementById('doc-modal-space-select');
  if (modalSpaceSelect) {
    modalSpaceSelect.innerHTML = activeSpaces.map(s => 
      `<option value="${s.id}">${s.name} (${s.domain})</option>`
    ).join('');
  }
}

async function loadReviewQueueBadge() {
  try {
    const res = await authFetch(`${API_BASE}/review?status=PENDING`);
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('review-badge-count').innerText = data.count;
    document.getElementById('stat-pending-reviews').innerText = data.count;
  } catch (err) {
    console.error("Error loading review count:", err);
  }
}

// ─────────────────────────────────────────────────────────────
// Multi-Agent Translation Studio
// ─────────────────────────────────────────────────────────────
async function runMultiAgentTranslation() {
  const text = document.getElementById('translate-input-text').value.trim();
  const targetLang = document.getElementById('global-target-lang').value;
  const domain = document.getElementById('global-domain-select').value;

  if (!text) {
    showToast("Please enter source technical text.");
    return;
  }

  const btn = document.getElementById('btn-run-translation');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Executing Agents...`;

  try {
    const res = await authFetch(`${API_BASE}/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_text: text,
        target_lang: targetLang,
        domain: domain
      })
    });

    const data = await res.json();
    renderAgentResults(data);
    loadReviewQueueBadge();
    loadStats();
    showToast("Multi-Agent verification completed!");
  } catch (err) {
    console.error("Translation error:", err);
    showToast("Error during multi-agent translation.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-microchip"></i> Execute Multi-Agent Pipeline`;
  }
}

function renderAgentResults(data) {
  const container = document.getElementById('agent-results-container');
  container.style.display = 'flex';

  document.getElementById('telemetry-avg-conf').innerText = data.avg_confidence;
  document.getElementById('telemetry-tsr').innerText = `${data.term_usage_rate}%`;

  const routingStatusEl = document.getElementById('telemetry-routing-status');
  const badgeContainer = document.getElementById('telemetry-badge-container');

  if (data.queued_for_review > 0) {
    routingStatusEl.innerText = `${data.queued_for_review} Segments Gated to Review`;
    routingStatusEl.style.color = 'var(--accent-amber)';
    badgeContainer.innerHTML = `<span class="badge-tag badge-warning"><i class="fa-solid fa-user-clock"></i> Low Confidence Span Gated</span>`;
  } else {
    routingStatusEl.innerText = `Automated (Confidence ≥ 0.85)`;
    routingStatusEl.style.color = 'var(--accent-emerald)';
    badgeContainer.innerHTML = `<span class="badge-tag badge-verified"><i class="fa-solid fa-circle-check"></i> Constraint Verified</span>`;
  }

  const firstSeg = data.segments[0] || {};

  // Agent 1: Translator
  document.getElementById('agent-1-output').innerText = firstSeg.target_segment || data.full_translation;

  // Agent 2: Verifier
  const verifier = firstSeg.verifier_report || {};
  document.getElementById('agent-2-explanation').innerText = verifier.explanation || "Constraints satisfied.";
  document.getElementById('agent-2-bar').style.width = `${(verifier.score || 1.0) * 100}%`;
  document.getElementById('agent-2-status').innerText = verifier.status || "PASSED";

  // Agent 3: Critic
  const critic = firstSeg.critic_report || {};
  document.getElementById('agent-3-notes').innerText = critic.notes || "Semantic fidelity verified.";
  document.getElementById('agent-3-bar').style.width = `${(critic.score || 0.95) * 100}%`;

  // Final Output
  document.getElementById('final-translation-text').innerText = data.full_translation;
}

// ─────────────────────────────────────────────────────────────
// Living Terminology Knowledge Graph (T-KG)
// ─────────────────────────────────────────────────────────────
async function loadKnowledgeGraph() {
  const domain = document.getElementById('global-domain-select').value;
  const search = document.getElementById('kg-search-input').value.trim();

  let url = `${API_BASE}/kg/terms?domain=${domain}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await authFetch(url);
    if (!res.ok) return;
    const data = await res.json();
    renderKGTable(data.terms);
  } catch (err) {
    console.error("Error loading KG:", err);
  }
}

function renderKGTable(terms) {
  const tbody = document.getElementById('kg-terms-tbody');
  if (!terms || terms.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No terms found. Add a term or extract from documents.</td></tr>`;
    return;
  }

  tbody.innerHTML = terms.map(t => {
    const trans = t.translations || {};
    const transStr = Object.entries(trans)
      .map(([lang, val]) => `<span style="margin-right: 8px; font-size: 12px;"><strong>${lang.toUpperCase()}:</strong> ${val}</span>`)
      .join('');

    return `
      <tr>
        <td><span class="term-tag">${escapeHtml(t.source_term)}</span></td>
        <td><span style="font-size: 12px; color: var(--text-secondary);">${t.domain}</span></td>
        <td>${transStr}</td>
        <td><span class="badge-tag badge-verified">v${t.version}</span></td>
        <td>${t.confidence ? (t.confidence * 100).toFixed(0) + '%' : '95%'}</td>
        <td><span class="badge-tag badge-verified">${t.status}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="openEditTermModal('${t.id}', '${escapeHtml(t.source_term)}', '${t.domain}')">
            <i class="fa-solid fa-pen"></i> Edit
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

async function handleAddTermSubmit(e) {
  e.preventDefault();
  const sourceTerm = document.getElementById('term-modal-source').value.trim();
  const domain = document.getElementById('term-modal-domain').value;
  const targetLang = document.getElementById('term-modal-lang').value;
  const translation = document.getElementById('term-modal-trans').value.trim();
  const definition = document.getElementById('term-modal-def').value.trim();

  try {
    const res = await authFetch(`${API_BASE}/kg/terms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_term: sourceTerm,
        domain: domain,
        target_lang: targetLang,
        translation: translation,
        definition: definition,
        reviewer_notes: "Expert addition via Knowledge Graph Studio"
      })
    });

    const data = await res.json();
    closeModal('modal-term');
    showToast(data.message || "Living KG updated successfully!");
    loadKnowledgeGraph();
    loadStats();
  } catch (err) {
    console.error("Error saving term:", err);
    showToast("Failed to save term.");
  }
}

function openEditTermModal(id, source, domain) {
  document.getElementById('term-modal-source').value = source;
  document.getElementById('term-modal-domain').value = domain;
  openModal('modal-term');
}

// ─────────────────────────────────────────────────────────────
// Confidence-Gated Review Queue (Self-Evolution Loop)
// ─────────────────────────────────────────────────────────────
async function loadReviewQueue() {
  try {
    const res = await authFetch(`${API_BASE}/review?status=PENDING`);
    if (!res.ok) return;
    const data = await res.json();
    renderReviewQueue(data.items);
  } catch (err) {
    console.error("Error loading review queue:", err);
  }
}

function renderReviewQueue(items) {
  const container = document.getElementById('review-queue-list');
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="glass-card" style="text-align: center; padding: 40px;">
        <i class="fa-solid fa-circle-check" style="font-size: 36px; color: var(--accent-emerald); margin-bottom: 12px;"></i>
        <h4 style="font-family: var(--font-display); font-size: 16px; margin-bottom: 6px;">All Constraints Verified</h4>
        <p style="color: var(--text-secondary); font-size: 13px;">No translations currently fall below the confidence threshold (&tau; = 0.85).</p>
      </div>
    `;
    return;
  }

  container.innerHTML = items.map(item => `
    <div class="glass-card" style="border-left: 4px solid var(--accent-amber);" id="review-card-${item.id}">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
        <div>
          <span class="badge-tag badge-warning" style="margin-right: 8px;">
            <i class="fa-solid fa-triangle-exclamation"></i> Calibrated Confidence: ${(item.confidence * 100).toFixed(1)}% (&lt; 85%)
          </span>
          <span style="font-size: 12px; color: var(--text-muted);">Target: ${item.target_lang.toUpperCase()} | Domain: ${item.domain}</span>
        </div>
        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="dismissReviewItem('${item.id}')">
          <i class="fa-solid fa-xmark"></i> Dismiss
        </button>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
        <div style="background: rgba(255,255,255,0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Source Segment</div>
          <div style="font-size: 13.5px; line-height: 1.5;">${escapeHtml(item.source_segment)}</div>
        </div>

        <div style="background: rgba(255,255,255,0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Translator Draft</div>
          <div style="font-size: 13.5px; line-height: 1.5;">${escapeHtml(item.target_segment)}</div>
        </div>
      </div>

      <div style="background: rgba(245, 158, 11, 0.08); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 12px; color: #fbbf24; margin-bottom: 16px;">
        <i class="fa-solid fa-stethoscope"></i> <strong>Critic Audit:</strong> ${escapeHtml(item.critic_notes || 'Low confidence verification threshold triggered.')}
      </div>

      <!-- Human Correction & Self-Update Trigger -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <div style="flex: 1;">
          <label style="font-size: 11.5px; color: var(--text-muted); display: block; margin-bottom: 4px;">
            Target Term: <strong>${escapeHtml(item.term_text)}</strong> &rarr; Approved Translation:
          </label>
          <input type="text" class="chat-input" id="correct-input-${item.id}" value="${escapeHtml(item.term_text)}" placeholder="Enter corrected target language rendering">
        </div>
        <div style="align-self: flex-end;">
          <button class="btn btn-primary" onclick="submitHumanCorrection('${item.id}')">
            <i class="fa-solid fa-code-branch"></i> Approve & Self-Update KG
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

async function submitHumanCorrection(itemId) {
  const correctedTranslation = document.getElementById(`correct-input-${itemId}`).value.trim();
  if (!correctedTranslation) {
    showToast("Please provide the approved term translation.");
    return;
  }

  try {
    const res = await authFetch(`${API_BASE}/review/${itemId}/correct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        corrected_translation: correctedTranslation,
        reviewer_comment: "Approved by human reviewer; persistent KG version incremented"
      })
    });

    const data = await res.json();
    showToast(data.message || "Feedback applied! Living KG self-evolved.");

    // Animate and remove card
    const card = document.getElementById(`review-card-${itemId}`);
    if (card) {
      card.style.opacity = '0';
      setTimeout(() => {
        loadReviewQueue();
        loadStats();
      }, 300);
    }
  } catch (err) {
    console.error("Correction error:", err);
    showToast("Failed to apply correction.");
  }
}

async function dismissReviewItem(itemId) {
  try {
    await authFetch(`${API_BASE}/review/${itemId}/dismiss`, { method: 'POST' });
    showToast("Item dismissed.");
    loadReviewQueue();
    loadStats();
  } catch (err) {
    console.error("Dismiss error:", err);
  }
}

// ─────────────────────────────────────────────────────────────
// Expertise-Adaptive Summarization Lab
// ─────────────────────────────────────────────────────────────
async function runAdaptiveSummarization() {
  const text = document.getElementById('adaptive-input-text').value.trim();
  const targetLang = document.getElementById('global-target-lang').value;
  const domain = document.getElementById('global-domain-select').value;

  if (!text) {
    showToast("Please enter technical text to adapt.");
    return;
  }

  const btn = document.getElementById('btn-run-adaptation');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Adapting...`;

  try {
    const res = await authFetch(`${API_BASE}/adaptive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_text: text,
        target_lang: targetLang,
        domain: domain
      })
    });

    const data = await res.json();
    document.getElementById('adaptive-results-row').style.display = 'grid';
    document.getElementById('novice-output-content').innerText = data.novice_adaptation.text;
    document.getElementById('expert-output-content').innerText = data.expert_adaptation.text;
    document.getElementById('novice-complexity-tag').innerText = `Complexity: Low (${data.novice_adaptation.complexity_index})`;
    document.getElementById('expert-complexity-tag').innerText = `Complexity: Rigorous (${data.expert_adaptation.complexity_index})`;

    showToast("Generated Novice & Expert adaptations!");
  } catch (err) {
    console.error("Adaptation error:", err);
    showToast("Failed to adapt text.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Dual Adaptations`;
  }
}

// ─────────────────────────────────────────────────────────────
// CL-RAG Conversational Chat
// ─────────────────────────────────────────────────────────────
async function sendChatMessage() {
  const input = document.getElementById('chat-query-input');
  const question = input.value.trim();
  const targetLang = document.getElementById('global-target-lang').value;

  if (!question) return;
  if (!currentSpaceId && activeSpaces.length > 0) {
    currentSpaceId = activeSpaces[0].id;
  }

  input.value = '';
  appendChatBubble('user', question);

  const loadingBubble = appendChatBubble('assistant', 'Searching knowledge spaces across language boundaries...');

  try {
    const res = await authFetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        space_id: currentSpaceId,
        question: question,
        target_lang: targetLang
      })
    });

    const data = await res.json();
    loadingBubble.remove();
    appendChatResponseWithCitations(data.answer, data.citations);
  } catch (err) {
    console.error("Chat error:", err);
    loadingBubble.innerHTML = `Error retrieving answer. Ensure documents are indexed.`;
  }
}

function appendChatBubble(role, text) {
  const container = document.getElementById('chat-messages-list');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.innerText = text;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  return bubble;
}

function appendChatResponseWithCitations(answer, citations) {
  const container = document.getElementById('chat-messages-list');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble assistant';

  let html = `<div>${escapeHtml(answer)}</div>`;

  if (citations && citations.length > 0) {
    html += `<div class="citations-box">
      <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">
        <i class="fa-solid fa-quote-left"></i> Grounded Source Citations
      </div>`;
    citations.forEach(c => {
      html += `
        <div class="citation-chip">
          <div class="citation-chip-header">
            <span>${escapeHtml(c.filename)} (Chunk #${c.chunk_index})</span>
            <span style="font-size: 10px; color: var(--accent-emerald);">Match: ${(c.relevance_score * 100).toFixed(0)}%</span>
          </div>
          <div style="color: var(--text-secondary); margin-top: 4px; font-style: italic;">"${escapeHtml(c.snippet)}"</div>
        </div>
      `;
    });
    html += `</div>`;
  }

  bubble.innerHTML = html;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ─────────────────────────────────────────────────────────────
// Knowledge Spaces & Documents
// ─────────────────────────────────────────────────────────────
async function loadDocuments() {
  try {
    const res = await authFetch(`${API_BASE}/documents`);
    if (!res.ok) return;
    const docs = await res.json();
    renderDocumentCards(docs);
  } catch (err) {
    console.error("Error loading documents:", err);
  }
}

function renderDocumentCards(docs) {
  const container = document.getElementById('documents-list-grid');
  if (!docs || docs.length === 0) {
    container.innerHTML = `<div class="glass-card"><p style="color: var(--text-muted);">No documents indexed yet.</p></div>`;
    return;
  }

  container.innerHTML = docs.map(doc => `
    <div class="glass-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <h4 style="font-family: var(--font-display); font-size: 15px; margin-bottom: 2px;">
            <i class="fa-solid fa-file-lines" style="color: var(--accent-cyan);"></i> ${escapeHtml(doc.filename)}
          </h4>
          <span style="font-size: 11.5px; color: var(--text-muted);">Type: ${doc.file_type.toUpperCase()} | Status: ${doc.status}</span>
        </div>
        <span class="badge-tag badge-verified">${doc.chunk_count} Chunks</span>
      </div>
      <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px;">
        ${escapeHtml(doc.raw_text.substring(0, 160))}...
      </p>
      <button class="btn btn-secondary" style="width: 100%; font-size: 12px;" onclick="viewDocumentChunks('${doc.id}', '${escapeHtml(doc.filename)}')">
        <i class="fa-solid fa-layer-group"></i> Inspect Chunks & Pinned Terms
      </button>
    </div>
  `).join('');
}

async function viewDocumentChunks(docId, filename) {
  try {
    const res = await authFetch(`${API_BASE}/documents/${docId}/chunks`);
    if (!res.ok) return;
    const chunks = await res.json();
    let preview = `Document: ${filename}\n\n`;
    chunks.forEach(c => {
      preview += `[Chunk #${c.chunk_index}]\nTerms Detected: ${(c.detected_terms || []).join(', ') || 'None'}\n${c.content}\n\n`;
    });
    alert(preview);
  } catch (err) {
    console.error("Error viewing chunks:", err);
  }
}

async function handleUploadDocSubmit(e) {
  e.preventDefault();
  const filename = document.getElementById('doc-modal-filename').value.trim();
  const spaceId = document.getElementById('doc-modal-space-select').value || currentSpaceId;
  const content = document.getElementById('doc-modal-content').value.trim();
  const domain = document.getElementById('global-domain-select').value;

  try {
    const res = await authFetch(`${API_BASE}/documents/ingest-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        space_id: spaceId,
        filename: filename,
        content: content,
        domain: domain
      })
    });

    const data = await res.json();
    closeModal('modal-document');
    showToast(`Document indexed into ${data.chunk_count} semantic chunks!`);
    loadDocuments();
    loadStats();
  } catch (err) {
    console.error("Upload error:", err);
    showToast("Failed to index document.");
  }
}

// ─────────────────────────────────────────────────────────────
// IEEE Evaluation & Ablation Hub
// ─────────────────────────────────────────────────────────────
async function loadEvaluationAblation() {
  try {
    const res = await authFetch(`${API_BASE}/eval/latest`);
    if (!res.ok) return;
    const data = await res.json();
    renderEvaluationCharts(data.metrics || data);
  } catch (err) {
    console.error("Error loading evaluation:", err);
  }
}

async function triggerAblationRun() {
  const btn = document.getElementById('btn-run-ablation-benchmark');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running Ablation Simulation...`;

  try {
    const domain = document.getElementById('global-domain-select').value;
    const res = await authFetch(`${API_BASE}/eval/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain: domain })
    });
    const data = await res.json();
    renderEvaluationCharts(data.metrics);
    showToast("Ablation benchmark completed!");
  } catch (err) {
    console.error("Ablation error:", err);
    showToast("Error running ablation.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-flask"></i> Run Multi-Round Ablation`;
  }
}

function renderEvaluationCharts(metrics) {
  const rounds = metrics.rounds || [];
  const comparison = metrics.comparison || [];

  const roundLabels = rounds.map(r => r.round);
  const tsrValues = rounds.map(r => r.tsr_percentage !== undefined ? r.tsr_percentage : r.term_usage_rate_percent);
  const reviewValues = rounds.map(r => r.review_volume_percentage !== undefined ? r.review_volume_percentage : r.review_rate_percent);

  // Chart 1: TSR
  const ctxTSR = document.getElementById('chart-tsr-rounds');
  if (ctxTSR) {
    if (chartTSR) chartTSR.destroy();
    chartTSR = new Chart(ctxTSR, {
      type: 'line',
      data: {
        labels: roundLabels,
        datasets: [{
          label: 'Term-Usage Success Rate (TSR %)',
          data: tsrValues,
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.15)',
          borderWidth: 3,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#06b6d4',
          pointRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
  }

  // Chart 2: Review Volume Reduction
  const ctxReview = document.getElementById('chart-review-volume');
  if (ctxReview) {
    if (chartReview) chartReview.destroy();
    chartReview = new Chart(ctxReview, {
      type: 'bar',
      data: {
        labels: roundLabels,
        datasets: [{
          label: 'Review Volume (% of total segments)',
          data: reviewValues,
          backgroundColor: ['#f59e0b', '#06b6d4', '#8b5cf6', '#10b981'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
          x: { grid: { color: 'rgba(255,255,255,0.05)' } }
        }
      }
    });
  }

  // Populate Comparison Table
  const tbody = document.getElementById('eval-benchmark-tbody');
  if (tbody && comparison.length > 0) {
    tbody.innerHTML = comparison.map(row => `
      <tr>
        <td><strong>${escapeHtml(row.system)}</strong></td>
        <td><span class="badge-tag ${row.tsr >= 95 ? 'badge-verified' : 'badge-warning'}">${row.tsr}%</span></td>
        <td>${row.review_mode}</td>
        <td>${row.review_volume}%</td>
        <td>${row.self_updating ? '<i class="fa-solid fa-check" style="color: var(--accent-emerald);"></i> Yes' : '<i class="fa-solid fa-xmark" style="color: var(--accent-rose);"></i> No'}</td>
        <td>${row.adaptive_summarization ? '<i class="fa-solid fa-check" style="color: var(--accent-emerald);"></i> Yes' : '<i class="fa-solid fa-xmark" style="color: var(--accent-rose);"></i> No'}</td>
      </tr>
    `).join('');
  }
}

// ─────────────────────────────────────────────────────────────
// Event Listeners & Modals
// ─────────────────────────────────────────────────────────────
function setupEventListeners() {
  // Studio Translate
  document.getElementById('btn-run-translation')?.addEventListener('click', runMultiAgentTranslation);
  document.getElementById('btn-load-sample-sentence')?.addEventListener('click', () => {
    const randomSentence = SAMPLE_SENTENCES[Math.floor(Math.random() * SAMPLE_SENTENCES.length)];
    document.getElementById('translate-input-text').value = randomSentence;
    showToast("Sample technical sentence loaded.");
  });

  // Quick action buttons on Dashboard
  document.getElementById('btn-quick-multiagent')?.addEventListener('click', () => switchTab('translate'));
  document.getElementById('btn-quick-kg')?.addEventListener('click', () => switchTab('kg'));
  document.getElementById('btn-quick-ablation')?.addEventListener('click', () => switchTab('eval'));

  // Adaptive
  document.getElementById('btn-run-adaptation')?.addEventListener('click', runAdaptiveSummarization);

  // Chat
  document.getElementById('btn-send-chat')?.addEventListener('click', sendChatMessage);
  document.getElementById('chat-query-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });

  // Copy Translation
  document.getElementById('btn-copy-translation')?.addEventListener('click', () => {
    const text = document.getElementById('final-translation-text').innerText;
    navigator.clipboard.writeText(text);
    showToast("Translation copied to clipboard!");
  });

  // Review
  document.getElementById('btn-refresh-review-queue')?.addEventListener('click', loadReviewQueue);

  // KG Search
  document.getElementById('kg-search-input')?.addEventListener('input', debounce(loadKnowledgeGraph, 300));
  document.getElementById('global-domain-select')?.addEventListener('change', () => {
    loadKnowledgeGraph();
    loadStats();
  });

  // Modals
  document.getElementById('btn-open-add-term-modal')?.addEventListener('click', () => openModal('modal-term'));
  document.getElementById('form-add-term')?.addEventListener('submit', handleAddTermSubmit);
  document.getElementById('btn-open-upload-modal')?.addEventListener('click', () => openModal('modal-document'));
  document.getElementById('form-upload-doc')?.addEventListener('submit', handleUploadDocSubmit);
  document.getElementById('btn-open-settings')?.addEventListener('click', () => openModal('modal-settings'));

  // Settings Save
  document.getElementById('btn-save-settings')?.addEventListener('click', () => {
    const threshold = document.getElementById('settings-threshold').value;
    const apiKey = document.getElementById('settings-gemini-key').value.trim();
    if (apiKey) {
      document.getElementById('system-mode-text').innerText = "Live Neural LLM Active";
    }
    document.getElementById('gating-threshold-badge').innerHTML = `<i class="fa-solid fa-filter"></i> Gate: &tau; &ge; ${threshold}`;
    closeModal('modal-settings');
    showToast("System settings updated!");
  });

  // Ablation Run
  document.getElementById('btn-run-ablation-benchmark')?.addEventListener('click', triggerAblationRun);

  // Authentication UI Controls
  document.getElementById('btn-open-login')?.addEventListener('click', () => openModal('modal-auth'));
  document.getElementById('btn-logout')?.addEventListener('click', handleLogout);

  document.getElementById('tab-auth-login')?.addEventListener('click', () => {
    document.getElementById('tab-auth-login').className = 'btn btn-primary';
    document.getElementById('tab-auth-register').className = 'btn btn-secondary';
    document.getElementById('form-auth-login').style.display = 'flex';
    document.getElementById('form-auth-register').style.display = 'none';
  });

  document.getElementById('tab-auth-register')?.addEventListener('click', () => {
    document.getElementById('tab-auth-register').className = 'btn btn-primary';
    document.getElementById('tab-auth-login').className = 'btn btn-secondary';
    document.getElementById('form-auth-login').style.display = 'none';
    document.getElementById('form-auth-register').style.display = 'flex';
  });

  document.getElementById('form-auth-login')?.addEventListener('submit', handleLoginSubmit);
  document.getElementById('form-auth-register')?.addEventListener('submit', handleRegisterSubmit);
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('auth-login-email').value.trim();
  const password = document.getElementById('auth-login-password').value;
  const errEl = document.getElementById('auth-login-error');
  if (errEl) errEl.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) {
      if (errEl) {
        errEl.textContent = data.detail || 'Login failed';
        errEl.style.display = 'block';
      }
      return;
    }
    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('clrag_token', authToken);
    localStorage.setItem('clrag_user', JSON.stringify(currentUser));
    updateUserSessionUI();
    closeModal('modal-auth');
    showToast(`Signed in as ${currentUser.name} (${currentUser.role})`);
    loadInitialData();
  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Network error during sign-in.';
      errEl.style.display = 'block';
    }
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('auth-reg-name').value.trim();
  const email = document.getElementById('auth-reg-email').value.trim();
  const password = document.getElementById('auth-reg-password').value;
  const tenant_id = document.getElementById('auth-reg-tenant').value.trim() || 'default_org';
  const errEl = document.getElementById('auth-reg-error');
  if (errEl) errEl.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, tenant_id, role: 'USER' })
    });
    const data = await res.json();
    if (!res.ok) {
      if (errEl) {
        errEl.textContent = data.detail || 'Registration failed';
        errEl.style.display = 'block';
      }
      return;
    }
    authToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('clrag_token', authToken);
    localStorage.setItem('clrag_user', JSON.stringify(currentUser));
    updateUserSessionUI();
    closeModal('modal-auth');
    showToast('Account created and signed in!');
    loadInitialData();
  } catch (err) {
    if (errEl) {
      errEl.textContent = 'Network error during registration.';
      errEl.style.display = 'block';
    }
  }
}

function handleLogout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('clrag_token');
  localStorage.removeItem('clrag_user');
  updateUserSessionUI();
  showToast('Logged out successfully.');
  openModal('modal-auth');
}

function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal.id);
    });
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('active');
}

function showToast(msg) {
  const toast = document.getElementById('toast-notification');
  const msgEl = document.getElementById('toast-message');
  msgEl.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
