"""
全局设置页面

允许用户配置数据源等全局设置
"""
import sys
from pathlib import Path

# Add project root to path for importing chan.py core modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from App.config import (
    get_data_source,
    set_data_source,
    get_data_source_display_name,
    load_config,
    save_config
)


def main():
    st.set_page_config(
        page_title="Settings",
        page_icon="⚙️",
        layout="wide"
    )
    
    st.title("⚙️ Global Settings")
    st.markdown("---")
    
    # Data Source Configuration
    st.subheader("📊 Data Source Configuration")
    st.markdown("Configure the data source for Chan theory analysis across all pages.")
    
    # Get current data source
    current_source = get_data_source()
    current_display = get_data_source_display_name()
    
    st.info(f"**Current Data Source:** {current_display}")
    
    # Data source selection
    data_source_options = {
        "BAO_STOCK": "BaoStock (Free, requires internet connection)",
        "QMTAPI": "QMT API (Custom data source)"
    }
    
    # Determine current selection index
    current_is_qmt = "QMTAPI" in str(current_source) or "custom:QMTAPI" in str(current_source)
    default_index = 1 if current_is_qmt else 0
    
    selected_source = st.radio(
        "Select Data Source",
        options=list(data_source_options.keys()),
        index=default_index,
        help="Choose the data source for fetching stock data"
    )
    
    # Display description
    st.markdown(f"**Description:** {data_source_options[selected_source]}")
    
    # Save button
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        set_data_source(selected_source)
        st.success(f"Data source changed to {data_source_options[selected_source]}")
        st.rerun()
    
    st.markdown("---")
    
    # Additional information
    with st.expander("ℹ️ About Data Sources", expanded=False):
        st.markdown("""
        **BaoStock:**
        - Free data source for A-share market
        - Requires internet connection
        - Supports daily, weekly, monthly, and minute-level data
        
        **QMT API:**
        - Custom data source implementation
        - Requires QMT platform setup
        - Supports real-time and historical data
        - Format: `custom:QMTAPI.CQMTAPI`
        """)
    
    # Show current configuration
    with st.expander("📋 Current Configuration", expanded=False):
        config = load_config()
        st.json(config)


if __name__ == "__main__":
    main()
