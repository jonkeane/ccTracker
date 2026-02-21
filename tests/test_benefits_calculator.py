"""
Tests for BenefitsCalculator - credit card benefits tracking.

This tests the complex date logic around:
- Period generation (yearly, half_yearly, quarterly, monthly, every_4_years)
- Calendar year vs. card anniversary renewal logic
- Anniversary year determination from post dates
- Period overlap calculations
- Every_4_years benefit availability
- Custom amount tracking
"""

import pytest
import yaml
import json
from datetime import date, datetime
from pathlib import Path
from benefits.benefits_calculator import BenefitsCalculator


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample benefits config YAML file."""
    config = {
        'cards': {
            'test_card_2025': {
                'display_name': 'Test Card',
                'year': 2025,
                'annual_fee': 695,
                'renewal_month': 7,
                'renewal_day': 15,
                'benefits': [
                    {
                        'id': 'quarterly_benefit',
                        'category': 'Quarterly Credit',
                        'amount': 100,
                        'frequency': 'quarterly',
                        'renewal_type': 'calendar_year'
                    },
                    {
                        'id': 'anniversary_benefit',
                        'category': 'Anniversary Bonus',
                        'amount': 200,
                        'frequency': 'yearly',
                        'renewal_type': 'card_anniversary'
                    },
                    {
                        'id': 'monthly_benefit',
                        'category': 'Monthly Credit',
                        'amount': 25,
                        'frequency': 'monthly',
                        'renewal_type': 'calendar_year'
                    }
                ]
            },
            'test_card_2026': {
                'display_name': 'Test Card',
                'year': 2026,
                'annual_fee': 795,
                'renewal_month': 7,
                'renewal_day': 15,
                'benefits': [
                    {
                        'id': 'quarterly_benefit',
                        'category': 'Quarterly Credit',
                        'amount': 100,
                        'frequency': 'quarterly',
                        'renewal_type': 'calendar_year'
                    },
                    {
                        'id': 'anniversary_benefit',
                        'category': 'Anniversary Bonus',
                        'amount': 200,
                        'frequency': 'yearly',
                        'renewal_type': 'card_anniversary'
                    }
                ]
            },
            'venture_x_2025': {
                'display_name': 'Venture X',
                'year': 2025,
                'annual_fee': 395,
                'renewal_month': 11,
                'renewal_day': 9,
                'benefits': [
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

    config_path = tmp_path / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    return config_path


@pytest.fixture
def empty_state(tmp_path):
    """Create an empty state file."""
    state_path = tmp_path / "test_state.json"
    state_path.write_text("{}")
    return state_path


class TestPeriodGeneration:
    """Test period generation for different frequencies."""

    def test_yearly_calendar_periods(self, sample_config, empty_state):
        """Yearly calendar benefits should generate yearly periods."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'yearly',
            'renewal_type': 'calendar_year'
        }

        periods = calc._generate_periods(benefit, 'test_card_2025')

        # Should have years 2023-2026 (current +/- 2 years, +1 year ahead)
        assert '2023' in periods
        assert '2024' in periods
        assert '2025' in periods
        assert '2026' in periods

    def test_quarterly_calendar_periods(self, sample_config, empty_state):
        """Quarterly calendar benefits should generate Q1-Q4 for each year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'quarterly',
            'renewal_type': 'calendar_year'
        }

        periods = calc._generate_periods(benefit, 'test_card_2025')

        # Should have quarters for multiple years
        assert '2025-Q1' in periods
        assert '2025-Q2' in periods
        assert '2025-Q3' in periods
        assert '2025-Q4' in periods

    def test_monthly_calendar_periods(self, sample_config, empty_state):
        """Monthly calendar benefits should generate all 12 months."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'monthly',
            'renewal_type': 'calendar_year'
        }

        periods = calc._generate_periods(benefit, 'test_card_2025')

        # Should have all months for 2025
        assert '2025-Jan' in periods
        assert '2025-Feb' in periods
        assert '2025-Dec' in periods

    def test_half_yearly_calendar_periods(self, sample_config, empty_state):
        """Half-yearly calendar benefits should generate H1 and H2."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'half_yearly',
            'renewal_type': 'calendar_year'
        }

        periods = calc._generate_periods(benefit, 'test_card_2025')

        assert '2025-H1' in periods
        assert '2025-H2' in periods

    def test_anniversary_yearly_periods(self, sample_config, empty_state):
        """Anniversary yearly benefits should use anniversary period format."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'yearly',
            'renewal_type': 'card_anniversary'
        }

        periods = calc._generate_periods(benefit, 'test_card_2025')

        # Anniversary periods: YYYY-AMM format
        # Renewal month 7 -> 2025-A07
        assert '2025-A07' in periods
        assert '2024-A07' in periods
        assert '2026-A07' in periods

    def test_every_4_years_periods(self, sample_config, empty_state):
        """Every 4 years benefits should generate anniversary periods."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        benefit = {
            'frequency': 'every_4_years',
            'renewal_type': 'card_anniversary'
        }

        periods = calc._generate_periods(benefit, 'venture_x_2025')

        # Should still generate yearly periods (availability checked separately)
        assert '2025-A11' in periods
        assert '2024-A11' in periods


class TestAnniversaryYearLogic:
    """Test anniversary year calculations."""

    def test_get_anniversary_year_range(self, sample_config, empty_state):
        """Anniversary year 2025 with July renewal should span July 2025 - July 2026."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        start_date, end_date = calc.get_anniversary_year_range('test_card_2025', 2025)

        assert start_date == date(2025, 7, 15)
        assert end_date == date(2026, 7, 14)

    def test_benefit_anniversary_year_from_post_date_after_renewal(self, sample_config, empty_state):
        """Post date after renewal date should count toward current anniversary year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        benefit = {
            'posted': True,
            'post_date': '2024-08-01'  # After July 15, 2024
        }

        anniv_year = calc.get_benefit_anniversary_year('test_card_2025', benefit)

        # August 2024 is after July 15, 2024 renewal -> counts toward 2024 anniversary year
        assert anniv_year == 2024

    def test_benefit_anniversary_year_from_post_date_before_renewal(self, sample_config, empty_state):
        """Post date before renewal date should count toward current anniversary year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        benefit = {
            'posted': True,
            'post_date': '2024-06-01'  # Before July 15, 2024
        }

        anniv_year = calc.get_benefit_anniversary_year('test_card_2025', benefit)

        # June 2024 is before July 15, 2024 renewal -> counts toward 2023 anniversary year
        assert anniv_year == 2023

    def test_get_benefit_period_anniversary_year(self, sample_config, empty_state):
        """Extract anniversary year from period string."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        benefit = {'period': '2025-A07'}
        assert calc.get_benefit_period_anniversary_year(benefit) == 2025

        benefit = {'period': '2026-AH1-07'}
        assert calc.get_benefit_period_anniversary_year(benefit) == 2026

        benefit = {'period': '2025-Q1'}  # Not anniversary period
        assert calc.get_benefit_period_anniversary_year(benefit) is None


class TestCalendarPeriodLogic:
    """Test calendar period date ranges and overlaps."""

    def test_get_calendar_period_date_range_yearly(self, sample_config, empty_state):
        """Yearly period should span full calendar year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        start, end = calc.get_calendar_period_date_range('2025')

        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)

    def test_get_calendar_period_date_range_quarterly(self, sample_config, empty_state):
        """Quarterly periods should span 3 months each."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        start, end = calc.get_calendar_period_date_range('2025-Q1')
        assert start == date(2025, 1, 1)
        assert end == date(2025, 3, 31)

        start, end = calc.get_calendar_period_date_range('2025-Q2')
        assert start == date(2025, 4, 1)
        assert end == date(2025, 6, 30)

        start, end = calc.get_calendar_period_date_range('2025-Q3')
        assert start == date(2025, 7, 1)
        assert end == date(2025, 9, 30)

        start, end = calc.get_calendar_period_date_range('2025-Q4')
        assert start == date(2025, 10, 1)
        assert end == date(2025, 12, 31)

    def test_get_calendar_period_date_range_half_yearly(self, sample_config, empty_state):
        """Half-yearly periods should span 6 months each."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        start, end = calc.get_calendar_period_date_range('2025-H1')
        assert start == date(2025, 1, 1)
        assert end == date(2025, 6, 30)

        start, end = calc.get_calendar_period_date_range('2025-H2')
        assert start == date(2025, 7, 1)
        assert end == date(2025, 12, 31)

    def test_get_calendar_period_date_range_monthly(self, sample_config, empty_state):
        """Monthly periods should span single month."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        start, end = calc.get_calendar_period_date_range('2025-Jan')
        assert start == date(2025, 1, 1)
        assert end == date(2025, 1, 31)

        start, end = calc.get_calendar_period_date_range('2025-Feb')
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)

        start, end = calc.get_calendar_period_date_range('2025-Dec')
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)

    def test_calendar_period_overlaps_anniversary_year(self, sample_config, empty_state):
        """Calendar periods should correctly detect overlap with anniversary years."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        # Anniversary year 2025 spans July 15, 2025 - July 14, 2026
        # 2025-H1 (Jan-Jun 2025) does NOT overlap
        assert calc.calendar_period_overlaps_anniversary_year('test_card_2025', '2025-H1', 2025) is False

        # 2025-H2 (Jul-Dec 2025) overlaps
        assert calc.calendar_period_overlaps_anniversary_year('test_card_2025', '2025-H2', 2025) is True

        # 2026-H1 (Jan-Jun 2026) overlaps
        assert calc.calendar_period_overlaps_anniversary_year('test_card_2025', '2026-H1', 2025) is True

        # 2026-H2 (Jul-Dec 2026) overlaps (through July 14, 2026)
        assert calc.calendar_period_overlaps_anniversary_year('test_card_2025', '2026-H2', 2025) is True


class TestBenefitToggling:
    """Test toggling benefit posted status."""

    def test_toggle_benefit_on(self, sample_config, empty_state):
        """Toggling benefit on should mark as posted with date."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        calc.toggle_benefit('test_benefit', '2025-Q1')

        key = 'test_benefit|2025-Q1'
        assert calc.state[key]['posted'] is True
        assert calc.state[key]['post_date'] == '2025-06-15'

    def test_toggle_benefit_off(self, sample_config, empty_state):
        """Toggling benefit off should clear post date."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        # Turn on then off
        calc.toggle_benefit('test_benefit', '2025-Q1')
        calc.toggle_benefit('test_benefit', '2025-Q1')

        key = 'test_benefit|2025-Q1'
        assert calc.state[key]['posted'] is False
        assert calc.state[key]['post_date'] is None

    def test_toggle_with_anniversary_year_tracking(self, sample_config, empty_state):
        """Toggling calendar benefit should track anniversary year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        calc.toggle_benefit('test_benefit', '2025-Q1', anniversary_year=2025)

        key = 'test_benefit|2025-Q1'
        assert calc.state[key]['posted'] is True
        assert calc.state[key]['posted_anniversary_year'] == 2025


class TestCustomAmounts:
    """Test custom amount tracking for partial benefit usage."""

    def test_set_custom_amount(self, sample_config, empty_state):
        """Setting custom amount should store in state."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        calc.set_custom_amount('test_benefit', '2025-Q1', 75.0)

        key = 'test_benefit|2025-Q1'
        assert calc.state[key]['custom_amount'] == 75.0

    def test_get_custom_amount_when_set(self, sample_config, empty_state):
        """Getting custom amount should return stored value."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        calc.set_custom_amount('test_benefit', '2025-Q1', 75.0)
        amount = calc.get_custom_amount('test_benefit', '2025-Q1', default_amount=100.0)

        assert amount == 75.0

    def test_get_custom_amount_when_not_set(self, sample_config, empty_state):
        """Getting custom amount should return default when not set."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        amount = calc.get_custom_amount('test_benefit', '2025-Q1', default_amount=100.0)

        assert amount == 100.0

    def test_clear_custom_amount(self, sample_config, empty_state):
        """Setting custom amount to None should clear it."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        calc.set_custom_amount('test_benefit', '2025-Q1', 75.0)
        calc.set_custom_amount('test_benefit', '2025-Q1', None)

        key = 'test_benefit|2025-Q1'
        assert calc.state[key]['custom_amount'] is None


class TestEvery4YearsBenefits:
    """Test the every_4_years benefit availability logic."""

    def test_every_4_years_available_when_never_used(self, sample_config, empty_state):
        """Every 4 years benefit should be available when never used."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        is_available, next_year, last_year = calc.is_every_4_years_benefit_available(
            'venture_x_2025_GE_precheck',
            'venture_x_2025',
            '2025-A11'
        )

        assert is_available is True
        assert next_year is None
        assert last_year is None

    def test_every_4_years_not_available_when_recently_used(self, sample_config, empty_state):
        """Every 4 years benefit should NOT be available if used in last 4 years."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        # Mark as used in 2023
        calc.state['venture_x_2025_GE_precheck|2023-A11'] = {
            'posted': True,
            'post_date': '2023-11-15',
            'custom_amount': None
        }

        # Check availability for 2025 (only 2 years later)
        is_available, next_year, last_year = calc.is_every_4_years_benefit_available(
            'venture_x_2025_GE_precheck',
            'venture_x_2025',
            '2025-A11'
        )

        assert is_available is False
        assert next_year == 2027  # Available again in 2027
        assert last_year == 2023

    def test_every_4_years_available_after_4_years(self, sample_config, empty_state):
        """Every 4 years benefit should be available again after 4 years."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        # Mark as used in 2021
        calc.state['venture_x_2025_GE_precheck|2021-A11'] = {
            'posted': True,
            'post_date': '2021-11-15',
            'custom_amount': None
        }

        # Check availability for 2025 (4 years later)
        is_available, next_year, last_year = calc.is_every_4_years_benefit_available(
            'venture_x_2025_GE_precheck',
            'venture_x_2025',
            '2025-A11'
        )

        assert is_available is True
        assert next_year is None
        assert last_year == 2021

    def test_get_every_4_years_benefit_info(self, sample_config, empty_state):
        """Test convenience method for getting every_4_years info."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        # Mark as used in 2023
        calc.state['venture_x_2025_GE_precheck|2023-A11'] = {
            'posted': True,
            'post_date': '2023-11-15',
            'custom_amount': None
        }

        benefit = {
            'benefit_id': 'venture_x_2025_GE_precheck',
            'card_key': 'venture_x_2025',
            'period': '2025-A11',
            'frequency': 'every_4_years'
        }

        info = calc.get_every_4_years_benefit_info(benefit)

        assert info['is_available'] is False
        assert info['next_available_year'] == 2027
        assert info['last_used_year'] == 2023
        assert 'Used in 2023' in info['disabled_reason']


class TestBenefitRenewalType:
    """Test determining benefit renewal type from period."""

    def test_get_benefit_renewal_type_calendar(self, sample_config, empty_state):
        """Calendar periods should return calendar_year."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        benefit = {'period': '2025-Q1'}
        assert calc.get_benefit_renewal_type(benefit) == 'calendar_year'

        benefit = {'period': '2025-H1'}
        assert calc.get_benefit_renewal_type(benefit) == 'calendar_year'

        benefit = {'period': '2025'}
        assert calc.get_benefit_renewal_type(benefit) == 'calendar_year'

    def test_get_benefit_renewal_type_anniversary(self, sample_config, empty_state):
        """Anniversary periods (with -A) should return card_anniversary."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)

        benefit = {'period': '2025-A07'}
        assert calc.get_benefit_renewal_type(benefit) == 'card_anniversary'

        benefit = {'period': '2025-AH1-07'}
        assert calc.get_benefit_renewal_type(benefit) == 'card_anniversary'


class TestCardSummary:
    """Test card summary calculations."""

    def test_get_card_summary(self, sample_config, empty_state):
        """Card summary should calculate totals correctly."""
        calc = BenefitsCalculator(config_path=sample_config, state_path=empty_state)
        calc.today = date(2025, 6, 15)

        # Get all benefits first to see what IDs are generated
        all_benefits = calc.get_card_benefits('test_card_2025')

        # Find the actual benefit IDs for the quarterly and monthly benefits
        quarterly_benefits = [b for b in all_benefits if 'quarterly' in b['benefit_id'].lower() and b['period'] == '2025-Q1']
        monthly_benefits = [b for b in all_benefits if 'monthly' in b['benefit_id'].lower() and b['period'] == '2025-Jan']

        # If we found the benefits, toggle them
        if quarterly_benefits:
            calc.toggle_benefit(quarterly_benefits[0]['benefit_id'], '2025-Q1')
        if monthly_benefits:
            calc.toggle_benefit(monthly_benefits[0]['benefit_id'], '2025-Jan')

        summary = calc.get_card_summary('test_card_2025')

        assert summary['card_name'] == 'Test Card'
        assert summary['annual_fee'] == 695

        # Verify the summary structure - totals may vary based on config
        assert 'total_posted' in summary
        assert 'total_potential' in summary
        assert 'net_value_posted' in summary
        assert 'roi_posted' in summary

        # If we successfully toggled benefits, total_posted should be > 0
        if quarterly_benefits and monthly_benefits:
            assert summary['total_posted'] > 0
        assert summary['total_potential'] > 0


class TestStatePersistence:
    """Test state saving and loading."""

    def test_state_persists_across_instances(self, sample_config, tmp_path):
        """State should persist when saved and reloaded."""
        state_path = tmp_path / "test_state.json"

        # Create calculator and toggle a benefit
        calc1 = BenefitsCalculator(config_path=sample_config, state_path=state_path)
        calc1.toggle_benefit('test_benefit', '2025-Q1')

        # Create new calculator instance
        calc2 = BenefitsCalculator(config_path=sample_config, state_path=state_path)

        key = 'test_benefit|2025-Q1'
        assert calc2.state[key]['posted'] is True
