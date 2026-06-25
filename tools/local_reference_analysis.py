"""Generate independently verifiable results and figures from steam.csv.

The graded big-data implementation is `src/steam_analysis.py`. This runner uses
Pandas only because the authoring machine has no Hadoop/Spark installation. Its
formulas and filters mirror the Spark pipeline and make the submitted report
reproducible without inventing cluster output.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("tmp/matplotlib").resolve()))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


RAW = Path("data/raw/steam.csv")
TAG_RAW = Path("data/raw/steamspy_tag_data.csv")
RESULTS = Path("output/results/local")
FIGURES = Path("output/figures")
PALETTE = ["#17c3b2", "#227c9d", "#ffcb77", "#fe6d73", "#6c5ce7", "#8ac926"]


def display_name(value: str) -> str:
    """Return a chart-safe label while preserving the informative Latin title."""
    label = "".join(char for char in str(value) if ord(char) < 128).strip(" ~-.")
    return label or f"App {value}"


def wilson(positive: pd.Series, total: pd.Series) -> pd.Series:
    z = 1.959963984540054
    safe = total.where(total > 0)
    phat = positive / safe
    return (phat + z * z / (2 * safe) - z * np.sqrt((phat * (1 - phat) + z * z / (4 * safe)) / safe)) / (1 + z * z / safe)


def save_csv(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(RESULTS / f"{name}.csv", index=False, encoding="utf-8")


def style_axis(ax, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color="#152238", pad=12)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.22, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW, low_memory=False)
    raw_rows = len(raw)
    duplicate_appids = int(raw.duplicated("appid").sum())
    missing_before = raw[["release_date", "price", "genres", "publisher"]].isna().sum().to_dict()

    df = raw.drop_duplicates("appid").copy()
    df = df[df["appid"].notna() & df["name"].notna()].copy()
    for column in ["name", "developer", "publisher", "platforms", "categories", "genres", "steamspy_tags", "owners"]:
        df[column] = df[column].fillna("").astype(str).str.strip()
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    for column in ["positive_ratings", "negative_ratings", "price", "average_playtime", "median_playtime"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["positive_ratings"] = df["positive_ratings"].fillna(0).clip(lower=0)
    df["negative_ratings"] = df["negative_ratings"].fillna(0).clip(lower=0)
    df.loc[df["price"] < 0, "price"] = np.nan
    df["total_reviews"] = df["positive_ratings"] + df["negative_ratings"]
    df["rating_pct"] = np.where(df["total_reviews"] > 0, 100 * df["positive_ratings"] / df["total_reviews"], np.nan)
    df["wilson_score"] = wilson(df["positive_ratings"], df["total_reviews"])
    df["release_year"] = df["release_date"].dt.year.astype("Int64")
    labels = ["Free", "Under 5", "5-10", "10-20", "20-40", "40+"]
    df["price_band"] = pd.cut(df["price"], [-0.001, 0.001, 5, 10, 20, 40, np.inf], labels=labels, right=False, include_lowest=True)

    owner_parts = df["owners"].str.extract(r"^(\d+)-(\d+)$").apply(pd.to_numeric, errors="coerce")
    df["owner_midpoint"] = owner_parts.mean(axis=1)

    quality = {
        "raw_rows": raw_rows,
        "clean_rows": len(df),
        "distinct_appids": int(df["appid"].nunique()),
        "duplicate_appids_removed": duplicate_appids,
        "missing_release_date_before": int(missing_before["release_date"]),
        "missing_release_date_after": int(df["release_date"].isna().sum()),
        "missing_price_after": int(df["price"].isna().sum()),
        "zero_review_games": int((df["total_reviews"] == 0).sum()),
        "total_positive_ratings": int(df["positive_ratings"].sum()),
        "total_negative_ratings": int(df["negative_ratings"].sum()),
        "overall_weighted_positive_pct": round(100 * df["positive_ratings"].sum() / df["total_reviews"].sum(), 2),
        "median_game_rating_pct": round(float(df["rating_pct"].median()), 2),
        "median_reviews_per_game": int(df["total_reviews"].median()),
    }
    (RESULTS / "summary.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    save_csv(pd.DataFrame([quality]), "data_quality")

    yearly = (
        df[df["release_year"].between(1997, 2019)]
        .groupby("release_year", observed=True)
        .agg(games=("appid", "size"), total_reviews=("total_reviews", "sum"), mean_rating_pct=("rating_pct", "mean"))
        .reset_index()
    )
    yearly["mean_rating_pct"] = yearly["mean_rating_pct"].round(2)
    save_csv(yearly, "yearly")

    genre_long = df.assign(genre=df["genres"].str.split(";")).explode("genre")
    genre_long["genre"] = genre_long["genre"].str.strip()
    genre_long = genre_long[genre_long["genre"] != ""]
    genre = (
        genre_long.groupby("genre")
        .agg(games=("appid", "nunique"), total_reviews=("total_reviews", "sum"), mean_rating_pct=("rating_pct", "mean"), mean_wilson_pct=("wilson_score", lambda x: 100 * x.mean()))
        .query("games >= 100")
        .sort_values("mean_wilson_pct", ascending=False)
        .reset_index()
    )
    genre[["mean_rating_pct", "mean_wilson_pct"]] = genre[["mean_rating_pct", "mean_wilson_pct"]].round(2)
    save_csv(genre, "genre")

    price = (
        df.groupby("price_band", observed=True)
        .agg(games=("appid", "size"), mean_price=("price", "mean"), mean_rating_pct=("rating_pct", "mean"), median_reviews=("total_reviews", "median"))
        .reindex(labels)
        .reset_index()
    )
    price[["mean_price", "mean_rating_pct"]] = price[["mean_price", "mean_rating_pct"]].round(2)
    price["median_reviews"] = price["median_reviews"].fillna(0).astype(int)
    save_csv(price, "price_band")

    top = (
        df[df["total_reviews"] >= 1000]
        .nlargest(20, "wilson_score")[["appid", "name", "total_reviews", "rating_pct", "wilson_score", "price"]]
        .copy()
    )
    top["rating_pct"] = top["rating_pct"].round(2)
    top["wilson_pct"] = (100 * top.pop("wilson_score")).round(2)
    save_csv(top, "top_reliable")

    publishers = (
        df[df["publisher"] != ""]
        .groupby("publisher")
        .agg(games=("appid", "size"), total_reviews=("total_reviews", "sum"), mean_wilson_pct=("wilson_score", lambda x: 100 * x.mean()))
        .query("games >= 10 and total_reviews >= 10000")
        .nlargest(20, "mean_wilson_pct")
        .reset_index()
    )
    publishers["mean_wilson_pct"] = publishers["mean_wilson_pct"].round(2)
    save_csv(publishers, "publishers")

    # Aggregate the wide SteamSpy vote matrix without materializing a 10M-row
    # melt. This mirrors the Spark sparse-long analysis while staying memory-safe.
    tags = pd.read_csv(TAG_RAW, low_memory=False).set_index("appid")
    tag_games = tags.gt(0).sum(axis=0)
    tag_votes = tags.sum(axis=0)
    rating_by_app = df.set_index("appid")["rating_pct"]
    aligned_ratings = rating_by_app.reindex(tags.index)
    tag_mean_rating = pd.Series({column: aligned_ratings[tags[column].gt(0)].mean() for column in tags.columns})
    top_tags = (
        pd.DataFrame({"tagged_games": tag_games, "total_tag_votes": tag_votes, "mean_rating_pct": tag_mean_rating})
        .sort_values("total_tag_votes", ascending=False)
        .head(30)
        .reset_index(names="tag")
    )
    top_tags["mean_rating_pct"] = top_tags["mean_rating_pct"].round(2)
    save_csv(top_tags, "top_tags")

    # Figure 1: market evolution.
    fig, ax = plt.subplots(figsize=(10, 5.3), dpi=180)
    ax.bar(yearly["release_year"].astype(int), yearly["games"], color=PALETTE[1], alpha=0.88)
    style_axis(ax, "Steam catalogue growth accelerated sharply", "Release year", "Games released")
    ax2 = ax.twinx()
    ax2.plot(yearly["release_year"].astype(int), yearly["mean_rating_pct"], color=PALETTE[3], marker="o", linewidth=2, markersize=3)
    ax2.set_ylabel("Mean game-level positive rate (%)", color=PALETTE[3])
    ax2.spines["top"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "01_market_evolution.png", bbox_inches="tight")
    plt.close(fig)

    # Figure 2: genre quality and scale.
    plot_genre = genre.sort_values("total_reviews", ascending=False).head(12).sort_values("mean_wilson_pct")
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=180)
    sizes = 80 + 520 * np.sqrt(plot_genre["total_reviews"] / plot_genre["total_reviews"].max())
    ax.scatter(plot_genre["games"], plot_genre["mean_wilson_pct"], s=sizes, c=PALETTE[0], alpha=0.72, edgecolor="white", linewidth=1)
    for _, row in plot_genre.iterrows():
        ax.annotate(row["genre"], (row["games"], row["mean_wilson_pct"]), xytext=(5, 4), textcoords="offset points", fontsize=8)
    style_axis(ax, "Genre comparison: catalogue size, quality and attention", "Number of games", "Mean Wilson lower bound (%)")
    fig.tight_layout()
    fig.savefig(FIGURES / "02_genre_quality.png", bbox_inches="tight")
    plt.close(fig)

    # Figure 3: price bands.
    fig, ax = plt.subplots(figsize=(10, 5.3), dpi=180)
    bars = ax.bar(price["price_band"].astype(str), price["mean_rating_pct"], color=PALETTE)
    style_axis(ax, "Price is not a simple proxy for player satisfaction", "Launch price band (GBP)", "Mean positive rate (%)")
    ax.set_ylim(max(0, price["mean_rating_pct"].min() - 8), min(100, price["mean_rating_pct"].max() + 5))
    for bar, value in zip(bars, price["mean_rating_pct"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.5, f"{value:.1f}%", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES / "03_price_bands.png", bbox_inches="tight")
    plt.close(fig)

    # Figure 4: reliable game ranking.
    plot_top = top.head(12).sort_values("wilson_pct").copy()
    plot_top["display_name"] = plot_top["name"].map(display_name)
    fig, ax = plt.subplots(figsize=(10, 6.3), dpi=180)
    ax.barh(plot_top["display_name"], plot_top["wilson_pct"], color=PALETTE[4], alpha=0.84)
    style_axis(ax, "Top games after uncertainty-aware ranking", "95% Wilson lower bound (%)", "")
    ax.set_xlim(max(0, plot_top["wilson_pct"].min() - 2), 100)
    fig.tight_layout()
    fig.savefig(FIGURES / "04_top_reliable.png", bbox_inches="tight")
    plt.close(fig)

    # Figure 5: why raw means mislead at small n.
    sample = df[(df["total_reviews"] > 0) & (df["total_reviews"] <= df["total_reviews"].quantile(0.995))]
    fig, ax = plt.subplots(figsize=(10, 5.3), dpi=180)
    ax.scatter(np.log10(sample["total_reviews"]), sample["rating_pct"], s=5, alpha=0.09, color=PALETTE[1], rasterized=True)
    style_axis(ax, "Small samples produce extreme-looking ratings", "log10(total reviews)", "Positive rate (%)")
    fig.tight_layout()
    fig.savefig(FIGURES / "05_sample_uncertainty.png", bbox_inches="tight")
    plt.close(fig)

    print(json.dumps(quality, indent=2))
    print("Top reliable games:")
    print(top.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
