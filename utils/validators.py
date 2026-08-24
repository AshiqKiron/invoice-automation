import math


def validate_and_correct(data: dict) -> dict:
    """
    Recalculate subtotal, tax, and total from line items using the same
    logic as the accounting API (math.floor per tax code group).
    Returns corrected data dict.
    """
    lines = data.get("lines", [])
    if not lines:
        return data

    calculated_subtotal = sum(item["amount"] for item in lines)

    # Group line amounts by tax code
    tax_groups: dict[str, int] = {}
    for item in lines:
        code = item["tax_code"]
        tax_groups[code] = tax_groups.get(code, 0) + item["amount"]

    # Calculate tax per group with floor rounding (matches API behavior)
    calculated_tax = 0
    for code, amount in tax_groups.items():
        rate = 0.10 if code == "T10" else 0.08
        calculated_tax += math.floor(amount * rate)

    calculated_total = calculated_subtotal + calculated_tax

    # Overwrite with correct values
    data["subtotal"] = calculated_subtotal
    data["tax_amount"] = calculated_tax
    data["total_amount"] = calculated_total

    return data