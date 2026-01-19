# Chan.py 应用

这是一个基于Streamlit的多页面应用，用于管理和分析股票数据。

## 功能页面

- **自选股管理**：管理个人自选股列表，支持添加、删除和查看股票信息

## 运行方式

1. 安装依赖：
```bash
pip install -r Script/requirements.txt
```

2. 运行应用：
```bash
cd App
streamlit run app.py
```

3. 在浏览器中打开显示的URL

## 数据存储

- 自选股数据存储在 `data/favorites.csv`
- `data/` 目录已被添加到 `.gitignore`，不会被版本控制

## 开发说明

- 主应用文件：`App/app.py`
- 页面文件位于：`App/pages/`
- 添加新页面：在 `app.py` 的 `pages` 列表中添加 `st.Page` 项