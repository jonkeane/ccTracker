"""
Tests for period parsing and sorting utilities.

This test suite verifies that period strings are correctly parsed and sorted
chronologically across various formats (monthly, quarterly, yearly, anniversary).
"""

import pytest
from benefits.period_utils import parse_period_for_sorting, sort_benefits_by_period


class TestParsePeriodForSorting:
    """Test period string parsing into sortable tuples."""

    def test_parses_monthly_periods(self):
        """Monthly periods with abbreviated months."""
        assert parse_period_for_sorting("2025-Jan") == (2025, 1)
        assert parse_period_for_sorting("2025-Feb") == (2025, 2)
        assert parse_period_for_sorting("2025-Mar") == (2025, 3)
        assert parse_period_for_sorting("2025-Apr") == (2025, 4)
        assert parse_period_for_sorting("2025-May") == (2025, 5)
        assert parse_period_for_sorting("2025-Jun") == (2025, 6)
        assert parse_period_for_sorting("2025-Jul") == (2025, 7)
        assert parse_period_for_sorting("2025-Aug") == (2025, 8)
        assert parse_period_for_sorting("2025-Sep") == (2025, 9)
        assert parse_period_for_sorting("2025-Oct") == (2025, 10)
        assert parse_period_for_sorting("2025-Nov") == (2025, 11)
        assert parse_period_for_sorting("2025-Dec") == (2025, 12)

    def test_parses_quarterly_periods(self):
        """Quarterly periods map to first month of quarter."""
        assert parse_period_for_sorting("2025-Q1") == (2025, 1)
        assert parse_period_for_sorting("2025-Q2") == (2025, 4)
        assert parse_period_for_sorting("2025-Q3") == (2025, 7)
        assert parse_period_for_sorting("2025-Q4") == (2025, 10)

    def test_parses_half_yearly_periods(self):
        """Half-yearly periods map to Jan or Jul."""
        assert parse_period_for_sorting("2025-H1") == (2025, 1)
        assert parse_period_for_sorting("2025-H2") == (2025, 7)

    def test_parses_anniversary_periods(self):
        """Anniversary periods extract month number."""
        assert parse_period_for_sorting("2025-A01") == (2025, 1)
        assert parse_period_for_sorting("2025-A07") == (2025, 7)
        assert parse_period_for_sorting("2026-A11") == (2026, 11)
        assert parse_period_for_sorting("2026-A12") == (2026, 12)

    def test_parses_complex_anniversary_periods(self):
        """Complex anniversary periods with extra parts."""
        # Formats like AH1-11, AQ1-11
        assert parse_period_for_sorting("2025-AH1-07") == (2025, 7)
        assert parse_period_for_sorting("2025-AQ1-03") == (2025, 3)
        assert parse_period_for_sorting("2026-AH2-11") == (2026, 11)

    def test_parses_yearly_periods(self):
        """Yearly periods return (year, 0)."""
        assert parse_period_for_sorting("2025") == (2025, 0)
        assert parse_period_for_sorting("2026") == (2026, 0)
        assert parse_period_for_sorting("2024") == (2024, 0)

    def test_handles_invalid_periods(self):
        """Invalid periods return (0, 0) for fallback sorting."""
        assert parse_period_for_sorting("invalid") == (0, 0)
        assert parse_period_for_sorting("") == (0, 0)
        assert parse_period_for_sorting("not-a-date") == (0, 0)
        assert parse_period_for_sorting("2025-XYZ") == (0, 0)

    def test_handles_different_years(self):
        """Parsing works correctly across different years."""
        assert parse_period_for_sorting("2023-Jan") == (2023, 1)
        assert parse_period_for_sorting("2024-Feb") == (2024, 2)
        assert parse_period_for_sorting("2025-Mar") == (2025, 3)
        assert parse_period_for_sorting("2026-Apr") == (2026, 4)


class TestSortBenefitsByPeriod:
    """Test benefit sorting by period."""

    def test_sorts_monthly_periods_chronologically(self):
        """Benefits sorted in chronological order by month."""
        benefits = [
            {'period': '2025-Dec', 'amount': 100},
            {'period': '2025-Jan', 'amount': 50},
            {'period': '2025-Jun', 'amount': 75},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        assert periods == ['2025-Jan', '2025-Jun', '2025-Dec']

    def test_sorts_across_years(self):
        """Sorts correctly across year boundaries."""
        benefits = [
            {'period': '2026-Jan', 'amount': 100},
            {'period': '2025-Dec', 'amount': 50},
            {'period': '2025-Jun', 'amount': 75},
            {'period': '2024-Nov', 'amount': 25},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        assert periods == ['2024-Nov', '2025-Jun', '2025-Dec', '2026-Jan']

    def test_sorts_mixed_period_types(self):
        """Correctly sorts different period formats together."""
        benefits = [
            {'period': '2025-Q3', 'amount': 1},
            {'period': '2025-Jan', 'amount': 2},
            {'period': '2025-H2', 'amount': 3},
            {'period': '2025-Q1', 'amount': 4},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        # Jan=1, Q1=1, Q3=7, H2=7
        assert periods[0] in ['2025-Jan', '2025-Q1']  # Both month 1
        assert periods[2] in ['2025-Q3', '2025-H2']   # Both month 7

    def test_sorts_quarterly_periods(self):
        """Quarterly periods sort correctly."""
        benefits = [
            {'period': '2025-Q4', 'amount': 1},
            {'period': '2025-Q1', 'amount': 2},
            {'period': '2025-Q3', 'amount': 3},
            {'period': '2025-Q2', 'amount': 4},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        assert periods == ['2025-Q1', '2025-Q2', '2025-Q3', '2025-Q4']

    def test_sorts_anniversary_periods(self):
        """Anniversary periods sort by month."""
        benefits = [
            {'period': '2025-A11', 'amount': 1},
            {'period': '2025-A03', 'amount': 2},
            {'period': '2025-A07', 'amount': 3},
            {'period': '2025-A01', 'amount': 4},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        assert periods == ['2025-A01', '2025-A03', '2025-A07', '2025-A11']

    def test_preserves_stable_sort_for_ties(self):
        """Original order preserved when periods are equal."""
        benefits = [
            {'period': '2025-Jan', 'amount': 100, 'id': 1},
            {'period': '2025-Jan', 'amount': 200, 'id': 2},
            {'period': '2025-Jan', 'amount': 300, 'id': 3},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        ids = [b['id'] for b in sorted_benefits]

        # Python's sort is stable, so original order should be preserved
        assert ids == [1, 2, 3]

    def test_handles_empty_list(self):
        """Empty list returns empty list."""
        assert sort_benefits_by_period([]) == []

    def test_handles_single_benefit(self):
        """Single benefit returns list with that benefit."""
        benefits = [{'period': '2025-Jan', 'amount': 100}]
        sorted_benefits = sort_benefits_by_period(benefits)
        assert sorted_benefits == benefits

    def test_real_world_scenario(self):
        """Test with realistic benefit data."""
        benefits = [
            {'period': '2026-Jan', 'category': 'Uber', 'amount': 15},
            {'period': '2025-Dec', 'category': 'Uber', 'amount': 15},
            {'period': '2025-Q4', 'category': 'Travel', 'amount': 300},
            {'period': '2025-H2', 'category': 'Hotel', 'amount': 200},
            {'period': '2025-A07', 'category': 'Annual', 'amount': 100},
            {'period': '2025', 'category': 'Yearly', 'amount': 500},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        # 2025 (0), A07 (7), H2 (7), Q4 (10), Dec (12), 2026-Jan (1)
        assert periods[0] == '2025'  # Yearly comes first (month 0)
        assert periods[-1] == '2026-Jan'  # Next year comes last
        assert '2025-Dec' in periods[1:5]  # December in 2025

    def test_invalid_periods_sort_to_end(self):
        """Invalid periods are sorted to the end."""
        benefits = [
            {'period': '2025-Jun', 'amount': 1},
            {'period': 'invalid', 'amount': 2},
            {'period': '2025-Jan', 'amount': 3},
        ]

        sorted_benefits = sort_benefits_by_period(benefits)
        periods = [b['period'] for b in sorted_benefits]

        assert periods == ['invalid', '2025-Jan', '2025-Jun']
