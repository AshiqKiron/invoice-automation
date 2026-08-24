# invoice-automation



````
invoice-automation/
├── README.md                  # Setup & demo instructions
├── SUBMISSION.md              # Completed submission document
├── requirements.txt           # Python dependencies
├── run.sh                     # Single command entry point
├── accounting_api.py          # Provided mock API (DO NOT MODIFY)
├── main.py                    # Orchestrator with HITL review
├── config.py                  # Environment configuration
├── services/
│   ├── __init__.py
│   ├── ocr_engine.py          # PDF text layer + Tesseract image OCR
│   ├── llm_parser.py          # Groq/Ollama structured extraction
│   ├── partner_matcher.py     # Fuzzy matching to supplier master
│   └── api_client.py          # Accounting API HTTP client
├── utils/
│   ├── __init__.py
│   └── validators.py          # Local tax/amount recalculation
├── invoices/                  # Place 12 sample invoices here
└── demo/                      # Screenshots for submission
    ├── cli_review.png
    └── api_success.png

````