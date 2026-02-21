"""Benefits Tracker page for monitoring credit card benefits."""
import streamlit as st
from benefits.period_utils import sort_benefits_by_period
from datetime import datetime
from calendar import month_name


def run():
    """Render the Benefits Tracker page."""
    st.title("💳 Benefits Tracker")
    st.markdown("Track and verify your credit card benefits as they post.")

    st.markdown(
        """
        <style>        
        /* Make buttons fill their container width */
        button[data-testid="stBaseButton-secondary"] {
            width: 100%;
        }
        
        /* Remove any padding/margin from the inner div */
        div[role="radiogroup"] label > div {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* Hide the actual radio button circles - all possible selectors */
        div[role="radiogroup"] label > div:has(+ input) {
            display: none !important;
            opacity: 0 !important;
            width: 0 !important;
            height: 0 !important;
            position: absolute !important;
        }
        
        /* Hover effect */
        div[role="radiogroup"] label div:hover {
            color: rgb(255, 75, 75) !important;
        }
        
        /* Selected tab styling - red text and underline */
        div[role="radiogroup"] label:has(input:checked) div {
            color: rgb(255, 75, 75) !important;
            border-bottom: 1px solid rgb(255, 75, 75) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    calculator = st.session_state.calculator
    summary_service = st.session_state.summary_service
    
    # Get all cards and group by base name (removing year suffix)
    cards = calculator.config.get('cards', {})
    
    # Group cards by base name
    card_groups = {}
    for card_key, card_data in cards.items():
        # Extract base name by removing _YYYY suffix
        base_name = '_'.join(card_key.rsplit('_', 1)[:-1]) if '_' in card_key and card_key.split('_')[-1].isdigit() else card_key
        if base_name not in card_groups:
            card_groups[base_name] = {
                'display_name': card_data['display_name'],
                'years': {}
            }
        year = card_data.get('year', card_key.split('_')[-1])
        card_groups[base_name]['years'][str(year)] = card_key
    
    # Create tabs for each unique card (base name)
    card_list = [(base_name, data['display_name']) for base_name, data in card_groups.items()]
    tabs = st.tabs([card_name for _, card_name in card_list])
    
    for tab, (base_name, card_name) in zip(tabs, card_list):
        with tab:
            # Get available years for this card in descending order (latest to earliest)
            available_years = sorted(card_groups[base_name]['years'].keys(), key=int, reverse=True)
            
            # Determine current anniversary year to set as default
            current_anniversary_year = None
            for year in available_years:
                card_key_check = card_groups[base_name]['years'][year]
                start_date, end_date = calculator.get_anniversary_year_range(card_key_check, int(year))
                if start_date <= calculator.today <= end_date:
                    current_anniversary_year = year
                    break
            
            # Set default index for year selection (current anniversary year if found, otherwise first year)
            default_index = available_years.index(current_anniversary_year) if current_anniversary_year in available_years else 0
            
            # Use radio buttons for year selection (allows setting default that isn't first)
            selected_year = st.radio(
                "Select Anniversary Year",
                options=available_years,
                index=default_index,
                horizontal=True,
                key=f"{base_name}_year_selector",
                label_visibility="collapsed"
            )
            
            # Get the card_key for the selected year (for fees and anniversary info)
            card_key = card_groups[base_name]['years'][selected_year]
            
            # Get benefits only from the selected year's configuration
            # This ensures we display the correct benefit amounts for each year
            all_benefits = calculator.get_card_benefits(card_key)
            
            # Get card summary for display (fees from selected year)
            card_summary = calculator.get_card_summary(card_key)

            # Get anniversary month and year range for display
            anniversary_month = calculator.get_card_anniversary_month(card_key)
            start_date, end_date = calculator.get_anniversary_year_range(card_key, int(selected_year))

            # Filter benefits by anniversary year using service
            benefits = summary_service.get_filtered_benefits_for_year(card_key, int(selected_year))

            # Calculate year-specific summary stats using service
            annual_fee = card_summary['annual_fee']
            year_summary = summary_service.calculate_year_summary(benefits, annual_fee, int(selected_year))

            # Card summary header - showing year-filtered data with anniversary info
            anniversary_display = f"{month_name[anniversary_month]} {start_date.strftime('%Y')} - {month_name[anniversary_month]} {end_date.strftime('%Y')}"
            st.markdown(f"**Anniversary Year {selected_year}** ({anniversary_display})")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Annual Fee", f"${annual_fee}")
            with col2:
                st.metric("Benefits Posted", f"${year_summary['total_posted_year']:,.0f}")
            with col3:
                st.metric("Potential Benefits", f"${year_summary['total_potential_year']:,.0f}")
            with col4:
                st.metric("Net Value (Posted)", f"${year_summary['net_value_posted_year']:,.0f}", delta=f"{year_summary['roi_posted_year']:.1f}%")
            
            st.markdown("")
            
            # Group by category
            categories = {}
            for benefit in benefits:
                cat = benefit['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(benefit)

            today = calculator.today

            def get_benefit_disabled_state(benefit, renewal_type):
                if benefit.get('frequency') == 'every_4_years':
                    every_4_info = calculator.get_every_4_years_benefit_info(benefit)
                    if not every_4_info['is_available']:
                        return True, every_4_info['disabled_reason']

                if renewal_type == 'calendar_year' and benefit['posted']:
                    posted_anniv_year = benefit.get('posted_anniversary_year')
                    if posted_anniv_year and posted_anniv_year != int(selected_year):
                        return True, f"Used in {posted_anniv_year}"

                return False, None
            
            # Sort categories: those with monthly benefits first, then alphabetically
            def category_sort_key(cat):
                has_monthly = any(b.get('frequency') == 'monthly' for b in categories[cat])
                return (not has_monthly, cat)  # False sorts before True, so has_monthly comes first
            
            # Display by category (no collapsible sections)
            for category in sorted(categories.keys(), key=category_sort_key):
                st.markdown(f'<h3 style="color: #ff9999;">{category}</h3>', unsafe_allow_html=True)
                cat_benefits = categories[category]

                sorted_cat_benefits = sort_benefits_by_period(cat_benefits)
                monthly_benefits = [b for b in sorted_cat_benefits if b.get('frequency') == 'monthly']
                if monthly_benefits:
                    def apply_monthly_toggle(target_state, date_filter=None):
                        changed = False
                        for idx, benefit in enumerate(sorted_cat_benefits):
                            if benefit.get('frequency') != 'monthly':
                                continue
                            renewal_type = calculator.get_benefit_renewal_type(benefit)
                            is_disabled, _ = get_benefit_disabled_state(benefit, renewal_type)
                            if is_disabled:
                                continue

                            if date_filter:
                                period_start, _ = calculator.get_calendar_period_date_range(benefit['period'])
                                if not period_start:
                                    continue
                                if date_filter == "up_to_today" and period_start > today:
                                    continue
                                if date_filter == "after_today" and period_start <= today:
                                    continue

                            if benefit['posted'] != target_state:
                                if target_state and renewal_type == 'calendar_year':
                                    calculator.toggle_benefit(benefit['benefit_id'], benefit['period'], int(selected_year))
                                else:
                                    calculator.toggle_benefit(benefit['benefit_id'], benefit['period'])
                                toggle_key = f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_toggle"
                                st.session_state[toggle_key] = target_state
                                changed = True

                        if changed:
                            st.rerun()

                    # Calculate posted vs total for monthly benefits
                    # Count unique periods to avoid double-counting
                    unique_periods = {b['period'] for b in monthly_benefits}
                    posted_periods = {b['period'] for b in monthly_benefits if b.get('posted')}
                    total_monthly = sum(b.get('custom_amount') or b['amount'] for b in monthly_benefits)
                    posted_monthly = sum((b.get('custom_amount') or b['amount']) for b in monthly_benefits if b.get('posted'))
                    posted_count = len(posted_periods)
                    total_count = len(unique_periods)

                    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 5])
                    with col1:
                        if st.button("all on", key=f"{card_key}_{category}_{selected_year}_monthly_on", use_container_width=True):
                            apply_monthly_toggle(True)
                    with col2:
                        if st.button("all off", key=f"{card_key}_{category}_{selected_year}_monthly_off", use_container_width=True):
                            apply_monthly_toggle(False)
                    with col3:
                        if st.button("past on", key=f"{card_key}_{category}_{selected_year}_monthly_on_to_today", use_container_width=True):
                            apply_monthly_toggle(True, date_filter="up_to_today")
                    with col4:
                        if st.button("future off", key=f"{card_key}_{category}_{selected_year}_monthly_off_after_today", use_container_width=True):
                            apply_monthly_toggle(False, date_filter="after_today")
                    with col5:
                        st.markdown(
                            f'<div style="display: flex; align-items: center; height: 100%; font-size: 1.5rem; margin-left: 2rem;">'
                            f'<span style="font-weight: 600;">${posted_monthly:.0f}/${total_monthly:.0f}</span>'
                            f'<span style="margin-left: 1rem; color: #888;">({posted_count}/{total_count} months)</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                # Separate monthly and non-monthly benefits for sorting
                non_monthly_benefits = [b for b in sorted_cat_benefits if b.get('frequency') != 'monthly']
                
                # Display monthly benefits section (collapsed by default)
                if monthly_benefits:
                    with st.expander("📅 Monthly Benefits", expanded=False):
                        col_period, col_total, col_custom, col_toggle = st.columns([2, 1.2, 1.5, 2.5])
                        with col_period:
                            st.write("**Period**")
                        with col_total:
                            st.write("**Total**")
                        with col_custom:
                            st.write("**Amount**")
                        with col_toggle:
                            st.write("**Posted**")
                        
                        # Display each monthly benefit as a row
                        for idx, benefit in enumerate(monthly_benefits):
                            col_period, col_total, col_custom, col_toggle = st.columns([2, 1.2, 1.5, 2.5])
                            
                            with col_period:
                                st.write(benefit['period'])
                            
                            with col_total:
                                st.write(f"${benefit['amount']}")
                            
                            with col_custom:
                                # Show custom amount or placeholder
                                current_custom = benefit['custom_amount']
                                
                                # Create a narrower column for the input
                                input_col, _ = st.columns([0.5, 1])
                                with input_col:
                                    # Use text input to allow empty state
                                    custom_text = st.text_input(
                                        "Amount",
                                        value=str(int(current_custom)) if current_custom and current_custom > 0 else "",
                                        key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_custom",
                                        label_visibility="collapsed",
                                        placeholder=f"${int(benefit['amount'])}"
                                    )
                                
                                # Parse and update custom amount
                                try:
                                    if custom_text.strip():
                                        custom_val = float(custom_text)
                                        if custom_val > benefit['amount']:
                                            st.error(f"Amount cannot exceed total (${benefit['amount']})")
                                        elif custom_val > 0 and custom_val != current_custom:
                                            calculator.set_custom_amount(benefit['benefit_id'], benefit['period'], custom_val)
                                            st.rerun()
                                    elif current_custom is not None and current_custom > 0:
                                        # Clear the custom amount if field is empty
                                        calculator.set_custom_amount(benefit['benefit_id'], benefit['period'], None)
                                        st.rerun()
                                except ValueError:
                                    st.error("Please enter a valid number")
                            
                            with col_toggle:
                                renewal_type = calculator.get_benefit_renewal_type(benefit)
                                is_disabled, disabled_reason = get_benefit_disabled_state(benefit, renewal_type)
                                
                                if is_disabled:
                                    # Show disabled toggle with explanation side-by-side
                                    toggle_col, reason_col = st.columns([1, 2])
                                    with toggle_col:
                                        st.toggle(
                                            "Posted",
                                            value=benefit['posted'],
                                            key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_toggle",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                    with reason_col:
                                        if disabled_reason:
                                            st.caption(disabled_reason)
                                else:
                                    # Normal toggle
                                    toggle_val = st.toggle(
                                        "Posted",
                                        value=benefit['posted'],
                                        key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_toggle",
                                        label_visibility="collapsed"
                                    )
                                    
                                    # If toggle value differs from stored state, update it
                                    if toggle_val != benefit['posted']:
                                        # For calendar year benefits, track which anniversary year it was used in
                                        if renewal_type == 'calendar_year':
                                            calculator.toggle_benefit(benefit['benefit_id'], benefit['period'], int(selected_year))
                                        else:
                                            # Anniversary benefits don't need anniversary year tracking
                                            calculator.toggle_benefit(benefit['benefit_id'], benefit['period'])
                                        st.rerun()
                
                # Display non-monthly benefits
                if non_monthly_benefits:
                    col_period, col_total, col_custom, col_toggle = st.columns([2, 1.2, 1.5, 2.5])
                    with col_period:
                        st.write("**Period**")
                    with col_total:
                        st.write("**Total**")
                    with col_custom:
                        st.write("**Amount**")
                    with col_toggle:
                        st.write("**Posted**")
                    
                    # Display each non-monthly benefit as a row
                    for idx, benefit in enumerate(non_monthly_benefits):
                        col_period, col_total, col_custom, col_toggle = st.columns([2, 1.2, 1.5, 2.5])
                        
                        with col_period:
                            st.write(benefit['period'])
                        
                        with col_total:
                            st.write(f"${benefit['amount']}")
                        
                        with col_custom:
                            # Show custom amount or placeholder
                            current_custom = benefit['custom_amount']
                            
                            # Create a narrower column for the input
                            input_col, _ = st.columns([0.5, 1])
                            with input_col:
                                # Use text input to allow empty state
                                custom_text = st.text_input(
                                    "Amount",
                                    value=str(int(current_custom)) if current_custom and current_custom > 0 else "",
                                    key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_custom",
                                    label_visibility="collapsed",
                                    placeholder=f"${int(benefit['amount'])}"
                                )
                            
                            # Parse and update custom amount
                            try:
                                if custom_text.strip():
                                    custom_val = float(custom_text)
                                    if custom_val > benefit['amount']:
                                        st.error(f"Amount cannot exceed total (${benefit['amount']})")
                                    elif custom_val > 0 and custom_val != current_custom:
                                        calculator.set_custom_amount(benefit['benefit_id'], benefit['period'], custom_val)
                                        st.rerun()
                                elif current_custom is not None and current_custom > 0:
                                    # Clear the custom amount if field is empty
                                    calculator.set_custom_amount(benefit['benefit_id'], benefit['period'], None)
                                    st.rerun()
                            except ValueError:
                                st.error("Please enter a valid number")
                        
                        with col_toggle:
                            renewal_type = calculator.get_benefit_renewal_type(benefit)
                            is_disabled, disabled_reason = get_benefit_disabled_state(benefit, renewal_type)
                            
                            if is_disabled:
                                # Show disabled toggle with explanation side-by-side
                                toggle_col, reason_col = st.columns([1, 2])
                                with toggle_col:
                                    st.toggle(
                                        "Posted",
                                        value=benefit['posted'],
                                        key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_toggle",
                                        label_visibility="collapsed",
                                        disabled=True
                                    )
                                with reason_col:
                                    if disabled_reason:
                                        st.caption(disabled_reason)
                            else:
                                # Normal toggle
                                toggle_val = st.toggle(
                                    "Posted",
                                    value=benefit['posted'],
                                    key=f"{card_key}_{category}_{benefit['benefit_id']}_{idx}_toggle",
                                    label_visibility="collapsed"
                                )
                                
                                # If toggle value differs from stored state, update it
                                if toggle_val != benefit['posted']:
                                    # For calendar year benefits, track which anniversary year it was used in
                                    if renewal_type == 'calendar_year':
                                        calculator.toggle_benefit(benefit['benefit_id'], benefit['period'], int(selected_year))
                                    else:
                                        # Anniversary benefits don't need anniversary year tracking
                                        calculator.toggle_benefit(benefit['benefit_id'], benefit['period'])
                                    st.rerun()
                
                st.markdown("")


# Run the page
run()

if __name__ == "__main__":
    pass
