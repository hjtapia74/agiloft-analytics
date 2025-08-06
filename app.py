"""
Agiloft CLM Analytics Dashboard with Authentication

Main application entry point with modular architecture and user authentication
"""

import streamlit as st
import logging
from pathlib import Path

# Import our modular components
from config.settings import AppConfig
from database.db_manager import DatabaseManager
from ui.pages import status_page, customer_page, country_page
from utils.logging_config import setup_logging
from utils.exceptions import DatabaseConnectionError

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize configuration
config = AppConfig()

def check_authentication():
    """Check if user is authenticated and handle login flow"""
    if not st.user.is_logged_in:
        # Set page config for login page
        st.set_page_config(
            page_title="CLM Analytics - Login",
            layout="centered"
        )
        
        # Login page styling
        st.markdown("""
        <style>
        .main-header {
            text-align: center;
            padding: 2rem 0;
            color: #253A5B;
        }
        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 2rem 0;
        }
        .feature-list {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown('<h1 class="main-header">Agiloft CLM Analytics</h1>', unsafe_allow_html=True)
        
        # Login container
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            st.markdown("### Welcome to CLM Analytics Dashboard")
            st.markdown("**Secure access to contract lifecycle management insights**")
            
            # Login button
            if st.button("Login with Google", use_container_width=True, type="primary"):
                st.login()
            
            # Features overview
            st.markdown('<div class="feature-list">', unsafe_allow_html=True)
            st.markdown("**Dashboard Features:**")
            st.markdown("""
            - **Contract Status Analysis** - Track contract values by status and manager
            - **Customer Performance** - Analyze contract trends by customer over time  
            - **Geographic Distribution** - View contract distribution by country/region
            - **Advanced Filtering** - Filter by date ranges, amounts, and categories
            - **Data Export** - Export analysis results to CSV/Excel
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer info
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9em;">
        Secure authentication required • Contact your administrator for access
        </div>
        """, unsafe_allow_html=True)
        
        st.stop()  # Stop execution if not logged in

def apply_sidebar_styling():
    """Apply custom CSS for sidebar text color override - call AFTER set_page_config"""
    st.markdown("""
    <style>
    /* Override sidebar text color for labels and headings only, NOT input fields */
    
    /* Sidebar headings and text content */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6 {
        color: white !important;
    }
    
    /* Sidebar markdown content (paragraphs, spans) */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] .stMarkdown div {
        color: white !important;
    }
    
    /* Form labels specifically (but not input values) */
    [data-testid="stSidebar"] .stSelectbox > label,
    [data-testid="stSidebar"] .stMultiSelect > label,
    [data-testid="stSidebar"] .stSlider > label,
    [data-testid="stSidebar"] .stTextInput > label,
    [data-testid="stSidebar"] .stNumberInput > label,
    [data-testid="stSidebar"] .stCheckbox > label,
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
    }
    
    /* Widget labels with data-testid */
    [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
        color: white !important;
    }
    
    /* Multiple approaches for expander headers - covers different Streamlit versions */
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .streamlit-expanderHeader p {
        color: white !important;
    }
    
    /* Alternative expander header selectors */
    [data-testid="stSidebar"] summary {
        color: white !important;
    }
    
    [data-testid="stSidebar"] details > summary {
        color: white !important;
    }
    
    /* Expander header using button-like elements */
    [data-testid="stSidebar"] button[kind="expander"] {
        color: white !important;
    }
    
    /* Target expander content directly */
    [data-testid="stSidebar"] .streamlit-expander {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .streamlit-expander > summary {
        color: white !important;
    }
    
    /* Modern Streamlit expander selectors using emotion cache classes */
    [data-testid="stSidebar"] [class*="st-emotion-cache"] summary {
        color: white !important;
    }
    
    [data-testid="stSidebar"] [class*="st-emotion-cache"] button[role="button"] {
        color: white !important;
    }
    
    /* Universal expander text styling */
    [data-testid="stSidebar"] details {
        color: white !important;
    }
    
    [data-testid="stSidebar"] details summary {
        color: white !important;
    }
    
    [data-testid="stSidebar"] details summary * {
        color: white !important;
    }
    
    /* Alert messages */
    [data-testid="stSidebar"] .stAlert,
    [data-testid="stSidebar"] .stInfo,
    [data-testid="stSidebar"] .stSuccess,
    [data-testid="stSidebar"] .stWarning,
    [data-testid="stSidebar"] .stError {
        color: white !important;
    }
    
    /* Radio button and checkbox option text */
    [data-testid="stSidebar"] .stRadio > div > div > div > label,
    [data-testid="stSidebar"] .stCheckbox > div > div > div > label {
        color: white !important;
    }
    
    /* PRESERVE original colors for input fields and buttons */
    
    /* Keep input field text dark for readability */
    [data-testid="stSidebar"] input {
        color: #000000 !important;
        background-color: white !important;
    }
    
    /* Keep select dropdown text dark */
    [data-testid="stSidebar"] .stSelectbox select {
        color: #000000 !important;
    }
    
    /* Keep multiselect text dark */
    [data-testid="stSidebar"] .stMultiSelect input {
        color: #000000 !important;
    }
    
    /* Keep button styling as intended (white background, dark text) */
    [data-testid="stSidebar"] .stButton button {
        background-color: white !important;
        color: #253A5B !important;
        text-align: left !important;
        border: 2px solid #253A5B !important;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #253A5B !important;
        color: white !important;
    }
    
    /* Keep slider values readable */
    [data-testid="stSidebar"] .stSlider input {
        color: #000000 !important;
    }
    
    /* User info styling */
    .user-info-container {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .user-info-container .user-name {
        font-weight: bold;
        color: white !important;
        font-size: 1.1em;
    }
    
    .user-info-container .user-email {
        color: rgba(255, 255, 255, 0.8) !important;
        font-size: 0.9em;
    }
    
    /* Logout button styling */
    .logout-button button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
    }
    
    .logout-button button:hover {
        background-color: #ff3333 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_app():
    """Initialize the Streamlit application with proper configuration"""
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply sidebar styling immediately after set_page_config
    apply_sidebar_styling()
    
    # Set up logo
    st.logo(
        config.LOGO_URL_LARGE,
        link=config.LOGO_URL_LARGE,
    )

def render_user_info():
    """Render user information and logout button in sidebar"""
    with st.sidebar:
        st.markdown("---")
        
        # User info container
        st.markdown("""
        <div class="user-info-container">
            <div class="user-name">{}</div>
            <div class="user-email">{}</div>
        </div>
        """.format(
            st.user.name if hasattr(st.user, 'name') and st.user.name else "User",
            st.user.email if hasattr(st.user, 'email') and st.user.email else "No email"
        ), unsafe_allow_html=True)
        
        # Logout button
        st.markdown('<div class="logout-button">', unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            logger.info(f"User {getattr(st.user, 'email', 'unknown')} logged out")
            st.logout()
        st.markdown('</div>', unsafe_allow_html=True)

def check_database_connection():
    """Check database connection and handle errors gracefully"""
    try:
        db_manager = DatabaseManager()
        if not db_manager.test_connection():
            st.error("Database connection failed. Please check your configuration.")
            st.stop()
        return db_manager
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {str(e)}")
        st.error(f"Database connection error: {str(e)}")
        st.stop()
    except Exception as e:
        logger.error(f"Unexpected error during database connection: {str(e)}")
        st.error("An unexpected error occurred. Please try again.")
        st.stop()

def main():
    """Main application function with authentication"""
    try:
        # Check authentication first - this will stop execution if not logged in
        check_authentication()
        
        # Log successful authentication
        logger.info(f"User {getattr(st.user, 'email', 'unknown')} accessed the application")
        
        # Initialize the app (user is authenticated at this point)
        initialize_app()
        
        # Check database connection
        db_manager = check_database_connection()
        
        # Store database manager in session state for access by pages
        st.session_state.db_manager = db_manager
        
        # Render user info in sidebar
        render_user_info()
        
        
        # Define pages
        pages = {
            "Contracts by Status": status_page.StatusPage(),
            "Contracts by Customer": customer_page.CustomerPage(),
            "Contracts by Country": country_page.CountryPage()
        }
        
        # Create navigation with bigger label
        page_names = list(pages.keys())
        
        # Use st.markdown to create a custom H2 label - PRESERVE ORIGINAL NAVIGATION
        st.sidebar.markdown("## Select Page")
        selected_page = st.sidebar.selectbox(
            "Select Page",  # This will be hidden
            page_names,
            label_visibility="collapsed"  # Hide the default label
        )
        
        # Render selected page
        if selected_page in pages:
            logger.info(f"User {getattr(st.user, 'email', 'unknown')} accessed page: {selected_page}")
            pages[selected_page].render()
        else:
            st.error("Page not found!")
            logger.error(f"User {getattr(st.user, 'email', 'unknown')} tried to access non-existent page: {selected_page}")
            
    except Exception as e:
        logger.error(f"Application error for user {getattr(st.user, 'email', 'unknown')}: {str(e)}")
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
