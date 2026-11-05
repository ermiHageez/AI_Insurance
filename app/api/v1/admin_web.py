"""FastAPI route serving the Web Admin Portal directly at /admin."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter(tags=["Admin Web Portal"])

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InsurTech AI - Admin Control Desk</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased min-h-screen">
  <!-- Top Navigation Bar -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-lg shadow-emerald-200 shadow-md">
          <i class="fa-solid fa-brain"></i>
        </div>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight">InsurTech AI Admin Portal</h1>
          <p class="text-xs text-slate-500">Ethiopian Amharic/English Knowledge Base & Regulatory Desk</p>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Port 5000 Online
        </span>
        <a href="/docs" target="_blank" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
          <i class="fa-solid fa-code mr-1"></i> Swagger Docs
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
    <!-- Tab Navigation -->
    <div class="flex border-b border-slate-200 space-x-8 text-sm font-medium">
      <button onclick="switchTab('ingestion')" id="tab-btn-ingestion" class="tab-btn pb-4 border-b-2 border-emerald-600 text-emerald-600 font-bold flex items-center gap-2">
        <i class="fa-solid fa-file-arrow-up"></i> Document Ingestion
      </button>
      <button onclick="switchTab('review')" id="tab-btn-review" class="tab-btn pb-4 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-2">
        <i class="fa-solid fa-clipboard-check"></i> Q&A Review Desk
        <span id="badge-flagged" class="hidden px-2 py-0.5 rounded-full text-xs bg-amber-100 text-amber-800 font-bold">0</span>
      </button>
      <button onclick="switchTab('regulatory')" id="tab-btn-regulatory" class="tab-btn pb-4 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-2">
        <i class="fa-solid fa-landmark"></i> Regulatory Compliance
        <span id="badge-diffs" class="hidden px-2 py-0.5 rounded-full text-xs bg-rose-100 text-rose-800 font-bold">0</span>
      </button>
      <button onclick="switchTab('export')" id="tab-btn-export" class="tab-btn pb-4 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-2">
        <i class="fa-solid fa-shield-halved"></i> Training Data Export
      </button>
    </div>

    <!-- TAB 1: DOCUMENT INGESTION -->
    <section id="panel-ingestion" class="tab-panel space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Upload Card -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-bold text-slate-900">Upload Policy or Tariff Document</h2>
              <p class="text-xs text-slate-500 mt-0.5">Upload PDF, DOCX, or TXT documents. Text is semantically chunked and vectorized.</p>
            </div>
            <a href="/api/v1/kb/sample-pdf" download="sample_amharic_policy.pdf" class="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-xl border border-emerald-200 transition shrink-0 flex items-center gap-1.5 shadow-sm">
              <i class="fa-solid fa-file-pdf text-rose-500"></i> Download Sample Amharic PDF
            </a>
          </div>

          <form id="upload-form" class="space-y-4" onsubmit="handleUpload(event)">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Document Category</label>
              <select id="doc-category" class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 outline-none">
                <option value="POLICY">Insurance Policy / Endorsement</option>
                <option value="REGULATORY">Regulatory Directive (NBE)</option>
                <option value="CLAIM_PROCEDURE">Claim Procedure Manual</option>
                <option value="FAQ">Customer FAQ</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Select File (Max 20MB)</label>
              <input type="file" id="doc-file" required accept=".pdf,.docx,.txt,.md" class="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 cursor-pointer border border-slate-200 rounded-xl p-1 bg-slate-50" />
            </div>

            <button type="submit" id="btn-upload" class="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition shadow-sm flex items-center justify-center gap-2">
              <i class="fa-solid fa-cloud-arrow-up"></i> Upload & Vectorize
            </button>
          </form>

          <div id="upload-feedback" class="hidden p-3 rounded-xl text-xs"></div>

          <!-- Job Status Block -->
          <div id="job-status-card" class="hidden p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-slate-700">Async Indexing Job</span>
              <span id="job-badge" class="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800">PROCESSING</span>
            </div>
            <p id="job-filename" class="text-xs text-slate-500 font-mono"></p>
            <div id="job-stats" class="grid grid-cols-2 gap-2 text-xs pt-1">
              <div class="p-2 bg-white rounded border border-slate-200">
                <span class="text-slate-500">Indexed Chunks:</span>
                <p id="job-chunks" class="font-bold text-slate-900">-</p>
              </div>
              <div class="p-2 bg-white rounded border border-slate-200">
                <span class="text-slate-500">Characters:</span>
                <p id="job-chars" class="font-bold text-slate-900">-</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Semantic Search Sandbox -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div>
            <h2 class="text-base font-bold text-slate-900">Semantic Knowledge Retrieval Test</h2>
            <p class="text-xs text-slate-500 mt-0.5">Test real-time citation matching in Amharic or English (&lt;80ms latency target).</p>
          </div>

          <div class="flex gap-2">
            <input type="text" id="kb-query" placeholder="e.g. የሞተር አደጋ ተቀናሽ ሂሳብ ወይም Third Party liability..." class="flex-1 px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 outline-none" onkeyup="if(event.key==='Enter') searchKnowledge()" />
            <button onclick="searchKnowledge()" class="px-4 py-2 bg-slate-900 hover:bg-black text-white text-sm font-semibold rounded-xl transition">
              <i class="fa-solid fa-magnifying-glass mr-1"></i> Search
            </button>
          </div>

          <div id="search-results" class="space-y-3 max-h-96 overflow-y-auto pr-1">
            <p class="text-xs text-slate-400 text-center py-8">Enter a query above to test vector retrieval citations.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: REVIEW DESK -->
    <section id="panel-review" class="tab-panel hidden space-y-6">
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-bold text-slate-900">Flagged Interactions & Golden Knowledge Base</h2>
            <p class="text-xs text-slate-500 mt-0.5">Review customer-downvoted responses, write verified expert answers, and promote to the Golden KB.</p>
          </div>
          <div class="flex items-center gap-3">
            <select id="review-filter" onchange="loadReviewInteractions()" class="px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium">
              <option value="DOWN">Downvoted Only (👎)</option>
              <option value="ALL">All Interactions</option>
            </select>
            <button onclick="loadReviewInteractions()" class="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition">
              <i class="fa-solid fa-arrows-rotate"></i>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 min-h-[480px]">
          <!-- Interactions List -->
          <div id="interactions-list" class="lg:col-span-5 border-r border-slate-200 divide-y divide-slate-100 max-h-[550px] overflow-y-auto">
            <p class="text-xs text-slate-400 p-6 text-center">Loading interactions...</p>
          </div>

          <!-- Detail & Editor -->
          <div class="lg:col-span-7 p-6 space-y-4">
            <div id="review-placeholder" class="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <i class="fa-regular fa-comment-dots text-4xl mb-3"></i>
              <p class="text-sm font-medium">Select an interaction on the left to review and promote.</p>
            </div>

            <div id="review-editor" class="hidden space-y-4">
              <div>
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Scrubbed Customer Prompt</span>
                <div id="rev-prompt" class="mt-1 p-3 bg-slate-50 rounded-xl text-sm font-medium text-slate-900 border border-slate-200"></div>
              </div>

              <div>
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Original Model Output</span>
                <div id="rev-response" class="mt-1 p-3 bg-slate-50 rounded-xl text-xs text-slate-700 whitespace-pre-wrap border border-slate-200"></div>
              </div>

              <div>
                <label class="block text-xs font-bold text-emerald-700 uppercase tracking-wider mb-1">
                  Expert Corrected Response (Amharic / English)
                </label>
                <textarea id="rev-corrected" rows="4" class="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500 outline-none"></textarea>
              </div>

              <div class="flex items-center gap-3">
                <button onclick="promoteToGolden()" id="btn-promote" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition shadow-sm flex items-center gap-2">
                  <i class="fa-solid fa-star"></i> Promote to Golden Knowledge Base
                </button>
              </div>

              <div id="promote-feedback" class="hidden p-3 rounded-xl text-xs"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: REGULATORY COMPLIANCE -->
    <section id="panel-regulatory" class="tab-panel hidden space-y-6">
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <h2 class="text-base font-bold text-slate-900">Register Ethiopian Regulatory Source</h2>
          <p class="text-xs text-slate-500 mt-0.5">Whitelist approved portals (*.nbe.gov.et or *.gov.et). SHA-256 change monitoring detects revisions automatically.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Source Domain URL</label>
            <input type="url" id="reg-url" value="https://www.nbe.gov.et/directives/insurance" class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 outline-none" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Descriptive Label</label>
            <input type="text" id="reg-name" value="NBE Motor Directives" class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 outline-none" />
          </div>
        </div>

        <button onclick="registerRegulatorySource()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition">
          <i class="fa-solid fa-plus mr-1"></i> Register Source
        </button>
        <div id="reg-feedback" class="hidden p-3 rounded-xl text-xs"></div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Sources List -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 class="text-sm font-bold text-slate-900">Active Regulatory Portals</h3>
          <div id="sources-container" class="space-y-3">
            <p class="text-xs text-slate-400">Loading sources...</p>
          </div>
        </div>

        <!-- Pending Queue -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900">Pending Approval Queue</h3>
            <span id="pending-count-tag" class="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800">0 Diff(s)</span>
          </div>
          <div id="diffs-container" class="space-y-3 max-h-80 overflow-y-auto">
            <p class="text-xs text-slate-400">Loading diffs...</p>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 4: TRAINING DATA EXPORT -->
    <section id="panel-export" class="tab-panel hidden space-y-6">
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-bold text-slate-900">PII-Sanitized ShareGPT Training Dataset Export</h2>
            <p class="text-xs text-slate-500 mt-0.5">Download customer interaction records in HuggingFace / ShareGPT JSONL format with zero private data leakage.</p>
          </div>
          <a href="/api/v1/admin/export/training-data" download="training_data.jsonl" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition shadow-sm inline-flex items-center gap-2">
            <i class="fa-solid fa-download"></i> Download Scrubbed JSONL
          </a>
        </div>

        <!-- Security Guarantee Card -->
        <div class="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
          <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider">Zero-Leak Redaction Verified</span>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-emerald-900 font-medium">
            <div><i class="fa-solid fa-check text-emerald-600 mr-1"></i> CBE Bank Accounts</div>
            <div><i class="fa-solid fa-check text-emerald-600 mr-1"></i> Ethiopian 10-Digit TINs</div>
            <div><i class="fa-solid fa-check text-emerald-600 mr-1"></i> Kebele ID Numbers</div>
            <div><i class="fa-solid fa-check text-emerald-600 mr-1"></i> Ethiopian Phone Numbers</div>
          </div>
        </div>

        <div class="space-y-1">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Format Preview</span>
          <pre class="p-4 bg-slate-900 text-slate-100 rounded-xl text-xs font-mono overflow-x-auto leading-relaxed">
{"conversations": [
  {"from": "system", "value": "ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"},
  {"from": "human", "value": "የፖሊሲ ቁጥሬ POL-100234 ሲሆን የክፍያ ሁኔታዬን ንገረኝ"},
  {"from": "gpt", "value": "የይገባኛል ጥያቄዎ በጥናት ላይ ይገኛል። ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው..."}
]}
          </pre>
        </div>
      </div>
    </section>
  </main>

  <script>
    // Tab switching
    function switchTab(tab) {
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-emerald-600', 'text-emerald-600', 'font-bold');
        btn.classList.add('border-transparent', 'text-slate-500');
      });
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));

      document.getElementById('tab-btn-' + tab).classList.add('border-emerald-600', 'text-emerald-600', 'font-bold');
      document.getElementById('tab-btn-' + tab).classList.remove('border-transparent', 'text-slate-500');
      document.getElementById('panel-' + tab).classList.remove('hidden');

      if (tab === 'review') loadReviewInteractions();
      if (tab === 'regulatory') { loadRegulatorySources(); loadPendingDiffs(); }
    }

    // 1. Ingestion & Search
    async function handleUpload(e) {
      e.preventDefault();
      const fileInput = document.getElementById('doc-file');
      const category = document.getElementById('doc-category').value;
      const feedback = document.getElementById('upload-feedback');
      const btn = document.getElementById('btn-upload');

      if (!fileInput.files.length) return;

      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('category', category);

      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Indexing...';

      try {
        const res = await fetch('/api/v1/kb/documents/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
          feedback.className = 'p-3 rounded-xl text-xs bg-emerald-50 text-emerald-800 border border-emerald-200';
          feedback.innerHTML = `<strong>Uploaded successfully!</strong> Tracking Job: <code class="font-mono">${data.jobId}</code>`;
          feedback.classList.remove('hidden');
          pollJob(data.jobId);
        } else {
          throw new Error(data.detail || 'Upload failed');
        }
      } catch (err) {
        feedback.className = 'p-3 rounded-xl text-xs bg-rose-50 text-rose-800 border border-rose-200';
        feedback.innerText = err.message;
        feedback.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Vectorize';
      }
    }

    async function pollJob(jobId) {
      const card = document.getElementById('job-status-card');
      card.classList.remove('hidden');
      try {
        const res = await fetch('/api/v1/kb/documents/jobs/' + jobId);
        const data = await res.json();
        document.getElementById('job-filename').innerText = data.filename;
        const badge = document.getElementById('job-badge');
        badge.innerText = data.status;
        if (data.status === 'COMPLETED') {
          badge.className = 'px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800';
          document.getElementById('job-chunks').innerText = data.chunks_indexed || 0;
          document.getElementById('job-chars').innerText = data.report?.total_chars || 0;
        } else if (data.status === 'PROCESSING') {
          badge.className = 'px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800';
          setTimeout(() => pollJob(jobId), 1500);
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function searchKnowledge() {
      const q = document.getElementById('kb-query').value.trim();
      const container = document.getElementById('search-results');
      if (!q) return;

      container.innerHTML = '<p class="text-xs text-slate-400 text-center py-4"><i class="fa-solid fa-spinner animate-spin mr-1"></i> Generating straightforward grounded answer...</p>';
      try {
        // Run both direct chat answer and vector chunk search in parallel
        const [chatRes, kbRes] = await Promise.all([
          fetch('/api/v1/chat/messages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: q })
          }),
          fetch('/api/v1/kb/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query: q, top_k: 2 })
          })
        ]);

        const chatData = await chatRes.json();
        const kbData = await kbRes.json();

        // Split reply and legal disclaimer
        let directAnswer = chatData.reply || '';
        let disclaimer = 'ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው';
        if (directAnswer.includes('---')) {
          const parts = directAnswer.split('---');
          directAnswer = parts[0].trim();
          disclaimer = parts[1].trim();
        }

        const providerName = (chatData.provider || 'mock').toUpperCase();
        const modelName = chatData.model || 'mock';
        const isGemini = providerName === 'GEMINI';
        const badgeClass = isGemini ? 'bg-blue-50 text-blue-800 border-blue-300' : 'bg-amber-50 text-amber-800 border-amber-300';
        const badgeIcon = isGemini ? 'fa-solid fa-sparkles text-blue-600' : 'fa-solid fa-microchip text-amber-600';
        const badgeLabel = isGemini ? `Google Gemini (${modelName})` : `Local Mock Engine`;

        let html = `
          <!-- Straightforward Direct Answer Card -->
          <div class="p-4 bg-emerald-50 border border-emerald-300 rounded-xl space-y-2 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                <i class="fa-solid fa-circle-check text-emerald-600"></i> ቀጥተኛ መልስ (Straightforward Answer)
              </span>
              <span class="text-[11px] font-bold ${badgeClass} border px-2 py-0.5 rounded-full flex items-center gap-1">
                <i class="${badgeIcon}"></i> ${badgeLabel}
              </span>
            </div>
            <p class="text-sm font-semibold text-slate-900 leading-relaxed font-sans">${directAnswer}</p>
            <p class="text-[11px] text-slate-500 italic border-t border-emerald-200 pt-1.5">${disclaimer}</p>
          </div>
        `;

        if (kbData && kbData.length > 0) {
          html += `
            <div class="space-y-2 pt-1">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">የሰነድ ማስረጃ (Source Citations)</span>
              ${kbData.map(item => `
                <details class="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs group">
                  <summary class="font-semibold text-slate-700 cursor-pointer flex items-center justify-between select-none">
                    <span><i class="fa-solid fa-file-lines text-slate-400 mr-1.5"></i> ${item.document_id} (${item.category})</span>
                    <span class="text-emerald-700 font-bold">${(item.score * 100).toFixed(1)}% Match</span>
                  </summary>
                  <div class="mt-2 text-slate-700 whitespace-pre-wrap leading-relaxed max-h-36 overflow-y-auto border-t border-slate-200 pt-2 font-mono text-[11px] bg-white p-2 rounded">
                    ${item.content_text}
                  </div>
                </details>
              `).join('')}
            </div>
          `;
        }

        container.innerHTML = html;
      } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-500 text-center">Search failed: ' + e.message + '</p>';
      }
    }

    // 2. Review Desk
    let currentInteractions = [];
    let selectedInteractionId = null;

    async function loadReviewInteractions() {
      const filter = document.getElementById('review-filter').value;
      const list = document.getElementById('interactions-list');
      const url = filter === 'DOWN' ? '/api/v1/admin/review/interactions?rating=DOWN' : '/api/v1/admin/review/interactions';
      try {
        const res = await fetch(url);
        currentInteractions = await res.json();
        document.getElementById('badge-flagged').innerText = currentInteractions.length;
        if (currentInteractions.length > 0) document.getElementById('badge-flagged').classList.remove('hidden');

        if (!currentInteractions.length) {
          list.innerHTML = '<p class="text-xs text-slate-400 p-6 text-center">No interactions matching filter.</p>';
          return;
        }

        list.innerHTML = currentInteractions.map(item => `
          <div onclick="selectInteraction('${item.id}')" class="p-4 cursor-pointer hover:bg-slate-50 transition space-y-1.5">
            <div class="flex items-center justify-between text-xs">
              <span class="font-mono text-slate-500">${item.customer_id}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${item.rating === 'DOWN' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'}">
                ${item.rating === 'DOWN' ? '👎 DOWNVOTED' : '👍 RATED'}
              </span>
            </div>
            <p class="text-xs font-semibold text-slate-900 truncate">"${item.scrubbed_prompt}"</p>
            ${item.feedback_comment ? `<p class="text-[11px] text-amber-600 italic">"${item.feedback_comment}"</p>` : ''}
            ${item.promoted_to_golden ? '<span class="text-[10px] font-bold text-emerald-600"><i class="fa-solid fa-star"></i> Promoted to Golden KB</span>' : ''}
          </div>
        `).join('');
      } catch (e) {
        list.innerHTML = '<p class="text-xs text-rose-500 p-6 text-center">Failed to load interactions.</p>';
      }
    }

    function selectInteraction(id) {
      selectedInteractionId = id;
      const item = currentInteractions.find(i => i.id === id);
      if (!item) return;

      document.getElementById('review-placeholder').classList.add('hidden');
      document.getElementById('review-editor').classList.remove('hidden');
      document.getElementById('rev-prompt').innerText = item.scrubbed_prompt;
      document.getElementById('rev-response').innerText = item.scrubbed_response;
      document.getElementById('rev-corrected').value = item.scrubbed_response;
      document.getElementById('promote-feedback').classList.add('hidden');
    }

    async function promoteToGolden() {
      if (!selectedInteractionId) return;
      const corrected = document.getElementById('rev-corrected').value.trim();
      const feedback = document.getElementById('promote-feedback');
      const btn = document.getElementById('btn-promote');
      if (!corrected) return;

      btn.disabled = true;
      try {
        const res = await fetch(`/api/v1/admin/review/interactions/${selectedInteractionId}/promote`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({corrected_answer: corrected, reviewer: 'admin@insurtech.et'})
        });
        const data = await res.json();
        if (res.ok) {
          feedback.className = 'p-3 rounded-xl text-xs bg-emerald-50 text-emerald-800 border border-emerald-200';
          feedback.innerHTML = `<strong>Promoted to Golden KB!</strong> Chunk ID: <code class="font-mono">${data.promoted_chunk_id}</code>`;
          feedback.classList.remove('hidden');
          loadReviewInteractions();
        } else {
          throw new Error(data.detail || 'Promotion failed');
        }
      } catch (err) {
        feedback.className = 'p-3 rounded-xl text-xs bg-rose-50 text-rose-800 border border-rose-200';
        feedback.innerText = err.message;
        feedback.classList.remove('hidden');
      } finally {
        btn.disabled = false;
      }
    }

    // 3. Regulatory
    async function loadRegulatorySources() {
      const container = document.getElementById('sources-container');
      try {
        const res = await fetch('/api/v1/admin/sources');
        const data = await res.json();
        if (!data.length) {
          container.innerHTML = '<p class="text-xs text-slate-400">No regulatory sources registered.</p>';
          return;
        }
        container.innerHTML = data.map(s => `
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between">
            <div>
              <p class="text-xs font-bold text-slate-900">${s.name}</p>
              <p class="text-[11px] text-slate-400 truncate max-w-xs font-mono">${s.url}</p>
            </div>
            <button onclick="triggerCheck('${s.id}')" class="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition">
              Check Updates
            </button>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-500">Failed to load sources.</p>';
      }
    }

    async function registerRegulatorySource() {
      const url = document.getElementById('reg-url').value.trim();
      const name = document.getElementById('reg-name').value.trim();
      const feedback = document.getElementById('reg-feedback');

      try {
        const res = await fetch('/api/v1/admin/sources', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url, name})
        });
        const data = await res.json();
        if (res.ok) {
          feedback.className = 'p-3 rounded-xl text-xs bg-emerald-50 text-emerald-800 border border-emerald-200';
          feedback.innerText = `Source '${data.name}' registered successfully.`;
          feedback.classList.remove('hidden');
          loadRegulatorySources();
        } else {
          throw new Error(data.detail || 'Registration rejected.');
        }
      } catch (err) {
        feedback.className = 'p-3 rounded-xl text-xs bg-rose-50 text-rose-800 border border-rose-200';
        feedback.innerText = err.message;
        feedback.classList.remove('hidden');
      }
    }

    async function triggerCheck(sourceId) {
      try {
        const res = await fetch('/api/v1/admin/regulatory/fetch', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({source_id: sourceId})
        });
        const data = await res.json();
        alert(data.status === 'CHANGE_DETECTED' ? 'Change detected! New diff queued for review.' : 'Verified: Upstream matches current hash (' + data.status + ')');
        loadPendingDiffs();
      } catch (e) {
        alert('Check failed: ' + e.message);
      }
    }

    async function loadPendingDiffs() {
      const container = document.getElementById('diffs-container');
      try {
        const res = await fetch('/api/v1/admin/regulatory/pending');
        const data = await res.json();
        document.getElementById('pending-count-tag').innerText = data.length + ' Diff(s)';
        document.getElementById('badge-diffs').innerText = data.length;
        if (data.length > 0) document.getElementById('badge-diffs').classList.remove('hidden');

        if (!data.length) {
          container.innerHTML = '<p class="text-xs text-slate-400 py-6 text-center">No pending regulatory diffs.</p>';
          return;
        }

        container.innerHTML = data.map(diff => `
          <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="font-bold text-slate-900 truncate max-w-[200px]">${diff.target_url}</span>
              <span class="text-[10px] text-slate-400 font-mono">Hash: ${diff.content_hash.slice(0, 8)}...</span>
            </div>
            <pre class="p-2 bg-white rounded text-[11px] font-mono text-slate-700 max-h-20 overflow-y-auto">${diff.content_snapshot}</pre>
            <div class="flex justify-end">
              <button onclick="approveDiff('${diff.id}')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold">
                Approve & Vectorize
              </button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<p class="text-xs text-rose-500">Failed to load diffs.</p>';
      }
    }

    async function approveDiff(diffId) {
      try {
        const res = await fetch(`/api/v1/admin/regulatory/pending/${diffId}/approve`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({reviewer: 'compliance@insurtech.et'})
        });
        const data = await res.json();
        alert('Diff approved! Indexed ' + data.chunks_indexed + ' chunks.');
        loadPendingDiffs();
      } catch (e) {
        alert('Approval failed: ' + e.message);
      }
    }

    // Initialize
    loadRegulatorySources();
  </script>
</body>
</html>
"""

@router.get("/admin", response_class=HTMLResponse)
async def serve_admin_portal():
    """Serve the Web Admin Portal dashboard."""
    return HTMLResponse(content=ADMIN_HTML)


@router.get("/api/v1/kb/sample-pdf")
async def download_sample_amharic_pdf():
    """Provide a 1-page sample Amharic insurance policy PDF for testing."""
    import os
    pdf_path = "sample_amharic_policy.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "insuretech-ai/sample_amharic_policy.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="sample_amharic_policy.pdf"
    )
