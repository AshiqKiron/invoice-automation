import json
import re
import time
import requests
from config import LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = (
    "You are an expert AI assistant for Japanese invoice processing. "
    "Extract data from the OCR text and return ONLY a valid JSON object. "
    "Do NOT include any explanation, markdown, code fences, thinking, or extra text. "
    "Return ONLY raw JSON starting with { and ending with }.\n\n"
    "Rules:\n"
    "1. Dates must be YYYY-MM-DD.\n"
    "2. Amounts must be integers (no decimals, no commas).\n"
    "3. The supplier name is usually near '御中', at the top of the invoice, or in the header. "
    "ALWAYS extract it into supplier_name AND match it to a partner_code from the provided list. "
    "If you cannot find the supplier name, look for company names, stamps, or letterhead text.\n"
    "4. Tax rate 10% -> tax_code T10, 8% -> T08. Default to T10 if unclear.\n"
    "5. quantity and unit_price may be null, but amount is always required per line.\n"
    "6. Be concise. Use short descriptions. Minimize whitespace in JSON output.\n\n"
    "Output schema:\n"
    "{\n"
    '  "partner_code": "P-XXXX",\n'
    '  "supplier_name": "string",\n'
    '  "invoice_number": "string",\n'
    '  "issue_date": "YYYY-MM-DD",\n'
    '  "due_date": "YYYY-MM-DD",\n'
    '  "currency": "JPY",\n'
    '  "lines": [\n'
    "    {\n"
    '      "description": "string",\n'
    '      "quantity": "int|null",\n'
    '      "unit": "string",\n'
    '      "unit_price": "int|null",\n'
    '      "amount": "int",\n'
    '      "tax_code": "T10|T08"\n'
    "    }\n"
    "  ],\n"
    '  "subtotal": "int",\n'
    '  "tax_amount": "int",\n'
    '  "total_amount": "int"\n'
    "}"
)

MAX_RETRIES = 3
BASE_DELAY = 5
FALLBACK_MODELS = ["qwen/qwen3-32b", "llama-3.1-8b-instant"]
THINK_PATTERN = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


class RateLimitError(Exception):
    def __init__(self, retry_after=0):
        self.retry_after = retry_after
        super().__init__("Rate limited")


class TruncationError(Exception):
    pass


class LLMParser:
    def parse_invoice(self, raw_text, partners_list):
        user_message = (
            "Partners List:\n"
            + json.dumps(partners_list, ensure_ascii=False)
            + "\n\nOCR Text:\n"
            + raw_text
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

                    stripped = content.strip() if content else ""
                    stripped = THINK_PATTERN.sub("", stripped).strip()
                    if stripped.startswith("{") and not stripped.endswith("}"):
                        print("   ⚠️  Response truncated with model " + str(model) + ". Trying next model...")
                        break

                    preview = content[:300] if content else "(empty)"
                    print("   ⚠️  Attempt " + str(attempt) + "/" + str(MAX_RETRIES) + ": Invalid JSON.")
                    print("   📋 LLM returned: " + preview)

                except RateLimitError as e:
                    wait = e.retry_after if e.retry_after > 0 else BASE_DELAY * attempt
                    print("   ⏳ Rate limited. Waiting " + str(int(wait)) + "s before retry " + str(attempt) + "/" + str(MAX_RETRIES) + "...")
                    time.sleep(wait)
                    continue

                except Exception as e:
                    print("   ❌ Attempt " + str(attempt) + "/" + str(MAX_RETRIES) + " failed: " + str(e))
                    if attempt < MAX_RETRIES:
                        time.sleep(BASE_DELAY * attempt)
                        continue
                    break

        print("   ❌ All models and retries exhausted.")
        return None

    def _call_groq(self, user_message, model=None):
        headers = {
            "Authorization": "Bearer " + GROQ_API_KEY,
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

        active_model = model or GROQ_MODEL
        if "qwen3.6" in active_model:
            payload["reasoning_effort"] = "none"

        url = "https://api.groq.com/openai/v1/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=60)

        if resp.status_code == 429:
            retry_after = self._extract_retry_after(resp)
            raise RateLimitError(retry_after)

        if resp.status_code == 400 and "reasoning" in resp.text.lower():
            del payload["reasoning_effort"]
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                raise RateLimitError(self._extract_retry_after(resp))
            if resp.status_code != 200:
                raise Exception("Groq returned " + str(resp.status_code) + ": " + resp.text)
            return resp.json()["choices"][0]["message"]["content"]

        if resp.status_code != 200:
            raise Exception("Groq returned " + str(resp.status_code) + ": " + resp.text)

        data = resp.json()
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason", "")
        content = choice["message"]["content"]

        if finish_reason == "length":
            raise TruncationError("Response truncated")

        return content

    @staticmethod
    def _extract_retry_after(resp):
        retry_after = 0
        header_val = resp.headers.get("retry-after", "")
        if header_val:
            try:
                retry_after = float(header_val)
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
            "prompt": SYSTEM_PROMPT + "\n\n" + user_message,
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
        cleaned = THINK_PATTERN.sub("", cleaned).strip()

        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            extracted = cleaned[brace_start:brace_end + 1]
            try:
                return json.loads(extracted)
            except (json.JSONDecodeError, ValueError):
                pass

        return None
