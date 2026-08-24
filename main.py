import os
import json
from services.ocr_engine import OCREngine
from services.llm_parser import LLMParser
from services.partner_matcher import PartnerMatcher
from services.api_client import AccountingAPIClient
from utils.validators import validate_amounts
from config import INVOICE_DIR, API_KEY, API_BASE_URL

def main():
    print("🚀 Starting Invoice Automation Pipeline...")
    
    # 1. Initialize Services
    ocr = OCREngine()
    llm = LLMParser()
    api_client = AccountingAPIClient()
    
    # 2. Fetch Partner Master Data
    partners = api_client.get_partners()
    matcher = PartnerMatcher(partners)
    
    # 3. Process Invoices
    for filename in sorted(os.listdir(INVOICE_DIR)):
        if not filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            continue
            
        filepath = os.path.join(INVOICE_DIR, filename)
        print(f"\n📄 Processing: {filename}")
        
        # Step A: OCR
        raw_text = ocr.extract_text(filepath)
        if not raw_text:
            print("⚠️ No text extracted.")
            continue
            
        # Step B: LLM Parsing
        structured_data = llm.parse_invoice(raw_text, partners)
        if not structured_data:
            print("❌ Failed to parse JSON from LLM.")
            continue
            
        # Step C: Partner Matching (if LLM didn't get the code right)
        if 'partner_code' not in structured_data or not structured_data['partner_code']:
            code = matcher.find_partner_code(structured_data.get('supplier_name', ''))
            if code:
                structured_data['partner_code'] = code
            else:
                print(f"⚠️ Could not match partner for {filename}")
                continue

        # Step D: Local Validation
        validation = validate_amounts(
            structured_data['lines'],
            structured_data['subtotal'],
            structured_data['tax_amount'],
            structured_data['total_amount']
        )
        
        if not all([validation['subtotal_match'], validation['tax_match'], validation['total_match']]):
            print(f"⚠️ Amount mismatch detected. Correcting...")
            # Auto-correct amounts to match line items
            structured_data['subtotal'] = validation['expected']['subtotal']
            structured_data['tax_amount'] = validation['expected']['tax']
            structured_data['total_amount'] = validation['expected']['total']

        # Step E: Register via API
        status, response = api_client.register_invoice(structured_data)
        
        if status == 201:
            print(f"✅ Successfully registered: {structured_data['invoice_number']}")
        else:
            print(f"❌ API Error {status}: {response}")

if __name__ == "__main__":
    main()