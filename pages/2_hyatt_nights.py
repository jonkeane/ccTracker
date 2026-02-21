"""Hyatt Nights page for tracking stays and nights."""
import streamlit as st
import pandas as pd

def run():
    """Render the Hyatt Nights page."""
    st.title("🏨 Hyatt Nights")
    st.markdown("Track your Hyatt nights, bonus night earnings, and elite status nights.")
    
    # ========================================================================
    # OVERALL / ELITE NIGHTS SECTION
    # ========================================================================
    st.subheader("Summary")

    # Get all calculated data from service
    summary_service = st.session_state.summary_service
    nights_summary = summary_service.calculate_nights_summary()

    cc_nights_pending_col, upcoming_nights_col, goh_upcoming_col = st.columns(3)
    cc_nights_posted_col, current_nights_col, goh_posted_col = st.columns(3)
    cc_yearly_col, nights_posted_col, nights_total_col = st.columns(3)

    with cc_yearly_col:
        st.metric("CC Yearly Start", nights_summary['cc_yearly_start'])
    with cc_nights_posted_col:
        st.metric("CC Nights (posted)", nights_summary['cc_nights_posted'])
    with cc_nights_pending_col:
        st.metric("CC Nights (pending)", nights_summary['cc_nights_pending'])

    with upcoming_nights_col:
        st.metric("Nights (upcoming)", nights_summary['upcoming_nights'])
    with current_nights_col:
        st.metric("Nights (posted)", nights_summary['current_nights'])
    with goh_upcoming_col:
        st.metric("GOH (upcoming)", nights_summary['goh_nights_upcoming'])
    with goh_posted_col:
        st.metric("GOH (posted)", nights_summary['goh_nights'])

    with nights_posted_col:
        st.metric("Nights Posted", nights_summary['nights_posted'])
    with nights_total_col:
        st.metric("Nights Total", nights_summary['nights_total'])
        
    # Edit Elite Nights - Stays
    with st.expander("✏️ Stays (Current & Upcoming)"):
        st.markdown("**Add a new stay:**")
        add_col1, add_col2, add_col3, add_col4 = st.columns([2, 2, 2, 1])
        
        stays_manager = st.session_state.stays_manager
        
        with add_col1:
            stay_name = st.text_input("Hotel/Location", key="stay_name_input")
        with add_col2:
            check_in = st.date_input("Check-in", key="stay_checkin_input")
        with add_col3:
            check_out = st.date_input("Check-out", key="stay_checkout_input")
        with add_col4:
            if st.button("➕ Add Stay", width='stretch'):
                if stay_name and check_in and check_out and check_out > check_in:
                    if stays_manager.add_stay(stay_name, check_in, check_out):
                        st.success(f"Added {stay_name}")
                        st.rerun()
                    else:
                        st.error("Failed to add stay")
                else:
                    st.error("Please fill all fields and ensure check-out is after check-in")
        
        st.markdown("**Current and upcoming stays:**")
        
        stays = stays_manager.get_stays()
        if stays:
            for idx, stay in enumerate(stays):
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                nights = (stay['check_out'] - stay['check_in']).days
                is_past = stay['check_out'] <= pd.Timestamp.now().date()
                
                with col1:
                    st.write(f"**{stay['name']}**")
                with col2:
                    st.write(f"{stay['check_in']} → {stay['check_out']}")
                with col3:
                    status = "✅ Completed" if is_past else "⏳ Upcoming"
                    st.write(f"{nights} nights {status}")
                with col4:
                    if st.button("✏️", key=f"edit_stay_{idx}", width='stretch'):
                        st.session_state.editing_stay = idx
                with col5:
                    if st.button("🗑️", key=f"delete_stay_{idx}", width='stretch'):
                        stays_manager.delete_stay(idx)
                        st.rerun()
        else:
            st.info("No stays added yet")
        
    # Edit Elite Nights - GOH
    with st.expander("✏️ GOH Nights"):
        st.markdown("**Add a new GOH night:**")
        goh_col1, goh_col2, goh_col3 = st.columns([2, 2, 1])
        
        with goh_col1:
            goh_name = st.text_input("Guest Name / Description", key="goh_name_input")
        with goh_col2:
            goh_date = st.date_input("Date", key="goh_date_input")
        with goh_col3:
            if st.button("➕ Add GOH", width='stretch'):
                if goh_name and goh_date:
                    if stays_manager.add_goh_night(goh_name, goh_date):
                        st.success(f"Added {goh_name}")
                        st.rerun()
                    else:
                        st.error("Failed to add GOH night")
                else:
                    st.error("Please fill all fields")
        
        st.markdown("**Current and upcoming GOH nights:**")
        
        goh_nights_list = stays_manager.get_goh_nights()
        if goh_nights_list:
            for idx, goh in enumerate(goh_nights_list):
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                is_past = goh['date'] <= pd.Timestamp.now().date()
                
                with col1:
                    st.write(f"**{goh['name']}**")
                with col2:
                    st.write(f"{goh['date']}")
                with col3:
                    status = "✅" if is_past else "⏳"
                    st.write(status)
                with col4:
                    if st.button("🗑️", key=f"delete_goh_{idx}", width='stretch'):
                        stays_manager.delete_goh_night(idx)
                        st.rerun()
        else:
            st.info("No GOH nights added yet")
        
    st.markdown("---")
    
    # ========================================================================
    # PERSONAL CARD SECTION
    # ========================================================================
    st.subheader("💳 Personal Card (Chase ending 4100/1695)")

    processor = st.session_state.processor
    personal_summary = processor.get_spending_summary('personal')
    personal_breakdown = processor.get_yearly_bonus_nights_breakdown('personal')
    
    if personal_summary:
        # Row 1: All-time and YTD spending
        personal_col1, personal_col2 = st.columns(2)
        
        with personal_col1:
            st.metric(
                "Total Spending All Time",
                f"${personal_summary['total_spending']:,.2f}",
                delta=None
            )
        
        with personal_col2:
            st.metric(
                "Total Spending This Year",
                f"${personal_summary['ytd_spending']:,.2f}",
                delta=None
            )
        
        # Row 2: Progress metrics
        personal_col3, personal_col4 = st.columns(2)
        
        with personal_col3:
            spend_to_next = personal_summary['spend_to_next_bonus']
            st.metric(
                "Spend Until Next 2 Nights",
                f"${spend_to_next:,.2f}",
                help=f"Each $5,000 = 2 nights. Current tier: {personal_summary['current_tier']}"
            )
        
        with personal_col4:
            cert_spend = personal_summary['spend_to_certificate']
            if cert_spend > 0:
                st.metric(
                    "Spend Until Certificate",
                    f"${cert_spend:,.2f}",
                    help="Annual certificate at $15,000 YTD"
                )
            else:
                st.metric(
                    "Spend Until Certificate",
                    "✅ Unlocked",
                    help="Annual certificate already unlocked"
                )
        
        # Row 3: Bonus nights breakdown
        personal_col5, personal_col6, personal_col7 = st.columns(3)
        
        with personal_col5:
            st.metric(
                "Nights This Year (Posted)",
                personal_breakdown['posted']
            )
        
        with personal_col6:
            st.metric(
                "Nights This Year (Pending)",
                personal_breakdown['pending']
            )
        
        with personal_col7:
            st.metric(
                "Nights This Year (Total)",
                personal_breakdown['total']
            )
    else:
        st.warning("No personal card data available")
    
    st.markdown("---")
    
    # ========================================================================
    # BUSINESS CARD SECTION
    # ========================================================================
    st.subheader("💳 Business Card (Chase 1505)")

    business_summary = processor.get_spending_summary('business')
    business_breakdown = processor.get_yearly_bonus_nights_breakdown('business')
    
    if business_summary:
        # Row 1: YTD spending
        business_col1 = st.columns(1)[0]
        
        with business_col1:
            st.metric(
                "Total Spending This Year",
                f"${business_summary['ytd_spending']:,.2f}",
                help="Resets January 1"
            )
        
        business_col2, business_col3 = st.columns(2)
        
        with business_col2:
            spend_to_next = business_summary['spend_to_next_bonus']
            st.metric(
                "Spend Until Next 5 Nights",
                f"${spend_to_next:,.2f}",
                help=f"Each $10,000 = 5 nights. Current tier: {business_summary['current_tier']}"
            )
        
        # Row 3: Bonus nights breakdown
        st.markdown("")  # spacing
        business_col4, business_col5, business_col6 = st.columns(3)
        
        with business_col4:
            st.metric(
                "Nights This Year (Posted)",
                business_breakdown['posted']
            )
        
        with business_col5:
            st.metric(
                "Nights This Year (Pending)",
                business_breakdown['pending']
            )
        
        with business_col6:
            st.metric(
                "Nights This Year (Total)",
                business_breakdown['total']
            )
    else:
        st.warning("No business card data available")


# Run the page
run()

if __name__ == "__main__":
    pass
