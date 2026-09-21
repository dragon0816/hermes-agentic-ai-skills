---
name: pdf-linked-markdown
description: Convert PDFs into linked Markdown with assets.
version: 0.1.0
author: Leo Chi, Hermes Agent
license: UNLICENSED
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [pdf, markdown, knowledge-base, tables, images, equations]
    related_skills: [pdf]
---

# PDF Linked Markdown Skill

Convert a technical PDF into Markdown while preserving links from extracted text, tables, figures, and formula-like fragments back to page images and bounding boxes. Use this when a normal PDF-to-Markdown conversion loses the relationship between text, figures, math symbols, and tables.

## When to Use

- A PDF contains diagrams, tables, formulas, symbols, or slide-like layouts.
- The user wants Markdown for Obsidian/knowledge-base ingestion but still needs traceability to the PDF layout.
- The user wants logos, page numbers, confidentiality marks, or decorative images filtered out.

Do not use this as a perfect LaTeX/math OCR tool. For high-accuracy equations or scanned PDFs, run `marker-pdf` or OCR first.

## Prerequisites

- Python 3.10+.
- `pymupdf` available to the Python process. If not installed, run through `uvx`:
  `terminal(command="uvx --from pymupdf python <script> <input.pdf> --out-dir <output_dir> --zip")`

## How to Run

Use the bundled script:

```bash
python scripts/pdf_linked_markdown.py "input.pdf" --out-dir "out/pdf_linked" --clean --zip
```

If `pymupdf` is not installed in the active interpreter:

```bash
uvx --from pymupdf python scripts/pdf_linked_markdown.py "input.pdf" --out-dir "out/pdf_linked" --clean --zip
```

## Output

- `<title>_linked_clean.md` — Markdown with page/table/figure/formula anchors.
- `assets/page_##/page_##.png` — rendered page images for visual traceability.
- `assets/page_##/image_p##_NN.png` — extracted content figures.
- `assets/page_##/table_p##_NN.csv` — extracted tables.
- `manifest.json` — source path, page count, output paths, and filtered counts.
- Optional `.zip` package for transfer to another agent.

## Procedure

1. Inspect the PDF first with `pdf` skill or a quick PyMuPDF page count. Confirm it has a text layer; if most pages have no text, use OCR/marker instead.
2. Run `pdf_linked_markdown.py` with `--clean` for knowledge-base output. This filters top/bottom logos, page marks, standalone confidentiality labels, and tiny decorative images.
3. Open the Markdown with `read_file` and check page 1 for sensible tables/figures.
4. Verify package integrity: confirm every `assets/...` Markdown link exists and the zip contains `manifest.json`, the Markdown, and assets.

## Pitfalls

- The full page screenshot intentionally preserves the original PDF page. Even in `--clean` mode, page screenshots may still show logos/page numbers; only extracted figure/text blocks are filtered. Use `--crop-page-margins` if the page screenshots themselves must omit headers/footers.
- Table extraction is heuristic. Merged cells and borderless tables may need manual cleanup.
- Formula extraction is conservative. The script links formula-like text and symbol fragments to page/bbox context; it does not guarantee valid LaTeX.
- Never overwrite `raw/` source files unless the user explicitly asks. Prefer output under a temp or review folder first.

## Verification

- Markdown file exists and has non-zero size.
- `manifest.json` reports the expected page count.
- Link check returns zero missing `assets/...` links.
- The zip exists when `--zip` is requested.
