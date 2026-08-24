import math


DEFAULT_UNIT = "式"
DEFAULT_TAX_CODE = "T10"


def validate_and_correct(data):
    """
    Fix missing required fields and recalculate totals using the same
    logic as the accounting API (math.floor per tax code group).
    Returns corrected data dict.
    """
    lines = data.get("lines", [])
    if not lines:
        return data

    # --- Fix missing required fields on each line ---
    for i, item in enumerate(lines):
        # unit is required by the API
        if not item.get("unit"):
            item["unit"] = DEFAULT_UNIT

        # description is required
        if not item.get("description"):
            item["description"] = f"Line item {i + 1}"

        # amount is required
        if item.get("amount") is None:
            qty = item.get("quantity") or 0
            price = item.get("unit_price") or 0
            item["amount"] = qty * price

        # tax_code is required
        if not item.get("tax_code"):
            item["tax_code"] = DEFAULT_TAX_CODE

    # --- Recalculate totals from corrected lines ---
    calculated_subtotal = sum(item["amount"] for item in lines)

    tax_groups = {}
    for item in lines:
        code = item["tax_code"]
        tax_groups[code] = tax_groups.get(code, 0) + item["amount"]

    calculated_tax = 0
    for code, amount in tax_groups.items():
        rate = 0.10 if code == "T10" else 0.08
        calculated_tax += math.floor(amount * rate)

    calculated_total = calculated_subtotal + calculated_tax

    data["subtotal"] = calculated_subtotal
    data["tax_amount"] = calculated_tax
    data["total_amount"] = calculated_total

    return data
