import streamlit as st
from benefits.card_processor import CardProcessor
from benefits.benefits_calculator import BenefitsCalculator
from hyatt.stays_manager import StaysManager
from hyatt.hyatt_summary_service import HyattSummaryService
from pathlib import Path
import yaml

# Configure page
st.set_page_config(
    page_title="Credit Card Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to make all toggles green when active
st.markdown("""
    <style>
    /* Make all toggles green when checked/active */
    .stCheckbox input[type="checkbox"]:checked + div {
        background-color: #00cc00 !important;
    }
    /* Target the visual toggle element when checked */
    .stCheckbox input[type="checkbox"]:checked ~ div div[class*="st-"] {
        background-color: #00cc00 !important;
    }
    /* Target the inner toggle circle container */
    label[data-baseweb="checkbox"]:has(input:checked) > div:first-child {
        background-color: #00cc00 !important;
        border-color: #00cc00 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Configuration file paths
CONFIG_PATH = Path("benefits_config.yaml")
EXAMPLE_CONFIG_PATH = Path("benefits_config_example.yaml")


def validate_config(config_content):
    """Validate the uploaded configuration file."""
    try:
        config = yaml.safe_load(config_content)
        
        # Check basic structure
        if not isinstance(config, dict) or "cards" not in config:
            return False, "Invalid config structure: missing 'cards' section"
        
        if not isinstance(config["cards"], dict):
            return False, "Invalid config structure: 'cards' must be a dictionary"
        
        # Validate each card has required fields
        for card_id, card_config in config["cards"].items():
            required_fields = ["display_name", "year", "annual_fee", "renewal_month", "renewal_day", "benefits"]
            for field in required_fields:
                if field not in card_config:
                    return False, f"Card '{card_id}' is missing required field: {field}"
            
            # Validate benefits structure
            if not isinstance(card_config["benefits"], list):
                return False, f"Card '{card_id}': benefits must be a list"
            
            for i, benefit in enumerate(card_config["benefits"]):
                required_benefit_fields = ["id", "category", "amount", "frequency", "renewal_type"]
                for field in required_benefit_fields:
                    if field not in benefit:
                        return False, f"Card '{card_id}', benefit {i}: missing required field '{field}'"
        
        return True, "Configuration is valid"
    except yaml.YAMLError as e:
        return False, f"YAML parsing error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def show_config_setup():
    """Show configuration setup screen."""
    st.title("⚙️ Configuration Setup")
    st.markdown("---")
    
    st.warning("⚠️ Configuration file `benefits_config.yaml` not found!")
    
    st.markdown("""
    ### Welcome to Credit Card Tracker!
    
    To get started, you need to set up your benefits configuration file. This file contains information about your credit cards and their benefits.
    
    **Follow these steps:**
    1. Download the example configuration file below
    2. Edit it with your credit card details
    3. Upload the completed file
    """)
    
    st.markdown("---")
    
    # Step 1: Download example
    st.subheader("📥 Step 1: Download Example Configuration")
    
    if EXAMPLE_CONFIG_PATH.exists():
        with open(EXAMPLE_CONFIG_PATH, "r") as f:
            example_content = f.read()
        
        st.download_button(
            label="⬇️ Download benefits_config_example.yaml",
            data=example_content,
            file_name="benefits_config_example.yaml",
            mime="application/x-yaml",
            help="Download this example file and edit it with your credit card details"
        )
        
        with st.expander("👀 Preview Example Configuration"):
            st.code(example_content, language="yaml")
    else:
        st.error("Example configuration file not found. Please check your installation.")
        return
    
    st.markdown("---")
    
    # Step 2: Upload completed config
    st.subheader("📤 Step 2: Upload Your Configuration")
    
    uploaded_file = st.file_uploader(
        "Upload your completed benefits_config.yaml",
        type=["yaml", "yml"],
        help="Upload the configuration file you edited with your credit card details"
    )
    
    if uploaded_file is not None:
        # Read and validate the uploaded file
        config_content = uploaded_file.read()
        
        is_valid, message = validate_config(config_content)
        
        if is_valid:
            st.success(f"✅ {message}")
            
            # Show a preview
            with st.expander("👀 Preview Your Configuration"):
                st.code(config_content.decode("utf-8"), language="yaml")
            
            # Button to save the configuration
            if st.button("💾 Save Configuration and Start App", type="primary"):
                try:
                    # Save the configuration file
                    with open(CONFIG_PATH, "wb") as f:
                        f.write(config_content)
                    
                    st.success("✅ Configuration saved successfully!")
                    st.info("🔄 Reloading app...")
                    
                    # Force a rerun to reload the app with the new config
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving configuration: {str(e)}")
        else:
            st.error(f"❌ {message}")
            st.info("Please fix the errors and upload the file again.")


# Check if configuration exists
if not CONFIG_PATH.exists():
    show_config_setup()
    st.stop()

# Initialize session state and data
@st.cache_resource
def load_data():
    """Load card processor, benefits calculator, stays manager, and summary service."""
    processor = CardProcessor()
    processor.process_personal_card()
    processor.process_business_card()

    calculator = BenefitsCalculator(
        config_path="benefits_config.yaml",
        state_path="benefits_state.json"
    )
    stays_manager = StaysManager(state_path="stays_state.json")
    summary_service = HyattSummaryService(processor, calculator, stays_manager)
    return processor, calculator, stays_manager, summary_service


processor, calculator, stays_manager, summary_service = load_data()

# Store in session state for access by page modules
st.session_state.processor = processor
st.session_state.calculator = calculator
st.session_state.stays_manager = stays_manager
st.session_state.summary_service = summary_service

# Define navigation pages
pages = [
    st.Page("pages/1_benefits_tracker.py", title="Benefits Tracker", icon="💳"),
    st.Page("pages/2_hyatt_nights.py", title="Hyatt Nights", icon="🏨"),
]

# Navigation
navigation = st.navigation(pages)
navigation.run()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Credit Card Tracker • Last updated: Today • Data auto-loads from CSV files"
    "</div>",
    unsafe_allow_html=True
)
