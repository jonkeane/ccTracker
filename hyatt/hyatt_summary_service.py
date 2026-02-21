"""
Service layer for Hyatt tracker summary calculations.

Separates business logic from UI presentation, enabling unit testing
and reusability across different interfaces.
"""

from datetime import date
from typing import Dict, List
import pandas as pd


class HyattSummaryService:
    """
    Aggregates data from CardProcessor, BenefitsCalculator, and StaysManager.
    Provides high-level summary calculations for the Hyatt tracker UI.
    """

    def __init__(self, card_processor, benefits_calculator, stays_manager):
        """
        Initialize the summary service.

        Args:
            card_processor: CardProcessor instance
            benefits_calculator: BenefitsCalculator instance
            stays_manager: StaysManager instance
        """
        self.card_processor = card_processor
        self.benefits_calculator = benefits_calculator
        self.stays_manager = stays_manager
        self.cc_yearly_start = 5  # Annual credit card bonus nights

    def calculate_nights_summary(self, reference_date: date = None) -> Dict:
        """
        Calculate comprehensive nights summary from all sources.

        Aggregates:
        - Credit card bonus nights (personal + business, posted + pending)
        - Actual hotel stays (current + upcoming)
        - Guest of Honor nights (current + upcoming)
        - Total nights (posted and projected)

        Args:
            reference_date: Date to use as "today" (defaults to actual today)

        Returns:
            Dictionary with keys:
            - cc_yearly_start: Annual CC bonus (int)
            - cc_nights_posted: CC nights that have posted (int)
            - cc_nights_pending: CC nights pending post (int)
            - current_nights: Nights from completed stays (int)
            - upcoming_nights: Nights from future stays (int)
            - goh_nights: GOH nights that have occurred (int)
            - goh_nights_upcoming: GOH nights in the future (int)
            - nights_posted: Total nights that have posted (int)
            - nights_total: Total nights including pending/upcoming (int)
        """
        if reference_date is None:
            reference_date = pd.Timestamp.now().date()

        # Get CC bonus nights breakdown
        personal_breakdown = self.card_processor.get_yearly_bonus_nights_breakdown('personal')
        business_breakdown = self.card_processor.get_yearly_bonus_nights_breakdown('business')

        cc_nights_posted = personal_breakdown['posted'] + business_breakdown['posted']
        cc_nights_pending = personal_breakdown['pending'] + business_breakdown['pending']

        # Get stays and calculate nights
        stays = self.stays_manager.get_stays()
        current_nights = sum(
            (stay['check_out'] - stay['check_in']).days
            for stay in stays
            if stay['check_out'] <= reference_date
        )
        upcoming_nights = sum(
            (stay['check_out'] - stay['check_in']).days
            for stay in stays
            if stay['check_out'] > reference_date
        )

        # Get GOH nights
        goh_nights_list = self.stays_manager.get_goh_nights()
        goh_nights = len([
            s for s in goh_nights_list
            if s['date'] <= reference_date
        ])
        goh_nights_upcoming = len([
            s for s in goh_nights_list
            if s['date'] > reference_date
        ])

        # Calculate totals
        nights_posted = (
            self.cc_yearly_start +
            current_nights +
            goh_nights +
            cc_nights_posted
        )
        nights_total = (
            self.cc_yearly_start +
            current_nights +
            goh_nights +
            goh_nights_upcoming +
            personal_breakdown['total'] +
            business_breakdown['total'] +
            upcoming_nights
        )

        return {
            'cc_yearly_start': self.cc_yearly_start,
            'cc_nights_posted': cc_nights_posted,
            'cc_nights_pending': cc_nights_pending,
            'current_nights': current_nights,
            'upcoming_nights': upcoming_nights,
            'goh_nights': goh_nights,
            'goh_nights_upcoming': goh_nights_upcoming,
            'nights_posted': nights_posted,
            'nights_total': nights_total,
        }

    def get_filtered_benefits_for_year(
        self,
        card_key: str,
        selected_year: int
    ) -> List[Dict]:
        """
        Get benefits filtered and deduplicated for a specific anniversary year.

        Handles complex logic:
        - Deduplication by (category, period)
        - Calendar year benefits: overlap with anniversary year
        - Anniversary benefits: match by period year
        - Posted benefits: use actual anniversary year

        Args:
            card_key: Card identifier (e.g., "schwab_platinum_2025")
            selected_year: Anniversary year to filter (e.g., 2025)

        Returns:
            List of benefit dicts filtered for the anniversary year
        """
        all_benefits = self.benefits_calculator.get_card_benefits(card_key)

        benefits_for_year = []
        seen_benefits = set()  # Track (category, period) to avoid duplicates

        for benefit in all_benefits:
            # Create deduplication key
            dedup_key = (benefit['category'], benefit['period'])

            if dedup_key in seen_benefits:
                continue

            # Get the card_key from the benefit to use for anniversary calculations
            benefit_card_key = benefit['card_key']
            renewal_type = self.benefits_calculator.get_benefit_renewal_type(benefit)
            include_benefit = False

            if benefit['posted']:
                # Posted benefits: check actual anniversary year
                if renewal_type == 'card_anniversary':
                    period_year = self.benefits_calculator.get_benefit_period_anniversary_year(benefit)
                    if period_year == selected_year:
                        include_benefit = True
                else:
                    # Calendar year: check overlap
                    if self.benefits_calculator.calendar_period_overlaps_anniversary_year(
                        benefit_card_key, benefit['period'], selected_year
                    ):
                        include_benefit = True
            else:
                # Pending benefits: filter by renewal type
                if renewal_type == 'card_anniversary':
                    period_year = self.benefits_calculator.get_benefit_period_anniversary_year(benefit)
                    if period_year == selected_year:
                        include_benefit = True
                else:
                    # Calendar year: check overlap
                    if self.benefits_calculator.calendar_period_overlaps_anniversary_year(
                        benefit_card_key, benefit['period'], selected_year
                    ):
                        include_benefit = True

            if include_benefit:
                benefits_for_year.append(benefit)
                seen_benefits.add(dedup_key)

        return benefits_for_year

    def calculate_year_summary(
        self,
        benefits: List[Dict],
        annual_fee: float,
        selected_year: int
    ) -> Dict:
        """
        Calculate year-specific benefit summary.

        Handles:
        - Posted benefits: count only those in this anniversary year
        - Potential benefits: include all available benefits
        - Every 4 years benefits: only count if available
        - Calendar vs anniversary year distinction

        Args:
            benefits: List of benefits (already filtered for year)
            annual_fee: Card annual fee
            selected_year: Anniversary year being calculated

        Returns:
            Dictionary with:
            - total_posted_year: Posted benefits value
            - total_potential_year: Potential benefits value
            - net_value_posted_year: Posted minus fee
            - roi_posted_year: ROI percentage on posted
        """
        total_posted_year = 0
        total_potential_year = 0

        for benefit in benefits:
            renewal_type = self.benefits_calculator.get_benefit_renewal_type(benefit)

            # Count potential benefits
            should_count_potential = False
            if renewal_type == 'card_anniversary':
                # Anniversary benefits: count as potential if available
                if benefit.get('frequency') == 'every_4_years':
                    # Check if every_4_years benefit is available
                    every_4_info = self.benefits_calculator.get_every_4_years_benefit_info(benefit)
                    if every_4_info['is_available']:
                        should_count_potential = True
                else:
                    # Regular anniversary benefits: always count as potential
                    should_count_potential = True
            else:
                # Calendar year benefits: only count if not posted in another year
                posted_anniv_year = benefit.get('posted_anniversary_year')
                if not benefit['posted'] or posted_anniv_year == selected_year:
                    should_count_potential = True

            if should_count_potential:
                total_potential_year += benefit['amount']

            # Count posted benefits
            if benefit['posted']:
                should_count_posted = False

                if renewal_type == 'card_anniversary':
                    # Anniversary benefits: always count if posted (they only appear in correct year)
                    should_count_posted = True
                else:
                    # Calendar year benefits: only count if posted in this anniversary year
                    posted_anniv_year = benefit.get('posted_anniversary_year')
                    if posted_anniv_year == selected_year:
                        should_count_posted = True

                if should_count_posted:
                    # Use custom amount if set, otherwise full amount
                    amount = (
                        benefit['custom_amount']
                        if benefit['custom_amount'] is not None and benefit['custom_amount'] > 0
                        else benefit['amount']
                    )
                    total_posted_year += amount

        net_value_posted_year = total_posted_year - annual_fee
        roi_posted_year = (
            (net_value_posted_year / annual_fee * 100)
            if annual_fee > 0
            else 0
        )

        return {
            'total_posted_year': total_posted_year,
            'total_potential_year': total_potential_year,
            'net_value_posted_year': net_value_posted_year,
            'roi_posted_year': roi_posted_year,
        }
