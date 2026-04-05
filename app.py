import streamlit as st
from benefits.card_processor import CardProcessor
from benefits.benefits_calculator import BenefitsCalculator
from bilt.bilt_cash_calculator import BiltCashCalculator
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


@st.cache_resource
def _load_custom_css():
    """Load app-wide custom CSS."""
    css_file = Path(__file__).parent / "styles" / "app.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


_load_custom_css()

# Configuration file paths
CONFIG_PATH = Path("benefits_config.yaml")
EXAMPLE_CONFIG_PATH = Path("benefits_config_example.yaml")


def load_hyatt_card_config(config_path: Path = CONFIG_PATH):
    """Load Hyatt tracker card metadata from config."""
    if not config_path.exists():
        raise ValueError("Configuration file not found")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    hyatt_cards = config.get("hyatt_cards", {})
    if not isinstance(hyatt_cards, dict):
        raise ValueError("Invalid config: missing 'hyatt_cards' section")

    parsed = {}

    for card_type in ("personal", "business"):
        card_settings = hyatt_cards.get(card_type, {})
        if not isinstance(card_settings, dict):
            raise ValueError(f"Invalid config: missing 'hyatt_cards.{card_type}' section")

        folder = card_settings.get("folder")
        if not isinstance(folder, str) or not folder.strip():
            raise ValueError(f"Invalid config: 'hyatt_cards.{card_type}.folder' is required")

        endings = card_settings.get("card_endings")
        if not isinstance(endings, list):
            raise ValueError(f"Invalid config: 'hyatt_cards.{card_type}.card_endings' must be a list")

        cleaned_endings = [str(ending).strip() for ending in endings if str(ending).strip()]
        if not cleaned_endings:
            raise ValueError(f"Invalid config: 'hyatt_cards.{card_type}.card_endings' must contain at least one value")

        parsed[card_type] = {
            "folder": folder.strip(),
            "card_endings": cleaned_endings,
        }

    return parsed


def validate_config(config_content):
    """Validate the uploaded configuration file."""
    try:
        config = yaml.safe_load(config_content)
        
        # Check basic structure
        if not isinstance(config, dict) or "cards" not in config:
            return False, "Invalid config structure: missing 'cards' section"
        
        if not isinstance(config["cards"], dict):
            return False, "Invalid config structure: 'cards' must be a dictionary"

        hyatt_cards = config.get("hyatt_cards")
        if not isinstance(hyatt_cards, dict):
            return False, "Invalid config structure: missing 'hyatt_cards' section"

        for card_type in ("personal", "business"):
            card_settings = hyatt_cards.get(card_type)
            if not isinstance(card_settings, dict):
                return False, f"Invalid config structure: missing 'hyatt_cards.{card_type}' section"

            folder = card_settings.get("folder")
            if not isinstance(folder, str) or not folder.strip():
                return False, f"Invalid config structure: 'hyatt_cards.{card_type}.folder' is required"

            endings = card_settings.get("card_endings")
            if not isinstance(endings, list):
                return False, f"Invalid config structure: 'hyatt_cards.{card_type}.card_endings' must be a list"

            cleaned_endings = [str(ending).strip() for ending in endings if str(ending).strip()]
            if not cleaned_endings:
                return False, f"Invalid config structure: 'hyatt_cards.{card_type}.card_endings' must have at least one entry"
        
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
    hyatt_card_config = load_hyatt_card_config()

    processor = CardProcessor(
        personal_folder=hyatt_card_config["personal"]["folder"],
        business_folder=hyatt_card_config["business"]["folder"],
    )
    processor.process_personal_card()
    processor.process_business_card()

    calculator = BenefitsCalculator(
        config_path="benefits_config.yaml",
        state_path="benefits_state.json"
    )
    stays_manager = StaysManager(state_path="stays_state.json")
    summary_service = HyattSummaryService(processor, calculator, stays_manager)
    bilt_calculator = BiltCashCalculator()
    return (
        processor,
        calculator,
        stays_manager,
        summary_service,
        bilt_calculator,
        hyatt_card_config,
    )

try:
    processor, calculator, stays_manager, summary_service, bilt_calculator, hyatt_card_config = load_data()
except ValueError as exc:
    st.error(f"❌ {exc}")
    st.info("Please update benefits_config.yaml with required hyatt_cards settings.")
    st.stop()

# Store in session state for access by page modules
st.session_state.processor = processor
st.session_state.calculator = calculator
st.session_state.stays_manager = stays_manager
st.session_state.summary_service = summary_service
st.session_state.bilt_calculator = bilt_calculator
st.session_state.hyatt_card_config = hyatt_card_config

# Define navigation pages
pages = [
    st.Page("pages/1_benefits_tracker.py", title="Benefits Tracker", icon="💳"),
    st.Page("pages/2_hyatt_nights.py", title="Hyatt Nights", icon="🏨"),
    st.Page("pages/3_bilt_cash.py", title="Bilt Cash", icon="🏠"),
]

# Navigation
navigation = st.navigation(pages)
navigation.run()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Credit Card Tracker • Last updated: Today"
    "</div>",
    unsafe_allow_html=True
)
