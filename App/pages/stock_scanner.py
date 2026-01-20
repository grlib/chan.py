"""
A-Share Stock Buy Point Scanner - Streamlit Version - Powered by chan.py

Features:
    - Batch scan A-share market to identify stocks with recent buy points
    - Support single stock analysis with Chan theory visualization
    - Display K-line, Bi, Segment, Zhongshu, Buy/Sell points, MACD, etc.

Data Source:
    - Use baostock to get A-share stock list and historical K-line data

Filter Rules:
    - Exclude ST stocks, STAR Market (688), Beijing Stock Exchange, B shares
    - Exclude suspended stocks and new listings

Dependencies:
    - streamlit: Web UI framework
    - pyecharts: Chart visualization
    - baostock: A-share data API
    - chan.py: Chan theory analysis core library

Usage:
    streamlit run App/stock_scanner.py
"""
import sys
from pathlib import Path

# Add project root to path for importing chan.py core modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import baostock as bs
import os
import json
from typing import Dict, Optional, List

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PyEchartsPlotDriver import CPyEchartsPlotDriver
from App.config import get_data_source_for_chan


# Cache configuration
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
STOCK_LIST_CACHE_DIR = CACHE_DIR / "stock_list"
ANALYSIS_CACHE_DIR = CACHE_DIR / "analysis"


def get_cache_path(cache_type: str, date_str: str, filename: str = None) -> Path:
    """
    Get cache file path
    
    Args:
        cache_type: Type of cache ('stock_list' or 'analysis')
        date_str: Date string in YYYY-MM-DD format
        filename: Optional filename
    
    Returns:
        Path: Cache file path
    """
    if cache_type == 'stock_list':
        cache_path = STOCK_LIST_CACHE_DIR
    elif cache_type == 'analysis':
        cache_path = ANALYSIS_CACHE_DIR / date_str
    else:
        raise ValueError(f"Unknown cache type: {cache_type}")
    
    cache_path.mkdir(parents=True, exist_ok=True)
    
    if filename:
        return cache_path / filename
    return cache_path


def load_stock_list_cache(date_str: str = None) -> Optional[pd.DataFrame]:
    """
    Load stock list from cache
    
    Args:
        date_str: Date string in YYYY-MM-DD format, None for today
    
    Returns:
        DataFrame if cache exists, None otherwise
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    cache_file = get_cache_path('stock_list', date_str, f"{date_str}.csv")
    
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file, dtype={'code': str})
            print(f"Loaded stock list from cache: {cache_file}")
            return df
        except Exception as e:
            print(f"Failed to load cache: {e}")
            return None
    return None


def save_stock_list_cache(df: pd.DataFrame, date_str: str = None):
    """
    Save stock list to cache
    
    Args:
        df: DataFrame to save
        date_str: Date string in YYYY-MM-DD format, None for today
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    cache_file = get_cache_path('stock_list', date_str, f"{date_str}.csv")
    
    try:
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        print(f"Saved stock list to cache: {cache_file}")
    except Exception as e:
        print(f"Failed to save cache: {e}")


def load_analysis_cache(code: str, date_str: str = None) -> Optional[Dict]:
    """
    Load single stock analysis from cache
    
    Args:
        code: Stock code (pure numeric)
        date_str: Date string in YYYY-MM-DD format, None for today
    
    Returns:
        Dict with 'chan' and 'bsp_list' if cache exists, None otherwise
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    cache_file = get_cache_path('analysis', date_str, f"{code}.json")
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid (same day)
            if cache_data.get('cache_date') == date_str:
                print(f"Loaded analysis cache for {code} from: {cache_file}")
                return cache_data
            else:
                print(f"Cache expired for {code}")
                return None
        except Exception as e:
            print(f"Failed to load analysis cache: {e}")
            return None
    return None


def save_analysis_cache(code: str, chan: CChan, bsp_list: List, date_str: str = None):
    """
    Save single stock analysis to cache
    
    Args:
        code: Stock code (pure numeric)
        chan: CChan object (will be serialized to JSON)
        bsp_list: List of buy/sell points
        date_str: Date string in YYYY-MM-DD format, None for today
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    cache_file = get_cache_path('analysis', date_str, f"{code}.json")
    
    try:
        # Prepare cache data
        buy_points = [bsp for bsp in bsp_list if bsp.is_buy]
        sell_points = [bsp for bsp in bsp_list if not bsp.is_buy]
        
        cache_data = {
            'code': code,
            'full_code': chan.code,
            'cache_date': date_str,
            'buy_points': [
                {
                    'type': bsp.type2str(),
                    'time': str(bsp.klu.time),
                }
                for bsp in buy_points[:20]
            ],
            'sell_points': [
                {
                    'type': bsp.type2str(),
                    'time': str(bsp.klu.time),
                }
                for bsp in sell_points[:20]
            ],
            'total_buy_points': len(buy_points),
            'total_sell_points': len(sell_points),
            # Note: CChan object cannot be easily serialized, so we only cache metadata
            # The actual CChan object needs to be recreated when loading
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved analysis cache for {code} to: {cache_file}")
    except Exception as e:
        print(f"Failed to save analysis cache: {e}")


def get_tradable_stocks():
    """
    Get all tradable A-share stock list (using baostock)

    Filter conditions:
        1. Exclude ST stocks (name contains ST)
        2. Exclude STAR Market (688 prefix)
        3. Exclude Beijing Stock Exchange (8, 43 prefix, bj. prefix)
        4. Exclude B shares (200 prefix Shenzhen B, 900 prefix Shanghai B)
        5. Exclude CDR (920 prefix)
        6. Exclude suspended stocks (tradeStatus != '1')

    Returns:
        pd.DataFrame: Stock list with ['code', 'name'] columns
                      Returns empty DataFrame on failure
    """
    lg = None
    try:
        # Initialize baostock connection
        lg = bs.login()
        if lg.error_code != '0':
            error_msg = f"Baostock login failed: error_code={lg.error_code}, error_msg={lg.error_msg}"
            st.error(error_msg)
            print(error_msg)
            return pd.DataFrame()
        
        # Try to get stock list for current trading day first
        rs = bs.query_hs300_stocks()
        
        if rs is None:
            error_msg = "Failed to get stock list: No response from baostock"
            st.error(error_msg)
            print(error_msg)
            bs.logout()
            return pd.DataFrame()
        
        if not hasattr(rs, 'error_code') or rs.error_code != '0':
            error_msg = f"Failed to get stock list: error_code={rs.error_code if hasattr(rs, 'error_code') else 'Unknown'}, error_msg={rs.error_msg if hasattr(rs, 'error_msg') else 'Unknown error'}"
            st.error(error_msg)
            print(error_msg)
            bs.logout()
            return pd.DataFrame()
        
        # Convert to DataFrame
        stock_list = []
        try:
            while (rs.error_code == '0') and rs.next():
                row_data = rs.get_row_data()
                print(row_data)
                if row_data:
                    stock_list.append(row_data)
        except Exception as e:
            print(f"Error reading stock data: {e}")
            if not stock_list:
                st.error(f"Failed to read stock data: {e}")
                bs.logout()
                return pd.DataFrame()
        
        if not stock_list:
            st.warning("No stock data retrieved. This might be a non-trading day.")
            bs.logout()
            return pd.DataFrame()
        
        df = pd.DataFrame(stock_list, columns=rs.fields)
        
        # Close connection
        bs.logout()
        
        if df.empty:
            st.warning("Stock list is empty after retrieval.")
            return pd.DataFrame()
        
        # Check if required columns exist
        if 'code' not in df.columns or 'code_name' not in df.columns:
            error_msg = f"Missing required columns. Available columns: {df.columns.tolist()}"
            st.error(error_msg)
            print(error_msg)
            return pd.DataFrame()
        
        # baostock returns columns: code, code_name, tradeStatus, etc.
        # Keep only A-shares (sh. and sz. prefix, exclude bj. Beijing Stock Exchange)
        df = df[df['code'].str.startswith(('sh.', 'sz.'))]
        
        if df.empty:
            st.warning("No A-share stocks found after filtering by market prefix.")
            return pd.DataFrame()
        
        # Extract pure numeric code (remove sh./sz. prefix)
        df['code'] = df['code'].str.replace('sh.', '').str.replace('sz.', '')
        df['name'] = df['code_name']
        
        # Filter conditions
        # 1. Exclude ST stocks (name contains ST)
        df = df[~df['name'].str.contains('ST', case=False, na=False)]
        
        # 3. Exclude Beijing Stock Exchange (8, 43 prefix)
        df = df[~df['code'].str.startswith('8')]
        df = df[~df['code'].str.startswith('43')]
        
        # 4. Exclude B shares (200 prefix Shenzhen B, 900 prefix Shanghai B)
        df = df[~df['code'].str.startswith('200')]
        df = df[~df['code'].str.startswith('900')]
        
        # 5. Exclude CDR (920 prefix)
        df = df[~df['code'].str.startswith('920')]
        
        # 6. Exclude suspended stocks (tradeStatus != '1' means normal trading)
        if 'tradeStatus' in df.columns:
            df = df[df['tradeStatus'] == '1']
        
        if df.empty:
            st.warning("No stocks remaining after applying filters.")
            return pd.DataFrame()
        
        # Return result (only code and name, baostock doesn't provide real-time quotes)
        result = df[['code', 'name']].reset_index(drop=True)
        print(f"Successfully retrieved {len(result)} tradable stocks")
        return result
        
    except Exception as e:
        error_msg = f"Exception in get_tradable_stocks: {type(e).__name__}: {str(e)}"
        st.error(error_msg)
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        try:
            if lg:
                bs.logout()
        except:
            pass
        return pd.DataFrame()


def get_chan_config(bi_strict: bool = True) -> CChanConfig:
    """
    Get Chan theory analysis configuration

    Args:
        bi_strict: Whether to enable strict Bi mode

    Returns:
        CChanConfig: Configuration object with Bi strict mode, buy/sell point types, etc.
    """
    return CChanConfig({
        "bi_strict": bi_strict,  # Strict Bi mode
        "trigger_step": False,  # Don't enable step-by-step trigger mode
        "skip_step": 0,
        "divergence_rate": float("inf"),  # Divergence rate
        "bsp2_follow_1": False,  # Type 2 buy/sell points don't follow type 1
        "bsp3_follow_1": False,  # Type 3 buy/sell points don't follow type 1
        "min_zs_cnt": 0,  # Minimum Zhongshu count
        "bs1_peak": False,
        "macd_algo": "peak",  # MACD algorithm
        "bs_type": "1,1p,2,2s,3a,3b",  # Enabled buy/sell point types
        "print_warning": False,
        "zs_algo": "normal",  # Zhongshu algorithm
    })


def analyze_stock(code: str, config: CChanConfig, begin_time: str, end_time: str = None, kl_type: KL_TYPE = KL_TYPE.K_DAY) -> Optional[CChan]:
    """
    Analyze a single stock

    Args:
        code: Stock code (e.g., '000001' or 'sh.600000')
        config: Chan theory configuration
        begin_time: Start date in YYYY-MM-DD format
        end_time: End date in YYYY-MM-DD format, None or empty string for current date
        kl_type: K-line level to analyze

    Returns:
        CChan object, returns None on failure
    """
    try:
        if end_time is None or end_time == "":
            end_time = datetime.now().strftime("%Y-%m-%d")

        # baostock needs sh./sz. prefix, if user inputs pure number, need to determine market
        if not code.startswith(('sh.', 'sz.')):
            # Determine Shanghai or Shenzhen: 600/601/603/605 prefix is Shanghai, 000/001/002/300 prefix is Shenzhen
            if code.startswith(('600', '601', '603', '605', '688')):
                code = f"sh.{code}"
            else:
                code = f"sz.{code}"

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
    except Exception as e:
        st.error(f"Failed to analyze stock {code}: {e}")
        return None


def scan_stocks(stock_list: pd.DataFrame, config: CChanConfig, begin_time: str, end_time: str, recent_days: int = 3, kl_type: KL_TYPE = KL_TYPE.K_DAY):
    """
    Batch scan stocks to find buy points

    Args:
        stock_list: Stock list DataFrame (contains 'code' and 'name' columns)
        config: Chan theory configuration
        begin_time: Start date in YYYY-MM-DD format
        end_time: End date in YYYY-MM-DD format
        recent_days: Number of recent days to look for buy points
        kl_type: K-line level to analyze

    Returns:
        tuple: (results list, success_count, fail_count)
    """
    results = []
    cutoff_date = datetime.now() - timedelta(days=recent_days)

    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(stock_list)
    success_count = 0
    fail_count = 0

    for idx, row in stock_list.iterrows():
        code = row['code']
        name = row['name']
        
        # Update progress
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Scanning progress: {idx + 1}/{total} - {code} {name}")

        try:
            # baostock needs sh./sz. prefix
            if not code.startswith(('sh.', 'sz.')):
                # Determine Shanghai or Shenzhen
                if code.startswith(('600', '601', '603', '605', '688')):
                    full_code = f"sh.{code}"
                else:
                    full_code = f"sz.{code}"
            else:
                full_code = code
            
            data_src = get_data_source_for_chan()
            chan = CChan(
                code=full_code,
                begin_time=begin_time,
                end_time=end_time,
                data_src=data_src,
                lv_list=[kl_type],
                config=config,
                autype=AUTYPE.QFQ,
            )

            # Check if there's data in the last 15 days
            if len(chan[0]) == 0:
                fail_count += 1
                continue

            last_klu = chan[0][-1][-1]
            last_time = last_klu.time
            last_date = datetime(last_time.year, last_time.month, last_time.day)
            if (datetime.now() - last_date).days > 15:
                fail_count += 1
                continue

            success_count += 1

            # Check for buy points (only look for buy points in recent N days)
            bsp_list = chan.get_latest_bsp(number=0)
            buy_points = [
                bsp for bsp in bsp_list
                if bsp.is_buy and datetime(bsp.klu.time.year, bsp.klu.time.month, bsp.klu.time.day) >= cutoff_date
            ]

            if buy_points:
                # Get the latest buy point
                latest_buy = buy_points[0]
                results.append({
                    'code': code,  # Save pure numeric code for display
                    'name': name,
                    'bsp_type': latest_buy.type2str(),
                    'bsp_time': str(latest_buy.klu.time),
                    'chan': chan,
                })
        except Exception as e:
            fail_count += 1
            continue

    progress_bar.empty()
    status_text.empty()
    
    return results, success_count, fail_count


def plot_chart(chan: CChan, kl_type: KL_TYPE = KL_TYPE.K_DAY, save_path: Optional[str] = None):
    """
    Plot Chan theory analysis chart

    Args:
        chan: CChan object
        kl_type: K-line level
        save_path: Optional path to save the chart HTML file
    """
    try:
        plot_driver = CPyEchartsPlotDriver(chan)
        level_name = plot_driver.LEVEL_NAMES.get(kl_type, str(kl_type))
        
        # Generate chart using temporary file path or provided save_path
        import tempfile
        if save_path:
            temp_file = save_path
        else:
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
            # Clean up temporary file only if it's not a save_path
            if not save_path:
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


def save_scan_results(results: List[Dict], stats: Dict):
    """
    Save batch scan results to Result directory organized by date
    Includes CSV results, statistics, and charts for each stock
    
    Args:
        results: List of scan result dictionaries (must contain 'chan' object)
        stats: Statistics dictionary with success/fail/found counts
    
    Returns:
        str: Path to saved directory, or None on failure
    """
    try:
        # Create Result directory if it doesn't exist
        result_dir = Path(__file__).resolve().parent.parent / "Result"
        result_dir.mkdir(exist_ok=True)
        
        # Create date subdirectory (YYYY-MM-DD)
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = result_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Save scan results CSV (include level info)
        df_results = []
        for r in results:
            chan = r.get('chan')
            if chan and chan.lv_list:
                plot_driver_temp = CPyEchartsPlotDriver(chan)
                actual_kl_type = chan.lv_list[0]
                level_name = plot_driver_temp.LEVEL_NAMES.get(actual_kl_type, "DAY")
            else:
                level_name = "DAY"
            
            df_results.append({
                'Code': r['code'],
                'Name': r['name'],
                'Level': level_name,
                'Buy Point Type': r['bsp_type'],
                'Buy Point Time': r['bsp_time']
            })
        
        df_results = pd.DataFrame(df_results)
        
        csv_path = date_dir / "scan_results.csv"
        df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Save statistics JSON
        stats_path = date_dir / "scan_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_date': date_str,
                'total_found': len(results),
                'success_count': stats.get('success', 0),
                'fail_count': stats.get('fail', 0),
                'found_count': stats.get('found', 0)
            }, f, indent=2, ensure_ascii=False)
        
        # Save charts for each stock
        charts_dir = date_dir / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        chart_count = 0
        chart_errors = []
        
        for r in results:
            try:
                code = r['code']
                chan = r.get('chan')
                
                if chan is None:
                    chart_errors.append(f"{code}: No CChan object")
                    continue
                
                # Generate and save chart
                plot_driver = CPyEchartsPlotDriver(chan)
                # Get the actual level used in analysis (from chan.lv_list)
                actual_kl_type = chan.lv_list[0] if chan.lv_list else KL_TYPE.K_DAY
                level_name = plot_driver.LEVEL_NAMES.get(actual_kl_type, "DAY")
                chart_path = charts_dir / f"{code}_{level_name}.html"
                
                plot_driver.plot_kline_with_bi_seg_zs(actual_kl_type, str(chart_path))
                chart_count += 1
                
            except Exception as e:
                error_msg = f"{code}: {str(e)}"
                chart_errors.append(error_msg)
                print(f"Failed to save chart for {code}: {e}")
                continue
        
        # Save chart generation summary
        if chart_errors:
            error_log_path = charts_dir / "chart_errors.log"
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Chart Generation Summary - {date_str}\n")
                f.write(f"Total stocks: {len(results)}\n")
                f.write(f"Charts saved: {chart_count}\n")
                f.write(f"Errors: {len(chart_errors)}\n\n")
                f.write("Error Details:\n")
                for error in chart_errors:
                    f.write(f"{error}\n")
        
        result_info = f"Saved {len(results)} results, {chart_count} charts"
        if chart_errors:
            result_info += f", {len(chart_errors)} errors"
        
        print(result_info)
        return str(date_dir)
        
    except Exception as e:
        st.error(f"Failed to save scan results: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def save_single_stock_analysis(chan: CChan, code: str, bsp_list: List):
    """
    Save single stock analysis results to Result directory organized by date and code
    
    Args:
        chan: CChan object
        code: Stock code (may be pure number or with sh./sz. prefix)
        bsp_list: List of buy/sell points
    
    Returns:
        str: Path to saved directory, or None on failure
    """
    try:
        # Extract pure numeric code for directory name
        pure_code = code.replace('sh.', '').replace('sz.', '')
        
        # Create Result directory if it doesn't exist
        result_dir = Path(__file__).resolve().parent.parent / "Result"
        result_dir.mkdir(exist_ok=True)
        
        # Create date subdirectory (YYYY-MM-DD)
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = result_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Create stock code subdirectory (use pure numeric code)
        stock_dir = date_dir / pure_code
        stock_dir.mkdir(exist_ok=True)
        
        # Save chart HTML (use the actual level from chan object)
        plot_driver = CPyEchartsPlotDriver(chan)
        actual_kl_type = chan.lv_list[0] if chan.lv_list else KL_TYPE.K_DAY
        level_name = plot_driver.LEVEL_NAMES.get(actual_kl_type, "DAY")
        chart_path = stock_dir / f"{pure_code}_{level_name}.html"
        plot_driver.plot_kline_with_bi_seg_zs(actual_kl_type, str(chart_path))
        
        # Save buy/sell points info
        buy_points = [bsp for bsp in bsp_list if bsp.is_buy]
        sell_points = [bsp for bsp in bsp_list if not bsp.is_buy]
        
        bsp_info = {
            'code': pure_code,
            'full_code': chan.code,  # Save full code with prefix
            'analysis_date': date_str,
            'kl_type': level_name,  # Save the K-line level used
            'buy_points': [
                {
                    'type': bsp.type2str(),
                    'time': str(bsp.klu.time),
                    'price': float(bsp.klu.close) if hasattr(bsp.klu, 'close') else None
                }
                for bsp in buy_points[:10]
            ],
            'sell_points': [
                {
                    'type': bsp.type2str(),
                    'time': str(bsp.klu.time),
                    'price': float(bsp.klu.close) if hasattr(bsp.klu, 'close') else None
                }
                for bsp in sell_points[:10]
            ],
            'total_buy_points': len(buy_points),
            'total_sell_points': len(sell_points)
        }
        
        info_path = stock_dir / "analysis_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(bsp_info, f, indent=2, ensure_ascii=False)
        
        return str(stock_dir)
    except Exception as e:
        st.error(f"Failed to save analysis results: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None


# Page configuration
st.set_page_config(
    page_title="A-Share Stock Buy Point Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("📈 A-Share Stock Buy Point Scanner")
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Scan Settings")
    
    bi_strict = st.checkbox("Strict Bi Mode", value=True)
    
    # Time range selection
    st.subheader("Time Range")
    default_start_date = datetime.now() - timedelta(days=365)
    begin_date = st.date_input(
        "Start Date",
        value=default_start_date,
        help="Select the start date for data retrieval"
    )
    end_date = st.date_input(
        "End Date",
        value=None,
        help="Leave empty to use current date, or select a specific end date"
    )
    
    # Convert to string format
    begin_time = begin_date.strftime("%Y-%m-%d")
    end_time = end_date.strftime("%Y-%m-%d") if end_date else datetime.now().strftime("%Y-%m-%d")
    
    # Display selected time range
    if end_date:
        st.info(f"📅 Time Range: {begin_time} to {end_time}")
    else:
        st.info(f"📅 Time Range: {begin_time} to {end_time} (current)")
    
    recent_days = st.number_input("Find Buy Points in Recent N Days", min_value=1, max_value=30, value=3, step=1)
    
    # K-line level selection
    st.markdown("---")
    st.header("📈 Analysis Level")
    
    kl_level_options = {
        "1分钟": KL_TYPE.K_1M,
        "3分钟": KL_TYPE.K_3M,
        "5分钟": KL_TYPE.K_5M,
        "15分钟": KL_TYPE.K_15M,
        "30分钟": KL_TYPE.K_30M,
        "60分钟": KL_TYPE.K_60M,
        "日线": KL_TYPE.K_DAY,
        "周线": KL_TYPE.K_WEEK,
        "月线": KL_TYPE.K_MON,
        "季线": KL_TYPE.K_QUARTER,
        "年线": KL_TYPE.K_YEAR,
    }
    
    selected_level_name = st.selectbox(
        "K-line Level",
        options=list(kl_level_options.keys()),
        index=6,  # Default to 日线
        help="Select the K-line level for analysis"
    )
    selected_kl_type = kl_level_options[selected_level_name]
    
    st.markdown("---")
    st.header("📊 Chart Settings")
    
    plot_kline = st.checkbox("Show K-line", value=True)
    plot_bi = st.checkbox("Show Bi", value=True)
    plot_seg = st.checkbox("Show Segment", value=True)
    plot_zs = st.checkbox("Show Zhongshu", value=True)
    plot_bsp = st.checkbox("Show Buy/Sell Points", value=True)
    plot_macd = st.checkbox("Show MACD", value=True)

# Main interface
tab1, tab2 = st.tabs(["🔍 Batch Scan", "📊 Single Stock Analysis"])

with tab1:
    st.header("Batch Scan Buy Point Stocks")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Start Scan", type="primary", use_container_width=True):
            config = get_chan_config(bi_strict)
            
            # Get stock list
            with st.spinner("Getting stock list..."):
                stock_list = get_tradable_stocks()
            
            if stock_list.empty:
                st.error("Failed to get stock list, please try again later")
            else:
                st.info(f"Got {len(stock_list)} tradable stocks, starting scan...")
                
                # Execute scan
                results, success_count, fail_count = scan_stocks(
                    stock_list, config, begin_time=begin_time, end_time=end_time, recent_days=recent_days, kl_type=selected_kl_type
                )
                
                # Save results to session state
                st.session_state['scan_results'] = results
                st.session_state['scan_stats'] = {
                    'success': success_count,
                    'fail': fail_count,
                    'found': len(results)
                }
                
                st.success(f"Scan completed! Success: {success_count}, Skipped: {fail_count}, Found buy points: {len(results)}")
    
    with col2:
        if st.button("🔄 Clear Results", use_container_width=True):
            if 'scan_results' in st.session_state:
                del st.session_state['scan_results']
            if 'scan_stats' in st.session_state:
                del st.session_state['scan_stats']
            st.rerun()
    
    # Display scan results
    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        results = st.session_state['scan_results']
        stats = st.session_state.get('scan_stats', {})
        
        st.markdown("---")
        st.subheader(f"📋 Buy Point Stock List (Total: {len(results)})")
        
        # Save button
        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button("💾 Save Results", type="secondary", use_container_width=True):
                with st.spinner("Saving results and charts..."):
                    saved_path = save_scan_results(results, stats)
                if saved_path:
                    chart_count = sum(1 for r in results if r.get('chan') is not None)
                    st.success(f"Results saved to: {saved_path}\nSaved {len(results)} results and {chart_count} charts")
                else:
                    st.error("Failed to save results")
        
        # Create results table (include level info)
        df_results = []
        for r in results:
            chan = r.get('chan')
            if chan and chan.lv_list:
                plot_driver_temp = CPyEchartsPlotDriver(chan)
                actual_kl_type = chan.lv_list[0]
                level_name = plot_driver_temp.LEVEL_NAMES.get(actual_kl_type, "DAY")
            else:
                level_name = selected_level_name
            
            df_results.append({
                'Code': r['code'],
                'Name': r['name'],
                'Level': level_name,
                'Buy Point Type': r['bsp_type'],
                'Buy Point Time': r['bsp_time']
            })
        
        df_results = pd.DataFrame(df_results)
        
        # Display table
        st.dataframe(df_results, use_container_width=True)
        
        # Select stock to view details
        if len(results) > 0:
            stock_options = [f"{r['code']} {r['name']}" for r in results]
            selected_stock_name = st.selectbox(
                "Select stock to view detailed analysis",
                options=stock_options,
                index=0
            )
            
            if selected_stock_name:
                selected_idx = stock_options.index(selected_stock_name)
                selected_stock = results[selected_idx]
                
                st.markdown("---")
                # Get the actual level used
                actual_kl_type = selected_stock['chan'].lv_list[0] if selected_stock['chan'].lv_list else selected_kl_type
                plot_driver_temp = CPyEchartsPlotDriver(selected_stock['chan'])
                level_name_display = plot_driver_temp.LEVEL_NAMES.get(actual_kl_type, "DAY")
                st.subheader(f"📈 {selected_stock['code']} {selected_stock['name']} - {level_name_display} Chan Theory Analysis Chart")
                
                # Display buy point info (baostock doesn't provide real-time quotes)
                st.info(f"**Level**: {level_name_display} | **Buy Point Type**: {selected_stock['bsp_type']} | **Buy Point Time**: {selected_stock['bsp_time']}")
                
                # Plot chart (use the level from the chan object)
                actual_kl_type = selected_stock['chan'].lv_list[0] if selected_stock['chan'].lv_list else selected_kl_type
                plot_chart(selected_stock['chan'], actual_kl_type)
    else:
        st.info('👆 Click "Start Scan" button to scan A-share market')

with tab2:
    st.header("Single Stock Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        stock_code = st.text_input("Stock Code", placeholder="e.g., 000001", help="Enter 6-digit stock code, e.g., 000001")
    
    with col2:
        st.write("")  # Spacer
        st.write("Time range uses sidebar settings")
    
    if st.button("🔍 Start Analysis", type="primary", use_container_width=True):
        if not stock_code or len(stock_code) != 6:
            st.warning("Please enter 6-digit stock code")
        else:
            config = get_chan_config(bi_strict)
            
            with st.spinner(f"Analyzing {stock_code}..."):
                chan = analyze_stock(stock_code, config, begin_time=begin_time, end_time=end_time, kl_type=selected_kl_type)
            
            if chan:
                st.session_state['single_chan'] = chan
                st.session_state['single_code'] = stock_code
                st.success(f"Analysis completed: {stock_code}")
            else:
                st.error(f"Analysis failed: {stock_code}")
    
    # Display analysis results
    if 'single_chan' in st.session_state:
        chan = st.session_state['single_chan']
        code = st.session_state.get('single_code', '')
        
        st.markdown("---")
        # Get the actual level used
        actual_kl_type = chan.lv_list[0] if chan.lv_list else selected_kl_type
        plot_driver_temp = CPyEchartsPlotDriver(chan)
        level_name_display = plot_driver_temp.LEVEL_NAMES.get(actual_kl_type, "DAY")
        st.subheader(f"📈 {code} - {level_name_display} Chan Theory Analysis Chart")
        
        # Display buy/sell point info
        bsp_list = chan.get_latest_bsp(number=10)
        buy_points = [bsp for bsp in bsp_list if bsp.is_buy]
        sell_points = [bsp for bsp in bsp_list if not bsp.is_buy]
        
        # Save button
        if st.button("💾 Save Analysis", type="secondary", use_container_width=True):
            saved_path = save_single_stock_analysis(chan, code, bsp_list)
            if saved_path:
                st.success(f"Analysis saved to: {saved_path}")
            else:
                st.error("Failed to save analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Buy Points", len(buy_points))
            if buy_points:
                st.write("Recent buy points:")
                for bsp in buy_points[:5]:
                    st.write(f"- {bsp.type2str()} @ {bsp.klu.time}")
        
        with col2:
            st.metric("Sell Points", len(sell_points))
            if sell_points:
                st.write("Recent sell points:")
                for bsp in sell_points[:5]:
                    st.write(f"- {bsp.type2str()} @ {bsp.klu.time}")
        
        # Plot chart (use the level from the chan object)
        actual_kl_type = chan.lv_list[0] if chan.lv_list else selected_kl_type
        plot_chart(chan, actual_kl_type)

# Footer
st.markdown("---")
st.markdown("**Powered by chan.py** | Chan Theory Analysis Framework")
