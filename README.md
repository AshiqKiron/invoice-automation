# 🧾 Invoice Automation Pipeline

AI-powered Japanese invoice intake automation for Sample Trading Co., Ltd.
Built for the AI Agent Engineer take-home assignment.

**[🌐 View Demo Site](https://ashiqkiron.github.io/invoice-automation/)** | **[▶ Open in Codespaces](https://codespaces.new/ashiqkiron/invoice-automation)**

---

## Quick Start (Codespaces – Recommended)

Zero local setup required. All 12 sample invoices and dependencies are pre-configured.

1. Click **[▶ Open in Codespaces](https://codespaces.new/ashiqkiron/invoice-automation)**
2. Wait ~30 seconds for post-create setup (installs Tesseract OCR + Python deps)
3. Create your environment file:

        cp .env.example .env

4. Add your free [Groq API key](https://console.groq.com):

        echo "GROQ_API_KEY=gsk_your_key_here" >> .env

5. Run the full pipeline:

        ./run.sh

6. Follow the CLI prompts to review each invoice (y = register, n = skip, q = quit)

> 💡 **Pro tip:** Set GROQ_API_KEY as a [Codespaces repository secret](https://github.com/ashiqkiron/invoice-automation/settings/secrets/codespaces) so it is injected automatically without editing .env.

---

## Local Setup

### Prerequisites

- Python 3.9+
- Tesseract OCR with Japanese language pack

Installation commands by platform:

    # macOS
    brew install tesseract tesseract-lang

    # Ubuntu / Debian
    sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn

    # Windows (Chocolatey)
    choco install tesseract

### Install and Run

    git clone https://github.com/ashiqkiron/invoice-automation.git
    cd invoice-automation
    pip install -r requirements.txt
    cp .env.example .env
    chmod +x run.sh
    ./run.sh

---

## Project Structure

    invoice-automation/
    ├── run.sh                 # Single-command entry point (starts API + runs pipeline)
    ├── main.py                # Orchestrator with human-in-the-loop review
    ├── accounting_api.py      # Mock accounting API (DO NOT MODIFY)
    ├── config.py              # Environment configuration
    ├── .env.example           # Template for environment variables
    ├── services/
    │   ├── ocr_engine.py      # PDF text layer (PyMuPDF) + image OCR (Tesseract JPN)
    │   ├── llm_parser.py      # Groq/Ollama structured JSON extraction with retry/fallback
    │   ├── partner_matcher.py # Fuzzy matching against supplier master aliases
    │   └── api_client.py      # Accounting API HTTP client with error handling
    ├── utils/
    │   └── validators.py      # Field correction + tax/amount recalculation
    ├── invoices/              # 12 sample Japanese invoices (PDF + scanned images)
    ├── docs/                  # GitHub Pages demo site
    ├── demo/                  # Screenshots for submission
    ├── SUBMISSION.md          # Assignment submission document
    └── README.md              # This file

---

## How It Works

    Invoice File (PDF/JPG)
           │
           ▼
    ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
    │  OCR Engine   │───▶│   LLM Parser    │───▶│ Partner Matcher  │
    │ Tesseract+JPN │    │ Qwen 3.6 + FB   │    │ difflib fuzzy    │
    └──────────────┘    └─────────────────┘    └────────┬─────────┘
                                                         │
           ┌─────────────────────────────────────────────┘
           ▼
    ┌──────────────────┐    ┌────────────────┐    ┌─────────────────┐
    │ Field Corrector   │───▶│ Local Validator │───▶│ Human Review    │
    │ fix null fields   │    │ math.floor tax  │    │ CLI y/n/q gate  │
    └──────────────────┘    └────────────────┘    └────────┬────────┘
                                                             │
                                                             ▼
                                                    ┌─────────────────┐
                                                    │ Accounting API  │
                                                    │ POST /invoices  │
                                                    └─────────────────┘

1. **OCR** – Extracts text from PDFs (text layer via PyMuPDF) and scanned images/PDFs (Tesseract JPN at 300 DPI)
2. **LLM Parsing** – Groq Qwen 3.6 27B converts raw OCR text into structured JSON; auto-falls back to Qwen 3 32B or Llama 3.1 8B on truncation/rate-limit
3. **Partner Matching** – difflib fuzzy matches extracted supplier names against API master aliases; last-resort full-text scan for known partner names
4. **Field Correction** – Fills missing unit (defaults to 式), description, tax_code before validation
5. **Local Validation** – Recalculates subtotal, per-code tax (math.floor), and total before every API call to prevent AMOUNT_MISMATCH
6. **Human Review** – CLI gate displays full extracted JSON and requires explicit confirmation before any write
7. **API Registration** – Posts to mock accounting API with graceful handling of duplicates (409), validation errors (422), bad requests (400), and unknown partners

---

## Configuration

| Variable | Default | Required | Description |
|---|---|---|---|
| GROQ_API_KEY | — | ✅ Yes | Free API key from [console.groq.com](https://console.groq.com) |
| GROQ_MODEL | qwen/qwen3.6-27b | No | Primary LLM model ID |
| LLM_PROVIDER | groq | No | Set to ollama for fully local inference |
| OLLAMA_MODEL | llama3.2 | No | Model name when using Ollama provider |
| API_BASE_URL | http://localhost:8080 | No | Accounting API endpoint |
| API_KEY | demo-key-1234 | No | Accounting API authentication key |

---

## Technology Choices

| Component | Chosen | Rejected | Rationale |
|---|---|---|---|
| OCR | Tesseract + PyMuPDF | Google Doc AI, AWS Textract | Zero cost, local execution, sufficient for demo volume |
| LLM | Groq Qwen 3.6 27B | GPT-4o, Claude | Free tier, <1s latency, strong Japanese support |
| Fallback | Qwen 3 32B, Llama 3.1 8B | Single model | Different rate-limit pools; ensures continuity |
| Validation | Deterministic Python | LLM self-correction | Instant, free, reliable vs. LLM arithmetic |
| Matching | difflib fuzzy + text scan | Embedding similarity | 5 partners; embeddings would be over-engineering |
| Review UI | CLI prompt | Streamlit web app | Meets verification requirement within 8-hour scope |

---

## Cost Estimate

| Metric | Value |
|---|---|
| Cost per invoice | ~$0.001 (Groq tokens + local OCR) |
| Monthly at 1,000 invoices | ~$0.50 – $1.00 |
| Processing time per invoice | 3–8 seconds (including rate-limit delay) |
| First failure point | Poor-quality scans → garbled OCR → caught by human review |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| tesseract: command not found | Install Tesseract: see Prerequisites above |
| ModuleNotFoundError: pymupdf | Run pip install -r requirements.txt |
| Connection refused on localhost:8080 | Ensure accounting_api.py exists; run.sh starts it automatically |
| LLM returns invalid JSON or truncates | Automatic retry with fallback models handles this; check GROQ_API_KEY |
| PARTNER_NOT_FOUND errors | Supplier not in master; expected behavior, logged with actionable message |
| Rate limit (429) errors | Automatic retry with exponential backoff; 8s delay between invoices |
| SyntaxError in llm_parser.py | File truncated during copy-paste; re-copy from repository |

---

## Submission

This project was built as a take-home assignment for the AI Agent Engineer position.
See [SUBMISSION.md](SUBMISSION.md) for design decisions, scoping trade-offs, and production considerations.

---

## License

This project was created as a take-home assignment for evaluation purposes only.
