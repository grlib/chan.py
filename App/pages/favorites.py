import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 数据目录和文件路径
DATA_DIR = "../data"  # 相对于App目录
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.csv")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

def load_favorites():
    """加载自选股数据"""
    if os.path.exists(FAVORITES_FILE):
        return pd.read_csv(FAVORITES_FILE)
    else:
        return pd.DataFrame(columns=["code", "name", "added_date", "note"])

def save_favorites(df):
    """保存自选股数据"""
    df.to_csv(FAVORITES_FILE, index=False)

# 页面标题
st.title("⭐ Favorites Management")

# 加载数据
favorites = load_favorites()

# 显示当前自选股
st.subheader("📋 Current Favorites")
if favorites.empty:
    st.info("No favorites yet, please add stocks")
else:
    st.dataframe(favorites, use_container_width=True)

# 添加股票表单
st.subheader("➕ Add Stock")
with st.form("add_stock_form"):
    col1, col2 = st.columns(2)
    with col1:
        code = st.text_input("Stock Code", placeholder="e.g., 000001.SZ or sz.000001")
    with col2:
        name = st.text_input("Stock Name", placeholder="e.g., Ping An Bank")

    note = st.text_area("Note", placeholder="Optional note")

    submitted = st.form_submit_button("Add Stock", use_container_width=True)

    if submitted:
        if code and name:
            # 检查是否已存在
            if code in favorites["code"].values:
                st.error(f"Stock {code} is already in favorites")
            else:
                new_row = {
                    "code": code,
                    "name": name,
                    "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "note": note
                }
                favorites = pd.concat([favorites, pd.DataFrame([new_row])], ignore_index=True)
                save_favorites(favorites)
                st.success(f"Successfully added stock: {name} ({code})")
                st.rerun()
        else:
            st.error("Please enter stock code and name")

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

# 统计信息
st.subheader("📊 Statistics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Stocks", len(favorites))
with col2:
    st.metric("Added Today", len(favorites[favorites["added_date"].str.startswith(datetime.now().strftime("%Y-%m-%d"))]))
with col3:
    st.metric("With Notes", len(favorites[favorites["note"].notna() & (favorites["note"] != "")]))