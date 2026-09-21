---
name: html-report-delivery
description: Browser HTML report files for readable tables.
version: 1.0.0
author: Hermes Agent
license: UNLICENSED
platforms: [windows]
metadata:
  hermes:
    tags: [Reporting, HTML, Telegram, Tables]
---

# HTML report delivery

Use this when Leo asks for tabular/report data to be shown as a human-readable HTML report, especially over Telegram.

## Procedure

1. **Render a real `.html` artifact, not inline HTML.** Telegram shows HTML snippets as message text, so write a complete HTML document to a local file and return it as `MEDIA:<absolute-path>`.
2. **Use a browser-oriented layout.** Include `<!DOCTYPE html>`, UTF-8 metadata, a title, CSS, summary cards, and styled tables. Avoid plain `border=1` tables unless the user explicitly asks for raw/simple markup.
3. **Regenerate from the source payload when adding columns.** If the user asks to add fields such as update time, rerun or retrieve the underlying report/job output instead of editing visible rows by hand, then render from structured data.
4. **For R&S chipset reports, include update metadata and release menus in the project table.** Show the chipset project name, category, chipset ID from GitLab project info/description, latest tag, pipeline/status, `committed_at` converted to Taipei time, author, and a compact per-cell release menu when release artifacts are available. For `rs-wmt-*` chipset repos, query `https://pypi.packages.rsint.net/artifactory/api/pypi/rs_common_components/simple/{repo-name}/`, parse both `.whl` and `.tar.gz` simple-index links, and render them inside a `<details><summary>...` menu in the corresponding row rather than expanding the table width with raw filenames.
5. **Default chipset reports to category-first ordering.** Sort rows by `category`, then project/repo name, unless Leo asks for a different primary sort; keep client-side clickable column sorting for exploration.
6. **Keep the response short.** Say what file was produced and name the important added field(s); do not paste the HTML source unless the user explicitly requests source code.
7. **For org/contact-map reports, keep the original report layout and improve only the graph area unless Leo asks otherwise.** Preferred graph treatment: Mermaid with `useMaxWidth:false`, a scrollable graph container, and zoom/reset controls. Do not replace the whole report with cards or a separate SVG when only the graph is hard to read.

## Pitfalls

- Do not answer a request for a “browser-viewable HTML table” with a Markdown code block or inline HTML; Telegram cannot render that as the page the user wants.
- Do not claim the attachment is a webpage if the message only contains literal markup; the deliverable is the `.html` file attached with `MEDIA:`.
- Do not use truncated CLI output as the data source for final tables when the job state or snapshot can be read back; truncation drops rows and fields.
- Do not list long artifact/version filenames directly in visible table cells; use an expandable menu (`details/summary` or equivalent) so the report stays readable.
