-- Steam Review Analysis: Spark SQL / HiveQL-compatible analytical queries.
-- The PySpark pipeline registers the cleaned Parquet data as `games`.

-- Q1. Market evolution: releases and attention by year.
SELECT release_year,
       COUNT(*) AS games,
       SUM(total_reviews) AS total_reviews,
       ROUND(AVG(rating_pct), 2) AS mean_rating_pct
FROM games
WHERE release_year BETWEEN 1997 AND 2019
GROUP BY release_year
ORDER BY release_year;

-- Q2. Genre quality, reach, and sample size (multi-label genre exploded).
SELECT genre,
       COUNT(*) AS games,
       SUM(total_reviews) AS total_reviews,
       ROUND(AVG(rating_pct), 2) AS mean_rating_pct,
       ROUND(AVG(wilson_score) * 100, 2) AS mean_wilson_pct
FROM game_genres
GROUP BY genre
HAVING COUNT(*) >= 100
ORDER BY mean_wilson_pct DESC;

-- Q3. Price bands and review outcomes.
SELECT price_band,
       COUNT(*) AS games,
       ROUND(AVG(price), 2) AS mean_price,
       ROUND(AVG(rating_pct), 2) AS mean_rating_pct,
       CAST(percentile_approx(total_reviews, 0.5) AS BIGINT) AS median_reviews
FROM games
GROUP BY price_band
ORDER BY CASE price_band
    WHEN 'Free' THEN 0 WHEN 'Under 5' THEN 1 WHEN '5-10' THEN 2
    WHEN '10-20' THEN 3 WHEN '20-40' THEN 4 ELSE 5 END;

-- Q4. Reliable top games. Wilson lower bound prevents tiny samples winning.
SELECT appid, name, total_reviews, ROUND(rating_pct, 2) AS rating_pct,
       ROUND(wilson_score * 100, 2) AS wilson_pct, price
FROM games
WHERE total_reviews >= 1000
ORDER BY wilson_score DESC
LIMIT 20;

-- Q5. Platform coverage.
SELECT platform, COUNT(*) AS games,
       ROUND(AVG(rating_pct), 2) AS mean_rating_pct
FROM game_platforms
GROUP BY platform
ORDER BY games DESC;

-- Q6. Publishers with both scale and consistently strong reception.
SELECT publisher, COUNT(*) AS games, SUM(total_reviews) AS total_reviews,
       ROUND(AVG(wilson_score) * 100, 2) AS mean_wilson_pct
FROM games
WHERE publisher IS NOT NULL AND publisher <> ''
GROUP BY publisher
HAVING COUNT(*) >= 10 AND SUM(total_reviews) >= 10000
ORDER BY mean_wilson_pct DESC
LIMIT 20;

-- Q7. SteamSpy tags are normalized from wide vote columns by the PySpark
-- pipeline into tag_votes(appid, tag, votes).
SELECT tag, COUNT(DISTINCT appid) AS tagged_games,
       SUM(votes) AS total_tag_votes,
       ROUND(AVG(rating_pct), 2) AS mean_rating_pct
FROM tag_votes
GROUP BY tag
ORDER BY total_tag_votes DESC
LIMIT 30;
