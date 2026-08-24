import difflib

class PartnerMatcher:
    def __init__(self, partners_data):
        self.partners = partners_data
        self.alias_map = {}
        for p in self.partners:
            self.alias_map[p['name']] = p['partner_code']
            for alias in p.get('aliases', []):
                self.alias_map[alias] = p['partner_code']

    def find_partner_code(self, extracted_name):
        if not extracted_name:
            return None
        
        # Direct match
        if extracted_name in self.alias_map:
            return self.alias_map[extracted_name]
        
        # Fuzzy match
        best_match = difflib.get_close_matches(extracted_name, self.alias_map.keys(), n=1, cutoff=0.6)
        if best_match:
            return self.alias_map[best_match[0]]
        
        return None