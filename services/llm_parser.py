import json
import re
import time
import requests
from config import LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """\
You are an expert AI assistant for Japanese invoice processing.
Extract data from the OCR text and return ONLY a valid JSON object.
Do NOT include any explanation, markdown, code fences, or extra text.
Return ONLY raw JSON starting with { and ending with }.

Rules:
1. Dates must be YYYY-MM-DD.
2. Amounts must be integers (no decimals, no commas).
3. Match supplier name to one of the provided partners. Return the partner_code.
4. Tax rate 10% → tax_code "T10", 8% → "T08". Default to "T10" if unclear.
5. quantity and unit_price may be null, but amount is always required per line.

Output schema:
{
  "partner_code": "P-XXXX",
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


class RateLimitError(Exception):
    def __init__(self, retry_after: float = 0):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class LLMParser:
    def parse_invoice(self, raw_text: str, partners_list: list) -> dict | None:
        user_message = (
            f"Partners List:\n{json.dumps(partners_list, ensure_ascii=False)}\n\n"
            f"OCR Text:\n{raw_text}"
        )

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if LLM_PROVIDER == "ollama":
                    content = self._call_ollama(user_message)
                else:
                    content = self._call_groq(user_message)

                result = self._parse_json(content)
                if result is not None:
                    return result

                # Debug: show what the LLM actually returned
                preview = content[:500] if content else "(empty response)"
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
                return None

        print(f"   ❌ All {MAX_RETRIES} attempts failed.")
        return None

    def _call_groq(self, user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code == 429:
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
            raise RateLimitError(retry_after)

        if resp.status_code != 200:
            raise Exception(f"Groq API returned {resp.status_code}: {resp.text}")

        return resp.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, user_message: str) -> str:
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
    def _parse_json(content: str) -> dict | None:
        if not content or not content.strip():
            return None

        cleaned = content.strip()

        # Strip markdown code fences
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to extract JSON object from surrounding text
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            extracted = cleaned[brace_start:brace_end + 1]
            try:
                return json.loads(extracted)
            except (json.JSONDecodeError, ValueError):
                pass

        return None
