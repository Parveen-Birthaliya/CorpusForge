/* app.js – CorpusForge frontend logic */
(() => {
'use strict';

// ─── Element References ──────────────────────────────────────────
const uploadView   = document.getElementById('upload-view');
const resultsView  = document.getElementById('results-view');
const dropzone     = document.getElementById('dropzone');
const fileInput    = document.getElementById('file-input');
const fileList     = document.getElementById('file-list');
const browseBtn    = document.getElementById('browse-btn');
const runBtn       = document.getElementById('run-btn');
const btnText      = document.getElementById('btn-text');
const btnLoader    = document.getElementById('btn-loader');
const uploadHint   = document.getElementById('upload-hint');
const newRunBtn    = document.getElementById('new-run-btn');
const copyCleanBtn = document.getElementById('copy-clean-btn');
const downloadZip  = document.getElementById('download-zip');
const downloadJsonl= document.getElementById('download-jsonl');
const warningsBar  = document.getElementById('warnings-bar');
const errorsList   = document.getElementById('errors-list');

// Stats
const statLoaded   = document.getElementById('stat-loaded');
const statAccepted = document.getElementById('stat-accepted');
const statRejected = document.getElementById('stat-rejected');
const statFinal    = document.getElementById('stat-final');
const statExact    = document.getElementById('stat-exact');
const statNear     = document.getElementById('stat-near');
const statAccRate  = document.getElementById('stat-acc-rate');
const statComp     = document.getElementById('stat-comp');

// Inspector panels
const rawText      = document.getElementById('raw-text');
const cleanedText  = document.getElementById('cleaned-text');
const garbageList  = document.getElementById('garbage-list');
const dupList      = document.getElementById('duplicates-list');

// ─── State ───────────────────────────────────────────────────────
let selectedFiles = [];

// ─── File Handling ───────────────────────────────────────────────
browseBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
    addFiles(Array.from(e.target.files));
    fileInput.value = '';          // reset so re-selecting same file works
});

dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    addFiles(Array.from(e.dataTransfer.files));
});

function addFiles(incoming) {
    incoming.forEach(f => {
        if (!selectedFiles.find(x => x.name === f.name && x.size === f.size)) {
            selectedFiles.push(f);
        }
    });
    renderFileList();
}

function removeFile(idx) {
    selectedFiles.splice(idx, 1);
    renderFileList();
}
window.removeFile = removeFile; // expose for inline onclick

function renderFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach((f, i) => {
        const kb   = (f.size / 1024).toFixed(1);
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span>📄 ${escHtml(f.name)} <small style="color:var(--text-muted)">${kb} KB</small></span>
            <button type="button" class="remove-btn" onclick="removeFile(${i})">✕</button>
        `;
        fileList.appendChild(item);
    });

    if (selectedFiles.length > 0) {
        runBtn.disabled = false;
        uploadHint.textContent = `${selectedFiles.length} file(s) ready.`;
    } else {
        runBtn.disabled = true;
        uploadHint.textContent = 'Select at least one file to begin.';
    }
}

// ─── Run Pipeline ─────────────────────────────────────────────────
runBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    // Loading state
    btnText.textContent = 'Processing…';
    btnLoader.classList.remove('hidden');
    runBtn.disabled = true;

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append('files', f));

    try {
        const res  = await fetch('/api/clean', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);

        renderResults(data);
        showView('results');

    } catch (err) {
        alert('Pipeline error: ' + err.message);
    } finally {
        btnText.textContent = 'Run Pipeline';
        btnLoader.classList.add('hidden');
        runBtn.disabled = false;
    }
});

// ─── Render Results ───────────────────────────────────────────────
function renderResults(d) {
    const r = d.report;

    // Stats
    statLoaded.textContent   = r.total_loaded   ?? '–';
    statAccepted.textContent = r.total_accepted  ?? '–';
    statRejected.textContent = r.total_rejected  ?? '–';
    statFinal.textContent    = r.total_after_dedup ?? '–';
    statExact.textContent    = r.exact_removed   ?? '–';
    statNear.textContent     = r.near_removed    ?? '–';
    statAccRate.textContent  = r.acceptance_rate ?? '–';
    statComp.textContent     = r.avg_compression ?? '–';

    // Before / After
    rawText.textContent     = d.raw_preview     || '(no content)';
    cleanedText.textContent = d.cleaned_preview || '(no content)';

    // Garbage list
    garbageList.innerHTML = '';
    if (d.garbage_lines && d.garbage_lines.length > 0) {
        d.garbage_lines.forEach(line => {
            const li = document.createElement('li');
            li.textContent = line;
            garbageList.appendChild(li);
        });
    } else {
        garbageList.innerHTML = '<li class="empty-msg">No garbage lines detected — output is already clean!</li>';
    }

    // Duplicates
    dupList.innerHTML = '';
    if (d.duplicate_previews && d.duplicate_previews.length > 0) {
        d.duplicate_previews.forEach(dup => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="dup-id">Doc: ${escHtml(dup.id)}</span>${escHtml(dup.text)}`;
            dupList.appendChild(li);
        });
    } else {
        dupList.innerHTML = '<li class="empty-msg">No duplicates found in this batch.</li>';
    }

    // Warnings
    if (d.errors && d.errors.length > 0) {
        warningsBar.classList.remove('hidden');
        errorsList.innerHTML = d.errors.map(e => `<li>${escHtml(e)}</li>`).join('');
    } else {
        warningsBar.classList.add('hidden');
    }

    // Downloads
    downloadZip.href   = d.download_zip_url   || '#';
    downloadJsonl.href = d.download_jsonl_url || '#';
}

// ─── Copy cleaned text ────────────────────────────────────────────
copyCleanBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(cleanedText.textContent).then(() => {
        copyCleanBtn.textContent = '✓';
        setTimeout(() => {
            copyCleanBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
        }, 2000);
    });
});

// ─── Tab switching ────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');

        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => {
            p.classList.remove('active');
            p.classList.add('hidden');
        });

        btn.classList.add('active');
        const panel = document.getElementById('tab-' + target);
        panel.classList.remove('hidden');
        panel.classList.add('active');
    });
});

// ─── New Run ──────────────────────────────────────────────────────
newRunBtn.addEventListener('click', () => {
    selectedFiles = [];
    renderFileList();
    showView('upload');
    // Reset first tab
    document.querySelectorAll('.tab-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
    document.querySelectorAll('.tab-panel').forEach((p, i) => {
        p.classList.toggle('active', i === 0);
        p.classList.toggle('hidden',  i !== 0);
    });
});

// ─── Helpers ──────────────────────────────────────────────────────
function showView(name) {
    uploadView.classList.toggle('active',  name === 'upload');
    uploadView.classList.toggle('hidden',  name !== 'upload');
    resultsView.classList.toggle('active', name === 'results');
    resultsView.classList.toggle('hidden', name !== 'results');
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

})();
