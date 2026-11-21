"""
Test Suite: Phase 4 Nagarpranali+ UX & Usability Verification
============================================================
Verifies compliance with Section 5 of the NAGARPRANALI+ assignment:
  1. Plain-language labels & first-time digital citizen formatting.
  2. One primary action per screen.
  3. Visible feedback on what system understood and what happens next.
  4. Anti-dark-pattern compliance (zero streaks, zero fake countdowns, zero forced logins).
  5. Multi-language accessibility cues (English, Hindi, Marathi).
"""

import sys
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(MASTERDB_DIR) not in sys.path:
    sys.path.insert(0, str(MASTERDB_DIR))

import unified_auth_runtime
import nagarpranali_adapter


def test_citizen_ux_card_thane_creek_happy_path():
    """Verifies that citizen UX card formats plain language for Thane Creek Mangrove."""
    card = nagarpranali_adapter.format_citizen_ux_card(location_name="Thane Creek Zone A")
    assert card["badge"]["text"] == "Protected Green Zone"
    assert card["badge"]["color"] == "green"
    assert "Thane Creek Mangrove Reserve" in card["headline"]
    assert "65%" in card["plain_explanation"]
    assert card["what_system_understood"]["location_recognized"] == "Thane Creek Mangrove Reserve"
    assert "Forest Officer" in card["what_happens_next"]
    assert card["receipt_id"].startswith("CR-")
    assert card["primary_action"] == "View Full Details"


def test_citizen_ux_card_fail_closed_unmapped():
    """Verifies that an unmapped location renders clean civic routing without error."""
    card = nagarpranali_adapter.format_citizen_ux_card(lat=0.0, lon=0.0)
    assert card["badge"]["text"] == "Urban Civic Zone"
    assert card["badge"]["color"] == "blue"
    assert "No protected forest or mangrove zone found here" in card["headline"]
    assert "standard municipal" in card["plain_explanation"].lower()
    assert card["receipt_id"].startswith("ABS-")


def test_citizen_view_endpoint_via_runtime():
    """Verifies GET /api/nagarpranali/citizen-view route handler."""
    card = unified_auth_runtime.get_nagarpranali_citizen_view(location="Thane Creek")
    assert card["screen_title"] == "Area Environmental Check"
    assert "Thane Creek" in card["headline"]
    assert card["receipt_id"].startswith("CR-")


def test_anti_dark_pattern_compliance():
    """Verifies that output contains no manipulative engagement traps or countdowns."""
    card = nagarpranali_adapter.format_citizen_ux_card(location_name="Thane Creek Zone A")

    # Serialize to text to check for dark patterns
    card_text = str(card).lower()
    dark_patterns = [
        "urgent",
        "hurry",
        "streak",
        "expires in",
        "countdown",
        "only today",
        "don't miss",
        "points earned",
    ]
    for pattern in dark_patterns:
        assert pattern not in card_text, f"Dark pattern detected: {pattern}"


def test_multilingual_options_present():
    """Verifies support cues for local languages (English, Hindi, Marathi)."""
    card = nagarpranali_adapter.format_citizen_ux_card(location_name="Thane Creek Zone A")
    languages = card.get("language_options", [])
    assert len(languages) >= 3
    lang_codes = [l["code"] for l in languages]
    assert "en" in lang_codes
    assert "hi" in lang_codes
    assert "mr" in lang_codes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
