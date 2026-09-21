#!/usr/bin/env python
import argparse, csv, json, re, zipfile
from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception as exc:
    raise SystemExit("Missing dependency: pymupdf. Run with `uvx --from pymupdf python scripts/pdf_linked_markdown.py ...`") from exc


def clean_text(s: str) -> str:
    return re.sub(r"[ \t]+", " ", (s or "").replace("\r", "")).strip()


def md_table(rows):
    if not rows:
        return ""
    max_cols = max(len(r) for r in rows)
    normalized = []
    for r in rows:
        cells = [("" if c is None else clean_text(str(c))).replace("|", "\\|") for c in r]
        cells += [""] * (max_cols - len(cells))
        normalized.append(cells)
    out = ["| " + " | ".join(normalized[0]) + " |", "| " + " | ".join(["---"] * max_cols) + " |"]
    out.extend("| " + " | ".join(r) + " |" for r in normalized[1:])
    return "\n".join(out)


def bbox_str(bbox) -> str:
    return ", ".join(f"{x:.1f}" for x in bbox)


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9 _().-]+", "_", path.stem).strip() or "document"


def is_decorative_image(bbox, page_rect, clean: bool) -> bool:
    if not clean:
        return False
    x0, y0, x1, y1 = bbox
    width, height = x1 - x0, y1 - y0
    if y1 < 95 or y0 > page_rect.height - 70:
        return True
    if width < 28 or height < 18:
        return True
    return False


def is_noise_text(text, bbox, page_rect, clean: bool) -> bool:
    if not clean:
        return False
    t = clean_text(text)
    if not t:
        return True
    x0, y0, x1, y1 = bbox
    low = t.casefold()
    if y1 < 95 and any(k in low for k in ["company", "confidential", "rohde", "schwarz", "©"]):
        return True
    if y0 > page_rect.height - 70:
        return True
    if re.fullmatch(r"\d+\s*/\s*\d+", t):
        return True
    if t in {"COMPANY", "CONFIDENTIAL", "©"}:
        return True
    if t.startswith("Rohde & Schwarz GmbH") or t.startswith("Rohde & Schwarz Taiwan"):
        return True
    return False


def render_page(page, out_path: Path, clean: bool, crop_page_margins: bool, scale: float = 2.0):
    rect = page.rect
    clip = rect
    if clean and crop_page_margins:
        clip = fitz.Rect(rect.x0, rect.y0 + 95, rect.x1, rect.y1 - 70)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    pix.save(out_path)


def convert(pdf_path: Path, out_dir: Path, clean_mode: bool, make_zip: bool, crop_page_margins: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = out_dir / "assets"
    asset_dir.mkdir(exist_ok=True)
    stem = safe_stem(pdf_path)
    md_path = out_dir / f"{stem}_linked{'_clean' if clean_mode else ''}.md"
    manifest_path = out_dir / "manifest.json"
    zip_path = out_dir.with_suffix(".zip")

    formula_re = re.compile(r"(\b\d+\s*(?:kHz|MHz|GHz|ms|slots?)\b|2\^\{|[≤≥±Δμ αβ]|\b(?:Periodicity|Slot Offset|Resource Repetition Factor)\b.*\d|\{\s*\d+\s*,)", re.I)
    doc = fitz.open(pdf_path)
    manifest = {
        "source_pdf": str(pdf_path),
        "pages": doc.page_count,
        "clean": clean_mode,
        "crop_page_margins": crop_page_margins,
        "outputs": {"markdown": str(md_path), "assets": str(asset_dir)},
        "filtered_counts": {"images": 0, "text_blocks": 0, "formula_candidates": 0},
    }
    lines = [
        "---",
        f"title: {pdf_path.stem} linked extraction",
        "type: source",
        f"source_path: {pdf_path.as_posix()}",
        "conversion: pymupdf layout-linked extraction",
        "---",
        "",
        f"# {pdf_path.stem} — layout-linked Markdown",
        "",
        "> Text, tables, figures, and formula-like fragments include page/bbox anchors back to page images.",
        "> Original PDF remains the source of truth.",
        "",
        "## Quick navigation",
        "",
    ]
    lines.extend(f"- [Page {i}](#page-{i})" for i in range(1, doc.page_count + 1))
    lines.append("")

    for page_no, page in enumerate(doc, start=1):
        page_dir = asset_dir / f"page_{page_no:02d}"
        page_dir.mkdir(exist_ok=True)
        page_png = page_dir / f"page_{page_no:02d}.png"
        render_page(page, page_png, clean_mode, crop_page_margins)
        lines += [f"## Page {page_no}", f"<a id=\"page-{page_no}\"></a>", "", f"[Page image](assets/page_{page_no:02d}/page_{page_no:02d}.png)", ""]

        try:
            tables = page.find_tables()
            for table_no, table in enumerate(tables.tables, start=1):
                rows = table.extract()
                if not rows:
                    continue
                csv_path = page_dir / f"table_p{page_no:02d}_{table_no:02d}.csv"
                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    csv.writer(f).writerows(rows)
                lines += [
                    f"### Table P{page_no}-{table_no}",
                    f"<a id=\"table-p{page_no}-{table_no}\"></a>",
                    f"- bbox: `{bbox_str(table.bbox)}`",
                    f"- CSV: [table_p{page_no:02d}_{table_no:02d}.csv](assets/page_{page_no:02d}/table_p{page_no:02d}_{table_no:02d}.csv)",
                    "",
                    md_table(rows),
                    "",
                ]
        except Exception as exc:
            lines += [f"> Table extraction warning on page {page_no}: `{exc}`", ""]

        blocks = page.get_text("dict").get("blocks", [])
        image_no = 0
        formula_no = 0
        text_blocks = []
        for block in blocks:
            bbox = tuple(block.get("bbox", []))
            if block.get("type") == 1:
                if is_decorative_image(bbox, page.rect, clean_mode):
                    manifest["filtered_counts"]["images"] += 1
                    continue
                image_no += 1
                ext = block.get("ext", "png")
                img_path = page_dir / f"image_p{page_no:02d}_{image_no:02d}.{ext}"
                img_path.write_bytes(block.get("image", b""))
                lines += [
                    f"### Figure P{page_no}-{image_no}",
                    f"<a id=\"fig-p{page_no}-{image_no}\"></a>",
                    f"- bbox: `{bbox_str(bbox)}`",
                    f"![Figure P{page_no}-{image_no}](assets/page_{page_no:02d}/{img_path.name})",
                    "",
                ]
            elif block.get("type") == 0:
                block_lines = []
                for line in block.get("lines", []):
                    t = clean_text("".join(span.get("text", "") for span in line.get("spans", [])))
                    if t and not is_noise_text(t, bbox, page.rect, clean_mode):
                        block_lines.append(t)
                if not block_lines:
                    manifest["filtered_counts"]["text_blocks"] += 1
                    continue
                text_blocks.append((bbox, "\n".join(block_lines)))
                for line in block_lines:
                    if formula_re.search(line) and 8 <= len(line) < 220:
                        formula_no += 1
                        lines += [
                            f"### Formula/Symbol P{page_no}-{formula_no}",
                            f"<a id=\"eq-p{page_no}-{formula_no}\"></a>",
                            f"- bbox approx: `{bbox_str(bbox)}`",
                            f"- text: `{line}`",
                            f"- context: [page image](assets/page_{page_no:02d}/page_{page_no:02d}.png)",
                            "",
                        ]
        lines += [f"### Text blocks — Page {page_no}", ""]
        for idx, (bbox, text) in enumerate(text_blocks, start=1):
            lines += [f"<a id=\"text-p{page_no}-{idx}\"></a>", f"> bbox `{bbox_str(bbox)}`", "", text, ""]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"ok": True, "markdown": str(md_path), "assets": str(asset_dir), "manifest": str(manifest_path), "pages": doc.page_count, "filtered_counts": manifest["filtered_counts"]}
    if make_zip:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for path in [md_path, manifest_path] + [p for p in asset_dir.rglob("*") if p.is_file()]:
                z.write(path, path.relative_to(out_dir))
        result["zip"] = str(zip_path)
    return result


def main():
    ap = argparse.ArgumentParser(description="Convert PDF to layout-linked Markdown with assets.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--clean", action="store_true", help="filter logos, page marks, confidentiality labels, and decorative images")
    ap.add_argument("--crop-page-margins", action="store_true", help="crop page screenshots to remove top/bottom margins in clean mode")
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()
    print(json.dumps(convert(args.pdf, args.out_dir, args.clean, args.zip, args.crop_page_margins), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
