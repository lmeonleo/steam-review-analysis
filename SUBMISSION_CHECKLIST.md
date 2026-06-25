# 提交前检查清单

1. 在 `project_metadata.json` 中把 `Student 1`、`Student 2` 换成真实姓名，并确认分工。
2. 重新运行：
   - `python tools/local_reference_analysis.py`
   - `python tools/build_report.py`
3. 在学校 Hadoop 环境运行：
   - `scripts/hdfs_setup.ps1`
   - `scripts/run_pipeline.ps1`
4. 保存终端中的 HDFS `ls`、Spark 完成日志和结果目录截图，答辩时作为运行证据。
5. 核对最终 PDF 封面姓名、页码、15 页图表及表格。
6. 可选加分：运行并部署 `dashboard/app.py`，把公开 URL 写进 README 或提交说明。
7. 建议提交：最终 PDF、`src/`、`sql/`、`scripts/`、`dashboard/`、`output/results/`、`output/figures/`、README 和依赖文件。

注意：报告中的数值来自真实数据并已本地复核；当前电脑没有 Hadoop/Java 服务，因此不要伪造集群截图，必须在课程集群补跑一次。
