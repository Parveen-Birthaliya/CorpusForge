document.addEventListener('DOMContentLoaded', () => {
    // ── DOM Elements ──────────────────────────────────────────────────
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const form = document.getElementById('pipeline-form');
    
    const viewUpload = document.getElementById('upload-view');
    const viewResults = document.getElementById('results-view');
    const btnLoader = document.getElementById('btn-loader');
    const btnText = document.querySelector('.btn-text');
    
    // Sliders
    const minChars = document.getElementById('min_chars');
    const minCharsVal = document.getElementById('min_chars_val');
    const maxRep = document.getElementById('max_rep');
    const maxRepVal = document.getElementById('max_rep_val');

    // State
    let selectedFiles = [];

    // ── Event Listeners ───────────────────────────────────────────────
    
    // Slider values
    minChars.addEventListener('input', (e) => minCharsVal.textContent = e.target.value);
    maxRep.addEventListener('input', (e) => maxRepVal.textContent = e.target.value);

    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    // File input click
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });

    function handleFiles(files) {
        selectedFiles = Array.from(files);
        renderFileList();
    }

    function renderFileList() {
        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            
            // Format size
            const size = (file.size / 1024).toFixed(1) + ' KB';
            
            item.innerHTML = `
                <span>📄 ${file.name} <span style="color:var(--text-muted);font-size:11px;margin-left:8px;">${size}</span></span>
                <button type="button" class="icon-btn" onclick="removeFile(${index})" style="color:var(--error);">✕</button>
            `;
            fileList.appendChild(item);
        });
    }

    window.removeFile = (index) => {
        selectedFiles.splice(index, 1);
        renderFileList();
    };

    // ── Form Submission ───────────────────────────────────────────────
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            alert("Please select at least one .txt or .pdf file.");
            return;
        }

        // UI Loading State
        btnLoader.classList.remove('hidden');
        btnText.textContent = 'Processing...';
        document.getElementById('run-btn').disabled = true;

        const formData = new FormData(form);
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // Ensure checkboxes that aren't checked send "false" because FormData omits them
        if (!formData.has('skip_near_dedup')) formData.append('skip_near_dedup', 'false');
        else formData.set('skip_near_dedup', 'true');
        
        if (!formData.has('enable_advanced_pii')) formData.append('enable_advanced_pii', 'false');
        else formData.set('enable_advanced_pii', 'true');
        
        if (!formData.has('enable_ocr')) formData.append('enable_ocr', 'false');
        else formData.set('enable_ocr', 'true');

        try {
            const response = await fetch('/api/clean', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Failed to process files");
            }

            showResults(data);

        } catch (error) {
            alert("Error: " + error.message);
        } finally {
            // Reset UI Loading State
            btnLoader.classList.add('hidden');
            btnText.textContent = 'Run Pipeline';
            document.getElementById('run-btn').disabled = false;
        }
    });

    // ── Show Results ──────────────────────────────────────────────────
    function showResults(data) {
        // Swap Views
        viewUpload.classList.remove('active');
        viewUpload.classList.add('hidden');
        viewResults.classList.remove('hidden');
        viewResults.classList.add('active');

        // Populate Stats
        document.getElementById('stat-loaded').textContent = data.report.total_loaded;
        document.getElementById('stat-accepted').textContent = data.report.total_accepted;
        document.getElementById('stat-rejected').textContent = data.report.total_rejected;
        document.getElementById('stat-final').textContent = data.report.total_after_dedup;
        
        document.getElementById('stat-exact').textContent = data.report.exact_removed;
        document.getElementById('stat-near').textContent = data.report.near_removed;
        document.getElementById('stat-acc-rate').textContent = data.report.acceptance_rate;
        document.getElementById('stat-comp').textContent = data.report.avg_compression;

        // Preview Text
        document.getElementById('preview-text').textContent = data.preview_text || "No preview available.";

        // Download Links
        document.getElementById('download-zip').href = data.download_zip_url;
        document.getElementById('download-jsonl').href = data.download_jsonl_url;

        // Errors
        const errorsContainer = document.getElementById('errors-container');
        const errorsList = document.getElementById('errors-list');
        if (data.errors && data.errors.length > 0) {
            errorsContainer.classList.remove('hidden');
            errorsList.innerHTML = data.errors.map(err => `<li>${err}</li>`).join('');
        } else {
            errorsContainer.classList.add('hidden');
        }
    }

    // ── Actions ───────────────────────────────────────────────────────
    document.getElementById('new-run-btn').addEventListener('click', () => {
        viewResults.classList.remove('active');
        viewResults.classList.add('hidden');
        viewUpload.classList.remove('hidden');
        viewUpload.classList.add('active');
        selectedFiles = [];
        renderFileList();
    });

    document.getElementById('copy-btn').addEventListener('click', () => {
        const text = document.getElementById('preview-text').textContent;
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.getElementById('copy-btn');
            btn.innerHTML = '✓';
            setTimeout(() => {
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
            }, 2000);
        });
    });
});
