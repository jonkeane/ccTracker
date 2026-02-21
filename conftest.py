"""
Shared pytest fixtures for all test modules.

This provides common test data and helper functions used across
test_card_processor.py, test_benefits_calculator.py, and test_stays_manager.py
"""

import pytest
import pandas as pd
import yaml
import json
from pathlib import Path
from datetime import date


@pytest.fixture
def sample_personal_csv_data():
    """Sample personal card CSV data for testing."""
    return pd.DataFrame({
        'Transaction Date': ['01/10/2025', '01/15/2025', '02/05/2025'],
        'Post Date': ['01/12/2025', '01/17/2025', '02/07/2025'],
        'Description': ['Store A', 'Store B', 'Store C'],
        'Category': ['Shopping', 'Dining', 'Shopping'],
        'Type': ['Sale', 'Sale', 'Sale'],
        'Amount': [-5100.0, -1000.0, -5200.0],
        'Memo': ['', '', ''],
    })


@pytest.fixture
def sample_business_csv_data():
    """Sample business card CSV data for testing."""
    return pd.DataFrame({
        'Transaction Date': ['01/10/2025', '02/15/2025'],
        'Post Date': ['01/12/2025', '02/17/2025'],
        'Description': ['Business expense A', 'Business expense B'],
        'Category': ['Office', 'Travel'],
        'Type': ['Sale', 'Sale'],
        'Amount': [-12000.0, -9000.0],
        'Memo': ['', ''],
    })


@pytest.fixture
def mock_csv_folder(tmp_path, sample_personal_csv_data):
    """Create a temporary folder with mock CSV files."""
    folder = tmp_path / "hyatt personal"
    folder.mkdir()

    # Write sample CSV
    csv_path = folder / "statement.CSV"
    sample_personal_csv_data.to_csv(csv_path, index=False)

    return folder


@pytest.fixture
def complete_benefits_config():
    """Complete benefits configuration covering all scenarios."""
    return {
        'cards': {
            'test_platinum_2025': {
                'display_name': 'Test Platinum Card',
                'year': 2025,
                'annual_fee': 695,
                'renewal_month': 7,
                'renewal_day': 15,
                'benefits': [
                    {
                        'id': 'resy',
                        'category': 'Dining Credit',
                        'amount': 100,
                        'frequency': 'quarterly',
                        'renewal_type': 'calendar_year'
                    },
                    {
                        'id': 'airline',
                        'category': 'Airline Credit',
                        'amount': 200,
                        'frequency': 'yearly',
                        'renewal_type': 'calendar_year'
                    },
                    {
                        'id': 'hotel',
                        'category': 'Hotel Credit',
                        'amount': 300,
                        'frequency': 'half_yearly',
                        'renewal_type': 'calendar_year'
                    },
                    {
                        'id': 'anniversary_bonus',
                        'category': 'Anniversary Bonus',
                        'amount': 100,
                        'frequency': 'yearly',
                        'renewal_type': 'card_anniversary'
                    },
                    {
                        'id': 'monthly_credit',
                        'category': 'Monthly Credit',
                        'amount': 25,
                        'frequency': 'monthly',
                        'renewal_type': 'calendar_year'
                    }
                ]
            },
            'test_venture_2025': {
                'display_name': 'Test Venture Card',
                'year': 2025,
                'annual_fee': 395,
                'renewal_month': 11,
                'renewal_day': 9,
                'benefits': [
                    {
                        'id': 'travel',
                        'category': 'Travel Credit',
                        'amount': 300,
                        'frequency': 'yearly',
                        'renewal_type': 'card_anniversary'
                    },
                    {
                        'id': 'GE_precheck',
                        'category': 'Global Entry',
                        'amount': 120,
                        'frequency': 'every_4_years',
                        'renewal_type': 'card_anniversary'
                    }
                ]
            },
            'test_venture_2026': {
                'display_name': 'Test Venture Card',
                'year': 2026,
                'annual_fee': 395,
                'renewal_month': 11,
                'renewal_day': 9,
                'benefits': [
                    {
                        'id': 'travel',
                        'category': 'Travel Credit',
                        'amount': 300,
                        'frequency': 'yearly',
                        'renewal_type': 'card_anniversary'
                    },
                    {
                        'id': 'GE_precheck',
                        'category': 'Global Entry',
                        'amount': 120,
                        'frequency': 'every_4_years',
                        'renewal_type': 'card_anniversary'
                    }
                ]
            }
        }
    }


@pytest.fixture
def benefits_config_file(tmp_path, complete_benefits_config):
    """Write benefits config to a temporary YAML file."""
    config_path = tmp_path / "benefits_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(complete_benefits_config, f)
    return config_path


@pytest.fixture
def empty_benefits_state(tmp_path):
    """Create an empty benefits state JSON file."""
    state_path = tmp_path / "benefits_state.json"
    state_path.write_text("{}")
    return state_path


@pytest.fixture
def empty_stays_state(tmp_path):
    """Create an empty stays state JSON file."""
    state_path = tmp_path / "stays_state.json"
    state_path.write_text(json.dumps({"stays": [], "goh_nights": []}))
    return state_path


@pytest.fixture
def sample_stays_data():
    """Sample stays data for testing."""
    return [
        {
            'name': 'Hyatt Regency Chicago',
            'check_in': date(2025, 3, 10),
            'check_out': date(2025, 3, 13)
        },
        {
            'name': 'Grand Hyatt New York',
            'check_in': date(2025, 5, 20),
            'check_out': date(2025, 5, 25)
        }
    ]


@pytest.fixture
def sample_goh_nights_data():
    """Sample GOH nights data for testing."""
    return [
        {
            'name': 'John Smith',
            'date': date(2025, 4, 15)
        },
        {
            'name': 'Jane Doe',
            'date': date(2025, 6, 10)
        }
    ]


# Helper functions for assertions

def assert_nights_calculation(cumsum, previous_cumsum, expected_nights, card_type='personal'):
    """
    Helper to assert bonus night calculations.

    Args:
        cumsum: Current cumulative spending
        previous_cumsum: Previous cumulative spending
        expected_nights: Expected number of bonus nights
        card_type: 'personal' or 'business'
    """
    from benefits.card_processor import CardProcessor
    processor = CardProcessor()

    if card_type == 'personal':
        row = pd.Series({
            'cumsum': cumsum,
            'previous_cumsum': previous_cumsum,
        })
        nights = processor._calculate_personal_bonus(row)
    else:
        row = pd.Series({
            'cumsum_year': cumsum,
            'previous_cumsum_year': previous_cumsum,
        })
        nights = processor._calculate_business_bonus(row)

    assert nights == expected_nights, f"Expected {expected_nights} nights, got {nights}"


def assert_date_in_range(test_date, start_date, end_date):
    """Helper to assert a date is within a range."""
    assert start_date <= test_date <= end_date, \
        f"{test_date} is not between {start_date} and {end_date}"


def assert_period_format(period, expected_type='calendar'):
    """
    Helper to assert period format is correct.

    Args:
        period: Period string (e.g., '2025-Q1', '2025-A07')
        expected_type: 'calendar' or 'anniversary'
    """
    if expected_type == 'calendar':
        # Calendar periods should NOT contain '-A'
        assert '-A' not in period, f"Calendar period {period} should not contain '-A'"
    else:
        # Anniversary periods should contain '-A'
        assert '-A' in period, f"Anniversary period {period} should contain '-A'"
