"""Build the editable DOCX final report from the supplied SCUT template."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(
    r"C:\Users\hp\xwechat_files\wxid_owx3mootag1922_1a09\msg\file\2026-06\Final Report Template.docx"
)
OUT_DIR = ROOT / "output" / "docx"
OUT_DOCX = OUT_DIR / "Steam_Review_Analysis_Final_Report_Revised.docx"
RESULTS = ROOT / "output" / "results" / "local"
FIGURES = ROOT / "output" / "figures"
TMP = ROOT / "tmp"
LOGO = TMP / "scut_template_image.jpeg"

ACCENT = RGBColor(151, 36, 43)  # restrained SCUT-like red
DARK = RGBColor(31, 41, 55)
MUTED = RGBColor(90, 100, 115)
LIGHT_FILL = "F7F2F2"
HEADER_FILL = "97242B"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(10)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_table_widths(table, widths_in: list[float]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    total_dxa = int(sum(widths_in) * 1440)
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total_dxa))
    tbl_w.set(qn("w:type"), "dxa")
    for row in table.rows:
        for idx, width in enumerate(widths_in):
            row.cells[idx].width = Inches(width)

def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "D9DEE7")


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_sep, text, fld_end])


def add_paragraph(doc: Document, text: str, style: str = "Normal", bold_prefix: str | None = None):
    p = doc.add_paragraph(style=style)
    if bold_prefix and text.startswith(bold_prefix):
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r2 = p.add_run(text[len(bold_prefix) :])
    else:
        p.add_run(text)
    return p


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.14)
        p.add_run("- ").bold = True
        p.add_run(item)

def add_numbered(doc: Document, items: list[str]) -> None:
    for idx, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.add_run(f"{idx}. ").bold = True
        p.add_run(item)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    # Plain heading paragraph avoids the supplied template's list-formatted
    # built-in Heading styles, which produced visible square bullets.
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0)
    p.paragraph_format.first_line_indent = Inches(0)
    p.paragraph_format.space_before = Pt(13 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(5)
    run = p.add_run(text)
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    run.font.size = Pt(15 if level == 1 else 12.5)
    run.font.color.rgb = ACCENT if level <= 2 else DARK
    run.bold = True

def add_caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED


def add_figure(doc: Document, path: Path, caption: str, width: float = 5.45) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def add_small_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    set_table_borders(table)
    set_table_widths(table, widths)
    for i, h in enumerate(headers):
        set_cell_shading(table.rows[0].cells[i], HEADER_FILL)
        set_cell_text(table.rows[0].cells[i], h, bold=True, color=RGBColor(255, 255, 255))
    for row_data in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row_data):
            set_cell_text(cells[i], value)
            if len(table.rows) % 2 == 1:
                set_cell_shading(cells[i], LIGHT_FILL)
    doc.add_paragraph()


def setup_styles(doc: Document) -> None:
    section = doc.sections[-1]
    section.top_margin = Inches(0.95)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(1.1)
    section.right_margin = Inches(1.1)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.35)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = DARK
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12

    for name, size in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)]:
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = ACCENT if name != "Heading 3" else DARK
        style.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        style.paragraph_format.space_after = Pt(5)


def extract_logo() -> None:
    TMP.mkdir(exist_ok=True)
    with ZipFile(TEMPLATE) as z:
        LOGO.write_bytes(z.read("word/media/image1.jpeg"))


def add_running_header(section) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(LOGO), width=Inches(1.2))
    label = p.add_run("   Steam Review Analysis | Big Data Final Project")
    label.font.size = Pt(8.5)
    label.font.color.rgb = MUTED

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    team = fp.add_run("Steam Insight Lab")
    team.font.size = Pt(8.5)
    team.font.color.rgb = MUTED

def fill_cover(doc: Document, metadata: dict) -> None:
    # Preserve the provided cover layout while filling the template fields.
    if doc.tables:
        table = doc.tables[0]
        values = {
            "Student Name": " / ".join(metadata["members"]),
            "Student ID": "",
            "Major": "Data Science and Big Data Technology",
            "Semester": "Second Semester of Academic Year 2025-2026",
        }
        for row in table.rows:
            key = row.cells[0].text.strip()
            for field, value in values.items():
                if field in key:
                    row.cells[1].text = value


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    extract_logo()

    metadata = json.loads((ROOT / "project_metadata.json").read_text(encoding="utf-8"))
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    genre = pd.read_csv(RESULTS / "genre.csv")
    price = pd.read_csv(RESULTS / "price_band.csv")
    top_games = pd.read_csv(RESULTS / "top_reliable.csv")
    publishers = pd.read_csv(RESULTS / "publishers.csv")
    top_tags = pd.read_csv(RESULTS / "top_tags.csv")

    doc = Document(str(TEMPLATE))
    fill_cover(doc, metadata)

    section = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_styles(doc)
    add_running_header(section)

    add_heading(doc, "Steam Review Analysis", 1)
    add_paragraph(
        doc,
        "This report analyzes the Kaggle Steam Store Games dataset using a big data "
        "workflow designed around HDFS storage, PySpark preprocessing, Spark SQL "
        "aggregation, and Python-based visualization. The public dashboard is available at "
        "https://steam-review-analysis-lmeonleo.streamlit.app/.",
    )

    add_small_table(
        doc,
        ["Item", "Description"],
        [
            ["Dataset", "Steam Store Games by Nik Davis on Kaggle"],
            ["Records", f"{summary['clean_rows']:,} game-level records after cleaning"],
            ["Review outcomes", f"{summary['total_positive_ratings'] + summary['total_negative_ratings']:,} positive/negative rating outcomes"],
            ["Team", f"{metadata['team_name']} - {' / '.join(metadata['members'])}"],
            ["Tools", "HDFS, PySpark, Spark SQL, Pandas, Matplotlib/Seaborn, Streamlit"],
        ],
        [1.25, 4.75],
    )

    add_heading(doc, "1. Dataset Introduction", 1)
    add_paragraph(
        doc,
        "The selected topic is Steam Review Analysis. The source data comes from the "
        "real Kaggle dataset 'Steam Store Games', which contains game metadata, prices, "
        "genres, platforms, SteamSpy tags, and aggregate positive and negative review "
        "counts. Because the available review fields are aggregate ratings rather than "
        "individual text reviews, the project focuses on review outcome analysis: how "
        "many users responded positively or negatively, and how those outcomes vary by "
        "year, genre, price band, publisher, and tag.",
    )
    add_paragraph(
        doc,
        "The cleaned game table contains 27,075 games and 32.8 million review outcomes. "
        "The overall weighted positive rate is 82.58%, while the median number of review "
        "outcomes per game is 36, indicating a long-tail catalogue in which a small number "
        "of games receive very high attention.",
    )

    add_heading(doc, "2. HDFS Storage and Access Strategy", 1)
    add_paragraph(
        doc,
        "The project separates raw, curated, and analytical data zones so that the pipeline "
        "is reproducible and safe to rerun. Raw CSV files are copied into HDFS without "
        "modification, cleaned game records are written as partitioned Parquet, and final "
        "analysis outputs are materialized as compact CSV result tables for reporting and "
        "the dashboard.",
    )
    add_small_table(
        doc,
        ["Layer", "HDFS / Local Path", "Purpose"],
        [
            ["Raw zone", "/projects/steam/raw", "Immutable Kaggle CSV files"],
            ["Curated zone", "/projects/steam/curated/games", "Cleaned Parquet table partitioned by release year"],
            ["Result zone", "output/results/spark", "Aggregated CSV outputs from Spark SQL"],
            ["Web layer", "output/results/local", "Small pre-aggregated files read by Streamlit"],
        ],
        [1.05, 2.05, 2.9],
    )

    add_heading(doc, "3. Data Preprocessing", 1)
    add_paragraph(
        doc,
        "The preprocessing pipeline is implemented in PySpark with an explicit schema. "
        "Key steps include parsing release dates, converting price and rating fields to "
        "numeric types, handling missing or malformed values, deriving total review counts "
        "and positive-rate percentages, splitting semicolon-delimited genres, and exploding "
        "platform indicators for analysis.",
    )
    add_numbered(
        doc,
        [
            "Load CSV files from HDFS using explicit Spark schemas.",
            "Normalize release dates, prices, platforms, genres, publishers, and rating counts.",
            "Remove or repair invalid rows while preserving the original raw zone.",
            "Derive analytical fields: release year, review total, positive percentage, price band, and Wilson lower bound.",
            "Write curated records to Parquet and run Spark SQL aggregations.",
        ],
    )

    add_heading(doc, "4. Analytical Questions and Methods", 1)
    add_bullets(
        doc,
        [
            "How did the Steam catalogue expand over time, and how did average reception change?",
            "Which genres combine broad coverage with reliable user reception?",
            "How do price bands relate to positive rates and review attention?",
            "Which games rank highest after accounting for uncertainty in small samples?",
            "Which publishers and tags dominate the reviewed catalogue?",
        ],
    )
    add_paragraph(
        doc,
        "Spark SQL is used for grouping, filtering, ranking, and producing final result "
        "tables. The ranking method uses the 95% Wilson lower confidence bound rather "
        "than raw positive rate alone, because a game with 3 positive reviews out of 3 "
        "should not outrank a game with hundreds of thousands of highly positive reviews.",
    )

    add_heading(doc, "5. Key Findings and Visualizations", 1)
    add_heading(doc, "5.1 Catalogue Growth", 2)
    add_paragraph(
        doc,
        "The number of games released per year rises sharply in the later years of the "
        "snapshot, especially after the mid-2010s. Mean positive reception remains within "
        "a relatively stable band, suggesting that the platform's growth reflects market "
        "expansion rather than a simple collapse in average user satisfaction.",
    )
    add_figure(doc, FIGURES / "01_market_evolution.png", "Figure 1. Steam catalogue growth and rating trend by release year.")

    add_heading(doc, "5.2 Genre-Level Reception", 2)
    add_paragraph(
        doc,
        "Genre analysis shows that genre labels overlap substantially, so one game can "
        "contribute to multiple categories. Wilson-adjusted genre scores make the comparison "
        "more conservative by considering both rating level and sample reliability.",
    )
    add_figure(doc, FIGURES / "02_genre_quality.png", "Figure 2. Genre coverage and Wilson-adjusted reception.")

    add_small_table(
        doc,
        ["Genre", "Games", "Total reviews", "Mean rating %", "Mean Wilson %"],
        [
            [
                str(r["genre"]),
                f"{int(r['games']):,}",
                f"{int(r['total_reviews']):,}",
                f"{r['mean_rating_pct']:.2f}",
                f"{r['mean_wilson_pct']:.2f}",
            ]
            for _, r in genre.head(6).iterrows()
        ],
        [1.45, 0.75, 1.15, 1.25, 1.25],
    )

    add_heading(doc, "5.3 Price Bands", 2)
    add_paragraph(
        doc,
        "Price bands are interpreted descriptively rather than causally. Mid-priced games "
        "tend to receive more review attention than very low-priced games, while free games "
        "show broad catalogue coverage and high median review counts.",
    )
    add_figure(doc, FIGURES / "03_price_bands.png", "Figure 3. Rating level and review attention by price band.")
    add_small_table(
        doc,
        ["Price band", "Games", "Mean price", "Mean rating %", "Median reviews"],
        [
            [
                str(r["price_band"]),
                f"{int(r['games']):,}",
                f"{r['mean_price']:.2f}",
                f"{r['mean_rating_pct']:.2f}",
                f"{int(r['median_reviews']):,}",
            ]
            for _, r in price.iterrows()
        ],
        [1.05, 0.75, 0.95, 1.35, 1.35],
    )

    add_heading(doc, "5.4 Reliable Game Rankings", 2)
    best = top_games.iloc[0]
    add_paragraph(
        doc,
        f"The highest-ranked game by Wilson lower bound is {best['name']}. This confirms "
        "that the ranking is not simply rewarding small-sample perfect scores; it favours "
        "games with both strong reception and sufficient review volume.",
    )
    add_figure(doc, FIGURES / "04_top_reliable.png", "Figure 4. Most reliable highly rated games by Wilson lower bound.")
    add_small_table(
        doc,
        ["Rank", "Game", "Reviews", "Rating %", "Wilson %"],
        [
            [
                str(i + 1),
                str(r["name"]),
                f"{int(r['total_reviews']):,}",
                f"{r['rating_pct']:.2f}",
                f"{r['wilson_pct']:.2f}",
            ]
            for i, (_, r) in enumerate(top_games.head(8).iterrows())
        ],
        [0.55, 2.65, 1.05, 0.9, 0.9],
    )

    add_heading(doc, "5.5 Publishers and Tags", 2)
    add_paragraph(
        doc,
        "Publisher portfolio analysis identifies publishers with both sufficient catalogue "
        "size and strong user reception. SteamSpy tags show the market's dominant content "
        "signals, with Action, Indie, Adventure, Multiplayer, and Singleplayer among the "
        "most-voted tags.",
    )
    add_small_table(
        doc,
        ["Publisher", "Games", "Total reviews", "Mean Wilson %"],
        [
            [
                str(r["publisher"]),
                f"{int(r['games']):,}",
                f"{int(r['total_reviews']):,}",
                f"{r['mean_wilson_pct']:.2f}",
            ]
            for _, r in publishers.head(6).iterrows()
        ],
        [2.1, 0.85, 1.45, 1.2],
    )
    add_small_table(
        doc,
        ["Tag", "Tagged games", "Total tag votes", "Mean rating %"],
        [
            [
                str(r["tag"]),
                f"{int(r['tagged_games']):,}",
                f"{int(r['total_tag_votes']):,}",
                f"{r['mean_rating_pct']:.2f}",
            ]
            for _, r in top_tags.head(10).iterrows()
        ],
        [1.45, 1.15, 1.45, 1.25],
    )

    add_heading(doc, "6. Dashboard Implementation", 1)
    add_paragraph(
        doc,
        "The optional dashboard is implemented with Streamlit and deployed to Streamlit "
        "Community Cloud. It reads only pre-aggregated result files, which keeps the web "
        "application lightweight while preserving the full big-data workflow behind the "
        "analysis. Public URL: https://steam-review-analysis-lmeonleo.streamlit.app/.",
    )

    add_heading(doc, "7. Conclusion and Reflection", 1)
    add_paragraph(
        doc,
        "The project demonstrates a complete analytical workflow from raw data storage to "
        "cleaned distributed processing, SQL-based aggregation, visualization, interpretation, "
        "and web presentation. The strongest methodological choice is the use of Wilson "
        "lower-bound ranking, which makes the results more reliable than a raw percentage "
        "ranking. A limitation is that the dataset contains aggregate review outcomes rather "
        "than individual review texts, so sentiment analysis of written review content is "
        "outside the scope of this project.",
    )

    add_heading(doc, "8. Team Roles", 1)
    add_small_table(
        doc,
        ["Member", "Main responsibilities"],
        [
            ["\u9ad8\u660e\u654f", "HDFS ingestion, PySpark ETL design, Spark SQL analysis, visualization, interpretation, report and dashboard"],
        ],
        [1.35, 4.65],
    )

    add_heading(doc, "References", 1)
    add_bullets(
        doc,
        [
            "Nik Davis. Steam Store Games. Kaggle. https://www.kaggle.com/datasets/nikdavis/steam-store-games/data",
            "Apache Spark documentation. https://spark.apache.org/docs/latest/",
            "Apache Hadoop HDFS documentation. https://hadoop.apache.org/docs/",
            "Streamlit documentation. https://docs.streamlit.io/",
        ],
    )

    doc.save(OUT_DOCX)
    print(OUT_DOCX)


if __name__ == "__main__":
    build()
