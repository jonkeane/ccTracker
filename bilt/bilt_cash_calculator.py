from datetime import date
from typing import Dict


class BiltCashCalculator:
    """Project Bilt cash usage and year-end expiration risk."""

    CASH_PER_MORTGAGE_DOLLAR = 0.03
    CASH_PER_OTHER_SPEND_DOLLAR = 0.04
    ROLLOVER_CAP = 100.0

    def __init__(self, today: date = None):
        self.today = today or date.today()

    def _remaining_months_in_year(self, as_of_date: date, include_one_extra_month: bool = False) -> int:
        """Return months after as_of month through December, with optional +1 month scenario."""
        months = 12 - as_of_date.month
        return months + (1 if include_one_extra_month else 0)

    @staticmethod
    def _round_currency(amount: float) -> float:
        return round(amount + 1e-9, 2)

    def project_usage(
        self,
        earned_cash_so_far: float,
        monthly_mortgage_payment: float,
        as_of_date: date = None,
        include_one_extra_mortgage_month: bool = False,
    ) -> Dict:
        """
        Calculate how much current-year Bilt cash can be consumed by year-end.

        Inputs are expected in dollars.
        """
        if earned_cash_so_far < 0:
            raise ValueError("earned_cash_so_far must be non-negative")
        if monthly_mortgage_payment < 0:
            raise ValueError("monthly_mortgage_payment must be non-negative")

        as_of_date = as_of_date or self.today
        remaining_months = self._remaining_months_in_year(
            as_of_date,
            include_one_extra_month=include_one_extra_mortgage_month,
        )
        total_mortgage_remaining = monthly_mortgage_payment * remaining_months

        max_redeemable_cash = total_mortgage_remaining * self.CASH_PER_MORTGAGE_DOLLAR
        usable_cash = min(earned_cash_so_far, max_redeemable_cash)

        mortgage_dollars_used = (
            usable_cash / self.CASH_PER_MORTGAGE_DOLLAR
            if self.CASH_PER_MORTGAGE_DOLLAR > 0
            else 0.0
        )
        mortgage_dollars_needed_for_all_cash = (
            earned_cash_so_far / self.CASH_PER_MORTGAGE_DOLLAR
            if self.CASH_PER_MORTGAGE_DOLLAR > 0
            else 0.0
        )

        remaining_cash = earned_cash_so_far - usable_cash
        rollover_cash = min(remaining_cash, self.ROLLOVER_CAP)
        expiring_cash = max(0.0, remaining_cash - self.ROLLOVER_CAP)

        # Additional non-mortgage spend needed (at 4% earn rate) to hit
        # target leftover amounts after projected mortgage redemption.
        additional_card_spend_needed_for_zero_leftover = (
            max(0.0, (max_redeemable_cash - earned_cash_so_far))
            / self.CASH_PER_OTHER_SPEND_DOLLAR
            if self.CASH_PER_OTHER_SPEND_DOLLAR > 0
            else 0.0
        )
        additional_card_spend_needed_for_100_leftover = (
            max(0.0, (self.ROLLOVER_CAP + max_redeemable_cash - earned_cash_so_far))
            / self.CASH_PER_OTHER_SPEND_DOLLAR
            if self.CASH_PER_OTHER_SPEND_DOLLAR > 0
            else 0.0
        )

        return {
            "as_of_date": as_of_date.isoformat(),
            "year": as_of_date.year,
            "include_one_extra_mortgage_month": include_one_extra_mortgage_month,
            "remaining_months": remaining_months,
            "monthly_mortgage_payment": self._round_currency(monthly_mortgage_payment),
            "earned_cash_so_far": self._round_currency(earned_cash_so_far),
            "total_mortgage_remaining": self._round_currency(total_mortgage_remaining),
            "max_redeemable_cash": self._round_currency(max_redeemable_cash),
            "usable_cash_by_year_end": self._round_currency(usable_cash),
            "mortgage_dollars_used": self._round_currency(mortgage_dollars_used),
            "mortgage_dollars_needed_for_all_cash": self._round_currency(mortgage_dollars_needed_for_all_cash),
            "remaining_cash_at_year_end": self._round_currency(remaining_cash),
            "rollover_cash": self._round_currency(rollover_cash),
            "expiring_cash": self._round_currency(expiring_cash),
            "additional_card_spend_needed_for_zero_leftover": self._round_currency(additional_card_spend_needed_for_zero_leftover),
            "additional_card_spend_needed_for_100_leftover": self._round_currency(additional_card_spend_needed_for_100_leftover),
            "has_expiration_risk": expiring_cash > 0,
            "has_unused_cash": remaining_cash > 0,
        }
