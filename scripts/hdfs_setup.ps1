param(
    [string]$LocalData = "data/raw",
    [string]$HdfsRoot = "/projects/steam"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "$LocalData/steam.csv")) {
    throw "Missing $LocalData/steam.csv. Extract the Kaggle dataset first."
}

hdfs dfs -mkdir -p "$HdfsRoot/raw"
hdfs dfs -mkdir -p "$HdfsRoot/curated"
hdfs dfs -mkdir -p "$HdfsRoot/checkpoints"

# Raw is immutable. -f makes rerunning the ingestion deterministic.
hdfs dfs -put -f "$LocalData/steam.csv" "$HdfsRoot/raw/steam.csv"
if (Test-Path "$LocalData/steamspy_tag_data.csv") {
    hdfs dfs -put -f "$LocalData/steamspy_tag_data.csv" "$HdfsRoot/raw/steamspy_tag_data.csv"
}

hdfs dfs -ls -h "$HdfsRoot/raw"

