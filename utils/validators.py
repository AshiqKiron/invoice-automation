import math

def validate_amounts(lines, subtotal, tax_amount, total_amount):
    """Recalculate totals to match API logic."""
    calculated_subtotal = sum(item['amount'] for item in lines)
    
    # Group by tax code
    tax_groups = {}
    for item in lines:
        code = item['tax_code']
        tax_groups[code] = tax_groups.get(code, 0) + item['amount']
    
    # Calculate tax per group (floor)
    calculated_tax = 0
    for code, amount in tax_groups.items():
        rate = 0.10 if code == 'T10' else 0.08
        calculated_tax += math.floor(amount * rate)
        
    calculated_total = calculated_subtotal + calculated_tax
    
    return {
        "subtotal_match": calculated_subtotal == subtotal,
        "tax_match": calculated_tax == tax_amount,
        "total_match": calculated_total == total_amount,
        "expected": {
            "subtotal": calculated_subtotal,
            "tax": calculated_tax,
            "total": calculated_total
        }
    }