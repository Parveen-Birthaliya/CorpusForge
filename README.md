# CorpusForge ⚡

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Status: Production](https://img.shields.io/badge/status-production-green)](/)

> **A professional-grade, hybrid NLP corpus cleaning pipeline for AI/NLP workloads.**

CorpusForge transforms raw, noisy documents (PDFs, TXT files) into high-quality, deduplicated, AI-ready text corpora, perfect for LLM fine-tuning, RAG pipelines, and embedding models. It features a **5-stage sequential pipeline**, a **hybrid heuristic + ML cleaning system**, and a **modern Inspection Web UI** built with FastAPI.

---

## ✨ What It Does

Raw scraped and digitised text is full of noise. CorpusForge fixes all of it:

| Problem | Fix |
|---|---|
| BOM chars, mojibake (`â€œ`) | Unicode normalisation (NFC) |
| Headers, footers, chapter markers | Structural boilerplate removal |
| HTML tags, URLs, navigation menus | Web noise stripping |
| Email addresses, phone numbers | Heuristic PII removal |
| Symbol-heavy lines (`@@@ ### $$$`) | Symbol-ratio line filter (>40% symbols dropped) |
| PDF hyphenation (`exam-⏎ple`) | Hyphenation rejoiner |
| Fragmented sentences across lines | Sentence joiner (no-punctuation merge) |
| OCR corruption (`l0rem 1psum`) | SymSpell ML correction (always-on) |
| Personal names, orgs, locations | spaCy NER redaction (always-on) |
| Exact duplicate paragraphs | MD5 exact deduplication |
| Near-duplicate documents | MinHash LSH near-deduplication |
| Short / non-English / spammy docs | Length · Language · Repetition filters |

---

## 🏗️ Pipeline Architecture

```
 ┌────────────────────────────────────────────────────────────┐
 │                    CorpusForge Pipeline                    │
 └────────────────────────────────────────────────────────────┘

 [1] Load          TxtLoader · PdfLoader (PyMuPDF)
       ↓
 [2] Heuristic     Unicode → Structural → Whitespace
     Clean         → Intra-doc dedup → Symbol filter
       ↓
 [3] ML Clean      spaCy NER (PII redaction)
                   SymSpell (OCR auto-correction)
       ↓
 [4] Filter        Length Gate → Language Gate → Repetition Gate
       ↓
 [5] Dedup         Exact (MD5) → Near (MinHash LSH)
       ↓
 [6] Output        JSONL + per-doc TXT + ZIP archive
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- `spaCy` English model

### Installation

```bash
git clone https://github.com/your-username/CorpusForge
cd CorpusForge

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

# Install all dependencies
pip install -r requirements.txt

# Download the spaCy model (required for PII redaction)
python -m spacy download en_core_web_sm
```

### Start the Web UI

```bash
bash restart.sh
```

Then open **http://localhost:7860** in your browser.

---

## 🌐 Web UI — Corpus Inspection Dashboard

The Web UI is built with **FastAPI + Vanilla HTML/CSS/JS** (no framework). It provides a full corpus inspection experience:

- **Drag & Drop Upload** — supports `.txt` and `.pdf` files
- **Live Stats Bar** — loaded / accepted / rejected / final docs, exact/near dups, acceptance rate, avg compression
- **Before / After Tab** — side-by-side raw vs. cleaned text view
- **Garbage Removed Tab** — every line deleted by the heuristics, shown in red
- **Duplicate Contents Tab** — text previews of deduplicated documents
- **Direct Downloads** — individual `.jsonl` and `.zip` archive

---

## 💻 Command Line Interface (CLI)

For batch processing of entire directories:

```bash
PYTHONPATH=. python -m src.corpusforge.cli \
    --input  data/raw      \
    --output data/cleaned  \
    --lang   en
```

---

## 🐍 Python API

Integrate CorpusForge into your own scripts:

```python
from pathlib import Path
from src.corpusforge.loaders import TxtLoader, PdfLoader
from src.corpusforge.cleaners import HeuristicCleaner
from src.corpusforge.filters import QualityFilter
from src.corpusforge.dedup import Deduplicator
from src.corpusforge.output import CorpusFormatter

# 1. Load
loader = TxtLoader()
doc    = loader.load(Path("data/raw/sample.txt"))

# 2. Clean (ML cleaners always-on)
cleaner      = HeuristicCleaner(enable_advanced_pii=True, enable_ocr=True)
clean_result = cleaner.clean(doc)

# 3. Filter
quality = QualityFilter(min_chars=100, target_lang="en", max_rep=0.20)
fr      = quality.evaluate(clean_result)

# 4. Dedup
deduplicator = Deduplicator()
dedup_result = deduplicator.run([fr], {doc.doc_id: clean_result.cleaned_text})

# 5. Output
formatter = CorpusFormatter(Path("data/cleaned"))
report    = formatter.write([clean_result], [fr], dedup_result, {})
print(f"Accepted: {report.total_accepted} | Compression: {report.avg_compression:.1%}")
```

---

## 📁 Project Structure

```
CorpusForge/
├── frontend/                  # Web UI (HTML + CSS + JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── src/corpusforge/
│   ├── cleaners/
│   │   ├── heuristic_cleaner.py      # Pipeline orchestrator
│   │   ├── unicode_cleaner.py        # NFC + control char removal
│   │   ├── structural_cleaner.py     # Boilerplate + symbol filter
│   │   ├── whitespace_cleaner.py     # Whitespace + sentence joiner
│   │   ├── intra_dedup.py            # Intra-document dedup
│   │   ├── advanced_pii_cleaner.py   # spaCy NER PII redaction
│   │   └── ocr_cleaner.py            # SymSpell OCR correction
│   ├── dedup/
│   │   ├── exact_dedup.py            # MD5-based deduplication
│   │   └── minhash_dedup.py          # MinHash LSH near-dedup
│   ├── filters/
│   │   ├── length_filter.py
│   │   ├── language_filter.py        # langdetect
│   │   └── repetition_filter.py      # N-gram repetition score
│   ├── loaders/
│   │   ├── txt_loader.py
│   │   └── pdf_loader.py             # PyMuPDF
│   ├── output/
│   │   └── formatter.py              # JSONL + TXT + ZIP export
│   ├── server.py                     # FastAPI REST backend
│   ├── app.py                        # Legacy Gradio UI (kept for reference)
│   ├── cli.py                        # CLI entry point
│   └── models.py                     # Dataclasses (Document, CleanResult …)
├── data/
│   └── raw/                          # Sample test documents
├── tests/                            # pytest test suite
├── requirements.txt
├── pyproject.toml
├── restart.sh                        # One-click server restart
└── start_server.sh
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `PyMuPDF` | PDF text extraction |
| `langdetect` | Language identification |
| `datasketch` | MinHash LSH near-deduplication |
| `spacy` (+ `en_core_web_sm`) | Named Entity Recognition for PII |
| `symspellpy` | OCR error correction |
| `fastapi` | REST API backend |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload handling |
| `gradio` | Legacy Web UI (kept) |

---

## 🧪 Running Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 📊 Component Roadmap

| # | Component | Status |
|---|---|---|
| 01 | Project Scaffold & Architecture | ✅ Done |
| 02 | Input Loaders (TXT, PDF) | ✅ Done |
| 03 | Heuristic Text Cleaner (Unicode, Structural, Whitespace, Intra-dedup) | ✅ Done |
| 04 | Quality Gate Filters (Length, Language, Repetition) | ✅ Done |
| 05 | Exact & Near Deduplication (MD5 + MinHash LSH) | ✅ Done |
| 06 | Output Formatter (JSONL + TXT + ZIP) | ✅ Done |
| 07 | Command Line Interface (CLI) | ✅ Done |
| 08 | Advanced ML Cleaners (spaCy NER + SymSpell OCR) | ✅ Done |
| 09 | FastAPI Backend + Custom Inspection Web UI | ✅ Done |

---

## 📄 License

MIT © Parveen Birthaliya
