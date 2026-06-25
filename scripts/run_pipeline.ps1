param(
    [string]$HdfsRoot = "/projects/steam",
    [string]$Output = "output/results/spark"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Output | Out-Null

spark-submit `
    --master yarn `
    --deploy-mode client `
    --conf spark.sql.adaptive.enabled=true `
    --conf spark.sql.shuffle.partitions=24 `
    src/steam_analysis.py `
    --input "$HdfsRoot/raw/steam.csv" `
    --tags "$HdfsRoot/raw/steamspy_tag_data.csv" `
    --curated "$HdfsRoot/curated/games" `
    --output $Output

