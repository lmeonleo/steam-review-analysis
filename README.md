# Steam Review Analysis - Big Data Final Project

This repository is a complete, reproducible final project built around the
Kaggle **Steam Store Games** dataset. The assessed implementation uses HDFS,
PySpark, and Spark SQL; a lightweight local runner is included only to verify
the numerical results and build the report on a machine without Hadoop.

## Deliverables

- `output/pdf/Steam_Review_Analysis_Report.pdf` - final report
- `src/steam_analysis.py` - complete PySpark ETL and analysis pipeline
- `sql/steam_analysis.sql` - reusable Spark SQL / HiveQL queries
- `scripts/hdfs_setup.ps1` and `scripts/run_pipeline.ps1` - ingestion and run scripts
- `tools/local_reference_analysis.py` - independent local result verification
- `tools/build_report.py` - deterministic PDF report generator
- `data/raw/` - original Kaggle CSV files (not duplicated in HDFS)
- `output/results/` - machine-readable analytical results
- `output/figures/` - report figures
- `dashboard/app.py` - optional interactive bonus dashboard

## Dataset

Source: Nik Davis, *Steam Store Games*, Kaggle:
`https://www.kaggle.com/datasets/nikdavis/steam-store-games/data`

The project uses `steam.csv` as the game-level fact table and
`steamspy_tag_data.csv` as a wide tag table. Ratings are aggregate positive and
negative recommendation counts; they are not individual review texts. The
report uses the more precise term **review outcome analysis** where relevant.

## Cluster execution

Prerequisites: Hadoop/HDFS, Spark 3.5+, Python 3.10+, and the CSV files in
`data/raw`.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hdfs_setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_pipeline.ps1
```

The pipeline reads from `/projects/steam/raw`, writes partitioned Parquet to
`/projects/steam/curated/games`, and materializes result CSVs under
`output/results/spark`. It is idempotent: curated and result paths are replaced
on each run while raw inputs remain immutable.

## Local verification and report build

```powershell
python tools/local_reference_analysis.py
python tools/build_report.py
```

Install visualization dependencies with `pip install -r requirements-local.txt`.
The local runner is not presented as a substitute for Spark; it provides a
second implementation for transparent result checking and PDF generation.

## Optional dashboard

```powershell
pip install -r requirements-dashboard.txt
streamlit run dashboard/app.py
```

The dashboard reads only pre-aggregated result files, so it starts quickly and
does not move raw data into a web process. Deploy it to Streamlit Community
Cloud or the course server if an accessible URL is required for bonus credit.

## Team metadata

Before submission, edit `project_metadata.json` with the real student names and
course information, then rerun `tools/build_report.py`.
