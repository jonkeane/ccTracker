from datetime import date

import pytest

from bilt.bilt_cash_calculator import BiltCashCalculator


class TestBiltCashCalculator:
    def test_projection_with_enough_mortgage_capacity(self):
        calc = BiltCashCalculator(today=date(2026, 4, 4))

        result = calc.project_usage(earned_cash_so_far=100.0, monthly_mortgage_payment=5000.0)

        assert result["remaining_months"] == 8
        assert result["usable_cash_by_year_end"] == pytest.approx(100.0)
        assert result["mortgage_dollars_used"] == pytest.approx(3333.33)
        assert result["remaining_cash_at_year_end"] == pytest.approx(0.0)
        assert result["rollover_cash"] == pytest.approx(0.0)
        assert result["expiring_cash"] == pytest.approx(0.0)
        assert result["has_expiration_risk"] is False
        assert result["additional_card_spend_needed_for_zero_leftover"] == pytest.approx(27500.0)
        assert result["additional_card_spend_needed_for_100_leftover"] == pytest.approx(30000.0)

    def test_projection_with_expiration_risk(self):
        calc = BiltCashCalculator(today=date(2026, 4, 4))

        result = calc.project_usage(earned_cash_so_far=500.0, monthly_mortgage_payment=500.0)

        assert result["remaining_months"] == 8
        assert result["max_redeemable_cash"] == pytest.approx(120.0)
        assert result["usable_cash_by_year_end"] == pytest.approx(120.0)
        assert result["remaining_cash_at_year_end"] == pytest.approx(380.0)
        assert result["rollover_cash"] == pytest.approx(100.0)
        assert result["expiring_cash"] == pytest.approx(280.0)
        assert result["has_expiration_risk"] is True
        assert result["additional_card_spend_needed_for_zero_leftover"] == pytest.approx(0.0)
        assert result["additional_card_spend_needed_for_100_leftover"] == pytest.approx(0.0)

    def test_projection_boundary_exact_rollover(self):
        calc = BiltCashCalculator(today=date(2026, 4, 4))

        result = calc.project_usage(earned_cash_so_far=220.0, monthly_mortgage_payment=500.0)

        assert result["remaining_cash_at_year_end"] == pytest.approx(100.0)
        assert result["rollover_cash"] == pytest.approx(100.0)
        assert result["expiring_cash"] == pytest.approx(0.0)
        assert result["has_expiration_risk"] is False

    def test_negative_input_validation(self):
        calc = BiltCashCalculator(today=date(2026, 4, 4))

        with pytest.raises(ValueError, match="earned_cash_so_far"):
            calc.project_usage(earned_cash_so_far=-1.0, monthly_mortgage_payment=1000.0)

        with pytest.raises(ValueError, match="monthly_mortgage_payment"):
            calc.project_usage(earned_cash_so_far=100.0, monthly_mortgage_payment=-1.0)

    def test_december_boundary_excludes_current_month(self):
        calc = BiltCashCalculator(today=date(2026, 12, 31))

        result = calc.project_usage(earned_cash_so_far=200.0, monthly_mortgage_payment=1000.0)

        assert result["remaining_months"] == 0
        assert result["max_redeemable_cash"] == pytest.approx(0.0)
        assert result["usable_cash_by_year_end"] == pytest.approx(0.0)
        assert result["remaining_cash_at_year_end"] == pytest.approx(200.0)
        assert result["rollover_cash"] == pytest.approx(100.0)
        assert result["expiring_cash"] == pytest.approx(100.0)

    def test_december_boundary_with_extra_month_toggle(self):
        calc = BiltCashCalculator(today=date(2026, 12, 31))

        result = calc.project_usage(
            earned_cash_so_far=200.0,
            monthly_mortgage_payment=1000.0,
            include_one_extra_mortgage_month=True,
        )

        assert result["include_one_extra_mortgage_month"] is True
        assert result["remaining_months"] == 1
        assert result["max_redeemable_cash"] == pytest.approx(30.0)
        assert result["usable_cash_by_year_end"] == pytest.approx(30.0)
        assert result["remaining_cash_at_year_end"] == pytest.approx(170.0)
        assert result["rollover_cash"] == pytest.approx(100.0)
        assert result["expiring_cash"] == pytest.approx(70.0)
