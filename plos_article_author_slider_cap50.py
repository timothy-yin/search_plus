import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="PLOS 專題資料觀察平台", layout="wide")
st.title("📘 PLOS Article Explorer（67600）")

@st.cache_data
def load_data():
    df = pd.read_csv("plos_all_cleaned_up_to_67600.csv")
    author_counts = df.groupby(["DOI", "Title"]).size().reset_index(name="AuthorCount")
    df = df.merge(author_counts, on=["DOI", "Title"])
    df["Year"] = df["DOI"].str.extract(r'10\.1371/journal\.pone\.(\d{2})', expand=False)
    df["Year"] = df["Year"].apply(lambda x: int("20" + x) if pd.notnull(x) else None)

    # 建立 capped 欄位（如 >50 → 51）
    df["AuthorCapped"] = df["AuthorCount"].apply(lambda x: x if x <= 50 else 51)
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("🔍 檢索設定")
search_column = st.sidebar.selectbox(
    "請選擇要檢索的欄位",
    ["DOI", "Title", "Author", "Affiliation", "Role", "Subjects", "Keywords", "Abstract"]
)
search_mode = st.sidebar.radio("檢索模式", ["關鍵字（模糊比對）", "正則表達式（Regex）"])
search_input = st.sidebar.text_input("輸入檢索內容")

# 作者數量滑桿（51 表示 50+）
author_slider = st.sidebar.slider("選擇作者數（最大 50+）", min_value=1, max_value=51, value=(1, 10))
mask = df["AuthorCapped"].between(author_slider[0], author_slider[1])

# 年份複選
year_options = sorted(df["Year"].dropna().astype(int).unique().tolist())
selected_years = st.sidebar.multiselect("選擇發表年份（可複選）", year_options, default=year_options)
mask &= df["Year"].isin(selected_years)

# 角色
role_filter = st.sidebar.multiselect("作者角色（可複選）", ["第一作者", "通訊作者"])

# 顯示筆數
max_results = st.sidebar.slider("顯示文章數量", 5, 100, 20)

# 搜尋按鈕
do_search = st.sidebar.button("🚀 開始搜尋")

if do_search:
    if role_filter:
        role_mask = df["Role"].fillna("").apply(lambda r: any(role in r for role in role_filter))
        mask &= role_mask

    if search_input:
        if search_mode == "關鍵字（模糊比對）":
            mask &= df[search_column].fillna("").str.contains(search_input, case=False)
        else:
            try:
                mask &= df[search_column].fillna("").str.contains(search_input, regex=True)
            except re.error:
                st.error("❌ 無效的正則表達式")
                mask &= pd.Series([False] * len(df))

    filtered = df[mask]
    unique_articles = filtered.drop_duplicates(subset=["DOI", "Title"]).head(max_results)

    if not unique_articles.empty:
        st.success(f"🔎 找到 {len(unique_articles)} 篇符合的文章")
        for _, row in unique_articles.iterrows():
            with st.expander(f"{row['Title']} ({row['DOI']})"):
                st.markdown(f"**DOI**: {row['DOI']}")
                st.markdown(f"**Subjects**: {row['Subjects']}")
                st.markdown(f"**Keywords**: {row['Keywords']}")
                st.markdown(f"**Abstract**: {row['Abstract']}")

                authors = filtered[(filtered["DOI"] == row["DOI"]) & (filtered["Title"] == row["Title"])][["Author", "Affiliation", "Role"]]
                st.markdown("**作者列表：**")
                st.dataframe(authors, use_container_width=True)

        st.download_button("📥 匯出結果 CSV", data=unique_articles.to_csv(index=False), file_name="plos_search_articles.csv")
    else:
        st.warning("❗ 查無符合條件的資料，請調整搜尋條件後重試。")
else:
    st.info("請在左側設定檢索條件，點選 🚀 開始搜尋")
