import difflib


class PartnerMatcher:
    """Maps extracted supplier names to API partner codes via fuzzy matching."""

    def __init__(self, partners_data):
        self.partners = partners_data
        self.alias_map = {}
        self.code_to_partner = {}
        for p in partners_data:
            self.code_to_partner[p["partner_code"]] = p
            self.alias_map[p["name"]] = p["partner_code"]
            for alias in p.get("aliases", []):
                self.alias_map[alias] = p["partner_code"]

    def find_partner_code(self, extracted_name, invoice_data=None):
        # Try exact match first
        if extracted_name and extracted_name.strip():
            name = extracted_name.strip()
            if name in self.alias_map:
                return self.alias_map[name]

            # Fuzzy match with lower cutoff for OCR errors
            matches = difflib.get_close_matches(
                name, self.alias_map.keys(), n=1, cutoff=0.5
            )
            if matches:
                return self.alias_map[matches[0]]

        # Fallback: try matching against all partner names/aliases
        # using any available text from the invoice
        if invoice_data:
            search_texts = []
            for key in ["supplier_name", "partner_name", "vendor_name", "company_name"]:
                val = invoice_data.get(key, "")
                if val and str(val).strip():
                    search_texts.append(str(val).strip())

            raw_desc = invoice_data.get("raw_supplier_text", "")
            if raw_desc and str(raw_desc).strip():
                search_texts.append(str(raw_desc).strip())

            for text in search_texts:
                if text in self.alias_map:
                    return self.alias_map[text]
                matches = difflib.get_close_matches(
                    text, self.alias_map.keys(), n=1, cutoff=0.5
                )
                if matches:
                    return self.alias_map[matches[0]]

        return None

    def get_all_partner_names(self):
        """Return all known partner names and aliases for debugging."""
        return list(self.alias_map.keys())
