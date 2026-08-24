import difflib


class PartnerMatcher:
    """Maps extracted supplier names to API partner codes via fuzzy matching."""

    def __init__(self, partners_data: list[dict]):
        self.alias_map: dict[str, str] = {}
        for p in partners_data:
            self.alias_map[p["name"]] = p["partner_code"]
            for alias in p.get("aliases", []):
                self.alias_map[alias] = p["partner_code"]

    def find_partner_code(self, extracted_name: str | None) -> str | None:
        if not extracted_name:
            return None

        # Exact match
        if extracted_name in self.alias_map:
            return self.alias_map[extracted_name]

        # Fuzzy match
        matches = difflib.get_close_matches(
            extracted_name, self.alias_map.keys(), n=1, cutoff=0.6
        )
        if matches:
            return self.alias_map[matches[0]]

        return None