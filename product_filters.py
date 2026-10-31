"""
Product Filter Engine for Aguatech Engineers Pvt. Ltd. (Pune)
Specialized Material Handling Equipment (MHE) Matching Matrix
Supports Tiered Priority Keywords, Buyer Authentication, Engagement Metrics, and Category-City Scoping.
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
    tier: int = 1                     # 1 = Tier 1 (High Value), 2 = Tier 2 (Standard), 3 = Tier 3 (Alert Only)
    action: str = "BUY"               # "BUY" or "ALERT_ONLY" or "REJECT"
    matched_keyword: Optional[str] = None
    matched_location: Optional[str] = None
    rejection_reason: Optional[str] = None
    buyer_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "tier": self.tier,
            "action": self.action,
            "matched_keyword": self.matched_keyword,
            "matched_location": self.matched_location,
            "rejection_reason": self.rejection_reason,
            "buyer_score": self.buyer_score
        }


class AguatechFilterEngine:
    """
    High-speed text analysis & matching engine for IndiaMART Buy Leads.
    Evaluates incoming leads against Aguatech's MHE catalog, negative filters,
    buyer verification, responsiveness history, and geographic boundaries.
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
                f"[Filter Engine] Loaded Tier 1 ({len(self.tier_1_keywords)}), "
                f"Tier 2 ({len(self.tier_2_keywords)}), "
                f"Tier 3 ({len(self.tier_3_keywords)}), "
                f"{len(self.excluded_keywords)} negative keywords."
            )
        except Exception as e:
            logger.error(f"[Filter Engine] Error reading config from {self.config_path}: {e}")
            self._load_defaults()

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        filters = data.get("filters", {})
        
        # Priority tiers
        priority_tiers = filters.get("priority_tiers", {})
        self.tier_1_keywords: List[str] = [
            k.strip().lower() for k in priority_tiers.get("tier_1_high_priority_buy", []) if k.strip()
        ]
        self.tier_2_keywords: List[str] = [
            k.strip().lower() for k in priority_tiers.get("tier_2_standard_buy", []) if k.strip()
        ]
        self.tier_3_keywords: List[str] = [
            k.strip().lower() for k in priority_tiers.get("tier_3_alert_only", []) if k.strip()
        ]

        if not self.tier_1_keywords and not self.tier_2_keywords:
            raw_included = filters.get("included_keywords", [])
            self.tier_1_keywords = [k.strip().lower() for k in raw_included if k.strip()]

        self.excluded_keywords: List[str] = [
            k.strip().lower() for k in filters.get("excluded_keywords", []) if k.strip()
        ]
        self.target_locations: List[str] = [
            loc.strip().lower() for loc in filters.get("target_locations", []) if loc.strip()
        ]
        self.pan_india_for_tier1: bool = bool(filters.get("pan_india_for_tier1", True))
        
        # Buyer Authentication & Responsiveness Rules
        self.require_mobile_verified: bool = bool(filters.get("require_mobile_verified", False))
        self.require_gst_buyer: bool = bool(filters.get("require_gst_buyer", False))
        self.min_buyer_reply_rate: float = float(filters.get("min_buyer_reply_rate", 0.0))
        self.min_order_quantity: int = int(filters.get("min_order_quantity", 1))

        # Category-to-City Matrix override (if mapped)
        self.category_city_matrix: Dict[str, List[str]] = {
            cat.lower(): [c.lower() for c in cities]
            for cat, cities in filters.get("category_city_matrix", {}).items()
        }

    def _load_defaults(self) -> None:
        self.tier_1_keywords = [
            "goods lift", "industrial goods lift", "freight elevator", "hydraulic cargo lift",
            "electric forklift", "battery operated forklift", "forklift",
            "reach truck", "reach stacker", "electric reach stacker",
            "scissor lift", "hydraulic scissor lift", "scissor lift table", "self propelled scissor lift",
            "hydraulic floor crane", "floor crane"
        ]
        self.tier_2_keywords = [
            "battery operated pallet truck", "bopt", "electric pallet truck",
            "pallet truck", "hand pallet", "hydraulic pallet", "pallet jack",
            "stacker", "hydraulic stacker", "semi electric stacker", "manual stacker",
            "electric stacker", "battery operated hydraulic stacker",
            "dock leveler", "hydraulic dock leveler", "container loading ramp", "loading ramp",
            "hydraulic ladder", "aerial work platform"
        ]
        self.tier_3_keywords = [
            "drum handling", "drum stacker", "drum lifter", "drum tilter", "drum trolley",
            "die loader", "die table"
        ]
        self.excluded_keywords = [
            "toy", "second hand", "used", "scrap", "repair only", "repairing", "service only",
            "rent", "hire", "rental", "job work", "water plant", "mineral water", "driver", "job"
        ]
        self.target_locations = [
            "pune", "mumbai", "thane", "navi mumbai", "nashik", "chhatrapati sambhajinagar",
            "aurangabad", "nagpur", "kolhapur", "solapur", "satara", "sangli", "ahilyanagar",
            "ahmednagar", "pimpri chinchwad", "bhor", "maharashtra",
            "ahmedabad", "surat", "vadodara", "rajkot", "vapi", "ankleshwar", "bharuch", "gujarat",
            "bengaluru", "bangalore", "mysore", "karnataka", "goa",
            "hyderabad", "indore", "bhopal", "chennai", "coimbatore", "kolkata"
        ]
        self.pan_india_for_tier1 = True
        self.require_mobile_verified = False
        self.require_gst_buyer = False
        self.min_buyer_reply_rate = 0.0
        self.min_order_quantity = 1
        self.category_city_matrix = {}

    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        """Normalizes text for fast tokenized search."""
        if not text:
            return ""
        cleaned = text.lower()
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def evaluate_lead(self, lead: Dict[str, Any]) -> FilterResult:
        """
        Evaluates a raw lead payload from IndiaMART against Aguatech parameters
        including Buyer Verification, Response Rates, and City Matrix.
        """
        subject = self._clean_text(
            lead.get("subject") or lead.get("title") or lead.get("product_name") or lead.get("item_name") or ""
        )
        desc = self._clean_text(
            lead.get("desc") or lead.get("description") or lead.get("query_message") or ""
        )
        location = self._clean_text(
            lead.get("location") or lead.get("city") or lead.get("state") or lead.get("buyer_address") or ""
        )
        
        raw_qty = lead.get("qty") or lead.get("quantity") or 1
        try:
            qty = int(raw_qty)
        except (ValueError, TypeError):
            qty = 1

        combined_text = f"{subject} {desc}".strip()

        if not combined_text:
            return FilterResult(
                passed=False,
                action="REJECT",
                rejection_reason="Empty lead subject and description."
            )

        # -----------------------------------------------------------------
        # STEP 1: Strict Negative/Excluded Keyword Check (Protect budget!)
        # -----------------------------------------------------------------
        for bad_word in self.excluded_keywords:
            pattern = r"\b" + re.escape(bad_word) + r"\b"
            if re.search(pattern, combined_text) or bad_word in combined_text:
                return FilterResult(
                    passed=False,
                    action="REJECT",
                    rejection_reason=f"Matched negative keyword exclusion: '{bad_word}'"
                )

        # -----------------------------------------------------------------
        # STEP 2: Minimum Order Quantity Check
        # -----------------------------------------------------------------
        if qty < self.min_order_quantity:
            return FilterResult(
                passed=False,
                action="REJECT",
                rejection_reason=f"Quantity ({qty}) is below minimum threshold ({self.min_order_quantity})."
            )

        # -----------------------------------------------------------------
        # STEP 3: Buyer Authentication & Engagement Checks
        # -----------------------------------------------------------------
        buyer_metrics = lead.get("buyer_metrics", {})
        
        # Check Mobile Verification
        if self.require_mobile_verified:
            is_mob = buyer_metrics.get("is_mob", False) or lead.get("is_verified", False)
            if not is_mob:
                return FilterResult(
                    passed=False,
                    action="REJECT",
                    rejection_reason="Buyer phone is unverified (require_mobile_verified=true)."
                )

        # Check GST Verification
        if self.require_gst_buyer:
            is_gst = buyer_metrics.get("is_gst", False) or bool(lead.get("buyer_gst"))
            if not is_gst:
                return FilterResult(
                    passed=False,
                    action="REJECT",
                    rejection_reason="Buyer has no verified GSTIN (require_gst_buyer=true)."
                )

        # Check Buyer Responsiveness / Reply Rate
        reply_rate = buyer_metrics.get("reply_rate", 0.0)
        req_count = buyer_metrics.get("req_count", 0)
        if self.min_buyer_reply_rate > 0.0 and req_count >= 3:
            if reply_rate < self.min_buyer_reply_rate:
                return FilterResult(
                    passed=False,
                    action="REJECT",
                    rejection_reason=f"Buyer response rate ({reply_rate}%) is below minimum ({self.min_buyer_reply_rate}%)."
                )

        # -----------------------------------------------------------------
        # STEP 4: DESCENDING PRIORITY MATCHING
        # -----------------------------------------------------------------

        # Check Tier 1: Highest Priority Capital Equipment (Goods Lifts, Forklifts, Scissor Lifts, Floor Cranes)
        for good_word in self.tier_1_keywords:
            pattern = r"\b" + re.escape(good_word) + r"\b"
            if re.search(pattern, combined_text) or good_word in combined_text:
                if self.pan_india_for_tier1 or self._matches_location(good_word, location):
                    matched_loc = self._extract_matched_location(location) or location or "India"
                    return FilterResult(
                        passed=True,
                        tier=1,
                        action="BUY",
                        matched_keyword=good_word,
                        matched_location=matched_loc,
                        buyer_score=reply_rate
                    )

        # Check Tier 2: Standard Core Volume Products (Pallet Trucks, Stackers, BOPT, Dock Levelers)
        for good_word in self.tier_2_keywords:
            pattern = r"\b" + re.escape(good_word) + r"\b"
            if re.search(pattern, combined_text) or good_word in combined_text:
                if self._matches_location(good_word, location):
                    matched_loc = self._extract_matched_location(location) or location
                    return FilterResult(
                        passed=True,
                        tier=2,
                        action="BUY",
                        matched_keyword=good_word,
                        matched_location=matched_loc,
                        buyer_score=reply_rate
                    )
                else:
                    return FilterResult(
                        passed=False,
                        tier=2,
                        action="REJECT",
                        rejection_reason=f"Tier 2 product '{good_word}' outside target cities: '{location}'"
                    )

        # Check Tier 3: Specialized MHE / Accessories (Alert Only - Zero Auto-Credits)
        for good_word in self.tier_3_keywords:
            pattern = r"\b" + re.escape(good_word) + r"\b"
            if re.search(pattern, combined_text) or good_word in combined_text:
                matched_loc = self._extract_matched_location(location) or location
                return FilterResult(
                    passed=True,
                    tier=3,
                    action="ALERT_ONLY",
                    matched_keyword=good_word,
                    matched_location=matched_loc,
                    buyer_score=reply_rate
                )

        # No keyword matched
        return FilterResult(
            passed=False,
            action="REJECT",
            rejection_reason="No matching MHE product keyword found in requirement."
        )

    def _matches_location(self, keyword: str, location: str) -> bool:
        # Check if category has a specific city mapping
        specific_cities = self.category_city_matrix.get(keyword.lower())
        if specific_cities:
            for c in specific_cities:
                if c in location:
                    return True
            return False

        # Fallback to general target locations
        if not self.target_locations:
            return True
        for loc in self.target_locations:
            if loc in location:
                return True
        return False

    def _extract_matched_location(self, location: str) -> Optional[str]:
        if not self.target_locations:
            return location
        for loc in self.target_locations:
            if loc in location:
                return loc
        return None
