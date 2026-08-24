import json
import re
import time
import requests
from config import LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """\
You are an expert AI assistant for Japanese invoice processing.
Extract data from the OCR text and return ONLY a valid JSON object.
Do NOT include any explanation, markdown, code fences, thinking, or extra text.
Return ONLY raw JSON starting with { and ending with }.

Rules:
1. Dates must be YYYY-MM-DD.
2. Amounts must be integers (no decimals, no commas).
3. The supplier name is usually near '御中', at the top of the invoice, or in the header. ALWAYS extract it into supplier_name AND match it to a partner_code from the provided list. If you cannot find the supplier name, look for company names, stamps, or letterhead text.
4. Tax rate 10% → tax_code "T10", 8% → "T08". Default to "T10" if unclear.
5. quantity and unit_price may be null, but amount is always required per line.
6. Be concise. Use short descriptions. Minimize whitespace in JSON output.

Output schema:
{
  "partner_code": "P-XXXX",
  "supplier_name": "string",
  "invoice_number": "string",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "currency": "JPY",
  "lines": [
    {
      "description": "string",
      "quantity": int|null,
      "unit": "string",
      "unit_price": int|null,
      "amount": int,
      "tax_code": "T10|T08"
    }
  ],
  "subtotal": int,
  "tax_amount": int,
  "total_amount": int
}
"""

MAX_RETRIES = 3
BASE_DELAY = 5
FALLBACK_MODELS = ["qwen/qwen3-32b", "llama-3.1-8b-instant"]


class RateLimitError(Exception):
    def __init__(self, retry_after=0):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class TruncationError(Exception):
    pass


class LLMParser:
    def parse_invoice(self, raw_text, partners_list):
        user_message = (
            f"Partners List:\n{json.dumps(partners_list, ensure_ascii=False)}\n\n"
            f"OCR Text:\n{raw_text}"
        )

        models_to_try = [GROQ_MODEL] + FALLBACK_MODELS if LLM_PROVIDER == "groq" else [None]

        for model in models_to_try:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    if LLM_PROVIDER == "ollama":
                        content = self._call_ollama(user_message)
                    else:
                        content = self._call_groq(user_message, model)

                    result = self._parse_json(content)
                    if result is not None:
                        return result

                    # Check if response was truncated
                    stripped = content.strip() if content else ""
                    stripped = re.sub(r"<think>.*?</think>", "", stripped, flags=re.DOTALL).strip()
                    if stripped.startswith("{") and not stripped.endswith("}"):
                        print(f"   ⚠️  Response truncated with model {model}. Trying next model...")
                        break

                    preview = content[:300] if content else "(empty)"
                    print(f"   ⚠️  Attempt {attempt}/{MAX_RETRIES}: Invalid JSON.")
                    print(f"   📋 LLM returned: {preview}")

                except RateLimitError as e:
                    wait = e.retry_after if e.retry_after > 0 else BASE_DELAY * attempt
                    print(f"   ⏳ Rate limited. Waiting {wait:.0f}s before retry {attempt}/{MAX_RETRIES}...")
                    time.sleep(wait)
                    continue

                except Exception as e:
                    print(f"   ❌ Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(BASE_DELAY * attempt)
                        continue
                    break

        print(f"   ❌ All models and retries exhausted.")
        return None

    def _call_groq(self, user_message, model=None):
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,
            "max_completion_tokens": 4096,
        }

        if "qwen3.6" in (model or GROQ_MODEL):
            payload["reasoning_effort"] = "none"

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code == 429:
            retry_after = self._extract_retry_after(resp)
            raise RateLimitError(retry_after)

        if resp.status_code == 400 and "reasoning" in resp.text.lower():
            del payload["reasoning_effort"]
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 429:
                raise RateLimitError(self._extract_retry_after(resp))
            if resp.status_code != 200:
                raise Exception(f"Groq returned {resp.status_code}: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

        if resp.status_code != 200:
            raise Exception(f"Groq returned {resp.status_code}: {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason", "")
        content = choice["message"]["content"]

        if finish_reason == "length":
            raise TruncationError("Response truncated due to max_completion_tokens")

        return content

    @staticmethod
    def _extract_retry_after(resp):
        retry_after = 0
        if "retry-after" in resp.headers:
            try:
                retry_after = float(resp.headers["retry-after"])
            except ValueError:
                pass
        if retry_after == 0:
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", "")
                match = re.search(r"try again in ([\d.]+)s", msg)
                if match:
                    retry_after = float(match.group(1)) + 1
            except Exception:
                pass
        return retry_after

    def _call_ollama(self, user_message):
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{SYSTEM_PROMPT}\n\n{user_message}",
            "stream": False,
            "format": "json",
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["response"]

    @staticmethod
    def _parse_json(content):
        if not content or not content.strip():
            return None

        cleaned = content.strip()
        cleaned = re.sub(r"
