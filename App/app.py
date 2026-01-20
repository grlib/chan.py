import streamlit as st

# 设置页面配置
st.set_page_config(
    page_title="Chan.py 应用",
    page_icon="📈",
    layout="wide"
)

# 定义页面
pages = [
    st.Page("pages/favorites.py", title="Favorites", icon="⭐"),
    st.Page("pages/stock_scanner.py", title="Stock Scanner", icon="📈"),
    st.Page("pages/chan_analysis_prompt.py", title="Chan Analysis Prompt", icon="📊"),
    # 可以在这里添加更多页面
    # st.Page("pages/other_page.py", title="Other Page", icon="📊"),
]

# 创建导航
pg = st.navigation(pages)

# 运行选中的页面
pg.run()