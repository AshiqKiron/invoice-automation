#!/usr/bin/env python3
"""Invoice Automation Pipeline – single entry point."""

import json
import os
import sys

from config import INVOICE_DIR
from services.api_client import AccountingAPIClient
from services.llm_parser import LLMParser
from services.ocr_engine import OCREngine
from services.partner_matcher import PartnerMatcher
from utils.validators import validate_and_correct


def main():
    print("=" * 60)
    print("🚀 Invoice Automation Pipeline")
    print("=" * 60)

    # --- Initialize services ---
    api_client = AccountingAPIClient()
    ocr = OCREngine()
    llm = LLMParser()

    # --- Fetch partner master ---
    print("\n📋 Fetching partner master data...")
    partners = api_client.get_partners()
    matcher = PartnerMatcher(partners)
    print(f"   Loaded {len(partners)} partners.")

    # --- Process each invoice ---
    invoice_files = sorted(
        f
        for f in os.listdir(INVOICE_DIR)
        if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png"))
    )

    if not invoice_files:
        print(f"\n⚠️  No invoice files found in '{INVOICE_DIR}/'")
        sys.exit(1)

    results = {"success": 0, "skipped": 0, "failed": 0}

    for filename in invoice_files:
        filepath = os.path.join(INVOICE_DIR, filename)
        print(f"\n{'─' * 60}")
        print(f"📄 Processing: {filename}")

        # Step 1: OCR
        raw_text = ocr.extract_text(filepath)
        if not raw_text.strip():
            print("   ⚠️  No text extracted. Skipping.")
            results["failed"] += 1
            continue

        # Step 2: LLM Parsing
        print("   🤖 Parsing with LLM...")
        structured = llm.parse_invoice(raw_text, partners)
        if not structured:
            print("   ❌ Failed to parse structured data. Skipping.")
            results["failed"] += 1
            continue

        # Step 3: Partner matching fallback
        if not structured.get("partner_code"):
            supplier_name = structured.get("supplier_name", "")
            code = matcher.find_partner_code(supplier_name)
            if code:
                structured["partner_code"] = code
                print(f"   🔗 Fuzzy matched '{supplier_name}' → {code}")
            else:
                print(f"   ❌ Could not match partner for '{supplier_name}'. Skipping.")
                results["failed"] += 1
                continue

        # Step 4: Local validation & correction
        structured = validate_and_correct(structured)
        print("   ✅ Local validation passed (amounts recalculated).")

        # Step 5: Human-in-the-loop review
        print(f"\n   📝 Extracted Data:")
        print(json.dumps(structured, indent=4, ensure_ascii=False))
        choice = input("\n   Register this invoice? [y/n/q]: ").strip().lower()

        if choice == "q":
            print("\n   🛑 Quitting pipeline.")
            break
        if choice != "y":
            print("   ⏭️  Skipped by user.")
            results["skipped"] += 1
            continue

        # Step 6: Register via API
        status, response = api_client.register_invoice(structured)

        if status == 201:
            inv_no = structured.get("invoice_number", "?")
            print(f"   ✅ Registered: {inv_no}")
            results["success"] += 1
        elif status == 409:
            inv_no = structured.get("invoice_number", "?")
            print(f"   ⚠️  Duplicate: {inv_no} already exists. Skipping.")
            results["skipped"] += 1
        elif status == 400:
            err = response.get("error", {})
            print(f"   ❌ Bad Request [{err.get('code')}]: {err.get('message')}")
            results["failed"] += 1
        else:
            print(f"   ❌ Unexpected error {status}: {response}")
            results["failed"] += 1

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("📊 Pipeline Summary")
    print(f"   ✅ Success: {results['success']}")
    print(f"   ⏭️  Skipped:  {results['skipped']}")
    print(f"   ❌ Failed:   {results['failed']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()