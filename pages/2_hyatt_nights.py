"""Hyatt Nights page for tracking stays and nights."""
from datetime import date
from pathlib import Path

import streamlit as st
import pandas as pd
from app_initialization import ensure_app_session_state_initialized
from benefits.transaction_csv_manager import TransactionCsvManager


@st.cache_resource
def _load_custom_css():
    """Load custom CSS for this page."""
    css_file = Path(__file__).parent.parent / "styles" / "hyatt_nights.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _reload_processor_data():
    """Reload transaction-derived card data after CSV updates."""
    processor = st.session_state.processor
    processor.process_personal_card()
    processor.process_business_card()


def _reset_uploader(uploader_key):
    """Reset a file_uploader by clearing its session state key."""
    st.session_state.pop(uploader_key, None)


def _build_processor_csv_signature():
    """Build a lightweight signature of current CSV inventory on disk."""
    processor = st.session_state.processor

    def _scan(folder_name):
        folder = Path(processor.base_path) / folder_name
        if not folder.exists():
            return (str(folder), 0, 0)

        csv_files = [
            path for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() == ".csv"
        ]
        if not csv_files:
            return (str(folder), 0, 0)

        latest_mtime_ns = max(path.stat().st_mtime_ns for path in csv_files)
        return (str(folder), len(csv_files), latest_mtime_ns)

    return (
        _scan(processor.hyatt_cards['personal']['folder']),
        _scan(processor.hyatt_cards['business']['folder']),
    )


def _refresh_processor_if_csvs_changed():
    """Reload processor data when underlying CSV files change on disk."""
    signature = _build_processor_csv_signature()
    previous = st.session_state.get("hyatt_processor_csv_signature")

    if previous != signature:
        _reload_processor_data()
        st.session_state.hyatt_processor_csv_signature = signature


def _render_upload_validation(manager, uploaded_files, card_type=None):
    """Show upload validation feedback and return result tuples."""
    results = []
    for uploaded_file in uploaded_files:
        validation = manager.validate_uploaded_file(uploaded_file)
        if validation["valid"] and card_type is not None:
            filename_check = manager.validate_filename_card_ending(
                uploaded_file.name, card_type
            )
            if not filename_check["valid"]:
                validation = {**validation, "valid": False, "message": filename_check["message"]}
        results.append((uploaded_file, validation))
        years_display = ", ".join(str(year) for year in validation.get("years", []))
        if validation["valid"]:
            st.success(
                f"{uploaded_file.name}: {validation['row_count']} rows, years [{years_display}]"
            )
        else:
            st.error(f"{uploaded_file.name}: {validation['message']}")

    return results


def _render_csv_inventory_panel(manager, inventory_card):
    """Render inventory and historical upload controls for one card type."""
    inventory = manager.list_csv_files(inventory_card)

    if not inventory:
        st.info("No CSV files found for this card.")
    else:
        folders = sorted({item["folder"] for item in inventory})
        if len(folders) == 1:
            st.caption(f"Path: {folders[0]}")
        else:
            st.caption("Paths: " + ", ".join(folders))

        h1, h2, h3, h_del = st.columns([7, 2, 3, 1])
        with h1:
            st.markdown("**File**")
        with h2:
            st.markdown("**Years**")
        with h3:
            st.markdown("**Last Modified**")

        for idx, item in enumerate(inventory):
            c1, c2, c3, c_del = st.columns([7, 2, 3, 1])
            with c1:
                st.write(item["name"])
            with c2:
                st.write(", ".join(str(y) for y in item["years"]))
            with c3:
                st.write(item["modified"].strftime("%Y-%m-%d %H:%M:%S"))
            with c_del:
                if st.button("🗑️", key=f"del_csv_{inventory_card}_{idx}"):
                    manager.delete_csv_file(item["full_path"])
                    _reload_processor_data()
                    st.rerun()

    add_file = st.file_uploader(
        "Upload CSV",
        type=["csv", "CSV"],
        key=f"add_inv_file_{inventory_card}",
    )
    add_validation = []
    if add_file:
        add_validation = _render_upload_validation(manager, [add_file], card_type=inventory_card)
    if st.button("💾 Save File", key=f"save_inv_file_{inventory_card}", width="stretch"):
        if not add_file:
            st.warning("Select a file first.")
        elif add_validation and not add_validation[0][1]["valid"]:
            st.error("Fix invalid file before saving.")
        else:
            manager.save_uploaded_file(
                uploaded_file=add_file,
                card_type=inventory_card,
            )
            _reload_processor_data()
            _reset_uploader(f"add_inv_file_{inventory_card}")
            st.success("File saved.")
            st.rerun()


def _render_csv_management_content():
    """Render filesystem-backed CSV management controls."""
    hyatt_card_config = st.session_state.get("hyatt_card_config", {})
    card_folders = {
        "personal": hyatt_card_config["personal"]["folder"],
        "business": hyatt_card_config["business"]["folder"],
    }
    personal_endings = "/".join(hyatt_card_config["personal"]["card_endings"])
    business_endings = "/".join(hyatt_card_config["business"]["card_endings"])

    manager = TransactionCsvManager(
        card_folders=card_folders,
        card_endings={
            "personal": hyatt_card_config["personal"]["card_endings"],
            "business": hyatt_card_config["business"]["card_endings"],
        },
    )
    current_year = pd.Timestamp.now().year

    personal_active = manager.get_active_current_year_file("personal")
    business_active = manager.get_active_current_year_file("business")

    upload_personal_col, upload_business_col = st.columns(2)

    with upload_personal_col:
        personal_uploads = st.file_uploader(
            f"💳 Personal Card Chase ending {personal_endings}",
            type=["csv", "CSV"],
            accept_multiple_files=False,
            key="current_csv_uploads_personal",
        )
        if personal_active:
            st.caption(f"Source: {personal_active['name']}  \nUpdated: {personal_active['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("Source: None  \nUpdated: None")

        replace_overlap_personal = st.checkbox(
            f"Replace personal files that overlap {current_year}",
            value=True,
            key="replace_current_overlap_personal",
            help="When enabled, personal files with overlapping years in root/current are replaced.",
        )

        personal_validation = []
        if personal_uploads:
            personal_validation = _render_upload_validation(manager, [personal_uploads], card_type="personal")

        if st.button("💾 Save File", key="apply_current_uploads_personal", width='stretch'):
            if not personal_uploads:
                st.warning("Upload at least one personal file before applying.")
            elif any(not result[1]["valid"] for result in personal_validation):
                st.error("Fix invalid personal files before applying.")
            else:
                for uploaded_file, _ in personal_validation:
                    manager.save_uploaded_file(
                        uploaded_file=uploaded_file,
                        card_type="personal",
                        replace_overlapping_years=replace_overlap_personal,
                    )
                _reload_processor_data()
                _reset_uploader("current_csv_uploads_personal")
                st.success("Personal current-year uploads applied.")
                st.rerun()

    with upload_business_col:
        business_uploads = st.file_uploader(
            f"💳 Business Card Chase ending {business_endings}",
            type=["csv", "CSV"],
            accept_multiple_files=False,
            key="current_csv_uploads_business",
        )
        if business_active:
            st.caption(f"Source: {business_active['name']}  \nUpdated: {business_active['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("Source: None  \nUpdated: None")

        replace_overlap_business = st.checkbox(
            f"Replace business files that overlap {current_year}",
            value=True,
            key="replace_current_overlap_business",
            help="When enabled, business files with overlapping years in root/current are replaced.",
        )

        business_validation = []
        if business_uploads:
            business_validation = _render_upload_validation(manager, [business_uploads], card_type="business")

        if st.button("💾 Save File", key="apply_current_uploads_business", width='stretch'):
            if not business_uploads:
                st.warning("Upload at least one business file before applying.")
            elif any(not result[1]["valid"] for result in business_validation):
                st.error("Fix invalid business files before applying.")
            else:
                for uploaded_file, _ in business_validation:
                    manager.save_uploaded_file(
                        uploaded_file=uploaded_file,
                        card_type="business",
                        replace_overlapping_years=replace_overlap_business,
                    )
                _reload_processor_data()
                _reset_uploader("current_csv_uploads_business")
                st.success("Business current-year uploads applied.")
                st.rerun()

    with st.expander("🧾All CSV files"):
        personal_tab, business_tab = st.tabs(["Personal", "Business"])

        with personal_tab:
            _render_csv_inventory_panel(manager, "personal")

        with business_tab:
            _render_csv_inventory_panel(manager, "business")


@st.dialog("📁 CSV Management")
def _show_csv_management_modal():
    """Render CSV management inside a modal dialog."""
    _render_csv_management_content()
    if st.button("Close", key="close_csv_management_modal", width='stretch'):
        st.session_state.show_csv_management_modal = False
        st.rerun()

def run():
    """Render the Hyatt Nights page."""
    _load_custom_css()
    ensure_app_session_state_initialized()
    _refresh_processor_if_csvs_changed()

    st.title("🏨 Hyatt Nights")
    st.markdown("Track your Hyatt nights, bonus night earnings, and elite status nights.")
    
    # ========================================================================
    # OVERALL / ELITE NIGHTS SECTION
    # ========================================================================
    st.subheader("Summary")

    # Get all calculated data from service
    summary_service = st.session_state.summary_service
    nights_summary = summary_service.calculate_nights_summary(reference_date=date.today())

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

    if "show_csv_management_modal" not in st.session_state:
        st.session_state.show_csv_management_modal = False

    if st.button("📁 Manage CSV Files", key="open_csv_management_modal", width='stretch'):
        st.session_state.show_csv_management_modal = True

    if st.session_state.show_csv_management_modal:
        _show_csv_management_modal()
        
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
    
    hyatt_card_config = st.session_state.get("hyatt_card_config", {})
    personal_endings = "/".join(hyatt_card_config.get("personal", {}).get("card_endings", []))
    business_endings = "/".join(hyatt_card_config.get("business", {}).get("card_endings", []))

    # ========================================================================
    # PERSONAL CARD SECTION
    # ========================================================================
    personal_header = "💳 Personal Card"
    if personal_endings:
        personal_header = f"💳 Personal Card (Chase ending {personal_endings})"
    st.subheader(personal_header)

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
    business_header = "💳 Business Card"
    if business_endings:
        business_header = f"💳 Business Card (Chase ending {business_endings})"
    st.subheader(business_header)

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
