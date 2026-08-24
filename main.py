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

    # --- Verify API is reachable before doing any work ---
    print("\n🔌 Checking accounting API connection...")
    if not api_client.health_check():
        print("❌ Cannot reach accounting API at", api_client.base_url)
        print("   Start it first:  python3 accounting_api.py")
        print("   Or use:          ./run.sh")
        sys.exit(1)
    print("✅ API is reachable.")

    # --- Fetch partner master ---
    print("\n📋 Fetching partner master data...")
    try:
        partners = api_client.get_partners()
    except Exception as e:
        print(f"❌ Failed to fetch partners: {e}")
        sys.exit(1)
    matcher = PartnerMatcher(partners)
    print(f"   Loaded {len(partners)} partners.")

    # --- Initialize remaining services ---
    ocr = OCREngine()
    llm = LLMParser()

    # --- Discover invoice files ---
    if not os.path.isdir(INVOICE_DIR):
        print(f"\n❌ Invoice directory '{INVOICE_DIR}/' does not exist.")
        sys.exit(1)

    invoice_files = sorted(
        f
        for f in os.listdir(INVOICE_DIR)
        if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png"))
    )

    if not invoice_files:
        print(f"\n⚠️  No invoice files found in '{INVOICE_DIR}/'")
        sys.exit(1)

    print(f"   Found {len(invoice_files)} invoice(s) to process.\n")

    # --- Process each invoice ---
    results = {"success": 0, "skipped": 0, "failed": 0}

    for filename in invoice_files:
        filepath = os.path.join(INVOICE_DIR, filename)
        print(f"{'─' * 60}")
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

        try:
            choice = input("\n   Register this invoice? [y/n/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n   🛑 Interrupted. Quitting pipeline.")
            break

        if choice == "q":
            print("\n   🛑 Quitting pipeline.")
            break
        if choice != "y":
            print("   ⏭️  Skipped by user.")
            results["skipped"] += 1
            continue

        # Step 6: Register via API
        try:
            status, response = api_client.register_invoice(structured)
        except Exception as e:
            print(f"   ❌ API request failed: {e}")
            results["failed"] += 1
            continue

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
        elif status == 422:
            err = response.get("error", {})
            print(f"   ❌ Validation Error [{err.get('code')}]: {err.get('message')}")
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
    print(f"   📁 Total:    {len(invoice_files)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()