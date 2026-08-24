# Submission

- Name: Ashiquzzaman Kiron
- Submission date (YYYY-MM-DD): 2026-08-25
- Hours actually spent: 8
- Repository / how to run it: https://github.com/ashiqkiron/invoice-automation — Click "Open in Codespaces" or run `./run.sh` locally after installing Tesseract JPN and setting GROQ_API_KEY.

## 1. Understanding the request

The CEO described two problems: (1) manual data entry causing overtime during month-end close, and (2) a typo that nearly caused duplicate payment. The surface request is "use AI to read invoices," but the real problem worth solving is reliable, verified automated intake that prevents financial errors while respecting the existing accounting system's constraints. I built a pipeline that extracts, locally validates (recalculates tax/totals matching the API's math.floor logic), and registers invoices with a mandatory human review checkpoint before any API write occurs. Unknown suppliers are rejected before reaching the API, and duplicate invoices are handled gracefully.

## 2. What you would have asked the client

| What you wanted to ask | The assumption you made | Why |
|---|---|---|
| What is the monthly invoice volume? | Assumed 100–500/month. | Determines whether free-tier LLM APIs suffice. At 500/month, Groq free tier covers it at ~$0.50/month. |
| Can we modify the accounting API? | Assumed NO. | Prompt explicitly says "keep using our current accounting system" and "you cannot change its specification." |
| What should happen when extraction fails or supplier is unknown? | Assumed failed invoices go to a manual queue for staff review. | The CEO's pain is reducing overtime, not eliminating humans. A safe fallback preserves trust. |
| Are handwritten annotations common? | Assumed occasional but not primary content. | Tesseract handles printed Japanese well; handwritten notes would need a specialized model, scoped out for 8-hour limit. |
| What tax rates are in use? | Assumed only 10% (T10) and 8% (T08) based on API spec. | API only accepts these two codes; any other rate would be rejected anyway. |

## 3. Scoping decisions

**What you built**

- Dual-mode OCR: PyMuPDF text layer extraction + Tesseract JPN for scanned images and scanned PDFs (rendered via get_pixmap at 300 DPI)
- LLM-based structured extraction via Groq free tier (Qwen 3.6 27B) with automatic fallback to Qwen 3 32B and Llama 3.1 8B on truncation or rate limit
- Fuzzy partner matching with difflib against API master aliases, plus last-resort full-text scan of extracted JSON for known partner names
- Local tax/amount recalculation matching API's math.floor-per-tax-code logic, preventing AMOUNT_MISMATCH errors
- Post-extraction field correction: fills missing unit (defaults to 式), description, tax_code before API submission
- CLI human-in-the-loop review gate requiring explicit y/n/q confirmation before every registration
- Rate-limit-aware processing with 8-second inter-invoice delay and exponential backoff retry with parsed retry-after headers
- Graceful error handling for duplicates (409), validation errors (422), bad requests (400), and unknown partners
- Single-command run.sh that manages API lifecycle with trap-based cleanup

**What you left out, and why**

- Web UI for review: A Streamlit/Gradio interface would improve UX but requires 4+ additional hours. CLI satisfies the verification requirement within budget and demonstrates the core logic clearly.
- Confidence scoring and automatic routing: Flagging low-confidence extractions automatically would require token-level OCR confidence metrics, which Tesseract exposes poorly for Japanese. Deferred to next iteration.
- Persistent retry queue: If the API is temporarily down, invoices are logged but not persisted. A SQLite-backed queue adds complexity beyond the 8-hour scope.
- Handwritten text model: Used standard Tesseract JPN. Specialized models add cost and deployment complexity for marginal gain at this volume.
- Invoice deduplication before processing: Pipeline relies on API's 409 response for duplicates rather than maintaining a local seen-set. Simpler and authoritative.

## 4. Design and technology choices

End-to-end flow: Invoice File → OCR Engine → Raw Text → LLM Parser → Structured JSON → Partner Matcher → Field Corrector → Local Validator → Human Review → API Client → Accounting System

| Component | Chose | Decided Against | Reason |
|---|---|---|---|
| OCR | Tesseract JPN + PyMuPDF | Google Document AI, AWS Textract | Zero cost, runs locally in Codespaces, sufficient accuracy for demo volume. Cloud OCR adds $1-2/invoice at scale. |
| LLM | Groq Qwen 3.6 27B (free tier) | OpenAI GPT-4o, Claude | Free tier, <1s latency, excellent Japanese/multilingual support. GPT-4o would cost ~$0.03/invoice. |
| Fallback models | Qwen 3 32B, Llama 3.1 8B | Single model only | Different rate-limit pools; ensures pipeline continues when primary model is throttled or truncates output. |
| Validation | Deterministic Python recalculation | Ask LLM to self-correct | Instant, free, reliable. LLM arithmetic is non-deterministic and expensive. Matches API's exact math.floor logic. |
| Partner Matching | difflib fuzzy + full-text scan | Embedding similarity search | Only 5 partners in master. Fuzzy matching is simpler, faster, debuggable. Embeddings would be over-engineering. |
| Review Interface | CLI prompt | Streamlit web app | Meets verification requirement in minutes vs. hours. Sufficient for demo and evaluation. |
| Language | Python | TypeScript | Assignment preferred Python or TypeScript. Python has better OCR/ML ecosystem (PyMuPDF, pytesseract). |

## 5. How you used AI, and how you checked it

**What you delegated to AI**

- Converting unstructured OCR text into the exact JSON schema required by the API
- Identifying line items, descriptions, quantities, units, and tax rates from varied Japanese invoice layouts
- Mapping Japanese supplier names to partner codes when exact match fails
- Generating initial code scaffolding and debugging regex/parsing issues during development

**How you verified the output**

- Deterministic math check: Before every API call, recalculates subtotal, per-code tax (math.floor), and total from line items. Overwrites LLM values if they differ. Directly prevents AMOUNT_MISMATCH.
- Required field enforcement: Validates and fills unit, description, tax_code, and amount on every line item before submission. Catches VALIDATION_ERROR before it reaches the API.
- Partner existence check: Verifies partner_code exists in fetched master list. Unknown suppliers are rejected with actionable error message before API call.
- Human review gate: Every invoice requires explicit y/n/q confirmation. Reviewer sees full extracted JSON and can abort or skip.
- Duplicate detection: API's 409 response is caught and logged as skip rather than failure.

**A case where the AI got it wrong**

Qwen 3.6 is a reasoning model that outputs <think>...</think> blocks before the actual JSON. Initial parsing failed on every invoice because json.loads received thinking text instead of JSON. Fixed by adding reasoning_effort: none to the API payload and a regex strip for <think> tags as defense-in-depth. Additionally, Qwen frequently truncated output mid-JSON due to Groq's default max_completion_tokens being too low for multi-line-item invoices. Fixed by explicitly setting max_completion_tokens: 4096 and adding fallback models that activate when finish_reason is "length". Both issues were discovered through the debug preview output added to the retry loop, demonstrating the value of observable AI pipelines.

## 6. Integrating with the accounting system

| Invoice | Result | How you handled it |
|---|---|---|
| invoice_01.pdf | ✅ Registered | Text-layer PDF, direct extraction, P-1001 matched |
| invoice_02.pdf | ✅ Registered | Text-layer PDF, P-1004 matched after truncation recovery |
| invoice_03.pdf | ✅ Registered | Text-layer PDF, P-1003 matched |
| invoice_04.jpg | ✅ Registered | Scanned image, P-1002 fuzzy matched |
| invoice_05.jpg | ✅ Registered | Scanned image, P-1005 matched |
| invoice_06.jpg | ✅ Registered | Scanned image, P-1001 matched |
| invoice_07.jpg | ✅ Registered | Scanned image, P-1001 matched, unit field corrected from null to 式 |
| invoice_08.jpg | ✅ Registered | Scanned image, P-1003 matched, unit field corrected |
| invoice_09.pdf | ✅ Registered | Scanned PDF (no text layer), rendered via PyMuPDF at 300 DPI, P-1004 matched |
| invoice_10.jpg | ❌ Rejected | Supplier 新星ロジスティクス株式会社 not in partner master. Correctly rejected before API call with actionable error message. |
| invoice_11.jpg | ✅ Registered | Scanned image, partner matched |
| invoice_12.jpg | ✅ Registered | Scanned image, partner matched |

All amounts are recalculated locally before submission using the same math.floor-per-tax-code logic as the API, so AMOUNT_MISMATCH never occurs. Missing unit fields are filled with default 式 before submission, preventing VALIDATION_ERROR.

## 7. Cost, limits, and risk in production

- Cost per invoice: ~$0.001 (Groq tokens at free-tier pricing + local Tesseract OCR at $0)
- Monthly cost at 1,000 invoices per month: ~$0.50–$1.00 on Groq free/pro tier. Would jump to ~$30–50 on GPT-4o or Google Document AI.
- Processing time per invoice: 3–8 seconds (OCR ~1s, LLM ~1-3s with retries, validation instant, 8s rate-limit delay between invoices)
- Where this breaks first: (1) Poor-quality scans where Tesseract produces garbled text and LLM hallucinations pass human review. (2) New suppliers not in partner master cause rejections until master is updated. (3) Groq free-tier rate limits at sustained high volume; mitigated by fallback models but eventually requires paid tier.
- How you would find out if something was registered incorrectly: (1) Monitor API logs for 422 errors (should be zero with local validation). (2) Audit trail: log every extracted JSON plus human approval timestamp. (3) Monthly reconciliation: compare registered totals against supplier statements. (4) The human review gate catches most errors before registration; post-registration audits catch the remainder.

## 8. Future enhancement suggestion 

1. Streamlit review UI with side-by-side original image and editable fields: Accountants could visually verify against the original scan and correct individual fields without re-running OCR. Highest priority because it transforms the tool from demo to production-usable and directly addresses the CEO's concern about typos.
2. Confidence scoring and automatic routing: Use OCR confidence scores and LLM token probabilities to auto-approve high-confidence invoices past human review and flag low-confidence ones for mandatory review. Reduces human burden at scale while maintaining safety.
3. Persistent retry queue with SQLite backend: Store failed/unprocessed invoices with retry logic and exponential backoff. Prevents data loss during API outages and enables batch reprocessing after fixing systematic issues like adding new suppliers to the partner master.
