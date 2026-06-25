"""Interactive bonus dashboard for the Steam Review Analysis project."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output/results/local"


@st.cache_data
def load_data():
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "project_metadata.json").read_text(encoding="utf-8"))
    frames = {
        name: pd.read_csv(RESULTS / f"{name}.csv")
        for name in ["yearly", "genre", "price_band", "top_reliable", "publishers", "top_tags"]
    }
    return summary, metadata, frames


st.set_page_config(page_title="Steam Review Analysis", page_icon="🎮", layout="wide")
summary, metadata, data = load_data()

st.title("Steam Review Analysis")
st.caption(f"{metadata['team_name']} · {' & '.join(metadata['members'])} · Big Data Final Project")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Games", f"{summary['clean_rows']:,}")
c2.metric("Review outcomes", f"{summary['total_positive_ratings'] + summary['total_negative_ratings']:,}")
c3.metric("Weighted positive", f"{summary['overall_weighted_positive_pct']:.2f}%")
c4.metric("Median reviews/game", f"{summary['median_reviews_per_game']:,}")

overview, genres, prices, rankings, method = st.tabs(["Market", "Genres", "Price", "Rankings", "Method"])

with overview:
    st.subheader("Catalogue growth and reception")
    year_range = st.slider("Release year", 1997, 2019, (2005, 2018))
    yearly = data["yearly"].query("release_year >= @year_range[0] and release_year <= @year_range[1]")
    bars = alt.Chart(yearly).mark_bar(color="#227C9D").encode(
        x=alt.X("release_year:O", title="Release year"),
        y=alt.Y("games:Q", title="Games released"),
        tooltip=["release_year", "games", "total_reviews", "mean_rating_pct"],
    )
    line = alt.Chart(yearly).mark_line(color="#FE6D73", point=True).encode(
        x="release_year:O", y=alt.Y("mean_rating_pct:Q", title="Mean positive rate (%)")
    )
    st.altair_chart(alt.layer(bars, line).resolve_scale(y="independent").properties(height=430), use_container_width=True)
    st.info("2019 is incomplete because the dataset is a snapshot taken during that year.")

with genres:
    st.subheader("Genre breadth, attention and reliable reception")
    min_games = st.slider("Minimum games in genre", 100, 3000, 100, 100)
    genre = data["genre"].query("games >= @min_games")
    chart = alt.Chart(genre).mark_circle(opacity=0.72, color="#17C3B2").encode(
        x=alt.X("games:Q", title="Games"),
        y=alt.Y("mean_wilson_pct:Q", title="Mean Wilson lower bound (%)"),
        size=alt.Size("total_reviews:Q", title="Review outcomes"),
        tooltip=["genre", "games", "total_reviews", "mean_rating_pct", "mean_wilson_pct"],
    ).properties(height=470)
    st.altair_chart(chart, use_container_width=True)
    st.caption("Genres overlap: one game can appear in several groups.")

with prices:
    st.subheader("Price bands")
    price = data["price_band"]
    chart = alt.Chart(price).mark_bar().encode(
        x=alt.X("price_band:N", sort=list(price["price_band"]), title="Price band (GBP)"),
        y=alt.Y("mean_rating_pct:Q", scale=alt.Scale(zero=False), title="Mean positive rate (%)"),
        color=alt.Color("price_band:N", legend=None),
        tooltip=["price_band", "games", "mean_price", "mean_rating_pct", "median_reviews"],
    ).properties(height=440)
    st.altair_chart(chart, use_container_width=True)
    st.warning("These are descriptive associations. Price is not identified as a causal effect.")

with rankings:
    left, right = st.columns(2)
    with left:
        st.subheader("Reliable games")
        n = st.slider("Number of games", 5, 20, 10)
        st.dataframe(
            data["top_reliable"].head(n),
            hide_index=True,
            use_container_width=True,
            column_config={"rating_pct": st.column_config.NumberColumn(format="%.2f%%"), "wilson_pct": st.column_config.NumberColumn(format="%.2f%%")},
        )
    with right:
        st.subheader("High-quality publisher portfolios")
        st.dataframe(data["publishers"].head(n), hide_index=True, use_container_width=True)
    st.subheader("Most-voted SteamSpy tags")
    st.dataframe(data["top_tags"].head(15), hide_index=True, use_container_width=True)

with method:
    st.subheader("Why the ranking is uncertainty-aware")
    st.markdown(
        "Raw 100% positive can mean 3/3 or 30,000/30,000. The project ranks games with the "
        "**95% Wilson lower confidence bound** and requires at least 1,000 review outcomes. "
        "All web views consume small, pre-aggregated CSVs produced by the reproducible pipeline."
    )
    st.code("hdfs raw CSV → explicit-schema PySpark ETL → partitioned Parquet → Spark SQL → result CSV → dashboard")
    st.markdown("Source dataset: [Steam Store Games on Kaggle](https://www.kaggle.com/datasets/nikdavis/steam-store-games/data)")

