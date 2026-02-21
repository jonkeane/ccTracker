"""
Utilities for parsing and sorting period strings.

This module provides utilities to parse various period formats used in the
benefits tracker and sort them chronologically.
"""

from datetime import datetime
from typing import Tuple, List


def parse_period_for_sorting(period: str) -> Tuple[int, int]:
    """
    Parse period string into sortable tuple (year, month).

    Handles formats:
    - "2025-May" -> (2025, 5)
    - "2026-Q1" -> (2026, 1)
    - "2025-H2" -> (2025, 7)
    - "2026-A11" -> (2026, 11)
    - "2026" -> (2026, 0)

    Args:
        period: Period string

    Returns:
        Tuple of (year, month_number) for chronological sorting.
        Month is 0 for periods that span multiple months.
        For invalid periods, returns (0, 0).

    Examples:
        >>> parse_period_for_sorting("2025-May")
        (2025, 5)
        >>> parse_period_for_sorting("2026-Q1")
        (2026, 1)
        >>> parse_period_for_sorting("2025-H2")
        (2025, 7)
    """
    try:
        # Handle "2025-May" format
        if '-' in period:
            parts = period.split('-')
            year = int(parts[0])

            # Try parsing month abbreviation first
            try:
                date_obj = datetime.strptime(period, "%Y-%b")
                return (date_obj.year, date_obj.month)
            except ValueError:
                pass

            # Handle anniversary format FIRST (before Q/H check)
            # Examples: A11, AH1-11, AQ1-11
            if 'A' in parts[1]:
                # Extract month number from the end of the period string
                # Examples: "2025-A11" -> 11, "2025-AH1-11" -> 11, "2025-AQ1-11" -> 11
                month_part = parts[-1] if len(parts) > 2 else parts[1].replace('A', '')

                # Try to extract 2-digit month from the end
                if len(month_part) >= 2 and month_part[-2:].isdigit():
                    month = int(month_part[-2:])
                    return (year, month)
                # Single digit month
                elif len(month_part) >= 1 and month_part[-1:].isdigit():
                    month = int(month_part[-1:])
                    return (year, month)
                # Otherwise just use 0
                return (year, 0)

            # Handle quarters: Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct
            if 'Q' in parts[1]:
                quarter_num = int(parts[1].replace('Q', ''))
                month = (quarter_num - 1) * 3 + 1
                return (year, month)

            # Handle half-years: H1=Jan, H2=Jul
            if 'H' in parts[1]:
                half_num = int(parts[1].replace('H', ''))
                month = 1 if half_num == 1 else 7
                return (year, month)

            # If we get here, format is unrecognized - return invalid
            return (0, 0)
        else:
            # Just year: "2025"
            return (int(period), 0)

    except (ValueError, IndexError):
        # Fallback: sort invalid periods to the end
        return (0, 0)


def sort_benefits_by_period(benefits: List[dict]) -> List[dict]:
    """
    Sort benefits chronologically by their period.

    Args:
        benefits: List of benefit dicts with 'period' key

    Returns:
        Sorted list of benefits (original order preserved for ties)

    Examples:
        >>> benefits = [
        ...     {'period': '2025-Dec', 'amount': 100},
        ...     {'period': '2025-Jan', 'amount': 50},
        ...     {'period': '2025-Jun', 'amount': 75},
        ... ]
        >>> sorted_benefits = sort_benefits_by_period(benefits)
        >>> [b['period'] for b in sorted_benefits]
        ['2025-Jan', '2025-Jun', '2025-Dec']
    """
    return sorted(benefits, key=lambda x: parse_period_for_sorting(x['period']))
