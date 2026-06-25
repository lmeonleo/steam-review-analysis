"""Distributed ETL and analysis for the Steam Store Games dataset.

The script deliberately keeps raw, curated, and analytical layers separate.
It uses explicit types, quality flags, multi-label normalization, Spark SQL,
window/statistical functions, and Wilson lower-bound ranking.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)


STEAM_SCHEMA = StructType([
    StructField("appid", IntegerType(), False),
    StructField("name", StringType(), True),
    StructField("release_date", DateType(), True),
    StructField("english", IntegerType(), True),
    StructField("developer", StringType(), True),
    StructField("publisher", StringType(), True),
    StructField("platforms", StringType(), True),
    StructField("required_age", IntegerType(), True),
    StructField("categories", StringType(), True),
    StructField("genres", StringType(), True),
    StructField("steamspy_tags", StringType(), True),
    StructField("achievements", IntegerType(), True),
    StructField("positive_ratings", LongType(), True),
    StructField("negative_ratings", LongType(), True),
    StructField("average_playtime", DoubleType(), True),
    StructField("median_playtime", DoubleType(), True),
    StructField("owners", StringType(), True),
    StructField("price", DoubleType(), True),
])


@F.udf(DoubleType())
def wilson_lower_bound(positive: int | None, total: int | None) -> float | None:
    """95% Wilson lower confidence bound for a binomial positive rate."""
    if not positive or not total or total <= 0:
        return None
    z = 1.959963984540054
    phat = positive / total
    denominator = 1 + z * z / total
    center = phat + z * z / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return float((center - margin) / denominator)


def read_games(spark: SparkSession, path: str) -> DataFrame:
    return (
        spark.read.option("header", True)
        .option("dateFormat", "yyyy-MM-dd")
        .option("mode", "PERMISSIVE")
        .schema(STEAM_SCHEMA)
        .csv(path)
    )


def clean_games(raw: DataFrame) -> DataFrame:
    strings = ["name", "developer", "publisher", "platforms", "categories", "genres", "steamspy_tags", "owners"]
    df = raw
    for column in strings:
        df = df.withColumn(column, F.trim(F.col(column)))

    df = (
        df.dropDuplicates(["appid"])
        .filter(F.col("appid").isNotNull() & F.col("name").isNotNull())
        .withColumn("positive_ratings", F.greatest(F.coalesce("positive_ratings", F.lit(0)), F.lit(0)))
        .withColumn("negative_ratings", F.greatest(F.coalesce("negative_ratings", F.lit(0)), F.lit(0)))
        .withColumn("price", F.when(F.col("price") >= 0, F.col("price")))
        .withColumn("total_reviews", F.col("positive_ratings") + F.col("negative_ratings"))
        .withColumn(
            "rating_pct",
            F.when(F.col("total_reviews") > 0, 100 * F.col("positive_ratings") / F.col("total_reviews")),
        )
        .withColumn("wilson_score", wilson_lower_bound("positive_ratings", "total_reviews"))
        .withColumn("release_year", F.year("release_date"))
        .withColumn(
            "price_band",
            F.when(F.col("price") == 0, "Free")
            .when(F.col("price") < 5, "Under 5")
            .when(F.col("price") < 10, "5-10")
            .when(F.col("price") < 20, "10-20")
            .when(F.col("price") < 40, "20-40")
            .otherwise("40+"),
        )
        .withColumn("owner_lower", F.regexp_extract("owners", r"^(\\d+)", 1).cast("long"))
        .withColumn("owner_upper", F.regexp_extract("owners", r"(\\d+)$", 1).cast("long"))
        .withColumn("owner_midpoint", (F.col("owner_lower") + F.col("owner_upper")) / 2)
        .withColumn("has_missing_core", F.col("release_date").isNull() | F.col("price").isNull())
    )
    return df


def exploded_view(df: DataFrame, source: str, alias: str) -> DataFrame:
    return (
        df.select("appid", F.explode_outer(F.split(F.col(source), ";")).alias(alias))
        .withColumn(alias, F.trim(F.col(alias)))
        .filter(F.col(alias).isNotNull() & (F.col(alias) != ""))
        .dropDuplicates(["appid", alias])
    )


def write_result(df: DataFrame, root: str, name: str, order_by: list[str] | None = None) -> None:
    if order_by:
        df = df.orderBy(*order_by)
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(f"{root}/{name}")


def analyse(spark: SparkSession, games: DataFrame, output: str, tags_path: str = "") -> None:
    genres = exploded_view(games, "genres", "genre")
    platforms = exploded_view(games, "platforms", "platform")
    games.createOrReplaceTempView("games")
    genres.join(games.select("appid", "total_reviews", "rating_pct", "wilson_score"), "appid").createOrReplaceTempView("game_genres")
    platforms.join(games.select("appid", "rating_pct"), "appid").createOrReplaceTempView("game_platforms")

    quality = games.agg(
        F.count("*").alias("clean_rows"),
        F.countDistinct("appid").alias("distinct_appids"),
        F.sum(F.col("release_date").isNull().cast("int")).alias("missing_release_date"),
        F.sum(F.col("price").isNull().cast("int")).alias("missing_price"),
        F.sum((F.col("total_reviews") == 0).cast("int")).alias("zero_review_games"),
    )
    write_result(quality, output, "data_quality")

    yearly = spark.sql("""
        SELECT release_year, COUNT(*) games, SUM(total_reviews) total_reviews,
               ROUND(AVG(rating_pct), 2) mean_rating_pct
        FROM games WHERE release_year BETWEEN 1997 AND 2019
        GROUP BY release_year ORDER BY release_year
    """)
    write_result(yearly, output, "yearly")

    genre = spark.sql("""
        SELECT genre, COUNT(*) games, SUM(total_reviews) total_reviews,
               ROUND(AVG(rating_pct), 2) mean_rating_pct,
               ROUND(AVG(wilson_score) * 100, 2) mean_wilson_pct
        FROM game_genres GROUP BY genre HAVING COUNT(*) >= 100
        ORDER BY mean_wilson_pct DESC
    """)
    write_result(genre, output, "genre")

    price = spark.sql("""
        SELECT price_band, COUNT(*) games, ROUND(AVG(price), 2) mean_price,
               ROUND(AVG(rating_pct), 2) mean_rating_pct,
               CAST(percentile_approx(total_reviews, 0.5) AS BIGINT) median_reviews
        FROM games GROUP BY price_band
    """)
    write_result(price, output, "price_band")

    top = spark.sql("""
        SELECT appid, name, total_reviews, ROUND(rating_pct, 2) rating_pct,
               ROUND(wilson_score * 100, 2) wilson_pct, price
        FROM games WHERE total_reviews >= 1000
        ORDER BY wilson_score DESC LIMIT 20
    """)
    write_result(top, output, "top_reliable")

    publishers = spark.sql("""
        SELECT publisher, COUNT(*) games, SUM(total_reviews) total_reviews,
               ROUND(AVG(wilson_score) * 100, 2) mean_wilson_pct
        FROM games WHERE publisher IS NOT NULL AND publisher <> ''
        GROUP BY publisher HAVING COUNT(*) >= 10 AND SUM(total_reviews) >= 10000
        ORDER BY mean_wilson_pct DESC LIMIT 20
    """)
    write_result(publishers, output, "publishers")

    # SteamSpy tag data is wide (one integer vote-count column per tag). Convert
    # it to a sparse long table without collecting records on the driver.
    if tags_path:
        tag_raw = spark.read.option("header", True).option("inferSchema", True).csv(tags_path)
        tag_columns = [column for column in tag_raw.columns if column != "appid"]
        tag_long = (
            tag_raw.select(
                F.col("appid").cast("int").alias("appid"),
                F.explode(F.array(*[
                    F.struct(F.lit(column).alias("tag"), F.col(column).cast("long").alias("votes"))
                    for column in tag_columns
                ])).alias("tag_vote"),
            )
            .select("appid", "tag_vote.tag", "tag_vote.votes")
            .filter(F.col("votes") > 0)
        )
        tag_votes = tag_long.join(games.select("appid", "rating_pct"), "appid").cache()
        tag_votes.createOrReplaceTempView("tag_votes")
        top_tags = (
            tag_votes
            .groupBy("tag")
            .agg(
                F.countDistinct("appid").alias("tagged_games"),
                F.sum("votes").alias("total_tag_votes"),
                F.round(F.avg("rating_pct"), 2).alias("mean_rating_pct"),
            )
            .orderBy(F.col("total_tag_votes").desc())
            .limit(30)
        )
        write_result(top_tags, output, "top_tags")
        tag_votes.unpersist()

    # Innovation/depth: rank within release year to compare games against their era.
    era_window = Window.partitionBy("release_year").orderBy(F.col("wilson_score").desc_nulls_last())
    era = (
        games.filter((F.col("total_reviews") >= 1000) & F.col("release_year").isNotNull())
        .withColumn("era_rank", F.dense_rank().over(era_window))
        .filter(F.col("era_rank") <= 3)
        .select("release_year", "era_rank", "appid", "name", "total_reviews", "rating_pct", "wilson_score")
    )
    write_result(era, output, "era_champions", ["release_year", "era_rank"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--tags", default="")
    parser.add_argument("--curated", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("SteamReviewAnalysis")
        .config("spark.sql.session.timeZone", "UTC")
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    raw = read_games(spark, args.input)
    games = clean_games(raw).cache()
    games.write.mode("overwrite").partitionBy("release_year").parquet(args.curated)
    curated = spark.read.parquet(args.curated).cache()
    analyse(spark, curated, args.output, args.tags)
    print(f"Completed Steam analysis: {curated.count():,} cleaned games")
    spark.stop()


if __name__ == "__main__":
    main()
