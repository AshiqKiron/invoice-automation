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
    │   ├── llm_parser.py      # Groq/Ollama structured JSON extraction
    │   ├── partner_matcher.py # Fuzzy matching against supplier master aliases
    │   └── api_client.py      # Accounting API HTTP client with error handling
    ├── utils/
    │   └── validators.py      # Local tax/amount recalculation (math.floor per code)
    ├── invoices/              # 12 sample Japanese invoices (PDF + scanned images)
    ├── docs/                  # GitHub Pages demo site
    ├── SUBMISSION.md          # Assignment submission document
    └── README.md              # This file

---

## How It Works

    Invoice File (PDF/JPG)
           │
           ▼
    ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
    │  OCR Engine   │───▶│   LLM Parser    │───▶│ Partner Matcher  │
    │ Tesseract+JPN │    │ Groq Llama3 70B │    │ difflib fuzzy    │
    └──────────────┘    └─────────────────┘    └────────┬─────────┘
                                                         │
           ┌─────────────────────────────────────────────┘
           ▼
    ┌──────────────────┐    ┌────────────────┐    ┌─────────────────┐
    │ Local Validator   │───▶│ Human Review   │───▶│ Accounting API  │
    │ math.floor tax    │    │ CLI y/n/q gate │    │ POST /invoices  │
    └──────────────────┘    └────────────────┘    └─────────────────┘

1. **OCR** – Extracts text from PDFs (text layer via PyMuPDF) and scanned images (Tesseract JPN)
2. **LLM Parsing** – Groq Llama 3 70B converts raw OCR text into structured JSON matching the API schema
3. **Partner Matching** – difflib fuzzy matches extracted supplier names against API master aliases
4. **Local Validation** – Recalculates subtotal, per-code tax (math.floor), and total before every API call to prevent AMOUNT_MISMATCH errors
5. **Human Review** – CLI gate displays full extracted JSON and requires explicit confirmation before any write
6. **API Registration** – Posts to mock accounting API with graceful handling of duplicates (409), bad requests (400), and missing partners

---

## Configuration

| Variable | Default | Required | Description |
|---|---|---|---|
| GROQ_API_KEY | — | ✅ Yes | Free API key from [console.groq.com](https://console.groq.com) |
| LLM_PROVIDER | groq | No | Set to ollama for fully local inference |
| OLLAMA_MODEL | llama3.2 | No | Model name when using Ollama provider |
| API_BASE_URL | http://localhost:8080 | No | Accounting API endpoint |
| API_KEY | demo-key-1234 | No | Accounting API authentication key |

---

## Technology Choices

| Component | Chosen | Rejected | Rationale |
|---|---|---|---|
| OCR | Tesseract + PyMuPDF | Google Doc AI, AWS Textract | Zero cost, local execution, sufficient for demo volume |
| LLM | Groq Llama 3 70B | GPT-4o, Claude | Free tier, <1s latency, strong Japanese instruction following |
| Validation | Deterministic Python | LLM self-correction | Instant, free, reliable. LLM arithmetic is non-deterministic |
| Matching | difflib fuzzy | Embedding similarity | Only 5 partners in master; embeddings would be over-engineering |
| Review UI | CLI prompt | Streamlit web app | Meets verification requirement within 8-hour scope |

---

## Cost Estimate

| Metric | Value |
|---|---|
| Cost per invoice | ~$0.001 (Groq tokens + local OCR) |
| Monthly at 1,000 invoices | ~$0.50 – $1.00 |
| Processing time per invoice | 3–6 seconds |
| First failure point | Poor-quality scans → garbled OCR → caught by human review |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| tesseract: command not found | Install Tesseract: see Prerequisites above |
| ModuleNotFoundError: No module named fitz | Run pip install -r requirements.txt |
| Connection refused on localhost:8080 | Ensure accounting_api.py is running (handled automatically by run.sh) |
| LLM returns invalid JSON | Check Groq API key; retry — transient parsing failures are caught and logged |
| PARTNER_NOT_FOUND errors | Supplier name on invoice does not match master; check fuzzy match threshold in partner_matcher.py |

---

## License

This project was created as a take-home assignment for evaluation purposes only.