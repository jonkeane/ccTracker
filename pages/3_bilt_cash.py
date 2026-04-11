"""Bilt Cash tracker page for year-end usage projection."""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from app_initialization import ensure_app_session_state_initialized

BILT_STATE_PATH = Path("bilt_state.json")


@st.cache_resource
def _load_custom_css():
    """Load custom CSS for this page."""
    css_file = Path(__file__).parent.parent / "styles" / "bilt_cash.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _load_bilt_state() -> dict:
    if BILT_STATE_PATH.exists():
        try:
            with open(BILT_STATE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "earned_cash_so_far": 0.0,
        "monthly_mortgage_payment": 0.0,
        "include_one_extra_mortgage_month": False,
    }


def _save_bilt_state():
    with open(BILT_STATE_PATH, "w") as f:
        json.dump(
            {
                "earned_cash_so_far": st.session_state["bilt_earned_cash"],
                "monthly_mortgage_payment": st.session_state["bilt_mortgage_payment"],
                "include_one_extra_mortgage_month": st.session_state["bilt_include_extra_month"],
            },
            f,
            indent=2,
        )


def run():
    """Render the Bilt cash projection tracker page."""
    _load_custom_css()
    ensure_app_session_state_initialized()
    
    st.title("🏠 Bilt Cash Tracker")
    st.markdown("Project how much Bilt cash you can use by Dec 31 and detect expiration risk.")

    calculator = st.session_state.bilt_calculator

    if "bilt_inputs_loaded" not in st.session_state:
        saved = _load_bilt_state()
        st.session_state["bilt_earned_cash"] = saved["earned_cash_so_far"]
        st.session_state["bilt_mortgage_payment"] = saved["monthly_mortgage_payment"]
        st.session_state["bilt_include_extra_month"] = saved.get("include_one_extra_mortgage_month", False)
        st.session_state["bilt_inputs_loaded"] = True

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        earned_cash_so_far = st.number_input(
            "Bilt cash",
            min_value=0.0,
            step=10.0,
            format="%.2f",
            key="bilt_earned_cash",
            on_change=_save_bilt_state,
            help="Total Bilt cash currently available this year.",
        )
    with col2:
        monthly_mortgage_payment = st.number_input(
            "Mortgage monthly",
            min_value=0.0,
            step=100.0,
            format="%.2f",
            key="bilt_mortgage_payment",
            on_change=_save_bilt_state,
            help="Projected monthly mortgage amount to put on this card for the remaining months.",
        )
    # Calculate projection with current toggle state
    projection = calculator.project_usage(
        earned_cash_so_far=earned_cash_so_far,
        monthly_mortgage_payment=monthly_mortgage_payment,
        include_one_extra_mortgage_month=st.session_state.get("bilt_include_extra_month", False),
    )
    with col3:
        st.metric("Months Remaining", projection["remaining_months"])
    with col4:
        next_year = datetime.now().year + 1
        st.toggle(
            f"add Jan {next_year}",
            key="bilt_include_extra_month",
            on_change=_save_bilt_state,
            help="Add one month to remaining mortgage payments to model paying January in December.",
        )
    st.markdown("---")

    if projection["has_expiration_risk"]:
        st.error(
            "⚠️ You are projected to lose Bilt cash at year-end. "
            f"About ${projection['expiring_cash']:,.2f} is expected to expire."
        )
    elif projection["has_unused_cash"]:
        st.warning(
            "You are projected to carry unused Bilt cash into year-end, but it should fit in the $100 rollover cap."
        )

    st.subheader("Projection Summary")

    c2, c3 = st.columns(2)
    with c2:
        st.metric("Max Redeemable Bilt Cash", f"${projection['max_redeemable_cash']:,.2f}")
    with c3:
        st.metric("Rollover to Next Year (max $100)", f"${projection['rollover_cash']:,.2f}")

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Cash Remaining at Year End", f"${projection['remaining_cash_at_year_end']:,.2f}")
    with c5:
        st.metric("Cash Expiring Dec 31", f"${projection['expiring_cash']:,.2f}")

    c8, c9 = st.columns(2)
    with c8:
        st.metric(
            "Bilt card spending to match mortgage",
            f"${projection['additional_card_spend_needed_for_zero_leftover']:,.2f}",
        )
    with c9:
        st.metric(
            "Bilt card spending to match mortgage",
            f"${projection['additional_card_spend_needed_for_100_leftover']:,.2f}",
        )

    c6, c7 = st.columns(2)
    with c6:
        st.metric("Total Mortgage Remaining", f"${projection['total_mortgage_remaining']:,.2f}")
    with c7:
        st.metric("Mortgage Dollars Used", f"${projection['mortgage_dollars_used']:,.2f}")

# Run the page
run()

if __name__ == "__main__":
    pass
