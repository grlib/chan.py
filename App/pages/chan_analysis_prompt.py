"""
缠论分析提示词生成器 - Streamlit Version

功能：
    - 多级别联立分析（周线、日线、30分钟、5分钟）
    - 可配置的时间范围
    - 生成结构化的提示词信息供大模型分析

使用方法：
    streamlit run App/app.py
"""
import sys
from pathlib import Path

# Add project root to path for importing chan.py core modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime, timedelta
import streamlit as st
from typing import Dict, Optional, List
import json
import os
import pandas as pd

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, KL_TYPE, DATA_SRC, BI_DIR
from App.config import get_data_source_for_chan


def get_chan_config() -> CChanConfig:
    """获取缠论配置"""
    return CChanConfig({
        "bi_strict": True,
        "zs_combine": True,
        "zs_algo": "normal",
        "seg_algo": "chan",
        "bs_type": "1,1p,2,2s,3a,3b",
        "macd_algo": "peak",
        "divergence_rate": float("inf"),
        "print_warning": False,
    })


def format_code(code: str) -> str:
    """
    格式化股票代码，添加市场前缀
    
    Args:
        code: 股票代码（如 '000001' 或 'sh.600000'）
    
    Returns:
        格式化后的代码（如 'sh.600000' 或 'sz.000001'）
    """
    if code.startswith(('sh.', 'sz.')):
        return code
    
    # 判断市场：600/601/603/605/688前缀是上海，000/001/002/300前缀是深圳
    if code.startswith(('600', '601', '603', '605', '688')):
        return f"sh.{code}"
    else:
        return f"sz.{code}"


def analyze_multi_level(
    code: str,
    config: CChanConfig,
    time_ranges: Dict[KL_TYPE, Dict[str, str]]
) -> Dict[KL_TYPE, Optional[CChan]]:
    """
    多级别联立分析
    
    Args:
        code: 股票代码
        config: 缠论配置
        time_ranges: 时间范围字典，格式为 {KL_TYPE: {'begin': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}}
    
    Returns:
        分析结果字典，格式为 {KL_TYPE: CChan对象}
    """
    results = {}
    code_formatted = format_code(code)
    
    # 按级别从大到小分析
    level_order = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
    
    for kl_type in level_order:
        if kl_type not in time_ranges:
            continue
            
        time_range = time_ranges[kl_type]
        begin_time = time_range.get('begin')
        end_time = time_range.get('end')
        
        if not begin_time:
            continue
            
        if not end_time:
            end_time = datetime.now().strftime("%Y-%m-%d")
        
        try:
            level_name_map = {
                KL_TYPE.K_WEEK: "Weekly",
                KL_TYPE.K_DAY: "Daily",
                KL_TYPE.K_30M: "30 Minutes",
                KL_TYPE.K_5M: "5 Minutes",
            }
            level_name = level_name_map.get(kl_type, kl_type.name)
            with st.spinner(f"Analyzing {level_name}..."):
                data_src = get_data_source_for_chan()
                chan = CChan(
                    code=code_formatted,
                    begin_time=begin_time,
                    end_time=end_time,
                    data_src=data_src,
                    lv_list=[kl_type],
                    config=config,
                    autype=AUTYPE.QFQ,
                )
                results[kl_type] = chan
        except Exception as e:
            level_name_map = {
                KL_TYPE.K_WEEK: "Weekly",
                KL_TYPE.K_DAY: "Daily",
                KL_TYPE.K_30M: "30 Minutes",
                KL_TYPE.K_5M: "5 Minutes",
            }
            level_name = level_name_map.get(kl_type, kl_type.name)
            st.error(f"Failed to analyze {level_name}: {e}")
            results[kl_type] = None
    
    return results


def extract_bi_info(chan: CChan, kl_type: KL_TYPE, config: CChanConfig) -> List[Dict]:
    """提取笔信息，包含MACD信息"""
    if chan is None or kl_type not in chan.kl_datas:
        return []
    
    bi_list = chan[kl_type].bi_list
    bi_info = []
    macd_algo = config.bs_point_conf.b_conf.macd_algo
    
    for bi in bi_list:
        # 获取MACD指标
        macd_metric = None
        try:
            macd_metric = bi.cal_macd_metric(macd_algo, is_reverse=False)
        except:
            pass
        
        # 获取笔的MACD值（如果有）
        begin_macd = None
        end_macd = None
        try:
            begin_klu = bi.get_begin_klu()
            end_klu = bi.get_end_klu()
            if hasattr(begin_klu, 'macd') and begin_klu.macd:
                begin_macd = {
                    "DIF": begin_klu.macd.DIF,
                    "DEA": begin_klu.macd.DEA,
                    "MACD": begin_klu.macd.macd
                }
            if hasattr(end_klu, 'macd') and end_klu.macd:
                end_macd = {
                    "DIF": end_klu.macd.DIF,
                    "DEA": end_klu.macd.DEA,
                    "MACD": end_klu.macd.macd
                }
        except:
            pass
        
        bi_info.append({
            "idx": bi.idx,
            "dir": "向上" if bi.dir == BI_DIR.UP else "向下",
            "begin_price": bi.get_begin_val(),
            "end_price": bi.get_end_val(),
            "begin_time": bi.get_begin_klu().time.to_str(),
            "end_time": bi.get_end_klu().time.to_str(),
            "is_sure": bi.is_sure,
            "macd_metric": macd_metric,
            "begin_macd": begin_macd,
            "end_macd": end_macd,
        })
    
    return bi_info


def extract_seg_info(chan: CChan, kl_type: KL_TYPE, config: CChanConfig) -> List[Dict]:
    """提取线段信息，包含MACD信息"""
    if chan is None or kl_type not in chan.kl_datas:
        return []
    
    seg_list = chan[kl_type].seg_list
    seg_info = []
    macd_algo = config.seg_bs_point_conf.b_conf.macd_algo
    
    for seg in seg_list:
        # 获取线段MACD指标
        macd_metric = None
        try:
            macd_metric = seg.cal_macd_metric(macd_algo, is_reverse=False)
        except:
            pass
        
        seg_info.append({
            "idx": seg.idx,
            "dir": "向上" if seg.dir == BI_DIR.UP else "向下",
            "begin_price": seg.get_begin_val(),
            "end_price": seg.get_end_val(),
            "begin_time": seg.start_bi.get_begin_klu().time.to_str(),
            "end_time": seg.end_bi.get_end_klu().time.to_str(),
            "is_sure": seg.is_sure,
            "macd_metric": macd_metric,
        })
    
    return seg_info


def extract_zs_info(chan: CChan, kl_type: KL_TYPE, config: CChanConfig) -> List[Dict]:
    """提取中枢信息，包含背驰信息"""
    if chan is None or kl_type not in chan.kl_datas:
        return []
    
    zs_list = chan[kl_type].zs_list
    zs_info = []
    bsp_config = config.bs_point_conf.b_conf
    
    for idx, zs in enumerate(zs_list):
        # 检查背驰
        is_divergence = False
        divergence_rate = None
        bi_in_macd = None
        bi_out_macd = None
        
        try:
            if zs.bi_in and zs.bi_out:
                # 获取进入和离开中枢的笔的MACD指标
                bi_in_macd = zs.get_bi_in().cal_macd_metric(bsp_config.macd_algo, is_reverse=False)
                bi_out_macd = zs.get_bi_out().cal_macd_metric(bsp_config.macd_algo, is_reverse=True)
                
                # 检查是否背驰
                if zs.end_bi_break():
                    is_divergence, divergence_rate = zs.is_divergence(bsp_config)
        except:
            pass
        
        zs_info.append({
            "idx": idx + 1,  # Use list index + 1 as identifier
            "begin_bi_idx": zs.begin_bi.idx,
            "end_bi_idx": zs.end_bi.idx,
            "begin_time": zs.begin.time.to_str(),
            "end_time": zs.end.time.to_str(),
            "high": zs.high,
            "low": zs.low,
            "is_sure": zs.is_sure,
            "is_divergence": is_divergence,
            "divergence_rate": divergence_rate,
            "bi_in_macd": bi_in_macd,
            "bi_out_macd": bi_out_macd,
        })
    
    return zs_info


def extract_macd_info(chan: CChan, kl_type: KL_TYPE) -> List[Dict]:
    """提取K线MACD信息"""
    if chan is None or kl_type not in chan.kl_datas:
        return []
    
    kl_data = chan[kl_type]
    macd_info = []
    
    # 获取最近的一些K线的MACD信息
    klu_list = []
    for klc in kl_data.lst:
        klu_list.extend(klc.lst)
    
    # 只取最近50根K线的MACD信息
    recent_klu = klu_list[-50:] if len(klu_list) > 50 else klu_list
    
    for klu in recent_klu:
        if hasattr(klu, 'macd') and klu.macd:
            macd_info.append({
                "time": klu.time.to_str(),
                "close": klu.close,
                "DIF": klu.macd.DIF,
                "DEA": klu.macd.DEA,
                "MACD": klu.macd.macd,
            })
    
    return macd_info


def generate_prompt_text(
    code: str,
    code_name: str,
    analysis_results: Dict[KL_TYPE, Optional[CChan]],
    time_ranges: Dict[KL_TYPE, Dict[str, str]],
    config: CChanConfig
) -> str:
    """
    生成缠论分析提示词文本
    
    Args:
        code: 股票代码
        code_name: 股票名称
        analysis_results: 分析结果字典
        time_ranges: 时间范围字典
    
    Returns:
        格式化的提示词文本
    """
    level_names = {
        KL_TYPE.K_WEEK: "周线",
        KL_TYPE.K_DAY: "日线",
        KL_TYPE.K_30M: "30分钟",
        KL_TYPE.K_5M: "5分钟",
    }
    
    prompt_parts = []
    prompt_parts.append(f"# 缠论多级别联立分析 - {code_name} ({code})\n")
    prompt_parts.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    prompt_parts.append("=" * 80 + "\n\n")
    
    # 按级别从大到小输出
    level_order = [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
    
    for kl_type in level_order:
        if kl_type not in analysis_results:
            continue
        
        chan = analysis_results[kl_type]
        if chan is None:
            continue
        
        level_name = level_names[kl_type]
        time_range = time_ranges.get(kl_type, {})
        
        prompt_parts.append(f"## {level_name}级别分析\n")
        prompt_parts.append(f"分析时间范围: {time_range.get('begin', 'N/A')} 至 {time_range.get('end', 'N/A')}\n")
        prompt_parts.append("-" * 80 + "\n")
        
        # K线数据统计
        if kl_type in chan.kl_datas:
            kl_data = chan[kl_type]
            kline_count = sum(len(klc.lst) for klc in kl_data.lst)
            prompt_parts.append(f"K线数量: {kline_count}\n")
            
            if kl_data.lst:
                first_kl = kl_data.lst[0].lst[0]
                last_kl = kl_data.lst[-1].lst[-1]
                prompt_parts.append(f"起始时间: {first_kl.time.to_str()}, 价格: {first_kl.close:.2f}\n")
                prompt_parts.append(f"结束时间: {last_kl.time.to_str()}, 价格: {last_kl.close:.2f}\n")
                price_change = ((last_kl.close - first_kl.close) / first_kl.close) * 100
                prompt_parts.append(f"期间涨跌幅: {price_change:.2f}%\n")
        
        prompt_parts.append("\n")
        
        # 笔信息（包含MACD）
        bi_info = extract_bi_info(chan, kl_type, config)
        prompt_parts.append(f"### 笔（Bi）分析\n")
        prompt_parts.append(f"笔数量: {len(bi_info)}\n")
        if bi_info:
            prompt_parts.append("最近5笔（含MACD信息）:\n")
            for bi in bi_info[-5:]:
                macd_str = ""
                if bi['macd_metric'] is not None:
                    macd_str = f" | MACD指标: {bi['macd_metric']:.4f}"
                if bi['begin_macd'] and bi['end_macd']:
                    macd_str += f" | 起始MACD(DIF/DEA/MACD): {bi['begin_macd']['DIF']:.4f}/{bi['begin_macd']['DEA']:.4f}/{bi['begin_macd']['MACD']:.4f}"
                    macd_str += f" | 结束MACD(DIF/DEA/MACD): {bi['end_macd']['DIF']:.4f}/{bi['end_macd']['DEA']:.4f}/{bi['end_macd']['MACD']:.4f}"
                
                prompt_parts.append(
                    f"  笔{bi['idx']}: {bi['dir']} | "
                    f"时间: {bi['begin_time']} ~ {bi['end_time']} | "
                    f"价格: {bi['begin_price']:.2f} ~ {bi['end_price']:.2f} | "
                    f"确认: {'是' if bi['is_sure'] else '否'}{macd_str}\n"
                )
        prompt_parts.append("\n")
        
        # 线段信息（包含MACD）
        seg_info = extract_seg_info(chan, kl_type, config)
        prompt_parts.append(f"### 线段（Segment）分析\n")
        prompt_parts.append(f"线段数量: {len(seg_info)}\n")
        if seg_info:
            prompt_parts.append("最近3条线段（含MACD信息）:\n")
            for seg in seg_info[-3:]:
                macd_str = ""
                if seg['macd_metric'] is not None:
                    macd_str = f" | MACD指标: {seg['macd_metric']:.4f}"
                
                prompt_parts.append(
                    f"  线段{seg['idx']}: {seg['dir']} | "
                    f"时间: {seg['begin_time']} ~ {seg['end_time']} | "
                    f"价格: {seg['begin_price']:.2f} ~ {seg['end_price']:.2f} | "
                    f"确认: {'是' if seg['is_sure'] else '否'}{macd_str}\n"
                )
        prompt_parts.append("\n")
        
        # 中枢信息（包含背驰）
        zs_info = extract_zs_info(chan, kl_type, config)
        prompt_parts.append(f"### 中枢（Zhongshu）分析\n")
        prompt_parts.append(f"中枢数量: {len(zs_info)}\n")
        if zs_info:
            prompt_parts.append("最近3个中枢（含背驰信息）:\n")
            for zs in zs_info[-3:]:
                divergence_str = ""
                if zs['is_divergence'] is not None:
                    if zs['is_divergence']:
                        divergence_str = f" | 背驰: 是 | 背驰率: {zs['divergence_rate']:.4f}" if zs['divergence_rate'] else " | 背驰: 是"
                    else:
                        divergence_str = f" | 背驰: 否 | 背驰率: {zs['divergence_rate']:.4f}" if zs['divergence_rate'] else " | 背驰: 否"
                
                macd_str = ""
                if zs['bi_in_macd'] is not None and zs['bi_out_macd'] is not None:
                    macd_str = f" | 进入笔MACD: {zs['bi_in_macd']:.4f} | 离开笔MACD: {zs['bi_out_macd']:.4f}"
                
                prompt_parts.append(
                    f"  中枢{zs['idx']} (笔{zs['begin_bi_idx']}-{zs['end_bi_idx']}): "
                    f"时间: {zs['begin_time']} ~ {zs['end_time']} | "
                    f"区间: {zs['low']:.2f} ~ {zs['high']:.2f} | "
                    f"确认: {'是' if zs['is_sure'] else '否'}{divergence_str}{macd_str}\n"
                )
        prompt_parts.append("\n")
        
        # MACD信息
        macd_info = extract_macd_info(chan, kl_type)
        prompt_parts.append(f"### MACD指标分析\n")
        if macd_info:
            prompt_parts.append(f"最近MACD数据（最近{len(macd_info)}根K线）:\n")
            prompt_parts.append("最近10根K线的MACD:\n")
            for macd in macd_info[-10:]:
                prompt_parts.append(
                    f"  时间: {macd['time']} | 收盘: {macd['close']:.2f} | "
                    f"DIF: {macd['DIF']:.4f} | DEA: {macd['DEA']:.4f} | MACD: {macd['MACD']:.4f}\n"
                )
        prompt_parts.append("\n")
        
        prompt_parts.append("=" * 80 + "\n\n")
    
    # 多级别联立分析总结和未来走势完全分类
    prompt_parts.append("## 多级别联立分析总结与未来走势完全分类\n")
    prompt_parts.append("请基于以上多级别分析结果，进行以下分析：\n\n")
    
    prompt_parts.append("### 一、当前趋势判断\n")
    prompt_parts.append("1. 结合周线、日线、30分钟、5分钟的趋势方向，判断当前处于什么趋势中\n")
    prompt_parts.append("2. 识别各级别的关键支撑位和阻力位\n")
    prompt_parts.append("3. 分析当前价格在各级别中的位置（是否接近关键位置）\n\n")
    
    prompt_parts.append("### 二、MACD和背驰分析\n")
    prompt_parts.append("1. 分析各级别笔和线段的MACD指标变化趋势\n")
    prompt_parts.append("2. 识别各级别中枢的背驰情况（是否出现背驰，背驰程度如何）\n")
    prompt_parts.append("3. 分析MACD与价格走势的背离情况\n")
    prompt_parts.append("4. 判断当前是否处于背驰状态，以及背驰的级别\n\n")
    
    prompt_parts.append("### 三、未来走势完全分类\n")
    prompt_parts.append("根据缠论理论，请对未来的走势进行完全分类分析，包括：\n\n")
    prompt_parts.append("**1. 周线级别未来走势分类：**\n")
    prompt_parts.append("   - 上涨情况：继续上涨、形成新的中枢、形成背驰后回调\n")
    prompt_parts.append("   - 下跌情况：继续下跌、形成新的中枢、形成背驰后反弹\n")
    prompt_parts.append("   - 盘整情况：在中枢内震荡、突破中枢向上、跌破中枢向下\n\n")
    
    prompt_parts.append("**2. 日线级别未来走势分类：**\n")
    prompt_parts.append("   - 结合周线趋势，分析日线可能的走势变化\n")
    prompt_parts.append("   - 识别日线级别的关键位置和可能的转折点\n")
    prompt_parts.append("   - 分析日线MACD和背驰情况对未来走势的影响\n\n")
    
    prompt_parts.append("**3. 30分钟级别未来走势分类：**\n")
    prompt_parts.append("   - 结合日线趋势，分析30分钟可能的走势变化\n")
    prompt_parts.append("   - 识别30分钟级别的关键位置和可能的转折点\n")
    prompt_parts.append("   - 分析30分钟MACD和背驰情况对未来走势的影响\n\n")
    
    prompt_parts.append("**4. 5分钟级别未来走势分类：**\n")
    prompt_parts.append("   - 结合30分钟趋势，分析5分钟可能的走势变化\n")
    prompt_parts.append("   - 识别5分钟级别的关键位置和可能的转折点\n")
    prompt_parts.append("   - 分析5分钟MACD和背驰情况对未来走势的影响\n\n")
    
    prompt_parts.append("**5. 多级别联立分析：**\n")
    prompt_parts.append("   - 综合分析各级别走势的相互影响\n")
    prompt_parts.append("   - 识别多级别共振的关键位置\n")
    prompt_parts.append("   - 判断未来最可能的走势路径（按概率排序）\n")
    prompt_parts.append("   - 分析各种走势分类的概率和条件\n\n")
    
    prompt_parts.append("### 四、操作建议\n")
    prompt_parts.append("1. 根据未来走势完全分类，给出不同情况下的操作策略\n")
    prompt_parts.append("2. 识别潜在的风险信号和需要注意的关键位置\n")
    prompt_parts.append("3. 给出具体的操作建议：买入时机、卖出时机、止损位置、目标位置\n")
    prompt_parts.append("4. 说明各种走势分类下的应对策略\n\n")
    
    prompt_parts.append("### 五、风险提示\n")
    prompt_parts.append("1. 识别潜在的风险信号\n")
    prompt_parts.append("2. 说明需要注意的关键位置和关键事件\n")
    prompt_parts.append("3. 提醒可能出现的意外情况\n")
    
    return "".join(prompt_parts)


def load_favorites():
    """Load favorites data from favorites.csv"""
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    favorites_file = data_dir / "favorites.csv"
    if favorites_file.exists():
        return pd.read_csv(favorites_file)
    else:
        return pd.DataFrame(columns=["code", "name", "added_date", "note"])


def get_stock_name(code: str, favorites: pd.DataFrame = None) -> str:
    """Get stock name from favorites or return code"""
    if favorites is None:
        favorites = load_favorites()
    
    if not favorites.empty:
        matched = favorites[favorites["code"] == code]
        if not matched.empty:
            return matched.iloc[0]["name"]
    
    return code


def main():
    st.set_page_config(
        page_title="Chan Theory Analysis Prompt Generator",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Chan Theory Multi-Level Analysis Prompt Generator")
    st.markdown("---")
    
    # Load favorites
    favorites = load_favorites()
    
    # Stock code input - allow selection from favorites or manual input
    col1, col2 = st.columns([2, 1])
    with col1:
        stock_code = ""
        if not favorites.empty:
            # Create options for selectbox
            stock_options = [f"{row['code']} - {row['name']}" for _, row in favorites.iterrows()]
            selected_option = st.selectbox(
                "Select Stock from Favorites",
                options=[""] + stock_options,
                index=0,
                key="favorite_stock_selector"
            )
            
            if selected_option and selected_option != "":
                # Extract code from selected option
                stock_code = selected_option.split(" - ")[0]
            
            # Always show manual input as fallback
            manual_code = st.text_input(
                "Or Enter Stock Code Manually",
                value=stock_code if stock_code else "",
                help="Enter stock code, e.g., 000001, 600000",
                key="manual_stock_code"
            )
            # Use manual input if provided, otherwise use selected favorite
            stock_code = manual_code if manual_code else stock_code
        else:
            stock_code = st.text_input(
                "Stock Code",
                value="000001",
                help="Enter stock code, e.g., 000001, 600000"
            )
    
    with col2:
        if not favorites.empty:
            st.info(f"📋 {len(favorites)} stocks in favorites")
        else:
            st.info("💡 Add stocks to favorites in the Favorites page")
    
    # Time range configuration
    st.subheader("⏰ Analysis Time Range Configuration")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**Weekly**")
        week_years = st.number_input("Years", min_value=1, max_value=10, value=3, key="week_years")
        week_end = st.date_input("End Date", value=datetime.now().date(), key="week_end")
    
    with col2:
        st.markdown("**Daily**")
        day_years = st.number_input("Years", min_value=1, max_value=10, value=1, key="day_years")
        day_end = st.date_input("End Date", value=datetime.now().date(), key="day_end")
    
    with col3:
        st.markdown("**30 Minutes**")
        min30_months = st.number_input("Months", min_value=1, max_value=12, value=3, key="min30_months")
        min30_end = st.date_input("End Date", value=datetime.now().date(), key="min30_end")
    
    with col4:
        st.markdown("**5 Minutes**")
        min5_days = st.number_input("Days", min_value=1, max_value=30, value=10, key="min5_days")
        min5_end = st.date_input("End Date", value=datetime.now().date(), key="min5_end")
    
    # 计算开始时间
    week_begin = (week_end - timedelta(days=week_years * 365)).strftime("%Y-%m-%d")
    day_begin = (day_end - timedelta(days=day_years * 365)).strftime("%Y-%m-%d")
    min30_begin = (min30_end - timedelta(days=min30_months * 30)).strftime("%Y-%m-%d")
    min5_begin = (min5_end - timedelta(days=min5_days)).strftime("%Y-%m-%d")
    
    time_ranges = {
        KL_TYPE.K_WEEK: {
            'begin': week_begin,
            'end': week_end.strftime("%Y-%m-%d")
        },
        KL_TYPE.K_DAY: {
            'begin': day_begin,
            'end': day_end.strftime("%Y-%m-%d")
        },
        KL_TYPE.K_30M: {
            'begin': min30_begin,
            'end': min30_end.strftime("%Y-%m-%d")
        },
        KL_TYPE.K_5M: {
            'begin': min5_begin,
            'end': min5_end.strftime("%Y-%m-%d")
        },
    }
    
    # Analysis button
    if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
        if not stock_code:
            st.error("Please enter a stock code")
            return
        
        config = get_chan_config()
        code_formatted = format_code(stock_code)
        code_name = get_stock_name(stock_code, favorites)
        
        # Execute multi-level analysis
        analysis_results = analyze_multi_level(code_formatted, config, time_ranges)
        
        # Check if there are successful analysis results
        success_count = sum(1 for v in analysis_results.values() if v is not None)
        if success_count == 0:
            st.error("All level analyses failed. Please check the stock code and time range.")
            return
        
        st.success(f"Successfully analyzed {success_count} level(s)")
        
        # Generate prompt text
        prompt_text = generate_prompt_text(
            code_formatted,
            code_name,
            analysis_results,
            time_ranges,
            config
        )
        
        # Display prompt text
        st.subheader("📝 Generated Prompt")
        st.text_area(
            "Prompt Content",
            value=prompt_text,
            height=600,
            label_visibility="collapsed"
        )
        
        # Download button
        st.download_button(
            label="📥 Download Prompt File",
            data=prompt_text,
            file_name=f"chan_analysis_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        # Display summary statistics
        with st.expander("📊 Analysis Results Summary", expanded=False):
            for kl_type, chan in analysis_results.items():
                if chan is None:
                    continue
                
                level_names = {
                    KL_TYPE.K_WEEK: "Weekly",
                    KL_TYPE.K_DAY: "Daily",
                    KL_TYPE.K_30M: "30 Minutes",
                    KL_TYPE.K_5M: "5 Minutes",
                }
                
                level_name = level_names[kl_type]
                if kl_type in chan.kl_datas:
                    kl_data = chan[kl_type]
                    st.markdown(f"**{level_name}**:")
                    st.markdown(f"- K-lines: {sum(len(klc.lst) for klc in kl_data.lst)}")
                    st.markdown(f"- Bi: {len(kl_data.bi_list)}")
                    st.markdown(f"- Segments: {len(kl_data.seg_list)}")
                    st.markdown(f"- Zhongshu: {len(kl_data.zs_list)}")
                    
                    # Count divergences
                    divergence_count = 0
                    try:
                        bsp_config = config.bs_point_conf.b_conf
                        for zs in kl_data.zs_list:
                            if zs.bi_in and zs.bi_out and zs.end_bi_break():
                                is_div, _ = zs.is_divergence(bsp_config)
                                if is_div:
                                    divergence_count += 1
                    except Exception as e:
                        pass
                    st.markdown(f"- Divergences: {divergence_count}")


if __name__ == "__main__":
    main()
