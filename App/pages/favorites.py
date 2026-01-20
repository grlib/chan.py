import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path for importing chan.py core modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PyEchartsPlotDriver import CPyEchartsPlotDriver
from App.config import get_data_source_for_chan

# Data directory and file paths
DATA_DIR = "../data"  # Relative to App directory
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.csv")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_favorites():
    """Load favorites data"""
    if os.path.exists(FAVORITES_FILE):
        return pd.read_csv(FAVORITES_FILE)
    else:
        return pd.DataFrame(columns=["code", "name", "added_date", "note"])

def save_favorites(df):
    """Save favorites data"""
    df.to_csv(FAVORITES_FILE, index=False)

def get_chan_config() -> CChanConfig:
    """Get Chan theory analysis configuration"""
    return CChanConfig({
        "bi_strict": True,
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": "1,2,3a,1p,2s,3b",
        "print_warning": False,
        "zs_algo": "normal",
    })

def analyze_stock(code: str, begin_time: str, end_time: str = None, kl_type: KL_TYPE = KL_TYPE.K_DAY) -> CChan:
    """Analyze a single stock"""
    # Convert code to string if it's not already
    code = str(code)
    
    if end_time is None or end_time == "":
        end_time = datetime.now().strftime("%Y-%m-%d")
    
    # Process stock code format
    if not code.startswith(('sh.', 'sz.')):
        # Determine Shanghai or Shenzhen: 600/601/603/605/688 prefix is Shanghai, 000/001/002/300 prefix is Shenzhen
        if code.startswith(('600', '601', '603', '605', '688')):
            code = f"sh.{code}"
        else:
            code = f"sz.{code}"
    
    config = get_chan_config()
    data_src = get_data_source_for_chan()
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=[kl_type],
        config=config,
        autype=AUTYPE.QFQ,
    )
    return chan

def plot_chart(chan: CChan, kl_type: KL_TYPE = KL_TYPE.K_DAY):
    """Plot Chan theory analysis chart"""
    try:
        plot_driver = CPyEchartsPlotDriver(chan)
        level_name = plot_driver.LEVEL_NAMES.get(kl_type, str(kl_type))
        
        # Generate temporary HTML file
        import tempfile
        temp_file = os.path.join(tempfile.gettempdir(), f"chan_{chan.code}_{level_name}_{datetime.now().timestamp()}.html")
        
        chart = plot_driver.plot_kline_with_bi_seg_zs(kl_type, temp_file)
        
        # Read generated HTML file and display in Streamlit
        if os.path.exists(temp_file):
            with open(temp_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # Adjust HTML to fit Streamlit container
            html_content = html_content.replace('width="1400px"', 'width="100%"')
            html_content = html_content.replace('width="800px"', 'width="100%"')
            st.components.v1.html(html_content, height=800, scrolling=True)
            # Clean up temporary file
            try:
                os.remove(temp_file)
            except:
                pass
        else:
            # If file doesn't exist, try using render_embed
            try:
                html_content = chart.render_embed()
                st.components.v1.html(html_content, height=800, scrolling=True)
            except:
                st.error("Failed to generate chart, please check if data is complete")
    except Exception as e:
        st.error(f"Failed to plot chart: {e}")
        import traceback
        st.code(traceback.format_exc())

# Page title
st.title("⭐ Favorites Management")

# Load data
favorites = load_favorites()

# Display current favorites
st.subheader("📋 Current Favorites")
if favorites.empty:
    st.info("No favorites yet, please add stocks")
else:
    # Display table
    st.markdown("💡 **Tip: Select a stock from the dropdown below or click on a table row to view Chan theory analysis**")
    
    # Use dataframe display, try to get selection
    selected_df = st.dataframe(
        favorites,
        use_container_width=True,
        hide_index=False,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # Try to get selected row from selection
    selected_index = None
    if selected_df and isinstance(selected_df, dict):
        if 'selection' in selected_df:
            selection = selected_df['selection']
            if 'rows' in selection and selection['rows']:
                selected_index = selection['rows'][0]
                # Save to session_state
                st.session_state['selected_stock_index'] = selected_index
    
    # If dataframe selection is not available, use selectbox as alternative
    if selected_index is None:
        stock_options = [f"{idx}: {row['code']} - {row['name']}" for idx, (_, row) in enumerate(favorites.iterrows())]
        selected_option = st.selectbox(
            "Select stock to view chart",
            options=[""] + stock_options,
            index=0,
            key="stock_viewer"
        )
        if selected_option and selected_option != "":
            selected_index = int(selected_option.split(":")[0])
            st.session_state['selected_stock_index'] = selected_index
    
    # Check session_state
    if selected_index is None:
        selected_index = st.session_state.get('selected_stock_index', None)
    
    # If there's a selected row, display chart on main page (not in dialog)
    if selected_index is not None and selected_index < len(favorites):
        selected_row = favorites.iloc[selected_index]
        selected_code = str(selected_row['code'])  # Ensure it's a string
        selected_name = str(selected_row['name'])  # Ensure it's a string
        
        st.markdown("---")
        st.subheader(f"📈 {selected_code} {selected_name} - Chan Theory Analysis")
        
        # Level options
        kl_level_options = {
            "5 Minutes": KL_TYPE.K_5M,
            "30 Minutes": KL_TYPE.K_30M,
            "Daily": KL_TYPE.K_DAY,
            "Weekly": KL_TYPE.K_WEEK,
            "Monthly": KL_TYPE.K_MON,
            "Quarterly": KL_TYPE.K_QUARTER,
            "Yearly": KL_TYPE.K_YEAR,
        }
        
        # Date range selection (outside tabs, shared by all levels)
        st.markdown("### 📅 Date Range")
        col1, col2 = st.columns(2)
        with col1:
            # Get or set default value from session_state
            date_key_begin = f"begin_date_{selected_code}"
            if date_key_begin not in st.session_state:
                st.session_state[date_key_begin] = datetime.now() - timedelta(days=365)
            begin_date = st.date_input(
                "Start Date",
                value=st.session_state[date_key_begin],
                key=date_key_begin
            )
            # Note: st.date_input automatically updates session_state, no need to manually assign
        with col2:
            date_key_end = f"end_date_{selected_code}"
            end_date = st.date_input(
                "End Date",
                value=st.session_state.get(date_key_end, None),
                key=date_key_end,
                help="Leave empty to use current date"
            )
            # Note: st.date_input automatically updates session_state, no need to manually assign
        
        begin_time = begin_date.strftime("%Y-%m-%d")
        end_time = end_date.strftime("%Y-%m-%d") if end_date else None
        
        # Use tabs to display different levels
        tab_names = list(kl_level_options.keys())
        tabs = st.tabs(tab_names)
        
        for idx, (level_name, kl_type) in enumerate(kl_level_options.items()):
            with tabs[idx]:
                # Generate analysis key
                analysis_key = f"chan_{selected_code}_{level_name}_{begin_time}_{end_time or 'current'}"
                
                # Check if already analyzed
                if analysis_key in st.session_state:
                    chan = st.session_state[analysis_key]
                    kl_type_stored = st.session_state.get(f"kl_type_{analysis_key}", kl_type)
                    
                    plot_driver_temp = CPyEchartsPlotDriver(chan)
                    level_name_display = plot_driver_temp.LEVEL_NAMES.get(kl_type_stored, level_name)
                    st.info(f"**Level**: {level_name_display} | **Date Range**: {begin_time} to {end_time or 'Current'}")
                    
                    plot_chart(chan, kl_type_stored)
                else:
                    # Display analyze button
                    if st.button(f"🔍 Analyze {level_name}", type="primary", use_container_width=True, key=f"analyze_{selected_code}_{level_name}"):
                        with st.spinner(f"Analyzing {selected_code} - {level_name}..."):
                            try:
                                chan = analyze_stock(selected_code, begin_time, end_time, kl_type)
                                st.session_state[analysis_key] = chan
                                st.session_state[f"kl_type_{analysis_key}"] = kl_type
                                st.success(f"Analysis completed: {selected_code} - {level_name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                    else:
                        st.info(f"👆 Click 「Analyze {level_name}」 button to view Chan theory chart")

# Add stock - use dialog
st.subheader("➕ Add Stock")

# Define dialog function for adding stock
@st.dialog("➕ Add Stock", width="medium")
def show_add_stock_form():
    with st.form("add_stock_form"):
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Stock Code", placeholder="e.g., 000001", key="add_code")
        with col2:
            name = st.text_input("Stock Name", placeholder="e.g., Ping An Bank", key="add_name")

        note = st.text_area("Note", placeholder="Optional note", key="add_note")

        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("Add", type="primary", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if submitted:
            if code and name:
                # Reload favorites to ensure latest data
                current_favorites = load_favorites()
                # Check if already exists
                if code in current_favorites["code"].values:
                    st.error(f"Stock {code} is already in favorites")
                else:
                    new_row = {
                        "code": code,
                        "name": name,
                        "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "note": note
                    }
                    current_favorites = pd.concat([current_favorites, pd.DataFrame([new_row])], ignore_index=True)
                    save_favorites(current_favorites)
                    st.success(f"Successfully added stock: {name} ({code})")
                    st.rerun()
            else:
                st.error("Please enter stock code and name")
        
        if cancelled:
            st.rerun()

# Add stock button
if st.button("➕ Add Stock", type="primary", use_container_width=True):
    show_add_stock_form()

# 删除股票
if not favorites.empty:
    st.subheader("🗑️ Delete Stocks")
    to_delete = st.multiselect(
        "Select stocks to delete",
        options=favorites["code"].tolist(),
        format_func=lambda x: f"{x} - {favorites[favorites['code']==x]['name'].iloc[0]}"
    )

    if st.button("Delete Selected Stocks", use_container_width=True):
        if to_delete:
            favorites = favorites[~favorites["code"].isin(to_delete)]
            save_favorites(favorites)
            st.success(f"Successfully deleted {len(to_delete)} stocks")
            st.rerun()
        else:
            st.warning("Please select stocks to delete")