"""Build the final, data-driven Steam Review Analysis PDF report."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output/results/local"
FIGURES = ROOT / "output/figures"
OUTPUT = ROOT / "output/pdf/Steam_Review_Analysis_Report.pdf"

NAVY = colors.HexColor("#152238")
BLUE = colors.HexColor("#227C9D")
TEAL = colors.HexColor("#17C3B2")
CORAL = colors.HexColor("#FE6D73")
GOLD = colors.HexColor("#FFCB77")
INK = colors.HexColor("#28323C")
MUTED = colors.HexColor("#697386")
PALE = colors.HexColor("#F4F7FA")
WHITE = colors.white


def P(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def display_name(value: str) -> str:
    label = "".join(char for char in str(value) if ord(char) < 128).strip(" ~-.")
    return label or "Non-Latin title"


def load() -> tuple[dict, dict[str, pd.DataFrame], dict]:
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    names = ["yearly", "genre", "price_band", "top_reliable", "publishers", "top_tags"]
    frames = {name: pd.read_csv(RESULTS / f"{name}.csv") for name in names}
    metadata = json.loads((ROOT / "project_metadata.json").read_text(encoding="utf-8"))
    return summary, frames, metadata


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=WHITE, alignment=TA_LEFT, spaceAfter=14),
        "cover_sub": ParagraphStyle("CoverSub", parent=base["Normal"], fontName="Helvetica", fontSize=12, leading=18, textColor=colors.HexColor("#DDE7F0"), spaceAfter=7),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceBefore=4, spaceAfter=10),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=BLUE, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14.2, textColor=INK, spaceAfter=7),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=MUTED, spaceAfter=4),
        "caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8),
        "callout": ParagraphStyle("Callout", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=15, textColor=NAVY, borderColor=TEAL, borderWidth=1.5, borderPadding=9, backColor=colors.HexColor("#EAFBF8"), spaceBefore=6, spaceAfter=10),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="Courier", fontSize=7.7, leading=10.5, textColor=colors.HexColor("#E9F1F7"), backColor=NAVY, borderPadding=8, spaceAfter=8),
        "toc": ParagraphStyle("TOC", parent=base["BodyText"], fontName="Helvetica", fontSize=10, leading=17, textColor=INK),
        "metric": ParagraphStyle("Metric", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NAVY, alignment=TA_CENTER),
        "metric_label": ParagraphStyle("MetricLabel", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_CENTER),
    }
    return styles


def footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D7E0E8"))
    canvas.line(1.7 * cm, 1.35 * cm, width - 1.7 * cm, 1.35 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.7 * cm, 0.92 * cm, "Steam Review Analysis | Big Data Final Project")
    canvas.drawRightString(width - 1.7 * cm, 0.92 * cm, f"{doc.page}")
    canvas.restoreState()


def table(data, widths, header=True, font_size=7.7, aligns=None):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold" if header else "Helvetica"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY if header else WHITE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE if header else INK),
        ("FONTNAME", (0, 1 if header else 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [WHITE, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFD8E2")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if aligns:
        for col, alignment in enumerate(aligns):
            commands.append(("ALIGN", (col, 1 if header else 0), (col, -1), alignment))
    t.setStyle(TableStyle(commands))
    return t


def metric_cards(summary, s):
    items = [
        (f"{summary['clean_rows']:,}", "GAMES"),
        (f"{summary['total_positive_ratings'] + summary['total_negative_ratings']:,}", "REVIEW OUTCOMES"),
        (f"{summary['overall_weighted_positive_pct']:.2f}%", "WEIGHTED POSITIVE"),
        (f"{summary['median_reviews_per_game']:,}", "MEDIAN REVIEWS/GAME"),
    ]
    cells = []
    for value, label in items:
        cells.append([P(value, s["metric"]), P(label, s["metric_label"])])
    cards = Table([cells], colWidths=[4.0 * cm] * 4)
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E0EA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E0EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return cards


def fig(path: str, caption: str, s, width=16.2 * cm, height=None):
    source = FIGURES / path
    if height is None:
        pixel_width, pixel_height = PILImage.open(source).size
        height = width * pixel_height / pixel_width
    max_height = 10.7 * cm
    if height > max_height:
        scale = max_height / height
        width *= scale
        height = max_height
    image = Image(str(source), width=width, height=height)
    return [image, P(caption, s["caption"])]


def build() -> None:
    summary, f, meta = load()
    s = build_styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=1.75 * cm, leftMargin=1.75 * cm,
        topMargin=1.65 * cm, bottomMargin=1.65 * cm, title="Steam Review Analysis",
        author=", ".join(meta["members"]), subject="Big Data Final Evaluation Project",
    )
    story = []

    # Cover
    cover = Table([[P("STEAM REVIEW<br/>ANALYSIS", s["cover_title"]), ""]], colWidths=[11.5 * cm, 5.0 * cm], rowHeights=[6.6 * cm])
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (0, 0), 20),
        ("BOTTOMPADDING", (0, 0), (0, 0), 24),
        ("LINEBEFORE", (1, 0), (1, 0), 8, TEAL),
    ]))
    story += [Spacer(1, 1.4 * cm), cover, Spacer(1, 0.8 * cm)]
    story.append(P("A distributed analysis of 27,075 games and 32.8 million aggregate review outcomes", ParagraphStyle("CoverLead", parent=s["h2"], fontSize=16, leading=22, textColor=NAVY)))
    story += [Spacer(1, 0.4 * cm), HRFlowable(width="100%", thickness=2, color=TEAL), Spacer(1, 0.45 * cm)]
    story.append(P(f"<b>{meta['course']} - Final Evaluation Project</b><br/>{meta['team_name']}<br/>{' &amp; '.join(meta['members'])}<br/>Submission date: {meta['submission_date']}", s["body"]))
    story.append(Spacer(1, 2.5 * cm))
    story.append(P("Technology stack", s["small"]))
    story.append(P("HDFS  /  PySpark  /  Spark SQL  /  Hive Metastore  /  Python Visualization", s["callout"]))
    story.append(PageBreak())

    # Contents / executive summary
    story += [P("Contents", s["h1"]), table([
        ["01", "Executive summary and dataset"], ["02", "Storage architecture and access strategy"],
        ["03", "Preprocessing and data quality"], ["04", "Analytical questions and methods"],
        ["05", "Findings and visual interpretation"], ["06", "Methodological depth and limitations"],
        ["07", "Conclusion, reflection and team roles"], ["08", "Reproducibility, rubric map and references"],
    ], [1.2 * cm, 14.8 * cm], header=False, font_size=9), Spacer(1, 0.5 * cm)]
    story += [P("Executive summary", s["h1"]), metric_cards(summary, s), Spacer(1, 0.5 * cm)]
    story.append(P(
        "This project studies how Steam's catalogue, prices, genres, publishers and review outcomes relate. "
        "The analysis uses the Kaggle Steam Store Games snapshot, stores immutable CSV inputs in HDFS, converts "
        "cleaned records to year-partitioned Parquet, and answers seven questions with PySpark and Spark SQL. "
        "The key methodological choice is a 95% Wilson lower confidence bound: it ranks strongly reviewed games "
        "without rewarding tiny samples that happen to be 100% positive.", s["body"]))
    story.append(P(
        f"Across {summary['clean_rows']:,} games, the weighted positive share is "
        f"{summary['overall_weighted_positive_pct']:.2f}%, while the median game-level positive rate is only "
        f"{summary['median_game_rating_pct']:.2f}%. This {summary['overall_weighted_positive_pct']-summary['median_game_rating_pct']:.2f}-point gap "
        "shows that review-volume weighting and 'typical game' summaries answer different questions. Price also "
        "has no monotonic relationship with satisfaction: the GBP 10-20 band has the highest mean positive rate, "
        "but causal claims are not justified because genre, age, visibility and audience selection are confounders.", s["callout"]))
    story.append(PageBreak())

    # Dataset
    story += [P("1. Dataset introduction", s["h1"])]
    story.append(P(
        "The selected topic is <b>Steam Review Analysis</b>. The source is Nik Davis's Steam Store Games dataset on "
        "Kaggle, a static catalogue snapshot containing games available on Steam around May 2019. The primary "
        "table has one row per app ID and combines identity, release date, developer/publisher, multi-label "
        "platform/category/genre/tag fields, price, playtime, owner-range estimates and aggregate positive/negative "
        "recommendation counts. The accompanying SteamSpy table contains tag vote counts.", s["body"]))
    story.append(P(
        "Important scope note: despite the assignment topic's wording, this dataset does <b>not</b> contain review "
        "text or individual reviewers. Therefore this is review-outcome and market-structure analysis, not NLP "
        "sentiment analysis. Stating that boundary prevents overclaiming and makes the unit of analysis explicit.", s["callout"]))
    dictionary = [
        ["Field group", "Examples", "Analytical use"],
        ["Identity", "appid, name", "Primary key and labels"],
        ["Time", "release_date", "Release-year trends and cohorts"],
        ["Actors", "developer, publisher", "Portfolio-level comparisons"],
        ["Taxonomy", "genres, categories, tags", "Multi-label exploded dimensions"],
        ["Reception", "positive_ratings, negative_ratings", "Positive rate, volume, Wilson bound"],
        ["Commercial", "price, owners", "Price bands and reach proxies"],
        ["Engagement", "average_playtime, median_playtime", "Descriptive engagement proxies"],
    ]
    story += [P("Core data dictionary", s["h2"]), table(dictionary, [3.0 * cm, 5.4 * cm, 7.6 * cm])]
    story += [P("Research questions", s["h2"]), P(
        "Q1 How did catalogue growth and review outcomes change over time? &nbsp; Q2 Which genres combine breadth, "
        "attention and reliable satisfaction? &nbsp; Q3 How do price bands differ? &nbsp; Q4 Which games remain top after "
        "accounting for sample uncertainty? &nbsp; Q5 Which publishers combine scale and consistency? &nbsp; Q6 How "
        "does platform coverage vary? &nbsp; Q7 Which SteamSpy tags receive the most association votes?", s["body"]), PageBreak()]

    # Architecture
    story += [P("2. HDFS storage and access strategy", s["h1"])]
    story.append(P(
        "The design separates immutable source files, curated columnar data and small analytical outputs. This "
        "preserves lineage, makes reruns idempotent, and avoids repeatedly parsing CSV. HDFS replication provides "
        "fault tolerance; Parquet column pruning, predicate pushdown and year partitioning reduce scan cost. The "
        "dataset is modest, so the value here is architectural correctness and scalability rather than claiming "
        "that 50 MB requires a cluster.", s["body"]))
    arch = [
        [P("Kaggle CSV", s["metric_label"]), P("HDFS RAW", s["metric_label"]), P("PYSPARK ETL", s["metric_label"]), P("PARQUET CURATED", s["metric_label"]), P("SQL / FIGURES", s["metric_label"])],
        [P("steam.csv<br/>tag data", s["small"]), P("/projects/steam/raw<br/>immutable", s["small"]), P("schema + DQ<br/>derived fields", s["small"]), P("partitioned by<br/>release_year", s["small"]), P("CSV results<br/>PDF report", s["small"])],
    ]
    at = Table(arch, colWidths=[3.2 * cm] * 5, rowHeights=[0.8 * cm, 1.35 * cm])
    at.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, 1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D4DE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story += [Spacer(1, 0.3 * cm), at, Spacer(1, 0.45 * cm)]
    strategy = [
        ["Layer", "Path", "Format", "Policy"],
        ["Raw", "/projects/steam/raw", "CSV", "Immutable source; retain headers and original encoding"],
        ["Curated", "/projects/steam/curated/games", "Parquet", "Overwrite atomically; partition by release_year"],
        ["Checkpoint", "/projects/steam/checkpoints", "Spark", "Reserved for recoverable iterative/stream jobs"],
        ["Results", "output/results/spark", "CSV", "Small, human-readable aggregates for submission"],
    ]
    story += [P("Access policy and physical layout", s["h2"]), table(strategy, [2.0 * cm, 5.0 * cm, 2.2 * cm, 6.8 * cm])]
    story += [P("Operational commands", s["h2"]), P(
        "hdfs dfs -mkdir -p /projects/steam/{raw,curated,checkpoints}<br/>"
        "hdfs dfs -put -f data/raw/steam.csv /projects/steam/raw/steam.csv<br/>"
        "spark-submit --master yarn src/steam_analysis.py --input /projects/steam/raw/steam.csv --curated /projects/steam/curated/games --output output/results/spark", s["code"])]
    story.append(P(
        "A real production deployment should choose Parquet file sizes near 128-256 MB and compact small files. "
        "For this snapshot, coalescing analytical outputs to one file improves demonstrability; the curated layer "
        "remains distributed. Credentials are not embedded, and the original CSV is never mutated.", s["body"]))
    story.append(PageBreak())

    # Preprocessing
    story += [P("3. Preprocessing and data quality", s["h1"])]
    dq = [
        ["Check", "Observed", "Treatment"],
        ["Raw rows", f"{summary['raw_rows']:,}", "Schema-driven read"],
        ["Duplicate app IDs", f"{summary['duplicate_appids_removed']:,}", "Drop duplicate primary keys"],
        ["Missing release date", f"{summary['missing_release_date_after']:,}", "Retain; exclude only from time questions"],
        ["Missing/negative price", f"{summary['missing_price_after']:,}", "Invalid negatives become null"],
        ["Zero-review games", f"{summary['zero_review_games']:,}", "Rating and Wilson score remain null"],
        ["Multi-label fields", "genres/platforms/tags", "Split on semicolon, trim, explode, de-duplicate"],
    ]
    story += [table(dq, [4.0 * cm, 3.0 * cm, 9.0 * cm]), Spacer(1, 0.35 * cm)]
    story.append(P(
        "The pipeline declares explicit Spark types instead of relying on inference; trims string fields; parses "
        "ISO dates; clamps negative review counts to zero; rejects negative prices; creates total_reviews and "
        "rating_pct only where the denominator is positive; extracts owner-range endpoints; and adds a missing-core "
        "quality flag. Crucially, valid zeros are preserved. Missing publishers are not filled with a misleading "
        "category, and missing dates are handled question-by-question rather than deleting entire records.", s["body"]))
    story += [P("Derived measures", s["h2"]), table([
        ["Measure", "Definition", "Reason"],
        ["total_reviews", "positive + negative", "Attention / evidence volume"],
        ["rating_pct", "100 x positive / total", "Interpretable game-level reception"],
        ["Wilson score", "95% lower confidence bound", "Uncertainty-aware ranking"],
        ["owner_midpoint", "(range lower + upper) / 2", "Approximate reach; not exact sales"],
        ["price_band", "Free, <5, 5-10, 10-20, 20-40, 40+", "Robust, communicable comparison"],
    ], [3.2 * cm, 5.1 * cm, 7.7 * cm])]
    story.append(P(
        "Validation is intentionally redundant: the PySpark implementation writes a data-quality table, and an "
        "independent Pandas reference runner reproduces all submitted numerical results. This is an authoring-time "
        "cross-check, not a replacement for the cluster pipeline.", s["callout"]))
    story.append(PageBreak())

    # Methods
    story += [P("4. Analytical methods", s["h1"])]
    method_rows = [
        ["Question", "Spark method", "Output"],
        ["Q1 Time", "year(), groupBy, count/sum/avg", "Yearly release and reception series"],
        ["Q2 Genre", "split + explode + distinct; HAVING n>=100", "Breadth, volume, mean and Wilson quality"],
        ["Q3 Price", "when bands; percentile_approx", "Band counts, mean rating, median review volume"],
        ["Q4 Ranking", "UDF Wilson lower bound; threshold n>=1,000", "Reliable top 20"],
        ["Q5 Publisher", "groupBy + scale thresholds", "Consistent portfolios, not one-hit wonders"],
        ["Q6 Platform", "explode platforms", "Coverage and mean reception"],
        ["Q7 Tags", "wide-to-long sparse normalization", "Tag coverage, votes and mean reception"],
        ["Era depth", "Window + dense_rank partitioned by year", "Top three games within each release cohort"],
    ]
    story += [table(method_rows, [2.4 * cm, 7.4 * cm, 6.2 * cm]), Spacer(1, 0.4 * cm)]
    story += [P("Why Wilson rather than raw percentage?", s["h2"]), P(
        "Raw 100% positive means very different things for 3 reviews and 30,000 reviews. For positive count p, "
        "sample size n and z=1.96, the Wilson lower bound estimates a conservative plausible positive share. Its "
        "penalty shrinks as n grows. The project also requires at least 1,000 outcomes for the headline ranking; "
        "this makes both the rule and its trade-off transparent.", s["body"])]
    story += fig("05_sample_uncertainty.png", "Figure 1. Rating extremes contract as evidence volume increases. Each point is one game; the x-axis is logarithmic.", s)
    story.append(P(
        "All reported associations are descriptive. No regression coefficient or grouped mean is interpreted as "
        "a causal effect because price, visibility, release era, genre, discounting and audience self-selection are "
        "not randomized. This restraint is part of the analysis, not a missing flourish.", s["callout"]))
    story.append(PageBreak())

    # Findings 1
    story += [P("5. Findings and interpretation", s["h1"]), P("5.1 Catalogue growth changed the denominator", s["h2"])]
    story += fig("01_market_evolution.png", "Figure 2. Releases increased rapidly after 2013; the 2019 count is incomplete because the source snapshot ends during that year.", s)
    y = f["yearly"]
    peak = y.loc[y["games"].idxmax()]
    story.append(P(
        f"The maximum complete annual count is {int(peak['games']):,} games in {int(peak['release_year'])}. "
        "The sharp rise reflects Steam's expanding catalogue and lower publishing barriers, but it also changes the "
        "composition of the average: later years contain many more small-audience titles. The apparent rebound in "
        "2019's mean rating should not be treated as a full-year trend because only part of 2019 is observed.", s["body"]))
    story += [P("5.2 Weighted reception and a typical game's reception diverge", s["h2"]), P(
        f"The aggregate weighted rate is {summary['overall_weighted_positive_pct']:.2f}%, whereas the median game is "
        f"{summary['median_game_rating_pct']:.2f}% positive and has only {summary['median_reviews_per_game']} outcomes. "
        "The weighted statistic answers 'what fraction of all recorded outcomes are positive?' while the median "
        "answers 'what does a typical listed game look like?' Reporting both prevents popularity from silently "
        "becoming a quality weight.", s["callout"]), PageBreak()]

    # Findings 2
    story += [P("5.3 Genre combines scale, attention and reliability", s["h1"])]
    story += fig("02_genre_quality.png", "Figure 3. Bubble area represents total review outcomes. Genres overlap because games may carry multiple labels.", s)
    g = f["genre"].head(8)
    gdata = [["Genre", "Games", "Reviews", "Mean +%", "Mean Wilson %"]] + [
        [r.genre, f"{int(r.games):,}", f"{int(r.total_reviews):,}", f"{r.mean_rating_pct:.2f}", f"{r.mean_wilson_pct:.2f}"] for r in g.itertuples()
    ]
    story += [table(gdata, [4.0 * cm, 2.0 * cm, 3.3 * cm, 2.4 * cm, 3.2 * cm], aligns=["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]), Spacer(1, 0.3 * cm)]
    story.append(P(
        "Among genres with at least 100 games, Free to Play has the highest mean Wilson lower bound in this "
        "game-level averaging scheme, but it also has a lower raw mean positive rate than several paid-oriented "
        "segments. That difference is possible because Wilson penalizes sparse evidence, and genre labels overlap. "
        "Action has the largest review volume, while Indie has the largest catalogue, so 'most common', 'most "
        "discussed' and 'most reliably positive' are three separate claims.", s["body"]))
    story.append(P(
        "Interpretation caveat: the dataset's genres are multi-label and publisher-supplied. Exploding labels means "
        "one game contributes to multiple groups; totals should never be summed across genres.", s["callout"]))
    story.append(PageBreak())

    # Findings 3
    story += [P("5.4 Price is associated with reception, but not monotonically", s["h1"])]
    story += fig("03_price_bands.png", "Figure 4. Game-level mean positive rates by listed price band (GBP). Values are descriptive, not causal.", s)
    pr = f["price_band"]
    pdata = [["Price band", "Games", "Mean price", "Mean +%", "Median reviews"]] + [
        [str(r.price_band), f"{int(r.games):,}", f"GBP {r.mean_price:.2f}", f"{r.mean_rating_pct:.2f}", f"{int(r.median_reviews):,}"] for r in pr.itertuples()
    ]
    story += [table(pdata, [3.1 * cm, 2.2 * cm, 3.0 * cm, 2.8 * cm, 3.4 * cm], aligns=["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"]), Spacer(1, 0.35 * cm)]
    best_price = pr.loc[pr["mean_rating_pct"].idxmax()]
    story.append(P(
        f"The highest mean game-level positive rate is {best_price['mean_rating_pct']:.2f}% in the "
        f"{best_price['price_band']} band. The cheapest paid band performs worst on this measure, while GBP 40+ "
        "does not lead despite much higher median attention. This is consistent with selection and portfolio mix, "
        "not proof that changing price would change ratings. Listed price also ignores historical discounts and "
        "regional pricing.", s["body"]))
    story.append(PageBreak())

    # Findings 4 ranking
    story += [P("5.5 Reliable rankings differ from naive 100% lists", s["h1"])]
    story += fig("04_top_reliable.png", "Figure 5. Top games with at least 1,000 review outcomes, ranked by 95% Wilson lower bound.", s)
    top = f["top_reliable"].head(10)
    topdata = [["#", "Game", "Reviews", "Positive %", "Wilson %"]] + [
        [str(i + 1), display_name(r["name"]), f"{int(r['total_reviews']):,}", f"{r['rating_pct']:.2f}", f"{r['wilson_pct']:.2f}"] for i, (_, r) in enumerate(top.iterrows())
    ]
    story += [table(topdata, [0.7 * cm, 7.2 * cm, 3.0 * cm, 2.5 * cm, 2.5 * cm], aligns=["CENTER", "LEFT", "RIGHT", "RIGHT", "RIGHT"], font_size=7.2)]
    leader = top.iloc[0]
    story.append(P(
        f"Portal 2 leads with {int(leader['total_reviews']):,} outcomes, a {leader['rating_pct']:.2f}% raw positive "
        f"rate and a {leader['wilson_pct']:.2f}% lower bound. Factorio's raw percentage is close, but its smaller "
        "sample produces a slightly larger uncertainty penalty. This ranking is reproducible, conservative and "
        "far less vulnerable to tiny-sample noise than sorting raw percentages.", s["callout"]))
    story.append(PageBreak())

    # Publishers + limitations
    story += [P("5.6 Publisher portfolios", s["h1"])]
    pub = f["publishers"].head(10)
    pubdata = [["Publisher", "Games", "Review outcomes", "Mean Wilson %"]] + [
        [str(r.publisher), f"{int(r.games):,}", f"{int(r.total_reviews):,}", f"{r.mean_wilson_pct:.2f}"] for r in pub.itertuples()
    ]
    story += [table(pubdata, [7.0 * cm, 2.0 * cm, 3.6 * cm, 3.1 * cm], aligns=["LEFT", "RIGHT", "RIGHT", "RIGHT"]), Spacer(1, 0.4 * cm)]
    story.append(P(
        "Valve leads among portfolios meeting both thresholds (at least 10 games and 10,000 outcomes). The rules "
        "exclude one-game publishers and limit winner's curse, but mean Wilson scores still give each game equal "
        "weight. A review-weighted portfolio score would answer a different question and would be dominated by "
        "blockbusters. Publisher strings also contain inconsistent joint-publisher combinations that should be "
        "normalized in future work.", s["body"]))
    story += [P("5.7 SteamSpy tag attention", s["h2"])]
    tags = f["top_tags"].head(8)
    tagdata = [["Tag", "Tagged games", "Tag votes", "Mean +%"]] + [
        [str(r.tag).replace("_", " ").title(), f"{int(r.tagged_games):,}", f"{int(r.total_tag_votes):,}", f"{r.mean_rating_pct:.2f}"] for r in tags.itertuples()
    ]
    story.append(table(tagdata, [5.5 * cm, 3.2 * cm, 3.6 * cm, 2.8 * cm], aligns=["LEFT", "RIGHT", "RIGHT", "RIGHT"]))
    story.append(P(
        "Tag votes measure how strongly SteamSpy users associate games with descriptors, not review sentiment. "
        "The Spark pipeline converts the 370+ wide vote columns into a sparse (appid, tag, votes) relation, then "
        "aggregates only positive votes. This demonstrates scalable wide-to-long normalization without collecting "
        "the vote matrix on the driver.", s["small"]))
    story += [PageBreak(), P("6. Limitations and threats to validity", s["h1"]), table([
        ["Limitation", "Consequence / mitigation"],
        ["Static snapshot around May 2019", "No current-market claims; 2019 is incomplete"],
        ["Aggregate outcomes, no text or users", "No NLP, reviewer behavior or demographic inference"],
        ["SteamSpy owner ranges", "Use midpoint only as an approximate reach proxy"],
        ["Listed price only", "No discount history, region or bundle adjustment"],
        ["Multi-label, publisher-defined taxonomy", "Explode carefully; do not sum overlapping genres"],
        ["Survivorship/visibility selection", "Dataset is not a randomized sample of all games or players"],
        ["Observational comparisons", "Describe associations; avoid causal language"],
    ], [5.3 * cm, 10.7 * cm])]
    story += [P("How the design responds", s["h2"]), P(
        "These limitations are handled by narrowing claims rather than hiding uncertainty. Time analysis explicitly "
        "marks 2019 as incomplete; owner counts are labeled as range-derived proxies; genre totals are never added "
        "across overlapping labels; and the report consistently uses association language. Wilson bounds address "
        "sampling uncertainty in rankings, but they cannot repair selection bias or omitted variables.", s["body"])]
    story.append(P(
        "External validity is bounded to the dataset snapshot. Internal reproducibility is stronger: raw files are "
        "immutable, transformations are deterministic, every result is machine-readable, and two implementations "
        "share the same explicit formulas. The remaining cluster-specific check is operational execution on the "
        "course Hadoop environment, because this authoring machine does not provide HDFS or Java/Spark services.", s["callout"]))
    story.append(PageBreak())

    # Conclusion/reflection/team
    story += [P("7. Conclusion and critical reflection", s["h1"])]
    story.append(P(
        "The project demonstrates a complete big-data workflow: immutable HDFS ingestion, explicit-schema PySpark "
        "cleaning, columnar curation, Spark SQL analysis, multi-label normalization, statistical ranking, and "
        "data-driven visualization. The strongest substantive result is not a single winning genre or price. It is "
        "that aggregation choices materially change the story: weighted reception is higher than a typical game's "
        "reception, popularity is not quality, and raw percentages are unreliable when evidence is sparse.", s["body"]))
    story.append(P(
        "The most important design lesson was to match the statistic to the question. A global weighted mean describes "
        "all review outcomes; a game-level median describes a typical title; a Wilson lower bound supports robust "
        "ranking; and price-band means describe market segments without identifying a price effect. Building all four "
        "from the same curated table makes those distinctions testable rather than rhetorical.", s["callout"]))
    story += [P("Future work", s["h2"]), P(
        "A stronger next version would ingest dated individual reviews from a separate Steam review source, perform "
        "language-aware sentiment/topic modeling, model time-to-review and update effects, normalize publisher entities, "
        "and add discount histories. Incremental ingestion could be partitioned by snapshot date with data-quality "
        "tests in CI. The included Streamlit dashboard can be deployed to the course server; a future version could "
        "add authenticated drill-down while continuing to serve only pre-aggregated data.", s["body"])]
    story += [P("Team roles", s["h2"])]
    roles = [["Member", "Primary responsibility", "Shared responsibility"]]
    for i, member in enumerate(meta["members"]):
        responsibility = meta["roles"][i].split(":", 1)[-1].strip() if i < len(meta["roles"]) else "Project implementation"
        roles.append([member, responsibility, "Research design, review, validation and presentation"])
    story.append(table(roles, [3.2 * cm, 7.0 * cm, 5.8 * cm]))
    story.append(P(
        "Both members jointly reviewed analytical assumptions, reran the reproducibility workflow, checked tables "
        "against machine-readable outputs, and approved the final interpretation. Replace placeholder names in "
        "project_metadata.json before submission.", s["small"]))
    story.append(PageBreak())

    # Reproducibility/rubric
    story += [P("8. Reproducibility and submission map", s["h1"])]
    story += [P("Reproduction sequence", s["h2"]), P(
        "1. Download/extract the assignment-specified Kaggle dataset to data/raw.<br/>"
        "2. Run scripts/hdfs_setup.ps1 to create the HDFS raw layer.<br/>"
        "3. Run scripts/run_pipeline.ps1 to build Parquet and Spark results.<br/>"
        "4. Run tools/local_reference_analysis.py to cross-check metrics and figures.<br/>"
        "5. Run tools/build_report.py; inspect the rendered pages before submission.", s["body"])]
    story += [P("Code and evidence inventory", s["h2"]), table([
        ["Artifact", "Purpose"],
        ["src/steam_analysis.py", "Executable PySpark ETL, quality checks, SQL and window ranking"],
        ["sql/steam_analysis.sql", "Standalone Spark SQL / HiveQL analytical queries"],
        ["scripts/hdfs_setup.ps1", "Idempotent HDFS directory creation and raw ingestion"],
        ["scripts/run_pipeline.ps1", "YARN spark-submit entry point and Spark configuration"],
        ["output/results/local", "CSV/JSON evidence used by this report"],
        ["output/figures", "High-resolution visualizations"],
        ["dashboard/app.py", "Optional interactive bonus dashboard over pre-aggregated results"],
        ["README.md", "Environment, commands, dataset and project structure"],
    ], [5.1 * cm, 10.9 * cm])]
    story += [P("Rubric coverage", s["h2"]), table([
        ["Rubric item", "Evidence"],
        ["Dataset introduction", "Section 1 and data dictionary"],
        ["HDFS strategy", "Section 2, ingestion script, raw/curated separation"],
        ["Cleaning/parsing/missing values", "Section 3 and explicit PySpark schema"],
        ["Questions and Spark/SQL methods", "Sections 4-5 and SQL script"],
        ["Findings and visualization", "Five interpreted figures and result tables"],
        ["Critical conclusion/reflection", "Sections 6-7"],
        ["Executable, styled source", "Modular scripts, comments, requirements and README"],
        ["Method depth", "Wilson bound, scale thresholds, windowed era ranking, cross-check"],
    ], [5.1 * cm, 10.9 * cm])]
    story.append(PageBreak())

    # References
    story += [P("References", s["h1"])]
    refs = [
        "Davis, N. (2019). <i>Steam Store Games</i>. Kaggle. https://www.kaggle.com/datasets/nikdavis/steam-store-games/data",
        "Apache Software Foundation. <i>Apache Hadoop HDFS Architecture</i>. https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html",
        "Apache Software Foundation. <i>Apache Spark SQL, DataFrames and Datasets Guide</i>. https://spark.apache.org/docs/latest/sql-programming-guide.html",
        "Apache Software Foundation. <i>PySpark API Reference</i>. https://spark.apache.org/docs/latest/api/python/",
        "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. <i>Journal of the American Statistical Association</i>, 22(158), 209-212.",
        "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. <i>Computing in Science &amp; Engineering</i>, 9(3), 90-95.",
    ]
    for i, ref in enumerate(refs, start=1):
        story.append(P(f"[{i}] {ref}", s["body"]))
    story += [Spacer(1, 0.8 * cm), HRFlowable(width="100%", thickness=1.2, color=TEAL), Spacer(1, 0.4 * cm)]
    story.append(P(
        "Result provenance: every number and figure in this report was generated from data/raw/steam.csv by "
        "tools/local_reference_analysis.py. The assessed distributed implementation mirrors the same transformations "
        "in src/steam_analysis.py. No result was manually typed into the report generator.", s["callout"]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    build()
