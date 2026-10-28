"""
Simulation & Testing Suite for Aguatech Engineers Pvt. Ltd.
Feeds realistic IndiaMART Buy Lead payloads into the filter and notification engine.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime

# Configure Windows console for UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from product_filters import AguatechFilterEngine
from tele_alerts import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AguatechBot.Simulator")

# Diverse test dataset reflecting real IndiaMART marketplace inquiries
SAMPLE_LEADS = [
    {
        "id": "BL-AGUA-001",
        "subject": "Requirement for Hydraulic Hand Pallet Truck 2500 kg Capacity",
        "desc": "Need 3 units of heavy duty hydraulic hand pallet truck for our engineering warehouse in Chakan MIDC Pune. Delivery required within 1 week.",
        "location": "Pune, Maharashtra",
        "qty": 3,
        "expected": True,
        "note": "Exact Aguatech core product (AHPT)"
    },
    {
        "id": "BL-AGUA-002",
        "subject": "Semi Electric Stacker 1.5 Ton Lifting Height 3.5 Meter",
        "desc": "Looking for battery operated semi electric stacker for pallet racking in Sanand industrial area. Send best quotation with warranty.",
        "location": "Ahmedabad, Gujarat",
        "qty": 1,
        "expected": True,
        "note": "Exact Aguatech core product (STAKON Series)"
    },
    {
        "id": "BL-AGUA-003",
        "subject": "Electro Hydraulic Goods Lift 1000 kg for 2 Floors (G+1)",
        "desc": "Industrial cage elevator / goods lift required for factory shop floor at Turbhe MIDC Navi Mumbai.",
        "location": "Navi Mumbai, Maharashtra",
        "qty": 1,
        "expected": True,
        "note": "Exact Aguatech custom engineering product"
    },
    {
        "id": "BL-AGUA-004",
        "subject": "Hydraulic Scissor Lift Table 500kg Capacity",
        "desc": "Required fixed scissor lift table for die loading and assembly line in Pimpri Pune.",
        "location": "Pimpri Chinchwad, Pune",
        "qty": 2,
        "expected": True,
        "note": "Exact Aguatech core product"
    },
    {
        "id": "BL-AGUA-005",
        "subject": "Drum Barrel Stacker Cum Tilter 350kg",
        "desc": "Need drum handling equipment to shift and tilt 200 liter chemical barrels safely.",
        "location": "Vadodara, Gujarat",
        "qty": 1,
        "expected": True,
        "note": "Exact Aguatech drum handling line"
    },
    {
        "id": "BL-AGUA-006",
        "subject": "Used Second Hand Forklift Scrap for Sale",
        "desc": "We have old scrap battery forklift and second hand pallet truck available.",
        "location": "Pune, Maharashtra",
        "qty": 1,
        "expected": False,
        "note": "Should FAIL: Contains negative keywords 'used', 'second hand', 'scrap'"
    },
    {
        "id": "BL-AGUA-007",
        "subject": "Packaged Drinking Water Plant 1000 LPH with Pet Bottles",
        "desc": "Need turnkey mineral water treatment plant and 500ml water bottle filling line.",
        "location": "Indore, Madhya Pradesh",
        "qty": 1,
        "expected": False,
        "note": "Should FAIL: Water plant negative keyword (preventing Agua/water confusion)"
    },
    {
        "id": "BL-AGUA-008",
        "subject": "Electric Stacker 2 Ton Required Urgently",
        "desc": "Need electric reach truck or stacker for warehouse in Guwahati.",
        "location": "Guwahati, Assam",
        "qty": 1,
        "expected": False,
        "note": "Should FAIL: Outside Aguatech target geographic territory"
    },
    {
        "id": "BL-AGUA-009",
        "subject": "Hydraulic Dock Leveler 10 Ton for Container Loading",
        "desc": "Looking for stationary hydraulic dock leveler for warehouse ramp in Bhiwandi Thane.",
        "location": "Thane, Maharashtra",
        "qty": 2,
        "expected": True,
        "note": "Exact Aguatech dock equipment"
    },
    {
        "id": "BL-AGUA-010",
        "subject": "Toy Forklift and Plastic Mini Truck for Kids",
        "desc": "Looking for plastic toy forklift battery operated model.",
        "location": "Mumbai, Maharashtra",
        "qty": 100,
        "expected": False,
        "note": "Should FAIL: Toy negative keyword"
    }
]


async def run_simulation(send_real_alerts: bool = False):
    print("\n" + "=" * 70)
    print("   AGUATECH ENGINEERS PVT. LTD. - LEAD FILTER SIMULATION SUITE")
    print("=" * 70)
    print(f"Timestamp:  {datetime.now().strftime('%d-%b-%Y %I:%M:%S %p')}")
    print(f"Test Leads: {len(SAMPLE_LEADS)} real-world scenarios")
    print(f"Alerts:     {'Telegram Bot Dispatch ACTIVE' if send_real_alerts else 'Dry-run Console Only'}")
    print("=" * 70 + "\n")

    filter_engine = AguatechFilterEngine()
    notifier = TelegramNotifier() if send_real_alerts else None

    passed_count = 0
    rejected_count = 0
    correct_matches = 0

    for i, lead in enumerate(SAMPLE_LEADS, 1):
        res = filter_engine.evaluate_lead(lead)
        is_match = res.passed
        expected = lead["expected"]
        is_correct = (is_match == expected)

        if is_correct:
            correct_matches += 1

        if is_match:
            passed_count += 1
            status_symbol = "✅ [MATCHED - AUTO-BUY]"
            detail = f"Category: '{res.matched_keyword}' | Region: '{res.matched_location}'"
        else:
            rejected_count += 1
            status_symbol = "⛔ [REJECTED]"
            detail = f"Reason: {res.rejection_reason}"

        print(f"Test #{i:02d} | ID: {lead['id']} | {status_symbol}")
        print(f"  Title:    {lead['subject']}")
        print(f"  Location: {lead['location']} | Qty: {lead['qty']}")
        print(f"  Audit:    {detail}")
        print(f"  Target:   {lead['note']}")
        print(f"  Accuracy: {'PERFECT' if is_correct else 'MISMATCH'}")
        print("-" * 70)

        # Dispatch test alert to Telegram if requested and matched
        if is_match and notifier and send_real_alerts:
            await notifier.send_alert(
                lead=lead,
                is_dry_run=True,
                success=True,
                matched_kw=res.matched_keyword
            )
            await asyncio.sleep(0.5)

    accuracy_pct = (correct_matches / len(SAMPLE_LEADS)) * 100
    print("\n" + "=" * 70)
    print("                      SIMULATION SUMMARY")
    print("=" * 70)
    print(f"Total Evaluated:     {len(SAMPLE_LEADS)}")
    print(f"Accepted for Buy:    {passed_count} leads (All legitimate Aguatech MHE equipment)")
    print(f"Safely Filtered:     {rejected_count} leads (Junk/Scrap/Retail/Out of state)")
    print(f"Filter Accuracy:     {accuracy_pct:.1f}%")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    send_alerts = "--notify" in sys.argv
    asyncio.run(run_simulation(send_real_alerts=send_alerts))
