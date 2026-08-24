# Submission

- Name: Ashiquzzaman Kiron
- Submission date (YYYY-MM-DD): 2026-08-24
- Hours actually spent: 7.5
- Repository / how to run it: 
  1. `pip install -r requirements.txt`
  2. Install Tesseract: `sudo apt-get install tesseract-ocr tesseract-ocr-jpn`
  3. Set `GROQ_API_KEY` in `.env` (free tier at console.groq.com)
  4. Place sample invoices in `invoices/`
  5. Run: `./run.sh`

## 1. Understanding the request

The CEO described two problems: (1) manual data entry causing overtime during month-end close, and (2) a typo that nearly caused duplicate payment. The surface request is "use AI to read invoices," but the real problem worth solving is **reliable, verified automated intake that prevents financial errors**. I built a pipeline that extracts, locally validates (recalculates tax/totals), and registers invoices with a mandatory human review checkpoint before any API write occurs.

## 2. What you would have asked the client

| What you wanted to ask | The assumption you made | Why |
|---|---|---|
| What is the monthly invoice volume? | Assumed 100–500/month. | Determines whether free-tier LLM APIs suffice or enterprise OCR is needed. At 500/month, Groq free tier covers it entirely. |
| Can we modify the accounting API? | Assumed NO. | Prompt explicitly says "keep using our current accounting system" and "you cannot change its specification." |
| What should happen when extraction fails? | Assumed failed invoices go to a manual queue. | The CEO's pain is reducing overtime, not eliminating humans. A safe fallback preserves trust. |
| Are handwritten annotations common? | Assumed occasional but not primary. | Tesseract handles printed Japanese well; handwritten notes would need a specialized model, which I scoped out for the 8-hour limit. |

## 3. Scoping decisions

**What you built**
- Dual-mode OCR (PyMuPDF text layer + Tesseract for scans/images)
- LLM-based structured extraction via Groq free tier (Llama 3 70B)
- Fuzzy partner matching with `difflib` against API master aliases
- Local tax/amount recalculation matching API's `math.floor` logic
- CLI human-in-the-loop review before every API registration
- Graceful handling of duplicates (409), bad requests (400), and missing partners
- Single-command `run.sh` that manages API lifecycle

**What you left out, and why**
- **Web UI for review:** A Streamlit/Gradio interface would improve UX but requires 4+ additional hours. CLI satisfies the verification requirement within budget.
- **Confidence scoring:** Flagging low-confidence extractions automatically would require token-level OCR confidence, which Tesseract exposes poorly for Japanese. Deferred to next iteration.
- **Batch retry queue:** If the API is temporarily down, invoices are lost. A persistent queue (SQLite/Redis) adds complexity beyond the 8-hour scope.
- **Handwritten text model:** Used standard Tesseract JPN. Specialized models (e.g., Google Handwriting) add cost and deployment complexity.

## 4. Design and technology choices

**End-to-end flow:**
`Invoice File → OCR Engine → Raw Text → LLM Parser → Structured JSON → Partner Matcher → Local Validator → Human Review → API Client → Accounting System`

**Key choices and trade-offs:**

| Component | Chose | Decided Against | Reason |
|---|---|---|---|
| OCR | Tesseract + PyMuPDF | Google Document AI, AWS Textract | Zero cost, runs locally, sufficient for 12 samples. Cloud OCR adds $1-2/invoice at scale. |
| LLM | Groq (Llama 3 70B) | OpenAI GPT-4o, Claude | Free tier, <1s latency, excellent Japanese instruction following. GPT-4o would cost ~$0.03/invoice. |
| Validation | Local Python recalculation | Ask LLM to self-correct | Deterministic, instant, zero cost. LLM re-prompting is slow, expensive, and unreliable for arithmetic. |
| Partner Matching | difflib fuzzy matching | Embedding similarity search | Only 5 partners in master. Fuzzy string matching is simpler, faster, and debuggable. Embeddings would be over-engineering. |
| Review Interface | CLI prompt | Streamlit web app | Meets verification requirement in minutes vs. hours. Sufficient for demo. |

## 5. How you used AI, and how you checked it

**What you delegated to AI**
- Converting unstructured OCR text into the exact JSON schema required by the API
- Identifying line items, descriptions, quantities, and tax rates from varied layouts
- Mapping Japanese supplier names to partner codes when exact match fails

**How you verified the output**
- **Deterministic math check:** Before every API call, I recalculate subtotal, tax (per-code with `math.floor`), and total from line items. If they differ from LLM output, I overwrite with correct values. This directly prevents the `AMOUNT_MISMATCH` error the API enforces.
- **Partner existence check:** Verify `partner_code` exists in the fetched master list before sending.
- **Human review gate:** Every invoice requires explicit `y` confirmation before registration. The reviewer sees the full extracted JSON.

**A case where the AI got it wrong**
On scanned invoices, Tesseract occasionally misread "¥108,000" as "108000" (missing comma handling) or confused similar kanji. The LLM correctly parsed the number, but if OCR had dropped a digit entirely (e.g., "18000" instead of "108000"), the local validator would catch the mismatch between line-item sum and stated total, flagging it for human review rather than silently registering wrong data.

## 6. Integrating with the accounting system

| Invoice | Result | How you handled it |
|---|---|---|
| invoice_01.pdf | ✅ Success | Text-layer PDF, direct extraction, auto-registered after review |
| invoice_04.jpg | ✅ Success | Scanned image, fuzzy-matched "ヤマダ製作所" → P-1001 |
| invoice_09.pdf | ✅ Success | Scanned PDF (no text layer), fell through to Tesseract OCR path |
| Hypothetical duplicate | ⏭️ Skipped | Caught 409 DUPLICATE_INVOICE, logged and continued |
| Hypothetical bad partner | ❌ Failed | PARTNER_NOT_FOUND caught, flagged for manual correction |

All amounts are recalculated locally before submission, so `AMOUNT_MISMATCH` should never occur unless line items themselves are misread (caught by human review).

## 7. Cost, limits, and risk in production

- **Cost per invoice:** ~$0.0005 (Groq tokens) + $0 (local Tesseract). Effectively free at demo scale.
- **Monthly cost at 1,000 invoices:** ~$0.50–$1.00 on Groq free/pro tier. Would jump to ~$30–50 on GPT-4o or Google Document AI.
- **Processing time per invoice:** 3–6 seconds (OCR ~1s, LLM ~1-2s, validation + review ~variable).
- **Where this breaks first:** 
  1. Poor-quality scans where Tesseract produces garbled text → LLM hallucinates plausible but wrong data → human reviewer must catch it.
  2. New suppliers not in partner master → registration fails until master is updated.
  3. Groq rate limits at high volume → need fallback provider or queue.
- **How to detect incorrect registrations:** 
  1. Monitor API logs for 422 errors (should be zero with local validation).
  2. Audit trail: log every extracted JSON + human approval timestamp.
  3. Monthly reconciliation: compare registered totals against supplier statements.

## 8. What you would do with another 8 hours

1. **Streamlit review UI with side-by-side image + editable fields:** Accountants could visually verify against the original scan and correct individual fields without re-running OCR. This directly addresses the CEO's concern about typos and builds trust in automation. Highest priority because it transforms the tool from "demo" to "usable."
2. **Confidence scoring + automatic routing:** Use OCR confidence scores and LLM token probabilities to auto-route high-confidence invoices past human review and flag low-confidence ones. This reduces review burden at scale while maintaining safety.
3. **Persistent retry queue (SQLite):** Store failed/unprocessed invoices with retry logic and exponential backoff. Prevents data loss during API outages and enables batch reprocessing after fixing systematic issues (e.g., new supplier added to master).