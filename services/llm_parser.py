import requests
import json
from config import LLM_PROVIDER, GROQ_API_KEY

class LLMParser:
    def parse_invoice(self, raw_text, partners_list):
        """Convert raw OCR text to structured JSON."""
        
        prompt = f"""
        You are an expert AI assistant for Japanese invoice processing.
        Extract data from the following OCR text and return ONLY a valid JSON object.
        
        Rules:
        1. Dates must be YYYY-MM-DD.
        2. Amounts must be integers (no decimals).
        3. Match the 'supplier_name' to one of the provided 'partners_list' names or aliases. Return the 'partner_code'.
        4. If tax rate is 10%, use tax_code 'T10'. If 8%, use 'T08'. Default to 'T10' if unclear.
        5. Recalculate subtotal, tax, and total from lines if possible, but prioritize extracted values if they look correct.
        
        Partners List:
        {json.dumps(partners_list, ensure_ascii=False)}
        
        OCR Text:
        {raw_text}
        
        Output JSON Format:
        {{
            "partner_code": "P-XXXX",
            "invoice_number": "string",
            "issue_date": "YYYY-MM-DD",
            "due_date": "YYYY-MM-DD",
            "currency": "JPY",
            "lines": [
                {{
                    "description": "string",
                    "quantity": int or null,
                    "unit": "string",
                    "unit_price": int or null,
                    "amount": int,
                    "tax_code": "T10" or "T08"
                }}
            ],
            "subtotal": int,
            "tax_amount": int,
            "total_amount": int
        }}
        """

        if LLM_PROVIDER == "groq":
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            }
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            content = response.json()['choices'][0]['message']['content']
        else:
            # Fallback for Ollama implementation if needed
            raise NotImplementedError("Ollama implementation not shown in this snippet")

        try:
            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except Exception as e:
            print(f"JSON Parsing Error: {e}\nRaw Content: {content}")
            return None