"""
Tests for HyattSummaryService - aggregation and calculation logic.

This test suite verifies that the service correctly aggregates data from
multiple sources (CardProcessor, BenefitsCalculator, StaysManager) and
performs accurate summary calculations.
"""

import pytest
from datetime import date
from unittest.mock import Mock
from hyatt.hyatt_summary_service import HyattSummaryService


@pytest.fixture
def mock_card_processor():
    """Mock CardProcessor with default behavior."""
    mock = Mock()
    # Default: return empty/zero values
    mock.get_yearly_bonus_nights_breakdown.return_value = {
        'posted': 0,
        'pending': 0,
        'total': 0
    }
    return mock


@pytest.fixture
def mock_benefits_calculator():
    """Mock BenefitsCalculator."""
    return Mock()


@pytest.fixture
def mock_stays_manager():
    """Mock StaysManager with default empty data."""
    mock = Mock()
    mock.get_stays.return_value = []
    mock.get_goh_nights.return_value = []
    return mock


@pytest.fixture
def summary_service(mock_card_processor, mock_benefits_calculator, mock_stays_manager):
    """Create HyattSummaryService with mocks."""
    return HyattSummaryService(
        mock_card_processor,
        mock_benefits_calculator,
        mock_stays_manager
    )


class TestCalculateNightsSummary:
    """Test nights summary aggregation from all sources."""

    def test_minimal_setup_only_yearly_start(self, summary_service):
        """With no stays or CC nights, only yearly start is counted."""
        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['cc_yearly_start'] == 5
        assert summary['cc_nights_posted'] == 0
        assert summary['cc_nights_pending'] == 0
        assert summary['current_nights'] == 0
        assert summary['upcoming_nights'] == 0
        assert summary['goh_nights'] == 0
        assert summary['goh_nights_upcoming'] == 0
        assert summary['nights_posted'] == 5  # Only yearly start
        assert summary['nights_total'] == 5

    def test_only_cc_bonus_nights(self, summary_service, mock_card_processor):
        """With only CC bonus nights, calculates correctly."""
        # Arrange
        mock_card_processor.get_yearly_bonus_nights_breakdown.side_effect = [
            {'posted': 10, 'pending': 5, 'total': 15},  # personal
            {'posted': 20, 'pending': 10, 'total': 30}, # business
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['cc_nights_posted'] == 30  # 10 + 20
        assert summary['cc_nights_pending'] == 15  # 5 + 10
        assert summary['nights_posted'] == 35  # 5 + 30
        assert summary['nights_total'] == 50  # 5 + 15 + 30

    def test_with_completed_stays(self, summary_service, mock_stays_manager):
        """Completed stays add to current nights."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 10), 'check_out': date(2025, 1, 13)},  # 3 nights
            {'check_in': date(2025, 3, 5), 'check_out': date(2025, 3, 8)},    # 3 nights
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 6  # 3 + 3
        assert summary['upcoming_nights'] == 0
        assert summary['nights_posted'] == 11  # 5 + 6

    def test_with_upcoming_stays(self, summary_service, mock_stays_manager):
        """Future stays add to upcoming nights, not current."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 7, 1), 'check_out': date(2025, 7, 5)},   # 4 nights (future)
            {'check_in': date(2025, 8, 10), 'check_out': date(2025, 8, 15)}, # 5 nights (future)
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 0
        assert summary['upcoming_nights'] == 9  # 4 + 5
        assert summary['nights_total'] == 14  # 5 + 9
        assert summary['nights_posted'] == 5  # Does NOT include upcoming

    def test_with_mixed_past_and_future_stays(self, summary_service, mock_stays_manager):
        """Correctly splits past and future stays."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 10), 'check_out': date(2025, 1, 13)},  # 3 past
            {'check_in': date(2025, 6, 14), 'check_out': date(2025, 6, 15)},  # 1 past (checkout on ref date)
            {'check_in': date(2025, 7, 1), 'check_out': date(2025, 7, 5)},    # 4 future
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 4  # 3 + 1
        assert summary['upcoming_nights'] == 4

    def test_with_goh_nights(self, summary_service, mock_stays_manager):
        """GOH nights are counted separately."""
        # Arrange
        mock_stays_manager.get_goh_nights.return_value = [
            {'date': date(2025, 2, 1)},  # past
            {'date': date(2025, 4, 15)}, # past
            {'date': date(2025, 9, 1)},  # future
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['goh_nights'] == 2
        assert summary['goh_nights_upcoming'] == 1
        assert summary['nights_posted'] == 7  # 5 + 2
        assert summary['nights_total'] == 8  # 5 + 2 + 1

    def test_with_goh_night_on_reference_date(self, summary_service, mock_stays_manager):
        """GOH night on reference date counts as occurred."""
        # Arrange
        mock_stays_manager.get_goh_nights.return_value = [
            {'date': date(2025, 6, 15)},  # On reference date
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['goh_nights'] == 1
        assert summary['goh_nights_upcoming'] == 0

    def test_all_sources_combined(self, summary_service, mock_card_processor, mock_stays_manager):
        """Integration test with all sources contributing."""
        # Arrange
        mock_card_processor.get_yearly_bonus_nights_breakdown.side_effect = [
            {'posted': 10, 'pending': 5, 'total': 15},  # personal
            {'posted': 20, 'pending': 10, 'total': 30}, # business
        ]
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 1), 'check_out': date(2025, 1, 4)},   # 3 past
            {'check_in': date(2025, 8, 1), 'check_out': date(2025, 8, 6)},   # 5 future
        ]
        mock_stays_manager.get_goh_nights.return_value = [
            {'date': date(2025, 3, 1)},  # 1 past
            {'date': date(2025, 10, 1)}, # 1 future
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['cc_yearly_start'] == 5
        assert summary['cc_nights_posted'] == 30
        assert summary['cc_nights_pending'] == 15
        assert summary['current_nights'] == 3
        assert summary['upcoming_nights'] == 5
        assert summary['goh_nights'] == 1
        assert summary['goh_nights_upcoming'] == 1
        # Posted: 5 (yearly) + 30 (CC posted) + 3 (current) + 1 (GOH)
        assert summary['nights_posted'] == 39
        # Total: 5 + 30 + 15 + 3 + 5 + 1 + 1 = 60
        # Or: 5 + 3 + 1 + 1 + 15 + 30 + 5 = 60
        assert summary['nights_total'] == 60

    def test_uses_default_reference_date_if_not_provided(self, summary_service, mock_stays_manager):
        """When reference_date is None, uses current date."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2020, 1, 1), 'check_out': date(2020, 1, 3)},  # Far past
        ]

        # Act
        summary = summary_service.calculate_nights_summary()  # No reference_date

        # Assert - should count as past since we're in 2026
        assert summary['current_nights'] == 2

    def test_with_one_night_stays(self, summary_service, mock_stays_manager):
        """One night stays (checkout next day) counted correctly."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 10), 'check_out': date(2025, 1, 11)},  # 1 night
            {'check_in': date(2025, 2, 5), 'check_out': date(2025, 2, 6)},    # 1 night
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 2

    def test_with_long_stay(self, summary_service, mock_stays_manager):
        """Long stays calculated correctly."""
        # Arrange
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 1), 'check_out': date(2025, 1, 31)},  # 30 nights
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 30

    def test_empty_stays_empty_goh(self, summary_service, mock_stays_manager):
        """Empty stays and GOH lists handled correctly."""
        # Arrange - defaults already empty
        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert
        assert summary['current_nights'] == 0
        assert summary['upcoming_nights'] == 0
        assert summary['goh_nights'] == 0
        assert summary['goh_nights_upcoming'] == 0

    def test_calculation_matches_app_formula(self, summary_service, mock_card_processor, mock_stays_manager):
        """Verify calculation matches app.py lines 128-129."""
        # Arrange
        mock_card_processor.get_yearly_bonus_nights_breakdown.side_effect = [
            {'posted': 8, 'pending': 4, 'total': 12},  # personal
            {'posted': 12, 'pending': 6, 'total': 18}, # business
        ]
        mock_stays_manager.get_stays.return_value = [
            {'check_in': date(2025, 1, 1), 'check_out': date(2025, 1, 3)},  # 2 past
            {'check_in': date(2025, 12, 1), 'check_out': date(2025, 12, 4)}, # 3 future
        ]
        mock_stays_manager.get_goh_nights.return_value = [
            {'date': date(2025, 2, 1)},  # 1 past
            {'date': date(2025, 11, 1)}, # 1 future
        ]

        # Act
        summary = summary_service.calculate_nights_summary(date(2025, 6, 15))

        # Assert - app.py line 128
        # nights_posted = cc_yearly_start + current_nights + goh_nights + cc_nights_posted
        expected_posted = 5 + 2 + 1 + 20
        assert summary['nights_posted'] == expected_posted

        # Assert - app.py line 129
        # nights_total = cc_yearly_start + current_nights + goh_nights + upcoming_goh_nights +
        #                personal_breakdown['total'] + business_breakdown['total'] + upcoming_nights
        expected_total = 5 + 2 + 1 + 1 + 12 + 18 + 3
        assert summary['nights_total'] == expected_total

class TestGetFilteredBenefitsForYear:
    """Test benefit filtering with deduplication for anniversary years."""

    def test_filters_anniversary_benefits_by_period_year(
        self, summary_service, mock_benefits_calculator
    ):
        """Anniversary benefits filtered by year in period."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = [
            {
                'category': 'Travel Credit',
                'period': '2025-A07',
                'amount': 300,
                'posted': False,
                'card_key': 'card_2025',
            },
            {
                'category': 'Travel Credit',
                'period': '2026-A07',
                'amount': 300,
                'posted': False,
                'card_key': 'card_2025',
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'
        mock_benefits_calculator.get_benefit_period_anniversary_year.side_effect = [2025, 2026]

        # Act
        benefits = summary_service.get_filtered_benefits_for_year('card_2025', 2025)

        # Assert
        assert len(benefits) == 1
        assert benefits[0]['period'] == '2025-A07'

    def test_deduplicates_by_category_and_period(
        self, summary_service, mock_benefits_calculator
    ):
        """Duplicate benefits by (category, period) are removed."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = [
            {
                'category': 'Travel Credit',
                'period': '2025-A07',
                'amount': 300,
                'posted': False,
                'card_key': 'card_2025',
            },
            {
                'category': 'Travel Credit',
                'period': '2025-A07',  # Duplicate
                'amount': 300,
                'posted': False,
                'card_key': 'card_2025',
            },
            {
                'category': 'Hotel Credit',
                'period': '2025-A07',  # Different category, keep
                'amount': 200,
                'posted': False,
                'card_key': 'card_2025',
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'
        mock_benefits_calculator.get_benefit_period_anniversary_year.return_value = 2025

        # Act
        benefits = summary_service.get_filtered_benefits_for_year('card_2025', 2025)

        # Assert
        assert len(benefits) == 2  # Duplicate removed
        categories = [b['category'] for b in benefits]
        assert 'Travel Credit' in categories
        assert 'Hotel Credit' in categories

    def test_posted_anniversary_benefits_use_actual_year(
        self, summary_service, mock_benefits_calculator
    ):
        """Posted anniversary benefits filtered by their actual anniversary year."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = [
            {
                'category': 'Travel Credit',
                'period': '2025-A07',
                'amount': 300,
                'posted': True,
                'card_key': 'card_2025',
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'
        mock_benefits_calculator.get_benefit_period_anniversary_year.return_value = 2025

        # Act - filter for 2025
        benefits_2025 = summary_service.get_filtered_benefits_for_year('card_2025', 2025)
        benefits_2026 = summary_service.get_filtered_benefits_for_year('card_2025', 2026)

        # Assert
        assert len(benefits_2025) == 1
        assert len(benefits_2026) == 0

    def test_calendar_year_benefits_check_overlap(
        self, summary_service, mock_benefits_calculator
    ):
        """Calendar year benefits filtered by overlap with anniversary year."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = [
            {
                'category': 'Uber Credit',
                'period': '2025-Jan',
                'amount': 15,
                'posted': False,
                'card_key': 'card_2025',
            },
            {
                'category': 'Uber Credit',
                'period': '2025-Dec',
                'amount': 15,
                'posted': False,
                'card_key': 'card_2025',
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'calendar_year'
        # Mock overlap: Jan overlaps with 2025, Dec doesn't
        mock_benefits_calculator.calendar_period_overlaps_anniversary_year.side_effect = [True, False]

        # Act
        benefits = summary_service.get_filtered_benefits_for_year('card_2025', 2025)

        # Assert
        assert len(benefits) == 1
        assert benefits[0]['period'] == '2025-Jan'

    def test_empty_benefits_returns_empty_list(
        self, summary_service, mock_benefits_calculator
    ):
        """No benefits returns empty list."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = []

        # Act
        benefits = summary_service.get_filtered_benefits_for_year('card_2025', 2025)

        # Assert
        assert benefits == []

    def test_uses_benefit_card_key_for_overlap_check(
        self, summary_service, mock_benefits_calculator
    ):
        """Uses each benefit's card_key for anniversary calculations."""
        # Arrange
        mock_benefits_calculator.get_card_benefits.return_value = [
            {
                'category': 'Uber Credit',
                'period': '2025-Jun',
                'amount': 15,
                'posted': True,
                'card_key': 'specific_card_key',  # Different from query key
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'calendar_year'
        mock_benefits_calculator.calendar_period_overlaps_anniversary_year.return_value = True

        # Act
        benefits = summary_service.get_filtered_benefits_for_year('card_2025', 2025)

        # Assert
        assert len(benefits) == 1
        # Verify it used the benefit's card_key
        mock_benefits_calculator.calendar_period_overlaps_anniversary_year.assert_called_with(
            'specific_card_key', '2025-Jun', 2025
        )


class TestCalculateYearSummary:
    """Test year-specific benefit calculations."""

    def test_posted_benefits_use_custom_amount(self, summary_service, mock_benefits_calculator):
        """Posted benefits use custom amount if set."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': 250,  # Partially used
                'posted': True,
                'frequency': 'yearly',
                'posted_anniversary_year': 2025,
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 250  # Uses custom amount
        assert summary['total_potential_year'] == 300  # Uses full amount

    def test_posted_benefits_use_full_amount_if_no_custom(
        self, summary_service, mock_benefits_calculator
    ):
        """Posted benefits use full amount if custom not set."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': None,
                'posted': True,
                'frequency': 'yearly',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 300

    def test_every_4_years_benefit_not_available(
        self, summary_service, mock_benefits_calculator
    ):
        """Every 4 years benefit doesn't count if not available."""
        # Arrange
        benefits = [
            {
                'amount': 100,
                'custom_amount': None,
                'posted': False,
                'frequency': 'every_4_years',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'
        mock_benefits_calculator.get_every_4_years_benefit_info.return_value = {
            'is_available': False
        }

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_potential_year'] == 0  # Not counted

    def test_every_4_years_benefit_counts_when_available(
        self, summary_service, mock_benefits_calculator
    ):
        """Every 4 years benefit counts when available."""
        # Arrange
        benefits = [
            {
                'amount': 100,
                'custom_amount': None,
                'posted': False,
                'frequency': 'every_4_years',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'
        mock_benefits_calculator.get_every_4_years_benefit_info.return_value = {
            'is_available': True
        }

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_potential_year'] == 100

    def test_calculates_roi_correctly(self, summary_service, mock_benefits_calculator):
        """ROI is calculated as (posted - fee) / fee * 100."""
        # Arrange
        benefits = [
            {
                'amount': 1000,
                'custom_amount': None,
                'posted': True,
                'frequency': 'yearly'
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 500, 2025)

        # Assert
        assert summary['total_posted_year'] == 1000
        assert summary['net_value_posted_year'] == 500  # 1000 - 500
        assert summary['roi_posted_year'] == 100.0  # (500 / 500) * 100

    def test_roi_is_zero_when_fee_is_zero(self, summary_service, mock_benefits_calculator):
        """ROI is 0 when annual fee is 0."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': None,
                'posted': True,
                'frequency': 'yearly'
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 0, 2025)

        # Assert
        assert summary['roi_posted_year'] == 0

    def test_calendar_year_posted_in_different_year_not_counted(
        self, summary_service, mock_benefits_calculator
    ):
        """Calendar year benefits posted in different anniversary year not counted."""
        # Arrange
        benefits = [
            {
                'amount': 15,
                'custom_amount': None,
                'posted': True,
                'frequency': 'monthly',
                'posted_anniversary_year': 2024,  # Posted in different year
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'calendar_year'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 0
        assert summary['total_potential_year'] == 0  # Not this year

    def test_pending_calendar_benefits_count_as_potential(
        self, summary_service, mock_benefits_calculator
    ):
        """Pending calendar year benefits count as potential."""
        # Arrange
        benefits = [
            {
                'amount': 15,
                'custom_amount': None,
                'posted': False,
                'frequency': 'monthly',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'calendar_year'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 0
        assert summary['total_potential_year'] == 15

    def test_anniversary_benefits_always_counted_when_posted(
        self, summary_service, mock_benefits_calculator
    ):
        """Anniversary benefits always counted if posted."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': 275,
                'posted': True,
                'frequency': 'yearly',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 275

    def test_empty_benefits_list(self, summary_service, mock_benefits_calculator):
        """Empty benefits list returns zeros."""
        # Act
        summary = summary_service.calculate_year_summary([], 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 0
        assert summary['total_potential_year'] == 0
        assert summary['net_value_posted_year'] == -695
        assert summary['roi_posted_year'] < 0  # Negative ROI

    def test_multiple_benefits_summed_correctly(
        self, summary_service, mock_benefits_calculator
    ):
        """Multiple benefits summed correctly."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': None,
                'posted': True,
                'frequency': 'yearly',
            },
            {
                'amount': 200,
                'custom_amount': None,
                'posted': True,
                'frequency': 'yearly',
            },
            {
                'amount': 150,
                'custom_amount': None,
                'posted': False,
                'frequency': 'yearly',
            },
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 500  # 300 + 200
        assert summary['total_potential_year'] == 650  # 300 + 200 + 150

    def test_custom_amount_zero_uses_full_amount(
        self, summary_service, mock_benefits_calculator
    ):
        """Custom amount of 0 is treated as not set, uses full amount."""
        # Arrange
        benefits = [
            {
                'amount': 300,
                'custom_amount': 0,  # Zero means not used
                'posted': True,
                'frequency': 'yearly',
            }
        ]
        mock_benefits_calculator.get_benefit_renewal_type.return_value = 'card_anniversary'

        # Act
        summary = summary_service.calculate_year_summary(benefits, 695, 2025)

        # Assert
        assert summary['total_posted_year'] == 300  # Uses full amount
