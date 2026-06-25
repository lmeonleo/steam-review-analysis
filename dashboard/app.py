"""Interactive bonus dashboard for the Steam Review Analysis project.

This app reads pre-aggregated result files produced by the analysis pipeline.
It avoids direct Altair imports so the public Streamlit deployment stays stable
across Streamlit Community Cloud runtime changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output/results/local"


def load_data():
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "project_metadata.json").read_text(encoding="utf-8"))
    frames = {
        name: pd.read_csv(RESULTS / f"{name}.csv")
        for name in ["yearly", "genre", "price_band", "top_reliable", "publishers", "top_tags"]
    }
    return summary, metadata, frames


def metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(text: str) -> None:
    st.markdown(f'<div class="insight-box">{text}</div>', unsafe_allow_html=True)


st.set_page_config(page_title="Steam Review Analysis", page_icon="🎮", layout="wide")
summary, metadata, data = load_data()
members_text = " / ".join(metadata["members"])
review_outcomes = summary["total_positive_ratings"] + summary["total_negative_ratings"]
top_game = data["top_reliable"].iloc[0]

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 2.4rem;
        padding-bottom: 2.8rem;
        max-width: 1180px;
      }
      .hero {
        padding: 1.4rem 1.6rem 1.2rem 1.6rem;
        border: 1px solid #e6edf5;
        border-radius: 18px;
        background: linear-gradient(135deg, #f8fbff 0%, #eef7fb 100%);
        margin-bottom: 1.2rem;
      }
      .eyebrow {
        color: #227c9d;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
      }
      .hero h1 {
        font-size: 2.9rem;
        line-height: 1.05;
        margin: 0 0 0.65rem 0;
        color: #152033;
      }
      .subtitle {
        color: #536273;
        font-size: 1.02rem;
        max-width: 860px;
        margin-bottom: 1rem;
      }
      .meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
      }
      .pill {
        display: inline-block;
        padding: 0.36rem 0.7rem;
        border-radius: 999px;
        background: #ffffff;
        border: 1px solid #dce8f2;
        color: #2f3b4a;
        font-size: 0.92rem;
      }
      .metric-card {
        border: 1px solid #e5eaf0;
        border-radius: 16px;
        padding: 1.05rem 1rem;
        background: #ffffff;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
      }
      .metric-label {
        color: #6b7787;
        font-size: 0.86rem;
        font-weight: 650;
        margin-bottom: 0.35rem;
      }
      .metric-value {
        color: #142033;
        font-size: 2rem;
        font-weight: 760;
        line-height: 1.1;
      }
      .metric-note {
        color: #7a8796;
        font-size: 0.78rem;
        margin-top: 0.4rem;
      }
      .insight-box {
        border-left: 4px solid #227c9d;
        background: #f5f9fc;
        color: #334155;
        padding: 0.75rem 0.95rem;
        border-radius: 0 12px 12px 0;
        margin: 0.35rem 0 1rem 0;
      }
      h2, h3 {
        color: #172033;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="hero">
      <div class="eyebrow">Big Data Final Project Dashboard</div>
      <h1>Steam Review Analysis</h1>
      <div class="subtitle">
        A reproducible analysis of Steam game catalogue growth, review outcomes,
        genre reception, price bands, and reliable rankings using Kaggle data,
        HDFS/PySpark design, Spark SQL outputs, and an interactive web layer.
      </div>
      <div class="meta-row">
        <span class="pill"><b>Team</b>: {metadata["team_name"]}</span>
        <span class="pill"><b>Members</b>: {members_text}</span>
        <span class="pill"><b>Dataset</b>: Kaggle Steam Store Games</span>
        <span class="pill"><b>Stack</b>: HDFS · PySpark · Spark SQL · Streamlit</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Games analyzed", f"{summary['clean_rows']:,}", "Clean game-level records")
with c2:
    metric_card("Review outcomes", f"{review_outcomes:,}", "Positive + negative ratings")
with c3:
    metric_card("Weighted positive", f"{summary['overall_weighted_positive_pct']:.2f}%", "Overall rating signal")
with c4:
    metric_card("Median reviews/game", f"{summary['median_reviews_per_game']:,}", "Typical attention level")

st.markdown("")

overview, genres, prices, rankings, method = st.tabs(["Market", "Genres", "Price", "Rankings", "Method"])

with overview:
    st.subheader("Catalogue growth and reception")
    insight(
        "The catalogue grows sharply in the later years of the snapshot, while the average "
        "positive rate remains relatively stable. This suggests a widening market rather than "
        "a simple quality collapse."
    )
    year_range = st.slider("Release year", 1997, 2019, (2005, 2018))
    yearly = (
        data["yearly"]
        .query("release_year >= @year_range[0] and release_year <= @year_range[1]")
        .set_index("release_year")
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Games released by year**")
        st.bar_chart(yearly["games"], use_container_width=True)
    with right:
        st.markdown("**Mean positive rate by year (%)**")
        st.line_chart(yearly["mean_rating_pct"], use_container_width=True)

    st.dataframe(yearly.reset_index(), hide_index=True, use_container_width=True)
    st.info("2019 is incomplete because the dataset is a snapshot taken during that year.")

with genres:
    st.subheader("Genre breadth, attention and reliable reception")
    insight(
        "Genre comparisons use Wilson lower-bound scores as a reliability-aware quality metric. "
        "This reduces the chance that tiny sample sizes dominate the interpretation."
    )
    min_games = st.slider("Minimum games in genre", 100, 3000, 100, 100)
    genre = data["genre"].query("games >= @min_games")
    genre_chart = genre.set_index("genre")[["mean_wilson_pct", "mean_rating_pct"]]
    st.bar_chart(genre_chart, use_container_width=True)
    st.dataframe(genre, hide_index=True, use_container_width=True)
    st.caption("Genres overlap: one game can appear in several groups.")

with prices:
    st.subheader("Price bands")
    insight(
        "Price bands are descriptive rather than causal. The dashboard compares rating level "
        "and review attention to show how user reception varies across pricing segments."
    )
    price = data["price_band"].set_index("price_band")
    left, right = st.columns(2)
    with left:
        st.markdown("**Mean positive rate by price band (%)**")
        st.bar_chart(price["mean_rating_pct"], use_container_width=True)
    with right:
        st.markdown("**Median reviews by price band**")
        st.bar_chart(price["median_reviews"], use_container_width=True)
    st.dataframe(price.reset_index(), hide_index=True, use_container_width=True)
    st.warning("These are descriptive associations. Price is not identified as a causal effect.")

with rankings:
    st.subheader("Reliable rankings")
    insight(
        f"{top_game['name']} ranks highest after applying the 95% Wilson lower bound, "
        "meaning it is both highly rated and supported by substantial review volume."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**Reliable games**")
        n = st.slider("Number of games", 5, 20, 10)
        st.dataframe(
            data["top_reliable"].head(n),
            hide_index=True,
            use_container_width=True,
            column_config={
                "rating_pct": st.column_config.NumberColumn(format="%.2f%%"),
                "wilson_pct": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
    with right:
        st.markdown("**High-quality publisher portfolios**")
        st.dataframe(data["publishers"].head(n), hide_index=True, use_container_width=True)
    st.markdown("**Most-voted SteamSpy tags**")
    st.dataframe(data["top_tags"].head(15), hide_index=True, use_container_width=True)

with method:
    st.subheader("Method and reproducibility")
    insight(
        "The web page is intentionally lightweight: it reads only small aggregated CSV outputs, "
        "while the heavy transformation logic remains in the PySpark/HDFS pipeline."
    )
    st.markdown(
        "Raw 100% positive can mean 3/3 or 30,000/30,000. The project ranks games with the "
        "**95% Wilson lower confidence bound** and requires at least 1,000 review outcomes. "
        "This makes the ranking more robust than a plain positive-rate sort."
    )
    st.code(
        "Kaggle CSV -> HDFS raw zone -> PySpark cleaning -> Parquet curated zone -> "
        "Spark SQL aggregation -> result CSV -> Streamlit dashboard"
    )
    st.markdown(
        "Source dataset: [Steam Store Games on Kaggle]"
        "(https://www.kaggle.com/datasets/nikdavis/steam-store-games/data)"
    )
