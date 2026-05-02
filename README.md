# CorpusForge 🔨

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)]()

**A professional-grade, heuristic text cleaning pipeline designed for AI workloads.**

CorpusForge transforms raw, noisy documents (PDFs, TXT files) into high-quality, deduplicated, and consistently formatted text corpora perfectly suited for LLM fine-tuning, RAG pipelines, and embedding models. 

## What it does

When scraping or downloading data, you often encounter:
- Corrupted Unicode and weird mojibake (e.g. `â€œ`)
- Navigation menus, URLs, and boilerplate text
- PDF hyphenation splitting words across lines
- Documents in the wrong language
- Extremely repetitive or spammy content

CorpusForge fixes this using a deterministic, rule-based approach—without relying on heavy ML models for the actual text cleaning. 

## Features (Built So Far)
- **Robust Loaders:** Extracts text from PDFs (via `PyMuPDF`) and resolves tricky text encodings (like `utf-8-sig` for BOM).
- **Heuristic Cleaner:** Normalizes Unicode (NFC), strips invisible control characters, rejoins PDF line breaks, and smartly removes URLs, page numbers, and erratic whitespace.
- **Quality Filters:** A strict three-gate system that rejects documents based on:
    1. **Length:** Drops documents that are too short to be useful.
    2. **Language:** Drops documents not matching the target language (via `langdetect`).
    3. **Repetition:** Drops spammy documents using n-gram frequency analysis.

## Installation

We recommend using a virtual environment:

```bash
git clone https://github.com/your-username/CorpusForge
cd CorpusForge
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start (Python API)

While the CLI is under development, you can use CorpusForge programmatically:

```python
from pathlib import Path
from corpusforge.loaders import TxtLoader, PdfLoader
from corpusforge.cleaners import HeuristicCleaner
from corpusforge.filters import QualityFilter

# 1. Load document
loader = PdfLoader()
doc = loader.load(Path("data/raw/sample.pdf"))

# 2. Clean text
cleaner = HeuristicCleaner()
clean_result = cleaner.clean(doc)

# 3. Filter for quality
quality_gate = QualityFilter(min_chars=100, target_lang="en", max_rep=0.20)
filter_result = quality_gate.evaluate(clean_result)

if filter_result.status == "accept":
    print("Document passed all quality gates!")
    print(clean_result.cleaned_text)
else:
    print(f"Rejected: {filter_result.reject_reason}")
```

## Project Roadmap

We are building CorpusForge component by component. Here is the current progress:

| Component | Description | Status |
| :--- | :--- | :--- |
| **01** | Project Scaffold & Architecture | ✅ Done |
| **02** | Input Loaders (TXT, PDF) | ✅ Done |
| **03** | Heuristic Text Cleaner | ✅ Done |
| **04** | Quality Gate Filters | ✅ Done |
| **05** | Exact & Near Deduplication (MinHash) | ✅ Done |
| **06** | Output Formatter (JSONL) | ✅ Done |
| **07** | Command Line Interface (CLI) | ✅ Done |
| **08** | Web UI (Gradio) | ✅ Done |

## License
MIT
