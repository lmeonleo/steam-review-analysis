from pathlib import Path

import pdfplumber


FILES = {
    "assignment": Path(r"C:\Users\hp\xwechat_files\wxid_owx3mootag1922_1a09\msg\file\2026-06\Big Data Final Evaluation Project.pdf"),
    "rubric": Path(r"C:\Users\hp\xwechat_files\wxid_owx3mootag1922_1a09\msg\file\2026-06\59cd56e2105365e4ed79da08df9c44f7.pdf"),
}

out_dir = Path("tmp/pdfs")
out_dir.mkdir(parents=True, exist_ok=True)

for label, path in FILES.items():
    pages = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            pages.append(f"\n===== PAGE {index} =====\n{text}\n")
    (out_dir / f"{label}.txt").write_text("".join(pages), encoding="utf-8")
    print(label, len(pages), "pages")
