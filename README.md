# invoice-automation



````
invoice-automation/
├── README.md                  # Setup instructions
├── SUBMISSION.md              # Your completed submission template
├── requirements.txt           # Dependencies
├── accounting_api.py          # The provided mock server (do not change)
├── main.py                    # Entry point: orchestrates the pipeline
├── config.py                  # Configuration (API keys, paths)
├── services/
│   ├── __init__.py
│   ├── ocr_engine.py          # Handles PDF text layer & Image OCR (Tesseract)
│   ├── llm_parser.py          # Uses LLM to convert raw text to JSON
│   ├── partner_matcher.py     # Fuzzy matches supplier names to API Master
│   └── api_client.py          # Interacts with the Accounting API
├── utils/
│   ├── __init__.py
│   └── validators.py          # Local math checks before sending to API
├── invoices/                  # Place the 12 sample files here
└── output/                    # Logs and intermediate JSON results
````