"""Tests for app initialization config loading and validation."""

import pytest
import yaml

from app_initialization import load_hyatt_card_config, validate_config


def _base_config():
    """Return a minimal valid config structure for validation tests."""
    return {
        "hyatt_cards": {
            "personal": {
                "folder": "transactions/hyatt personal",
                "renewal_day": 2,
                "card_endings": ["1234"],
            },
            "business": {
                "folder": "transactions/hyatt business",
                "renewal_day": 2,
                "card_endings": ["5309"],
            },
        },
        "cards": {
            "sample_card": {
                "display_name": "Sample Card",
                "year": 2026,
                "annual_fee": 100,
                "renewal_month": 1,
                "renewal_day": 1,
                "benefits": [
                    {
                        "id": "sample_benefit",
                        "category": "Sample",
                        "amount": 10,
                        "frequency": "monthly",
                        "renewal_type": "calendar_year",
                    }
                ],
            }
        },
    }


def test_load_hyatt_card_config_reads_renewal_day(tmp_path):
    """Hyatt card config should include per-card renewal_day values."""
    config = _base_config()
    config["hyatt_cards"]["personal"]["renewal_day"] = 9
    config["hyatt_cards"]["business"]["renewal_day"] = 13

    config_path = tmp_path / "benefits_config.yaml"
    config_path.write_text(yaml.dump(config))

    parsed = load_hyatt_card_config(config_path)

    assert parsed["personal"]["renewal_day"] == 9
    assert parsed["business"]["renewal_day"] == 13


@pytest.mark.parametrize("bad_value", [0, 32, "2", None])
def test_load_hyatt_card_config_rejects_invalid_renewal_day(tmp_path, bad_value):
    """Hyatt card renewal_day must be an integer in the 1-31 range."""
    config = _base_config()
    config["hyatt_cards"]["personal"]["renewal_day"] = bad_value

    config_path = tmp_path / "benefits_config.yaml"
    config_path.write_text(yaml.dump(config))

    with pytest.raises(ValueError, match="hyatt_cards.personal.renewal_day"):
        load_hyatt_card_config(config_path)


def test_validate_config_rejects_missing_hyatt_renewal_day():
    """Uploaded config should fail validation when Hyatt renewal_day is missing."""
    config = _base_config()
    del config["hyatt_cards"]["business"]["renewal_day"]

    is_valid, message = validate_config(yaml.dump(config).encode("utf-8"))

    assert not is_valid
    assert "hyatt_cards.business.renewal_day" in message
