"""
Product Filter Engine for Aguatech Engineers Pvt. Ltd. (Pune)
Specialized Material Handling Equipment (MHE) Matching Matrix
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("AguatechBot.Filters")


@dataclass
class FilterResult:
    passed: bool
    matched_keyword: Optional[str] = None
    matched_location: Optional[str] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "matched_keyword": self.matched_keyword,
            "matched_location": self.matched_location,
            "rejection_reason": self.rejection_reason
        }


class AguatechFilterEngine:
    """
    High-speed text analysis & matching engine for IndiaMART Buy Leads.
    Evaluates incoming leads against Aguatech's MHE catalog, negative filters,
    and geographic boundaries in sub-milliseconds.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None, config_path: str = "config.json"):
        self.config_path = config_path
        if config_dict:
            self._load_from_dict(config_dict)
        else:
            self.reload()

    def reload(self) -> None:
        """Loads or reloads filter parameters from configuration."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._load_from_dict(data)
            logger.info(
                f"[Filter Engine] Loaded {len(self.included_keywords)} product keywords, "
                f"{len(self.excluded_keywords)} negative keywords, "
                f"{len(self.target_locations)} target locations."
            )
        except Exception as e:
            logger.error(f"[Filter Engine] Error reading config from {self.config_path}: {e}")
            # Fallback defaults if config file is unavailable
            self._load_defaults()

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        filters = data.get("filters", {})
        self.included_keywords: List[str] = [
            k.strip().lower() for k in filters.get("included_keywords", []) if k.strip()
        ]
        self.excluded_keywords: List[str] = [
            k.strip().lower() for k in filters.get("excluded_keywords", []) if k.strip()
        ]
        self.target_locations: List[str] = [
            loc.strip().lower() for loc in filters.get("target_locations", []) if loc.strip()
        ]
        self.min_order_quantity: int = int(filters.get("min_order_quantity", 1))

    def _load_defaults(self) -> None:
        self.included_keywords = [
            "pallet truck", "hand pallet", "hydraulic pallet", "electric pallet",
            "stacker", "electric stacker", "hydraulic stacker", "reach truck", "forklift",
            "goods lift", "industrial lift", "scissor lift", "lift table", "dock leveler",
            "drum handling", "barrel lifter", "barrel stacker", "aerial work platform",
            "material handling equipment", "mhe"
        ]
        self.excluded_keywords = [
            "toy", "second hand", "used", "scrap", "repair only", "service only",
            "rent", "hire", "water plant", "mineral water"
        ]
        self.target_locations = [
            "maharashtra", "gujarat", "goa", "karnataka", "madhya pradesh",
            "pune", "mumbai", "ahmedabad", "bengaluru", "indore"
        ]
        self.min_order_quantity = 1

    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        """Normalizes text for fast tokenized search."""
        if not text:
            return ""
        # Lowercase and normalize whitespace
        cleaned = text.lower()
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def evaluate_lead(self, lead: Dict[str, Any]) -> FilterResult:
        """
        Evaluates a raw lead payload from IndiaMART against Aguatech parameters.
        Returns a FilterResult with pass/fail status and audit reasoning.
        """
        # IndiaMART fields can vary by API version; check standard aliases
        subject = self._clean_text(
            lead.get("subject") or lead.get("title") or lead.get("product_name") or lead.get("item_name") or ""
        )
        desc = self._clean_text(
            lead.get("desc") or lead.get("description") or lead.get("query_message") or ""
        )
        location = self._clean_text(
            lead.get("location") or lead.get("city") or lead.get("state") or lead.get("buyer_address") or ""
        )
        
        # Parse quantity safely
        raw_qty = lead.get("qty") or lead.get("quantity") or 1
        try:
            qty = int(raw_qty)
        except (ValueError, TypeError):
            qty = 1

        combined_text = f"{subject} {desc}".strip()

        if not combined_text:
            return FilterResult(
                passed=False,
                rejection_reason="Empty lead subject and description."
            )

        # -----------------------------------------------------------------
        # STEP 1: Strict Negative/Excluded Keyword Check (Protect budget!)
        # -----------------------------------------------------------------
        for bad_word in self.excluded_keywords:
            # Word boundary check or substring match
            pattern = r"\b" + re.escape(bad_word) + r"\b"
            if re.search(pattern, combined_text) or bad_word in combined_text:
                return FilterResult(
                    passed=False,
                    rejection_reason=f"Matched negative keyword exclusion: '{bad_word}'"
                )

        # -----------------------------------------------------------------
        # STEP 2: Product Keyword Match (Must match Aguatech MHE catalog)
        # -----------------------------------------------------------------
        matched_kw = None
        for good_word in self.included_keywords:
            pattern = r"\b" + re.escape(good_word) + r"\b"
            if re.search(pattern, combined_text) or good_word in combined_text:
                matched_kw = good_word
                break

        if not matched_kw:
            return FilterResult(
                passed=False,
                rejection_reason="No matching MHE product keyword found in requirement."
            )

        # -----------------------------------------------------------------
        # STEP 3: Geographic Boundary Check
        # -----------------------------------------------------------------
        matched_loc = None
        if self.target_locations:
            for loc in self.target_locations:
                if loc in location:
                    matched_loc = loc
                    break

            if not matched_loc:
                return FilterResult(
                    passed=False,
                    rejection_reason=f"Location '{location}' is outside target service clusters."
                )
        else:
            matched_loc = location or "All Locations"

        # -----------------------------------------------------------------
        # STEP 4: Minimum Order Quantity Check
        # -----------------------------------------------------------------
        if qty < self.min_order_quantity:
            return FilterResult(
                passed=False,
                rejection_reason=f"Quantity ({qty}) is below minimum threshold ({self.min_order_quantity})."
            )

        # -----------------------------------------------------------------
        # ALL CHECKS PASSED: Ready to buy!
        # -----------------------------------------------------------------
        return FilterResult(
            passed=True,
            matched_keyword=matched_kw,
            matched_location=matched_loc or location
        )


if __name__ == "__main__":
    # Self-test when executed directly
    logging.basicConfig(level=logging.INFO)
    engine = AguatechFilterEngine()

    test_lead_pass = {
        "id": "BL1001",
        "subject": "Requirement for Hydraulic Hand Pallet Truck 2.5 Ton",
        "desc": "Need heavy duty 2500kg hand pallet truck for warehouse in Chakan MIDC",
        "location": "Pune, Maharashtra",
        "qty": 2
    }

    test_lead_fail_negative = {
        "id": "BL1002",
        "subject": "Used Forklift Repair and Scrap battery",
        "desc": "Want scrap and second hand stacker parts",
        "location": "Pune, Maharashtra",
        "qty": 1
    }

    test_lead_fail_location = {
        "id": "BL1003",
        "subject": "Electric Stacker 1.5 Ton needed",
        "desc": "Required battery operated stacker",
        "location": "Guwahati, Assam",
        "qty": 1
    }

    print("\n--- TEST RESULTS ---")
    for lead in [test_lead_pass, test_lead_fail_negative, test_lead_fail_location]:
        res = engine.evaluate_lead(lead)
        print(f"Lead ID {lead['id']} ({lead['subject']}):")
        print(f"  Passed: {res.passed} | Reason/Keyword: {res.matched_keyword or res.rejection_reason}")
